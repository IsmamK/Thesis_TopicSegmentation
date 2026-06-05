"""Generate qualitative case-study artifacts from final LECSEG diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_metric(row: dict, key: str) -> str:
    return f"{row[key]:.4f}" if key in row and isinstance(row[key], (int, float)) else "n/a"


def _case_block(title: str, row: dict, interpretation: str) -> list[str]:
    baseline = row["baseline"]
    current = row["current"]
    selector = row["selector"]
    return [
        f"## {title}\n",
        "\n",
        f"- Video: `{row['video_id']}` - {row['title']}\n",
        f"- Domain: {row['domain']}; chapters: {row['chapters']}\n",
        f"- Selector method: `{row['chosen_method']}` ({row['chosen_family']})\n",
        "\n",
        "| Method | Pk | WD | BS | F1@2 |\n",
        "|---|---:|---:|---:|---:|\n",
        f"| BGE-divisive baseline | {_fmt_metric(baseline, 'pk')} | {_fmt_metric(baseline, 'wd')} | {_fmt_metric(baseline, 'boundary_similarity')} | {_fmt_metric(baseline, 'f1_tol2')} |\n",
        f"| Cross-model conservative | {_fmt_metric(current, 'pk')} | {_fmt_metric(current, 'wd')} | {_fmt_metric(current, 'boundary_similarity')} | {_fmt_metric(current, 'f1_tol2')} |\n",
        f"| Balanced selector | {_fmt_metric(selector, 'pk')} | {_fmt_metric(selector, 'wd')} | {_fmt_metric(selector, 'boundary_similarity')} | {_fmt_metric(selector, 'f1_tol2')} |\n",
        "\n",
        f"Interpretation: {interpretation}\n",
        "\n",
    ]


def main() -> None:
    audit = _read_json(ROOT / "results" / "selector_choice_audit.json")
    domain = _read_json(ROOT / "results" / "domain_performance_analysis.json")
    portfolio = _read_json(ROOT / "results" / "method_portfolio_analysis.json")

    success = audit["best_vs_current"][0]
    failure = audit["worst_vs_current"][0]
    math_row = next(row for row in domain["rows"] if row["domain"] == "MATH")
    oracle = portfolio["per_video_oracle"]["metrics"]
    current = portfolio["best_global"]

    lines: list[str] = [
        "# Qualitative Case Studies\n",
        "\n",
        "Generated from `selector_choice_audit.json`, `domain_performance_analysis.json`, and `method_portfolio_analysis.json`.\n",
        "\n",
        "These cases are intended for thesis discussion and defense slides. They turn the metric table into concrete interpretation: where the selector helps, where it fails, and why the oracle gap matters.\n",
        "\n",
    ]
    lines.extend(
        _case_block(
            "Case 1 - Success: multimodal/cross-model evidence helps",
            success,
            "The selector substantially reduces Pk/WD relative to the cross-model method, showing that the method portfolio contains useful complementary evidence on some lectures.",
        )
    )
    lines.extend(
        _case_block(
            "Case 2 - Failure: selector over-switching hurts",
            failure,
            "The selector chooses an aggressive alternative that worsens Pk/WD. This is the core reason the thesis avoids claiming domain-general deployment.",
        )
    )
    lines.extend(
        [
            "## Case 3 - Domain weakness: Mathematics\n",
            "\n",
            "Mathematics is the clearest domain-level failure case.\n",
            "\n",
            "| Method | Pk | WD | F1@2 |\n",
            "|---|---:|---:|---:|\n",
            f"| BGE-divisive baseline | {math_row['baseline']['pk']:.4f} | {math_row['baseline']['wd']:.4f} | {math_row['baseline']['f1_tol2']:.4f} |\n",
            f"| Cross-model conservative | {math_row['current']['pk']:.4f} | {math_row['current']['wd']:.4f} | {math_row['current']['f1_tol2']:.4f} |\n",
            f"| Balanced selector | {math_row['selector']['pk']:.4f} | {math_row['selector']['wd']:.4f} | {math_row['selector']['f1_tol2']:.4f} |\n",
            "\n",
            "Interpretation: math lectures often preserve vocabulary across real topic changes and contain ASR-sensitive notation. The selector gains exact-boundary hits but hurts Pk/WD, so Math needs domain-specific transcript and notation handling.\n",
            "\n",
            "## Case 4 - Oracle gap: the next research problem\n",
            "\n",
            "| Method | Pk | WD | F1@2 |\n",
            "|---|---:|---:|---:|\n",
            f"| Best global cross-model | {current['pk']:.4f} | {current['wd']:.4f} | {current['f1_tol2']:.4f} |\n",
            f"| Per-video method oracle | {oracle['pk']:.4f} | {oracle['wd']:.4f} | {oracle['f1_tol2']:.4f} |\n",
            "\n",
            "Interpretation: the method pool often contains better choices than the deployable selector can identify. The strongest next contribution is therefore boundary/method selection, not another raw candidate generator.\n",
        ]
    )

    out = ROOT / "docs" / "CASE_STUDIES.md"
    out.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
