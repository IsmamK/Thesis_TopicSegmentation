"""Generate a compute-efficiency table for final LECSEG methods."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


ROWS = [
    {
        "method": "TextTiling / C99",
        "training": "None",
        "main_cost": "CPU lexical similarity",
        "reported_time": "<1 min for full benchmark",
        "notes": "Classical lightweight baselines.",
    },
    {
        "method": "BGE-divisive baseline",
        "training": "None",
        "main_cost": "Cached sentence embeddings + divisive segmentation",
        "reported_time": "embedding cached; segmentation <1 min",
        "notes": "Stable local baseline.",
    },
    {
        "method": "Cross-model conservative",
        "training": "None",
        "main_cost": "Two cached embedding streams + agreement filter",
        "reported_time": "<1 min once embeddings exist",
        "notes": "Best single global method.",
    },
    {
        "method": "Balanced LOO selector",
        "training": "Small ExtraTrees meta-selector",
        "main_cost": "Existing result portfolio + video-level features",
        "reported_time": "~2 min per selector sweep on local CPU",
        "notes": "Best deployable mean Pk/WD operating point.",
    },
    {
        "method": "TreeSeg same-dataset adapter",
        "training": "None",
        "main_cost": "Local embeddings + TreeSeg split objective",
        "reported_time": "~49 sec for 30 videos, bge-large",
        "notes": "Same-dataset comparator; worse Pk/WD, better F1@2.",
    },
    {
        "method": "Local LLM verifier",
        "training": "None",
        "main_cost": "Ollama prompts over candidate shortlist",
        "reported_time": "cacheable; depends on shortlist size/model",
        "notes": "Diagnostic baseline/comparison, not promoted unless metrics improve.",
    },
    {
        "method": "High-resource chaptering systems",
        "training": "Large supervised/LLM training",
        "main_cost": "Thousands to hundreds of thousands of videos",
        "reported_time": "not locally reproduced",
        "notes": "Not directly comparable without same benchmark.",
    },
]


def main() -> None:
    md = ROOT / "docs" / "COMPUTE_EFFICIENCY.md"
    tex = ROOT / "thesis" / "tables" / "compute_efficiency.tex"
    lines = [
        "# Compute Efficiency\n",
        "\n",
        "This table supports a narrow efficiency claim: LECSEG is inexpensive and reproducible locally compared with high-resource chaptering systems. It does not prove external performance superiority.\n",
        "\n",
        "| Method | Training | Main cost | Observed/expected runtime | Notes |\n",
        "|---|---|---|---|---|\n",
    ]
    for row in ROWS:
        lines.append(
            f"| {row['method']} | {row['training']} | {row['main_cost']} | {row['reported_time']} | {row['notes']} |\n"
        )
    md.write_text("".join(lines), encoding="utf-8")

    tex_lines = [
        "\\begin{table}[t]\n",
        "  \\centering\n",
        "  \\caption{Compute-efficiency positioning. Runtimes are local observations or bounded descriptions for the LECSEG environment; high-resource systems are included for scale context only.}\n",
        "  \\label{tab:compute_efficiency}\n",
        "  \\small\n",
        "  \\resizebox{\\linewidth}{!}{%\n",
        "  \\begin{tabular}{llll}\n",
        "    \\toprule\n",
        "    Method & Training & Main cost & Interpretation \\\\\n",
        "    \\midrule\n",
    ]
    for row in ROWS:
        method = row["method"].replace("&", "\\&")
        training = row["training"].replace("&", "\\&")
        cost = row["main_cost"].replace("&", "\\&")
        notes = row["notes"].replace("&", "\\&")
        tex_lines.append(f"    {method} & {training} & {cost} & {notes} \\\\\n")
    tex_lines.extend(
        [
            "    \\bottomrule\n",
            "  \\end{tabular}%\n",
            "  }\n",
            "\\end{table}\n",
        ]
    )
    tex.write_text("".join(tex_lines), encoding="utf-8")

    json_out = ROOT / "results" / "compute_efficiency.json"
    json_out.write_text(json.dumps({"rows": ROWS}, indent=2), encoding="utf-8")
    print(f"Wrote {md}")
    print(f"Wrote {tex}")
    print(f"Wrote {json_out}")


if __name__ == "__main__":
    main()
