"""
Print a plain-English explanation of what an output file means.

Usage:
    python scripts/interpret.py results/20261023_1430_baseline_tt/metrics.json

Recognizes common filenames (metrics.json, predictions.jsonl, *.csv, figures/*)
and prints what to look at and how to interpret it.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def interpret_metrics(p: Path) -> None:
    print(f"📊  Interpreting metrics file: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  Could not parse JSON: {e}")
        return

    print()
    print("Each key is a segmentation metric. Lower is better for Pk and WD; higher is better for F1.")
    print()
    explanations = {
        "pk": "Pk — probability that a random window of words crosses a wrongly-predicted boundary. Lower is better. <0.30 is strong.",
        "wd": "WindowDiff — like Pk but penalises over- and under-segmentation. Lower is better.",
        "bs": "Boundary Similarity — 1 = perfect, 0 = worst. Higher is better.",
        "f1": "Segment F1 with ±tolerance — 1 = perfect. Higher is better.",
        "hwd": "Hierarchical WindowDiff — weighted sum of chapter-level and subtopic-level WD. Lower is better.",
        "tol_f1": "Tolerance-F1 — boundary-match F1 with a ±N-second tolerance.",
    }
    for k, v in data.items():
        hint = explanations.get(k.lower(), "(no preset explanation — see docs/CONCEPTS.md#metrics)")
        print(f"  {k:>10} = {v}    → {hint}")


def interpret_predictions(p: Path) -> None:
    print(f"🔮  Interpreting predictions file: {p}")
    lines = p.read_text(encoding="utf-8").splitlines()
    print(f"  {len(lines)} prediction records. One per video.")
    if lines:
        first = json.loads(lines[0])
        print(f"  Example keys: {sorted(first.keys())[:10]}")
        print("  Each record usually has: video_id, pred_boundaries (list of seconds),")
        print("                          gt_boundaries, num_chapters, score.")
    print("  Compare pred_boundaries vs gt_boundaries to eyeball quality.")


def interpret_generic(p: Path) -> None:
    print(f"🗂️  File: {p}")
    if p.suffix == ".csv":
        head = p.read_text(encoding="utf-8").splitlines()[:5]
        print("  First 5 lines:")
        for line in head:
            print(f"    {line}")
        print("  Open it in a spreadsheet or `pandas.read_csv(...)` for details.")
    elif p.suffix in (".png", ".jpg", ".pdf"):
        print("  Open the file in an image viewer to inspect the figure.")
        print(f"  Path (absolute): {p.resolve()}")
    else:
        print("  (no preset interpretation — see docs/OUTPUT_INTERPRETATION.md)")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"Not found: {p}")
        sys.exit(1)
    name = p.name.lower()
    if name == "metrics.json":
        interpret_metrics(p)
    elif name == "predictions.jsonl":
        interpret_predictions(p)
    else:
        interpret_generic(p)
    print()
    print("More examples and help: docs/OUTPUT_INTERPRETATION.md")


if __name__ == "__main__":
    main()
