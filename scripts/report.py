"""
Generate a Markdown report from evaluation results.

Usage:
    python scripts/report.py results/eval.json
    python scripts/report.py results/eval.json --output reports/eval_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


METHOD_LABELS = {
    "texttiling":    "TextTiling (B1)",
    "c99":           "C99 (B2)",
    "cosine":        "CosineSeg (B3)",
    "kmeans":        "KMeansSeg (B4)",
    "bert_seg":      "BertSeg (B5)",
    "two_stage":     "**TwoStage** (N1+N2)",
    "two_stage_llm": "**TwoStage+LLM** (N1+N2+N4)",
    "hierarchical":  "**Hierarchical** (N1+N2+N3)",
}

METRICS = ["pk", "wd", "f1", "bs"]
LOWER_IS_BETTER = {"pk", "wd", "hwd"}


def _mean(vals):
    return sum(vals) / len(vals) if vals else float("nan")


def _aggregate(results: dict) -> dict[str, dict[str, float]]:
    agg = {}
    for method, vid_results in results.items():
        agg[method] = {}
        for m in METRICS:
            vals = [v[m] for v in vid_results.values() if isinstance(v, dict) and m in v]
            agg[method][m] = _mean(vals)
    return agg


def _improvement(novel: float, baseline: float, metric: str) -> str:
    if metric in LOWER_IS_BETTER:
        delta = baseline - novel
        pct = delta / baseline * 100 if baseline else 0
        arrow = "↓" if delta > 0 else "↑"
    else:
        delta = novel - baseline
        pct = delta / baseline * 100 if baseline else 0
        arrow = "↑" if delta > 0 else "↓"
    return f"{arrow}{abs(pct):.1f}%"


def generate_report(results: dict) -> str:
    agg = _aggregate(results)
    n_videos = len(next(iter(results.values()))) if results else 0
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# LECSEG Evaluation Report",
        f"*Generated: {now} — {n_videos} videos*",
        "",
        "## 1. Main Results",
        "",
    ]

    # Header
    header = "| Method | Pk ↓ | WD ↓ | F1 ↑ | BS ↑ |"
    sep    = "|--------|------|------|------|------|"
    lines += [header, sep]

    method_order = ["texttiling", "c99", "cosine", "kmeans", "bert_seg",
                    "two_stage", "two_stage_llm", "hierarchical"]

    best_vals = {}
    for m in METRICS:
        all_vals = [agg[meth][m] for meth in method_order if meth in agg and m in agg[meth]]
        if not all_vals:
            continue
        best_vals[m] = min(all_vals) if m in LOWER_IS_BETTER else max(all_vals)

    prev_novel = False
    for method in method_order:
        if method not in agg:
            continue
        is_novel = method in {"two_stage", "two_stage_llm", "hierarchical"}
        if is_novel and not prev_novel:
            lines.append("|---|---|---|---|---|")
        prev_novel = is_novel

        label = METHOD_LABELS.get(method, method)
        cells = [label]
        for m in METRICS:
            v = agg[method].get(m, float("nan"))
            if v != v:  # nan
                cells.append("—")
            else:
                s = f"{v:.3f}"
                if m in best_vals and abs(v - best_vals[m]) < 1e-6:
                    s = f"**{s}**"
                cells.append(s)
        lines.append("| " + " | ".join(cells) + " |")

    # Improvement summary
    lines += ["", "## 2. Improvement over Best Baseline (BertSeg)", ""]
    if "bert_seg" in agg and "two_stage" in agg:
        lines.append("| Metric | BertSeg | TwoStage | Δ |")
        lines.append("|--------|---------|----------|---|")
        for m in METRICS:
            b = agg["bert_seg"].get(m, float("nan"))
            n = agg["two_stage"].get(m, float("nan"))
            if b == b and n == n:
                imp = _improvement(n, b, m)
                lines.append(f"| {m.upper()} | {b:.3f} | {n:.3f} | {imp} |")

    # Per-video breakdown
    lines += ["", "## 3. Per-Video Results (TwoStage)", ""]
    if "two_stage" in results:
        vids = sorted(results["two_stage"].keys())
        lines.append("| Video | Pk | WD | F1 |")
        lines.append("|-------|----|----|-----|")
        for vid in vids:
            v = results["two_stage"][vid]
            if isinstance(v, dict):
                pk = f"{v.get('pk', float('nan')):.3f}"
                wd = f"{v.get('wd', float('nan')):.3f}"
                f1 = f"{v.get('f1', float('nan')):.3f}"
                lines.append(f"| {vid} | {pk} | {wd} | {f1} |")

    # Configuration
    lines += ["", "## 4. Configuration", ""]
    lines.append(f"- Videos: {n_videos}/30")
    lines.append(f"- Metrics: Pk, WD, F1 (tolerance-2), BS")
    lines.append(f"- Embedding model: see run_eval.py --model")
    lines.append(f"- Bootstrap CI n_iterations: 1000")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate Markdown report from eval results")
    parser.add_argument("results_json", help="Path to results JSON")
    parser.add_argument("--output", default=None, help="Output .md path (default: stdout)")
    args = parser.parse_args()

    results_path = Path(args.results_json)
    if not results_path.exists():
        print(f"Not found: {results_path}", file=sys.stderr)
        sys.exit(1)

    results = json.loads(results_path.read_text(encoding="utf-8"))
    report = generate_report(results)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        sys.stdout.write(report)


if __name__ == "__main__":
    main()
