"""
Regenerate docs/LITERATURE_MATRIX.md from every paper summary in papers_summary/.

Run: python scripts/build_literature_matrix.py
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS_DIR = ROOT / "papers_summary"
OUT = ROOT / "docs" / "LITERATURE_MATRIX.md"


def parse(md: str) -> dict:
    """Best-effort parser that pulls key fields from the fixed paper template."""
    out = {"title": "?", "authors": "?", "year": "?", "venue": "?", "key": "?",
           "problem": "?", "method": "?", "datasets": "?", "metrics": "?",
           "limitations": "?", "novelty": "?"}
    first = md.splitlines()[0] if md.strip() else ""
    m = re.match(r"^#\s+(.+)$", first)
    if m:
        out["title"] = m.group(1).strip()
    for key, rex in (
        ("authors", r"\*\*Authors:\*\*\s*(.+)"),
        ("year", r"\*\*Year:\*\*\s*(\d{4})"),
        ("venue", r"\*\*Venue:\*\*\s*(.+)"),
        ("key", r"\*\*Citation key:\*\*\s*`([^`]+)`"),
    ):
        m = re.search(rex, md)
        if m:
            out[key] = m.group(1).strip()
    return out


def main() -> None:
    if not PAPERS_DIR.exists():
        print(f"{PAPERS_DIR} does not exist. Run scripts/add_paper.py first.")
        return
    files = sorted(PAPERS_DIR.glob("*.md"))
    rows = []
    for f in files:
        info = parse(f.read_text(encoding="utf-8"))
        info["file"] = f.relative_to(ROOT).as_posix()
        rows.append(info)
    rows.sort(key=lambda r: (r["year"], r["title"]))

    lines = [
        "# 📚 Literature Review Matrix",
        "",
        "_Auto-generated from `papers_summary/`. Do not edit by hand._",
        "_Regenerate: `python scripts/build_literature_matrix.py`_",
        "",
        f"**Papers indexed: {len(rows)}**",
        "",
        "| Year | Paper | Venue | Summary | Addresses our novelty |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['year']} | [{r['title']}]({r['file']}) | {r['venue']} | "
            f"see file | {r['novelty']} |"
        )
    lines += [
        "",
        "## Gap Analysis",
        "",
        "_List 5–7 concrete gaps in the current literature. Each gap should map to one of our novelty claims N1–N7._",
        "",
        "- **Gap 1** (→ N1): …",
        "- **Gap 2** (→ N2): …",
        "- **Gap 3** (→ N3): …",
        "- **Gap 4** (→ N4): …",
        "- **Gap 5** (→ N5): …",
        "- **Gap 6** (→ N6): …",
        "- **Gap 7** (→ N7): …",
        "",
        "> Claude: regenerate the Gap Analysis by reading all rows above and writing precise, sourced gaps.",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Wrote {OUT.relative_to(ROOT).as_posix()} with {len(rows)} papers.")


if __name__ == "__main__":
    main()
