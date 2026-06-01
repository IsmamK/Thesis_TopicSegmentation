"""Leave-one-video-out method selector over existing LECSEG eval results.

This is a lightweight meta-model: for each held-out video, train regressors on
the remaining videos to predict each candidate method's Pk/WD from video-level
features and training-fold method statistics, then select the method predicted
to perform best.

It is designed to test whether the strong method-portfolio oracle can be
approached without using ground truth from the held-out video.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from method_portfolio_analysis import DEFAULT_INPUTS, _extract_per_video, _mean, _score  # noqa: E402


DOMAIN_ORDER = ("BIOLOGY", "CS", "MATH", "PHILOSOPHY", "PHYSICS")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest() -> dict[str, dict[str, Any]]:
    path = ROOT / "data" / "manifest.jsonl"
    rows = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            rows[str(obj.get("id"))] = obj
    return rows


def _load_video_features(video_id: str, manifest: dict[str, dict[str, Any]]) -> dict[str, float]:
    sent_path = ROOT / "data" / "sentences" / video_id / "sentences.json"
    gt_path = ROOT / "data" / "gt" / f"{video_id}.json"
    sentences = _read_json(sent_path).get("sentences", []) if sent_path.exists() else []
    gt = _read_json(gt_path) if gt_path.exists() else {}

    starts = np.array([float(s.get("start", 0.0)) for s in sentences], dtype=np.float64)
    ends = np.array([float(s.get("end", s.get("start", 0.0))) for s in sentences], dtype=np.float64)
    lengths = np.array([len(str(s.get("text", "")).split()) for s in sentences], dtype=np.float64)
    duration = float(max(ends) - min(starts)) if len(ends) else 0.0
    n_sent = len(sentences)
    n_bound = len(gt.get("boundaries_sec", []))
    manifest_row = manifest.get(video_id, {})
    domain = str(manifest_row.get("domain", "")).upper()
    domain_index = DOMAIN_ORDER.index(domain) if domain in DOMAIN_ORDER else -1

    features = {
        "n_sentences": float(n_sent),
        "log_n_sentences": float(math.log1p(n_sent)),
        "duration_min": duration / 60.0,
        "target_boundaries": float(n_bound),
        "boundary_density": n_bound / max(1.0, float(n_sent)),
        "mean_sentence_words": float(lengths.mean()) if len(lengths) else 0.0,
        "std_sentence_words": float(lengths.std()) if len(lengths) else 0.0,
        "domain_code": float(domain_index),
    }
    for name in DOMAIN_ORDER:
        features[f"domain_is_{name.lower()}"] = 1.0 if domain == name else 0.0
    return features


def _load_portfolio(input_paths: list[Path]) -> dict[str, dict[str, dict[str, float]]]:
    portfolio: dict[str, dict[str, dict[str, float]]] = {}
    for path in input_paths:
        if not path.exists():
            continue
        for method, by_video in _extract_per_video(path).items():
            name = method if method not in portfolio else f"{path.stem}::{method}"
            portfolio[name] = by_video
    return portfolio


def _candidate_methods(
    portfolio: dict[str, dict[str, dict[str, float]]],
    ranking_videos: list[str],
    top_k: int,
    primary: str,
) -> list[str]:
    means = {}
    min_coverage = max(3, int(round(len(ranking_videos) * 0.80)))
    for method, by_video in portfolio.items():
        rows = [by_video[v] for v in ranking_videos if v in by_video]
        if len(rows) >= min_coverage:
            means[method] = _mean(rows)
    return [m for m, _ in sorted(means.items(), key=lambda item: _score(item[1], primary))[:top_k]]


def _build_training_rows(
    portfolio: dict[str, dict[str, dict[str, float]]],
    methods: list[str],
    videos: list[str],
    video_features: dict[str, dict[str, float]],
    primary: str,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    feature_names = sorted(next(iter(video_features.values())).keys())
    method_train_means = {
        method: _mean([portfolio[method][v] for v in videos if v in portfolio[method]])
        for method in methods
    }

    rows = []
    y = []
    for method_index, method in enumerate(methods):
        for video_id in videos:
            if video_id not in portfolio[method]:
                continue
            vf = video_features[video_id]
            row = [vf[name] for name in feature_names]
            mean = method_train_means[method]
            row.extend([
                float(method_index) / max(1, len(methods) - 1),
                mean.get("pk", 1.0),
                mean.get("wd", 1.0),
                mean.get("f1_tol2", mean.get("f1_t2", mean.get("f1", 0.0))),
            ])
            rows.append(row)
            metric = portfolio[method][video_id]
            y.append(_score(metric, primary)[0])
    return np.asarray(rows, dtype=np.float64), np.asarray(y, dtype=np.float64), feature_names


def _predict_for_holdout(
    portfolio: dict[str, dict[str, dict[str, float]]],
    methods: list[str],
    train_videos: list[str],
    holdout: str,
    video_features: dict[str, dict[str, float]],
    primary: str,
    model_name: str,
) -> str:
    from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    x_train, y_train, feature_names = _build_training_rows(
        portfolio, methods, train_videos, video_features, primary
    )
    if model_name == "ridge":
        model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10.0))
    elif model_name == "rf":
        model = make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=17),
        )
    elif model_name == "extra":
        model = make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesRegressor(n_estimators=500, min_samples_leaf=3, random_state=17),
        )
    else:
        raise ValueError(model_name)
    model.fit(x_train, y_train)

    train_means = {
        method: _mean([portfolio[method][v] for v in train_videos if v in portfolio[method]])
        for method in methods
    }
    rows = []
    available = []
    for method_index, method in enumerate(methods):
        if holdout not in portfolio[method]:
            continue
        vf = video_features[holdout]
        row = [vf[name] for name in feature_names]
        mean = train_means[method]
        row.extend([
            float(method_index) / max(1, len(methods) - 1),
            mean.get("pk", 1.0),
            mean.get("wd", 1.0),
            mean.get("f1_tol2", mean.get("f1_t2", mean.get("f1", 0.0))),
        ])
        rows.append(row)
        available.append(method)
    pred = model.predict(np.asarray(rows, dtype=np.float64))
    return available[int(np.argmin(pred))]


def run(input_paths: list[Path], primary: str, top_k: int) -> dict[str, Any]:
    portfolio = _load_portfolio(input_paths)
    all_videos = sorted({video_id for by_video in portfolio.values() for video_id in by_video})
    report_methods = _candidate_methods(portfolio, all_videos, top_k, primary)
    manifest = _load_manifest()
    video_features = {video_id: _load_video_features(video_id, manifest) for video_id in all_videos}

    reports = {}
    for model_name in ("ridge", "rf", "extra"):
        choices = {}
        rows = []
        for holdout in all_videos:
            train_videos = [v for v in all_videos if v != holdout]
            methods = [
                method for method in _candidate_methods(portfolio, train_videos, top_k, primary)
                if holdout in portfolio.get(method, {})
            ]
            chosen = _predict_for_holdout(
                portfolio, methods, train_videos, holdout, video_features, primary, model_name
            )
            choices[holdout] = chosen
            rows.append(portfolio[chosen][holdout])
        reports[model_name] = {"metrics": _mean(rows), "choices": choices}

    method_means = {
        method: _mean([portfolio[method][v] for v in all_videos if v in portfolio[method]])
        for method in report_methods
    }
    best_method, best_metrics = min(method_means.items(), key=lambda item: _score(item[1], primary))

    return {
        "meta": {
            "primary": primary,
            "top_k": top_k,
            "n_videos": len(all_videos),
            "n_methods": len(report_methods),
            "method_pool_note": "Each held-out fold ranks top-k candidate methods using training videos only.",
            "reported_methods_full_data_preview": report_methods,
            "inputs": [str(p.relative_to(ROOT)) for p in input_paths if p.exists()],
        },
        "best_global_within_candidates": {"name": best_method, **best_metrics},
        "selectors": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--primary", choices=("pk", "wd", "balanced"), default="pk")
    parser.add_argument("--top-k", type=int, default=80)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "method_selector_experiment.json")
    args = parser.parse_args()

    report = run(args.inputs, args.primary, args.top_k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    best = report["best_global_within_candidates"]
    print("Best candidate global: {name} Pk={pk:.4f} WD={wd:.4f}".format(**best))
    for name, obj in report["selectors"].items():
        metrics = obj["metrics"]
        print(
            f"{name}: Pk={metrics['pk']:.4f} WD={metrics['wd']:.4f} "
            f"F1@2={metrics.get('f1_tol2', metrics.get('f1_t2', metrics.get('f1', 0.0))):.4f}"
        )


if __name__ == "__main__":
    main()
