"""Summarise LECSEG selector operating points for thesis reporting.

The selector experiments produce different tradeoffs depending on whether the
training-fold method pool is ranked by Pk, WD, or a balanced Pk/WD score. This
script turns those result files into a compact, reproducible comparison table.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METRICS = ("pk", "wd", "boundary_similarity", "f1_tol2")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _metric(row: dict[str, Any], key: str) -> float:
    if key in row:
        return float(row[key])
    if key == "f1_tol2":
        return float(row.get("f1_t2", row.get("f1", 0.0)))
    return float(row.get(key, 0.0))


def _metrics(row: dict[str, Any]) -> dict[str, float]:
    return {key: _metric(row, key) for key in METRICS}


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
    )


def _selector_row(path: Path, label: str, role: str, selector_name: str = "extra") -> dict[str, Any]:
    data = _read(path)
    metrics = _metrics(data["selectors"][selector_name]["metrics"])
    return {
        "label": label,
        "source": str(path.relative_to(ROOT)),
        "role": role,
        "primary": data["meta"].get("primary", ""),
        **metrics,
    }


def _best_method_from_file(path: Path, metric: str, label: str, role: str, reverse: bool) -> dict[str, Any]:
    data = _read(path)
    methods = data["methods"]
    best_name, best = sorted(
        methods.items(),
        key=lambda item: _metric(item[1], metric),
        reverse=reverse,
    )[0]
    return {
        "label": label,
        "source": f"{path.relative_to(ROOT)}::{best_name}",
        "role": role,
        "primary": metric,
        **_metrics(best),
    }


def _is_better_or_equal(candidate: dict[str, Any], other: dict[str, Any]) -> bool:
    return (
        candidate["pk"] <= other["pk"]
        and candidate["wd"] <= other["wd"]
        and candidate["boundary_similarity"] >= other["boundary_similarity"]
        and candidate["f1_tol2"] >= other["f1_tol2"]
    )


def _strictly_better(candidate: dict[str, Any], other: dict[str, Any]) -> bool:
    return _is_better_or_equal(candidate, other) and any(
        candidate[key] != other[key] for key in METRICS
    )


def _dominance(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    dominated_by: dict[str, list[str]] = {}
    for row in rows:
        dominators = [
            other["label"]
            for other in rows
            if other is not row and _strictly_better(other, row)
        ]
        dominated_by[row["label"]] = dominators
    return dominated_by


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Operating point | Pk | WD | BS | F1@2 | Role |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {label} | {pk} | {wd} | {bs} | {f1} | {role} |".format(
                label=row["label"],
                pk=_fmt(row["pk"]),
                wd=_fmt(row["wd"]),
                bs=_fmt(row["boundary_similarity"]),
                f1=_fmt(row["f1_tol2"]),
                role=row["role"],
            )
        )
    return "\n".join(lines)


def _latex_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Selector and ranker operating points on LECSEG-30.}",
        r"\label{tab:selector_operating_points}",
        r"\begin{tabularx}{\linewidth}{lrrrrX}",
        r"\toprule",
        r"Operating point & Pk & WD & BS & F1@2 & Role \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    _latex_escape(row["label"]),
                    _fmt(row["pk"]),
                    _fmt(row["wd"]),
                    _fmt(row["boundary_similarity"]),
                    _fmt(row["f1_tol2"]),
                    _latex_escape(row["role"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    significance = _read(ROOT / "results" / "method_selector_significance.json")
    portfolio = _read(ROOT / "results" / "method_portfolio_analysis.json")

    rows = [
        {
            "label": "BGE-divisive baseline",
            "source": "results/method_selector_significance.json::summary.baseline",
            "role": "Stable implemented baseline",
            "primary": "baseline",
            **_metrics(significance["summary"]["baseline"]),
        },
        {
            "label": "Cross-model conservative",
            "source": "results/method_selector_significance.json::summary.current",
            "role": "Best single global Pk/WD method",
            "primary": "single_method",
            **_metrics(significance["summary"]["current"]),
        },
        _selector_row(
            ROOT / "results" / "method_selector_experiment_trainrank.json",
            "Pk-ranked selector",
            "Pk-optimised selector; weaker after stable feature fix",
        ),
        _selector_row(
            ROOT / "results" / "method_selector_experiment_trainrank_wd.json",
            "WD-ranked selector",
            "WD-optimised selector; useful robustness check",
        ),
        _selector_row(
            ROOT / "results" / "method_selector_experiment_trainrank_balanced.json",
            "Balanced selector",
            "Best reproducible selector operating point",
        ),
        _best_method_from_file(
            ROOT / "results" / "eval_text_transition_ranker.json",
            "f1_tol2",
            "Text-transition ranker",
            "Best strict boundary-hit operating point; hurts Pk/WD",
            reverse=True,
        ),
        {
            "label": "Per-video method oracle",
            "source": "results/method_portfolio_analysis.json::per_video_oracle",
            "role": "Diagnostic upper bound, not deployable",
            "primary": "oracle",
            **_metrics(portfolio["per_video_oracle"]["metrics"]),
        },
    ]

    dominance = _dominance(rows)
    best_balanced = min(rows, key=lambda row: (row["pk"] + row["wd"]) / 2.0)
    best_f1 = max(rows, key=lambda row: row["f1_tol2"])
    best_deployable = min(
        [row for row in rows if "oracle" not in row["primary"]],
        key=lambda row: (row["pk"] + row["wd"]) / 2.0,
    )

    return {
        "meta": {
            "n_operating_points": len(rows),
            "metrics": list(METRICS),
            "lower_better": ["pk", "wd"],
            "higher_better": ["boundary_similarity", "f1_tol2"],
        },
        "rows": rows,
        "dominance": dominance,
        "best_balanced_overall": best_balanced["label"],
        "best_balanced_deployable": best_deployable["label"],
        "best_boundary_hit": best_f1["label"],
    }


def write_docs(report: dict[str, Any], md_path: Path, tex_path: Path) -> None:
    rows = report["rows"]
    lines = [
        "# Selector Operating Points",
        "",
        "Generated by `python scripts/selector_operating_point_analysis.py`.",
        "",
        _markdown_table(rows),
        "",
        "## Interpretation",
        "",
        f"- Best deployable Pk/WD operating point: {report['best_balanced_deployable']}.",
        f"- Best strict boundary-hit operating point: {report['best_boundary_hit']}.",
        "- The per-video oracle remains diagnostic only because it uses held-out "
        "ground-truth outcomes to choose methods.",
        "- A row is dominated only if another row is no worse on Pk/WD and no worse "
        "on BS/F1@2, with at least one strict improvement.",
        "",
        "## Dominance",
        "",
    ]
    for row in rows:
        dominators = report["dominance"][row["label"]]
        if dominators:
            lines.append(f"- {row['label']}: dominated by {', '.join(dominators)}.")
        else:
            lines.append(f"- {row['label']}: not dominated among listed operating points.")
    lines.append("")

    md_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")
    tex_path.write_text(_latex_table(rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "selector_operating_point_analysis.json")
    parser.add_argument("--docs-output", type=Path, default=ROOT / "docs" / "SELECTOR_OPERATING_POINTS.md")
    parser.add_argument("--tex-output", type=Path, default=ROOT / "thesis" / "tables" / "selector_operating_points.tex")
    args = parser.parse_args()

    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_docs(report, args.docs_output, args.tex_output)

    best = next(row for row in report["rows"] if row["label"] == report["best_balanced_deployable"])
    print(f"Wrote {args.output}")
    print(f"Wrote {args.docs_output}")
    print(f"Wrote {args.tex_output}")
    print(
        "Best deployable: {label} Pk={pk:.4f} WD={wd:.4f} F1@2={f1_tol2:.4f}".format(
            **best
        )
    )


if __name__ == "__main__":
    main()
