"""Generate thesis-ready result tables from current authoritative JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
    )


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _latex_table(
    headers: list[str],
    rows: list[list[str]],
    caption: str,
    label: str,
    col_spec: str | None = None,
) -> str:
    if col_spec is None:
        col_spec = "l" + "".join("r" if i < len(headers) - 1 else "l" for i in range(1, len(headers)))
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & ".join(_latex_escape(h) for h in headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(_latex_escape(cell) for cell in row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def _latex_table_with_flexible_last_column(
    headers: list[str],
    rows: list[list[str]],
    caption: str,
    label: str,
    numeric_cols: int,
) -> str:
    """Generate a table using tabularx for long explanatory final columns."""
    col_spec = "l" + ("r" * numeric_cols) + ("l" * max(0, len(headers) - numeric_cols - 2)) + "X"
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        rf"\begin{{tabularx}}{{\linewidth}}{{{col_spec}}}",
        r"\toprule",
        " & ".join(_latex_escape(h) for h in headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(_latex_escape(cell) for cell in row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])
    return "\n".join(lines)


def build_tables() -> dict[str, dict[str, str]]:
    significance = _read(ROOT / "results" / "method_selector_significance.json")
    portfolio = _read(ROOT / "results" / "method_portfolio_analysis.json")

    summary = significance["summary"]
    main_rows = [
        [
            "BGE-divisive baseline",
            _fmt(summary["baseline"]["pk"]),
            _fmt(summary["baseline"]["wd"]),
            _fmt(summary["baseline"]["boundary_similarity"]),
            _fmt(summary["baseline"]["f1_tol2"]),
            "Strong implemented baseline",
        ],
        [
            "Cross-model conservative",
            _fmt(summary["current"]["pk"]),
            _fmt(summary["current"]["wd"]),
            _fmt(summary["current"]["boundary_similarity"]),
            _fmt(summary["current"]["f1_tol2"]),
            "Best statistically supported Pk/WD result",
        ],
        [
            "LOO ExtraTrees method selector",
            _fmt(summary["selector"]["pk"]),
            _fmt(summary["selector"]["wd"]),
            _fmt(summary["selector"]["boundary_similarity"]),
            _fmt(summary["selector"]["f1_tol2"]),
            "Stable balanced selector; significant Pk/WD gain vs baseline",
        ],
        [
            "Per-video method oracle",
            _fmt(portfolio["per_video_oracle"]["metrics"]["pk"]),
            _fmt(portfolio["per_video_oracle"]["metrics"]["wd"]),
            _fmt(portfolio["per_video_oracle"]["metrics"]["boundary_similarity"]),
            _fmt(portfolio["per_video_oracle"]["metrics"]["f1_tol2"]),
            "Diagnostic upper bound, not deployable",
        ],
    ]
    main_headers = ["Method", "Pk", "WD", "BS", "F1@2", "Role"]

    sig_rows = []
    for comparison_name, label in [
        ("current_vs_baseline", "Cross-model vs BGE baseline"),
        ("selector_vs_current", "Selector vs cross-model"),
        ("selector_vs_baseline", "Selector vs BGE baseline"),
    ]:
        comparison = significance[comparison_name]
        for metric in ("pk", "wd", "boundary_similarity", "f1_tol2"):
            row = comparison["metrics"][metric]
            sig_rows.append(
                [
                    label,
                    metric,
                    _fmt(row["delta"]),
                    _fmt(row["p_value"]),
                    "yes" if row["significant"] else "no",
                    f"{row['win_count']}/{comparison['n_videos']}",
                ]
            )
    sig_headers = ["Comparison", "Metric", "Delta", "p", "Significant", "Wins"]

    external_rows = [
        ["LECSEG-30", "30", "32.52 h", "Pk/WD/BS/F1@2", "Low-resource reproducible lecture benchmark"],
        ["TreeSeg TinyRec", "21", "not directly matched", "Pk/WD", "Closest small transcript comparator"],
        ["Videoaula", "34", "not directly matched", "F1 / hierarchy metrics", "Lecture corpus in multilingual ToC work"],
        ["LectureDE", "96", "not directly matched", "F1 / hierarchy metrics", "German lecture corpus"],
        ["AVLectures", "2,350+", "large STEM lecture resource", "task-specific", "Large multimodal lecture resource"],
        ["Chapter-Gen", "9,631", "user-generated videos", "AP/Recall@seconds/ROUGE", "Supervised multimodal chapter generation"],
        ["MiniSeg/YTSEG", "19,299", "6,533 h", "Pk/BS/F1", "Large supervised YouTube transcript benchmark"],
        ["VidChapters-7M", "817,000", "7M chapters", "SODA/localization/captioning", "Large-scale video chaptering benchmark"],
    ]
    external_headers = ["Work", "Videos", "Scale", "Metrics", "Positioning"]

    tables = {
        "main_results": {
            "markdown": _markdown_table(main_headers, main_rows),
            "latex": _latex_table_with_flexible_last_column(
                main_headers,
                main_rows,
                "Current LECSEG result variants and diagnostic upper bound.",
                "tab:lecseg_result_variants",
                numeric_cols=4,
            ),
        },
        "significance": {
            "markdown": _markdown_table(sig_headers, sig_rows),
            "latex": _latex_table(
                sig_headers,
                sig_rows,
                "Paired Wilcoxon significance tests for key LECSEG comparisons.",
                "tab:lecseg_significance",
                col_spec=r"p{0.30\linewidth}lrrlp{0.09\linewidth}",
            ),
        },
        "external_scale": {
            "markdown": _markdown_table(external_headers, external_rows),
            "latex": _latex_table_with_flexible_last_column(
                external_headers,
                external_rows,
                "Video-count scale comparison for related lecture/video chaptering work.",
                "tab:external_scale",
                numeric_cols=1,
            ),
        },
    }
    return tables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-output", type=Path, default=ROOT / "docs" / "THESIS_RESULT_TABLES.md")
    parser.add_argument("--tex-output-dir", type=Path, default=ROOT / "thesis" / "tables")
    args = parser.parse_args()

    tables = build_tables()
    args.tex_output_dir.mkdir(parents=True, exist_ok=True)

    doc_lines = [
        "# Thesis Result Tables",
        "",
        "Generated from current result JSON files. Do not edit numbers manually; rerun",
        "`python scripts/generate_thesis_result_tables.py` after changing results.",
        "",
    ]
    for name, table in tables.items():
        doc_lines.extend([f"## {name.replace('_', ' ').title()}", "", table["markdown"], ""])
        (args.tex_output_dir / f"{name}.tex").write_text(table["latex"], encoding="utf-8")

    args.docs_output.write_text("\n".join(doc_lines), encoding="utf-8")
    print(f"Wrote {args.docs_output}")
    print(f"Wrote LaTeX tables to {args.tex_output_dir}")


if __name__ == "__main__":
    main()
