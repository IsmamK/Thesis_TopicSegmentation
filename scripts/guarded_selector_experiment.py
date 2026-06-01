"""Risk-controlled leave-one-video-out method selector.

The earlier method-selector experiment always chooses the method with the best
predicted held-out score. That is useful diagnostically, but it can over-switch:
small prediction differences may trade away the stable Pk/WindowDiff behavior of
the conservative cross-model method.

This script adds a training-fold guard. For each held-out video, it tunes a
minimum predicted margin on the remaining videos only. At test time the selector
may switch away from the baseline method only when the predicted improvement is
at least that tuned margin; otherwise it falls back to the baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from method_portfolio_analysis import DEFAULT_INPUTS, _extract_per_video, _mean, _score  # noqa: E402
from method_selector_experiment import (  # noqa: E402
    _build_training_rows,
    _candidate_methods,
    _load_manifest,
    _load_video_features,
)


def _load_portfolio(input_paths: list[Path]) -> dict[str, dict[str, dict[str, float]]]:
    portfolio: dict[str, dict[str, dict[str, float]]] = {}
    for path in input_paths:
        if not path.exists():
            continue
        for method, by_video in _extract_per_video(path).items():
            name = method if method not in portfolio else f"{path.stem}::{method}"
            portfolio[name] = by_video
    return portfolio


def _model(model_name: str):
    from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if model_name == "ridge":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10.0))
    if model_name == "rf":
        return make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=17),
        )
    if model_name == "extra":
        return make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesRegressor(n_estimators=500, min_samples_leaf=3, random_state=17),
        )
    raise ValueError(model_name)


def _ensure_baseline(methods: list[str], baseline_method: str) -> list[str]:
    if baseline_method in methods:
        return methods
    return [baseline_method, *methods]


def _fit_predict_scores(
    portfolio: dict[str, dict[str, dict[str, float]]],
    methods: list[str],
    train_videos: list[str],
    target_video: str,
    video_features: dict[str, dict[str, float]],
    primary: str,
    model_name: str,
) -> dict[str, float]:
    x_train, y_train, feature_names = _build_training_rows(
        portfolio, methods, train_videos, video_features, primary
    )
    model = _model(model_name)
    model.fit(x_train, y_train)

    train_means = {
        method: _mean([portfolio[method][v] for v in train_videos if v in portfolio[method]])
        for method in methods
    }
    rows = []
    available = []
    for method_index, method in enumerate(methods):
        if target_video not in portfolio.get(method, {}):
            continue
        vf = video_features[target_video]
        row = [vf[name] for name in feature_names]
        mean = train_means[method]
        row.extend(
            [
                float(method_index) / max(1, len(methods) - 1),
                mean.get("pk", 1.0),
                mean.get("wd", 1.0),
                mean.get("f1_tol2", mean.get("f1_t2", mean.get("f1", 0.0))),
            ]
        )
        rows.append(row)
        available.append(method)
    predictions = model.predict(np.asarray(rows, dtype=np.float64))
    return {method: float(pred) for method, pred in zip(available, predictions)}


def _inner_cv_records(
    portfolio: dict[str, dict[str, dict[str, float]]],
    outer_train_videos: list[str],
    video_features: dict[str, dict[str, float]],
    primary: str,
    top_k: int,
    model_name: str,
    baseline_method: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for inner_holdout in outer_train_videos:
        inner_train = [v for v in outer_train_videos if v != inner_holdout]
        methods = [
            method
            for method in _candidate_methods(portfolio, inner_train, top_k, primary)
            if inner_holdout in portfolio.get(method, {})
        ]
        methods = _ensure_baseline(methods, baseline_method)
        methods = [method for method in methods if inner_holdout in portfolio.get(method, {})]
        if baseline_method not in methods:
            continue
        scores = _fit_predict_scores(
            portfolio, methods, inner_train, inner_holdout, video_features, primary, model_name
        )
        best_method = min(scores, key=scores.get)
        margin = scores[baseline_method] - scores[best_method]
        records.append(
            {
                "video_id": inner_holdout,
                "best_method": best_method,
                "margin": float(margin),
                "baseline_metric": portfolio[baseline_method][inner_holdout],
                "best_metric": portfolio[best_method][inner_holdout],
            }
        )
    return records


def _choose_margin_threshold(
    records: list[dict[str, Any]],
    primary: str,
    grid: list[float],
) -> float:
    if not records:
        return float("inf")
    ranked = []
    for threshold in grid:
        rows = [
            record["best_metric"] if record["margin"] >= threshold else record["baseline_metric"]
            for record in records
        ]
        metrics = _mean(rows)
        switch_count = sum(1 for record in records if record["margin"] >= threshold)
        ranked.append((threshold, _score(metrics, primary), switch_count))
    # Prefer fewer switches when primary scores tie to four decimals.
    threshold, _, _ = min(
        ranked,
        key=lambda item: (round(item[1][0], 4), round(item[1][1], 4), item[2]),
    )
    return float(threshold)


def run(
    input_paths: list[Path],
    primary: str,
    top_k: int,
    model_name: str,
    baseline_method: str,
) -> dict[str, Any]:
    portfolio = _load_portfolio(input_paths)
    if baseline_method not in portfolio:
        raise KeyError(f"Baseline method not found in portfolio: {baseline_method}")

    all_videos = sorted(set(portfolio[baseline_method]))
    manifest = _load_manifest()
    video_features = {video_id: _load_video_features(video_id, manifest) for video_id in all_videos}
    threshold_grid = [-0.01, -0.005, 0.0, 0.0025, 0.005, 0.01, 0.02, 0.04, 0.08, 0.12]

    choices: dict[str, str] = {}
    diagnostics: dict[str, dict[str, Any]] = {}
    selected_rows = []
    baseline_rows = []
    always_switch_rows = []

    for holdout in all_videos:
        outer_train = [v for v in all_videos if v != holdout]
        inner_records = _inner_cv_records(
            portfolio, outer_train, video_features, primary, top_k, model_name, baseline_method
        )
        threshold = _choose_margin_threshold(inner_records, primary, threshold_grid)

        methods = [
            method
            for method in _candidate_methods(portfolio, outer_train, top_k, primary)
            if holdout in portfolio.get(method, {})
        ]
        methods = _ensure_baseline(methods, baseline_method)
        methods = [method for method in methods if holdout in portfolio.get(method, {})]
        scores = _fit_predict_scores(
            portfolio, methods, outer_train, holdout, video_features, primary, model_name
        )
        best_method = min(scores, key=scores.get)
        margin = scores[baseline_method] - scores[best_method]
        chosen = best_method if margin >= threshold else baseline_method

        choices[holdout] = chosen
        selected_rows.append(portfolio[chosen][holdout])
        baseline_rows.append(portfolio[baseline_method][holdout])
        always_switch_rows.append(portfolio[best_method][holdout])
        diagnostics[holdout] = {
            "threshold": threshold,
            "margin": float(margin),
            "best_method": best_method,
            "chosen_method": chosen,
            "switched": chosen != baseline_method,
            "inner_switch_rate": float(np.mean([r["margin"] >= threshold for r in inner_records]))
            if inner_records
            else 0.0,
        }

    return {
        "meta": {
            "primary": primary,
            "top_k": top_k,
            "model": model_name,
            "baseline_method": baseline_method,
            "n_videos": len(all_videos),
            "threshold_grid": threshold_grid,
            "inputs": [str(p.relative_to(ROOT)) for p in input_paths if p.exists()],
        },
        "baseline": _mean(baseline_rows),
        "always_switch_selector": _mean(always_switch_rows),
        "guarded_selector": _mean(selected_rows),
        "choices": choices,
        "diagnostics": diagnostics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--primary", choices=("pk", "wd", "balanced"), default="pk")
    parser.add_argument("--top-k", type=int, default=80)
    parser.add_argument("--model", choices=("ridge", "rf", "extra"), default="extra")
    parser.add_argument("--baseline-method", default="cross_e5_frac70_minlen11__align_contains_before")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "guarded_selector_experiment.json",
    )
    args = parser.parse_args()

    report = run(args.inputs, args.primary, args.top_k, args.model, args.baseline_method)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {args.output}")
    for label in ("baseline", "always_switch_selector", "guarded_selector"):
        metrics = report[label]
        print(
            f"{label}: Pk={metrics['pk']:.4f} WD={metrics['wd']:.4f} "
            f"BS={metrics.get('boundary_similarity', metrics.get('bs', 0.0)):.4f} "
            f"F1@2={metrics.get('f1_tol2', metrics.get('f1_t2', metrics.get('f1', 0.0))):.4f}"
        )


if __name__ == "__main__":
    main()
