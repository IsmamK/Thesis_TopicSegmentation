"""Analyze whether existing LECSEG methods contain complementary wins.

This is a diagnostic script, not a deployable model. It aggregates per-video
metrics from existing evaluation JSON files and computes:

- the best single global method over the available portfolio;
- a leave-one-video-out global-method baseline;
- a per-video oracle that picks the best available method for each video.

The oracle result answers a research question: if the current method family
already contains good predictions on different videos, then future work should
focus on method selection. If the oracle is also weak, the boundary candidates
or scoring functions need to change.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = [
    ROOT / "results" / "eval_bgelarge_fine2.json",
    ROOT / "results" / "eval_alignment_sweep.json",
    ROOT / "results" / "eval_smoothing.json",
    ROOT / "results" / "eval_bgelarge_window_rank.json",
    ROOT / "results" / "eval_text_transition_ranker.json",
    ROOT / "results" / "eval_multimodal_fusion_search.json",
    ROOT / "results" / "eval_candidate_ranker.json",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_row(row: dict[str, Any]) -> dict[str, float] | None:
    if not isinstance(row, dict) or "pk" not in row or "wd" not in row:
        return None
    out: dict[str, float] = {}
    for key, value in row.items():
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            out[key] = float(value)
    if "f1_tol2" not in out:
        if "f1_t2" in out:
            out["f1_tol2"] = out["f1_t2"]
        elif "f1" in out:
            out["f1_tol2"] = out["f1"]
    return out


def _extract_per_video(path: Path) -> dict[str, dict[str, dict[str, float]]]:
    """Return {method_name: {video_id: metrics}} from supported eval schemas."""
    data = _read_json(path)
    extracted: dict[str, dict[str, dict[str, float]]] = {}

    if isinstance(data.get("results"), dict):
        for method, by_video in data["results"].items():
            if not isinstance(by_video, dict):
                continue
            rows = {}
            for video_id, metrics in by_video.items():
                row = _metric_row(metrics)
                if row is not None:
                    rows[str(video_id)] = row
            if rows:
                extracted[method] = rows

    return extracted


def _mean(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = sorted({key for row in rows for key in row})
    return {
        key: float(np.mean([row[key] for row in rows if key in row]))
        for key in keys
    }


def _score(row: dict[str, float], primary: str) -> tuple[float, float]:
    if primary == "pk":
        return (row.get("pk", 1.0), row.get("wd", 1.0))
    if primary == "wd":
        return (row.get("wd", 1.0), row.get("pk", 1.0))
    if primary == "balanced":
        return ((row.get("pk", 1.0) + row.get("wd", 1.0)) / 2.0, row.get("pk", 1.0))
    raise ValueError(f"Unknown primary metric: {primary}")


def _aggregate_portfolio(
    portfolio: dict[str, dict[str, dict[str, float]]],
    primary: str,
) -> dict[str, Any]:
    method_means: dict[str, dict[str, float]] = {}
    all_videos = sorted({vid for by_video in portfolio.values() for vid in by_video})

    for method, by_video in portfolio.items():
        rows = [by_video[vid] for vid in all_videos if vid in by_video]
        if rows:
            method_means[method] = _mean(rows)

    best_global_name, best_global = min(
        method_means.items(),
        key=lambda item: _score(item[1], primary),
    )

    oracle_rows = []
    oracle_choices = {}
    for video_id in all_videos:
        available = {
            method: by_video[video_id]
            for method, by_video in portfolio.items()
            if video_id in by_video
        }
        if not available:
            continue
        chosen_method, chosen_row = min(
            available.items(),
            key=lambda item: _score(item[1], primary),
        )
        oracle_choices[video_id] = chosen_method
        oracle_rows.append(chosen_row)

    loo_rows = []
    loo_choices = {}
    for holdout in all_videos:
        train_means = {}
        for method, by_video in portfolio.items():
            rows = [row for vid, row in by_video.items() if vid != holdout]
            if rows and holdout in by_video:
                train_means[method] = _mean(rows)
        if not train_means:
            continue
        chosen_method = min(train_means.items(), key=lambda item: _score(item[1], primary))[0]
        loo_choices[holdout] = chosen_method
        loo_rows.append(portfolio[chosen_method][holdout])

    top_methods = [
        {"name": method, **metrics}
        for method, metrics in sorted(method_means.items(), key=lambda item: _score(item[1], primary))[:25]
    ]

    return {
        "n_methods": len(method_means),
        "n_videos": len(all_videos),
        "primary": primary,
        "best_global": {"name": best_global_name, **best_global},
        "leave_one_out_global_selector": {
            "metrics": _mean(loo_rows),
            "choices": loo_choices,
        },
        "per_video_oracle": {
            "metrics": _mean(oracle_rows),
            "choices": oracle_choices,
        },
        "top_methods": top_methods,
    }


def run(input_paths: list[Path], primary: str) -> dict[str, Any]:
    portfolio: dict[str, dict[str, dict[str, float]]] = {}
    sources = {}

    for path in input_paths:
        if not path.exists():
            continue
        extracted = _extract_per_video(path)
        for method, by_video in extracted.items():
            # Prefix on collision to preserve both variants.
            name = method
            if name in portfolio:
                name = f"{path.stem}::{method}"
            portfolio[name] = by_video
            sources[name] = str(path.relative_to(ROOT))

    report = _aggregate_portfolio(portfolio, primary)
    report["meta"] = {
        "inputs": [str(p.relative_to(ROOT)) for p in input_paths if p.exists()],
        "sources": sources,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--primary", choices=("pk", "wd", "balanced"), default="pk")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "method_portfolio_analysis.json")
    args = parser.parse_args()

    report = run(args.inputs, args.primary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    best = report["best_global"]
    loo = report["leave_one_out_global_selector"]["metrics"]
    oracle = report["per_video_oracle"]["metrics"]
    print(f"Wrote {args.output}")
    print(
        "Best global: {name} Pk={pk:.4f} WD={wd:.4f} F1@2={f1_tol2:.4f}".format(
            **best
        )
    )
    print(
        "LOO selector: Pk={pk:.4f} WD={wd:.4f} F1@2={f1_tol2:.4f}".format(
            **loo
        )
    )
    print(
        "Per-video oracle: Pk={pk:.4f} WD={wd:.4f} F1@2={f1_tol2:.4f}".format(
            **oracle
        )
    )


if __name__ == "__main__":
    main()
