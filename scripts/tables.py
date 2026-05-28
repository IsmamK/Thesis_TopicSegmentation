"""
Generate LaTeX tables from evaluation results for the thesis.

Usage:
    python scripts/tables.py results/eval.json
    python scripts/tables.py results/eval.json --output tables/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


METHOD_LABELS = {
    "texttiling":   r"\textsc{TextTiling}",
    "c99":          r"\textsc{C99}",
    "cosine":       r"CosineSeg",
    "kmeans":       r"KMeansSeg",
    "bert_seg":     r"BertSeg",
    "two_stage":    r"\textbf{TwoStage} (ours)",
    "two_stage_llm": r"\textbf{TwoStage+LLM} (ours)",
    "hierarchical": r"\textbf{Hierarchical} (ours)",
}

METRIC_LABELS = {
    "pk":    r"$P_k \downarrow$",
    "wd":    r"$WD \downarrow$",
    "f1":    r"$F_1 \uparrow$",
    "bs":    r"$B_S \uparrow$",
    "hwd":   r"$H\text{-}WD \downarrow$",
}

LOWER_IS_BETTER = {"pk", "wd", "hwd"}


def _fmt(val: float, metric: str, bold: bool) -> str:
    s = f"{val:.3f}"
    if bold:
        s = r"\textbf{" + s + "}"
    return s


def _best_per_col(rows: list[dict], metrics: list[str]) -> dict[str, float]:
    best = {}
    for m in metrics:
        vals = [r[m] for r in rows if r.get(m) is not None]
        if not vals:
            continue
        best[m] = min(vals) if m in LOWER_IS_BETTER else max(vals)
    return best


def make_main_table(
    results: dict,
    metrics: list[str] | None = None,
    caption: str = "Segmentation results on the LECSEG-30 benchmark.",
    label: str = "tab:main_results",
) -> str:
    """Generate the main results LaTeX table."""
    if metrics is None:
        metrics = ["pk", "wd", "f1", "bs"]

    method_order = [
        "texttiling", "c99", "cosine", "kmeans", "bert_seg",
        "two_stage", "two_stage_llm", "hierarchical",
    ]

    # Aggregate per-method: mean across videos
    rows = []
    for method in method_order:
        if method not in results:
            continue
        method_results = results[method]
        row = {"method": method}
        for m in metrics:
            vals = [v[m] for v in method_results.values() if isinstance(v, dict) and m in v]
            row[m] = sum(vals) / len(vals) if vals else None
        rows.append(row)

    best = _best_per_col(rows, metrics)

    # Column spec: l + one c per metric
    col_spec = "l" + "r" * len(metrics)
    header_cells = ["Method"] + [METRIC_LABELS.get(m, m) for m in metrics]

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & ".join(header_cells) + r" \\",
        r"\midrule",
    ]

    prev_group = None
    for row in rows:
        method = row["method"]
        group = "novel" if method in {"two_stage", "two_stage_llm", "hierarchical"} else "baseline"
        if prev_group == "baseline" and group == "novel":
            lines.append(r"\midrule")
        prev_group = group

        label_str = METHOD_LABELS.get(method, method)
        cells = [label_str]
        for m in metrics:
            v = row.get(m)
            if v is None:
                cells.append("—")
            else:
                is_best = (best.get(m) is not None and abs(v - best[m]) < 1e-9)
                cells.append(_fmt(v, m, is_best))
        lines.append(" & ".join(cells) + r" \\")

    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def make_ablation_table(
    results: dict,
    caption: str = "Ablation study: contribution of each module.",
    label: str = "tab:ablation",
) -> str:
    """Generate ablation study table (N1, N2, N3, N4 combinations)."""
    ablation_methods = {
        "cosine":        (False, False, False, False),
        "two_stage":     (True,  True,  False, False),
        "hierarchical":  (True,  True,  True,  False),
        "two_stage_llm": (True,  True,  False, True),
    }
    metrics = ["pk", "wd", "f1"]

    rows = []
    for method, (n1, n2, n3, n4) in ablation_methods.items():
        if method not in results:
            continue
        method_results = results[method]
        row = {"method": method, "n1": n1, "n2": n2, "n3": n3, "n4": n4}
        for m in metrics:
            vals = [v[m] for v in method_results.values() if isinstance(v, dict) and m in v]
            row[m] = sum(vals) / len(vals) if vals else None
        rows.append(row)

    best = _best_per_col(rows, metrics)

    def tick(b: bool) -> str:
        return r"\checkmark" if b else "—"

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\begin{tabular}{lcccc" + "r" * len(metrics) + "}",
        r"\toprule",
        r"Method & N1 & N2 & N3 & N4 & "
        + " & ".join(METRIC_LABELS.get(m, m) for m in metrics) + r" \\",
        r"\midrule",
    ]

    for row in rows:
        method = row["method"]
        label_str = METHOD_LABELS.get(method, method)
        cells = [label_str, tick(row["n1"]), tick(row["n2"]), tick(row["n3"]), tick(row["n4"])]
        for m in metrics:
            v = row.get(m)
            if v is None:
                cells.append("—")
            else:
                is_best = (best.get(m) is not None and abs(v - best[m]) < 1e-9)
                cells.append(_fmt(v, m, is_best))
        lines.append(" & ".join(cells) + r" \\")

    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate LaTeX tables from eval results")
    parser.add_argument("results_json", help="Path to results JSON (from run_eval.py)")
    parser.add_argument("--output", default=None, help="Output directory (default: print to stdout)")
    args = parser.parse_args()

    results_path = Path(args.results_json)
    if not results_path.exists():
        print(f"Results file not found: {results_path}", file=sys.stderr)
        sys.exit(1)

    results = json.loads(results_path.read_text(encoding="utf-8"))

    main_table = make_main_table(results)
    ablation_table = make_ablation_table(results)

    if args.output:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "table_main.tex").write_text(main_table, encoding="utf-8")
        (out_dir / "table_ablation.tex").write_text(ablation_table, encoding="utf-8")
        print(f"Tables written to {out_dir}/")
    else:
        print("% ── Main Results Table ─────────────────────────────")
        print(main_table)
        print()
        print("% ── Ablation Table ─────────────────────────────────")
        print(ablation_table)


if __name__ == "__main__":
    main()
