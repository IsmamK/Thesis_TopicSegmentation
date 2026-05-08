"""
After a task that produced a figure, table, or number, ask Claude to merge it
into the thesis chapter. Prints a ready-to-paste prompt.

Run: python scripts/update_thesis.py T29

Output: a Claude prompt that tells it exactly which chapter section to update
and which results file to read.
"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent

TASK_TO_CHAPTER = {
    # Phase 2: Literature
    "T06": "thesis/chapters/chapter2_literature.tex",
    "T07": "thesis/chapters/chapter2_literature.tex",
    "T08": "thesis/chapters/chapter2_literature.tex",
    # Phase 3: Dataset (→ Chapter 3 methodology + Chapter 4 dataset description)
    "T09": "thesis/chapters/chapter3_methodology.tex",
    "T10": "thesis/chapters/chapter3_methodology.tex",
    "T11": "thesis/chapters/chapter3_methodology.tex",
    "T12": "thesis/chapters/chapter3_methodology.tex",
    "T13": "thesis/chapters/chapter3_methodology.tex",
    # Phase 4–7: Methodology
    "T14": "thesis/chapters/chapter3_methodology.tex",
    "T15": "thesis/chapters/chapter3_methodology.tex",
    "T16": "thesis/chapters/chapter3_methodology.tex",
    "T17": "thesis/chapters/chapter3_methodology.tex",
    "T18": "thesis/chapters/chapter3_methodology.tex",
    "T19": "thesis/chapters/chapter3_methodology.tex",
    "T20": "thesis/chapters/chapter3_methodology.tex",
    "T21": "thesis/chapters/chapter3_methodology.tex",
    "T22": "thesis/chapters/chapter3_methodology.tex",
    "T23": "thesis/chapters/chapter4_results.tex",
    "T24": "thesis/chapters/chapter4_results.tex",
    "T25": "thesis/chapters/chapter3_methodology.tex",
    "T26": "thesis/chapters/chapter3_methodology.tex",
    "T27": "thesis/chapters/chapter3_methodology.tex",
    "T28": "thesis/chapters/chapter3_methodology.tex",
    # Phase 8: Evaluation
    "T29": "thesis/chapters/chapter4_results.tex",
    "T30": "thesis/chapters/chapter4_results.tex",
    "T31": "thesis/chapters/chapter4_results.tex",
}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/update_thesis.py T<NN>")
        sys.exit(1)
    tid = sys.argv[1].upper()
    data = yaml.safe_load((ROOT / "progress.yaml").read_text(encoding="utf-8"))
    if tid not in data["tasks"]:
        print(f"Unknown task {tid}")
        sys.exit(1)
    t = data["tasks"][tid]
    chapter = TASK_TO_CHAPTER.get(tid, "(no chapter mapped — update TASK_TO_CHAPTER in this script)")

    print("=" * 72)
    print(f"Prompt to paste into Claude after finishing {tid} — {t['title']}")
    print("=" * 72)
    print()
    print(f"{tid} is complete. Merge its results into the thesis.")
    print()
    print(f"1. Read results/ for the latest run produced by {tid}.")
    print(f"2. Open the chapter file: {chapter}")
    print(f"3. Find the section/subsection that corresponds to {tid}.")
    print("4. Fill in the paragraph with:")
    print("   - the exact metric values (formatted to 3 decimal places with 95% CI)")
    print("   - a reference to the table/figure number produced")
    print("   - a sentence on why the number is meaningful (compared to baselines)")
    print("5. If a new figure exists, copy it into thesis/figures/ and reference it with \\includegraphics.")
    print("6. Do NOT invent numbers — if the result is missing, write \\TODO{...} and stop.")
    print("7. After editing, `cd thesis && pdflatex main.tex` to verify compilation.")
    print()
    print("Rules:")
    print(" - Voice: passive / we. No mention of AI.")
    print(" - Every new number goes into both the chapter prose and results/table_*.csv.")
    print(" - Cite every compared method from references.bib by BibTeX key.")


if __name__ == "__main__":
    main()
