"""Bootstrap and paired-test analysis for the method-selector result."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from lecseg.eval.stats import bootstrap_ci, wilcoxon_test  # noqa: E402
from method_portfolio_analysis import DEFAULT_INPUTS, _extract_per_video  # noqa: E402


METRICS = ("pk", "wd", "boundary_similarity", "f1_tol2")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_portfolio(input_paths: list[Path]) -> dict[str, dict[str, dict[str, float]]]:
    portfolio: dict[str, dict[str, dict[str, float]]] = {}
    for path in input_paths:
        if not path.exists():
            continue
        for method, by_video in _extract_per_video(path).items():
            name = method if method not in portfolio else f"{path.stem}::{method}"
            portfolio[name] = by_video
    return portfolio


def _normalize_metric_keys(row: dict[str, float]) -> dict[str, float]:
    out = dict(row)
    if "f1_tol2" not in out:
        if "f1_t2" in out:
            out["f1_tol2"] = out["f1_t2"]
        elif "f1" in out:
            out["f1_tol2"] = out["f1"]
    return out


def _selector_results(
    portfolio: dict[str, dict[str, dict[str, float]]],
    selector_path: Path,
    selector_name: str,
) -> dict[str, dict[str, float]]:
    selector = _read_json(selector_path)
    choices = selector["selectors"][selector_name]["choices"]
    rows: dict[str, dict[str, float]] = {}
    for video_id, method in choices.items():
        rows[video_id] = _normalize_metric_keys(portfolio[method][video_id])
    return rows


def _summary(rows: dict[str, dict[str, float]]) -> dict[str, float]:
    return {
        metric: float(np.mean([row[metric] for row in rows.values() if metric in row]))
        for metric in METRICS
    }


def _compare(
    baseline: dict[str, dict[str, float]],
    novel: dict[str, dict[str, float]],
    n_bootstrap: int,
) -> dict[str, Any]:
    common = sorted(set(baseline) & set(novel))
    report: dict[str, Any] = {"n_videos": len(common), "metrics": {}}
    for metric in METRICS:
        base = [baseline[v][metric] for v in common if metric in baseline[v] and metric in novel[v]]
        new = [novel[v][metric] for v in common if metric in baseline[v] and metric in novel[v]]
        if not base:
            continue
        lower_better = metric in {"pk", "wd"}
        base_ci = bootstrap_ci(base, n_bootstrap=n_bootstrap)
        new_ci = bootstrap_ci(new, n_bootstrap=n_bootstrap)
        p = wilcoxon_test(base, new)
        delta = float(np.mean(new) - np.mean(base))
        if lower_better:
            wins = sum(1 for b, n in zip(base, new) if n < b)
        else:
            wins = sum(1 for b, n in zip(base, new) if n > b)
        report["metrics"][metric] = {
            "baseline_mean": round(float(np.mean(base)), 4),
            "baseline_ci": [base_ci[1], base_ci[2]],
            "novel_mean": round(float(np.mean(new)), 4),
            "novel_ci": [new_ci[1], new_ci[2]],
            "delta": round(delta, 4),
            "relative_delta_pct": round((delta / max(abs(float(np.mean(base))), 1e-12)) * 100, 2),
            "p_value": p,
            "significant": p < 0.05,
            "win_count": wins,
            "loss_count": len(base) - wins,
            "lower_better": lower_better,
        }
    return report


def run(args: argparse.Namespace) -> dict[str, Any]:
    selector_path = args.selector if args.selector.is_absolute() else ROOT / args.selector
    portfolio = _load_portfolio(args.inputs)
    selector = _selector_results(portfolio, selector_path, args.selector_name)
    current = {
        vid: _normalize_metric_keys(row)
        for vid, row in portfolio[args.current_method].items()
    }
    baseline = {
        vid: _normalize_metric_keys(row)
        for vid, row in portfolio[args.baseline_method].items()
    }
    report = {
        "meta": {
            "selector_file": str(selector_path.relative_to(ROOT)),
            "selector_name": args.selector_name,
            "current_method": args.current_method,
            "baseline_method": args.baseline_method,
            "n_bootstrap": args.n_bootstrap,
        },
        "summary": {
            "baseline": _summary(baseline),
            "current": _summary(current),
            "selector": _summary(selector),
        },
        "selector_vs_current": _compare(current, selector, args.n_bootstrap),
        "selector_vs_baseline": _compare(baseline, selector, args.n_bootstrap),
        "current_vs_baseline": _compare(baseline, current, args.n_bootstrap),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument(
        "--selector",
        type=Path,
        default=ROOT / "results" / "method_selector_experiment_trainrank_balanced.json",
    )
    parser.add_argument("--selector-name", default="extra")
    parser.add_argument("--current-method", default="cross_e5_frac70_minlen11__align_contains_before")
    parser.add_argument("--baseline-method", default="divisive")
    parser.add_argument("--n-bootstrap", type=int, default=5000)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "method_selector_significance.json")
    args = parser.parse_args()

    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {args.output}")
    for label, comparison in [
        ("selector_vs_current", report["selector_vs_current"]),
        ("selector_vs_baseline", report["selector_vs_baseline"]),
        ("current_vs_baseline", report["current_vs_baseline"]),
    ]:
        print(label)
        for metric, row in comparison["metrics"].items():
            print(
                f"  {metric}: delta={row['delta']:+.4f} "
                f"p={row['p_value']:.4f} wins={row['win_count']}/{comparison['n_videos']}"
            )


if __name__ == "__main__":
    main()
