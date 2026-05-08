"""
Add a new paper to the literature review.

Usage:
    python scripts/add_paper.py <url-or-pdf-or-title>

It will:
  1. Create `papers_summary/<firstauthor>_<year>.md` from the fixed template.
  2. Print a prompt to give Claude so Claude fills it in.
  3. Print the command to regenerate the literature matrix.

You then:
  - run the Claude prompt
  - review the summary
  - run `python scripts/build_literature_matrix.py`
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "papers_summary"
TEMPLATE = ROOT / "internal" / "PROMPTS" / "paper_template.md"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = " ".join(sys.argv[1:])

    # Make a conservative stub filename. User can rename after Claude fills it.
    stub = "newpaper_TBD"
    out = PAPERS / f"{stub}.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    template_body = (
        TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists()
        else "# <Short Title>\n\n(fill with Claude)\n"
    )
    out.write_text(
        f"<!-- Source: {arg} -->\n\n{template_body}",
        encoding="utf-8",
    )
    print(f"✅ Created {out.relative_to(ROOT)}")
    print()
    print("=" * 70)
    print("Now open Claude Code and paste this prompt:")
    print("=" * 70)
    print()
    print(f"Please fill in {out.relative_to(ROOT).as_posix()} using the")
    print(f"paper template. The source is: {arg}.")
    print("Read internal/PROMPTS/paper_template.md for the 8-section structure.")
    print("Do not invent results: if unknown, write 'not reported in abstract'.")
    print("After filling it in, rename the file to")
    print("papers_summary/<firstauthor>_<year>.md (all lowercase).")
    print("Finally append a BibTeX entry to thesis/bibliography/references.bib.")
    print()
    print("=" * 70)
    print("After Claude is done, run: python scripts/build_literature_matrix.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
