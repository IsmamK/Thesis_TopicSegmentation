"""
STRIP INTERNAL before submission.

This script removes every file that references AI / Claude / prompt usage so that
the submitted project looks like a clean, hand-written artifact.

Run: python scripts/strip_internal.py --dry-run   (preview)
     python scripts/strip_internal.py --go        (actually delete)

Files removed:
  - internal/                       (the entire folder)
  - .claude/                         (Claude Code settings)
  - scripts/resume.py, context.py    (Claude-specific helpers)
  - scripts/add_paper.py             (references prompts)
  - Any file matching **/CLAUDE*
  - Any line in a .md file that mentions 'Claude' is flagged (not auto-edited)

ALWAYS review the diff afterwards and re-run `python scripts/today.py` to check
the project still functions for your team (even without Claude-specific scripts).
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REMOVE_FOLDERS = ["internal", ".claude"]
REMOVE_FILES = [
    "scripts/resume.py",
    "scripts/context.py",
    "scripts/add_paper.py",
    "scripts/strip_internal.py",   # last act — delete self
]
REMOVE_GLOBS = ["**/CLAUDE*.md", "**/CLAUDE*.MD", "**/*_claude_*.md"]
FLAG_GLOBS = ["**/*.md", "**/*.py", "**/*.tex"]


def main() -> None:
    dry = "--dry-run" in sys.argv or "--go" not in sys.argv

    removed = []
    flagged = []

    for f in REMOVE_FOLDERS:
        p = ROOT / f
        if p.exists():
            removed.append(str(p.relative_to(ROOT)))
            if not dry:
                shutil.rmtree(p, ignore_errors=True)

    for f in REMOVE_FILES:
        p = ROOT / f
        if p.exists():
            removed.append(str(p.relative_to(ROOT)))
            if not dry:
                p.unlink()

    for pat in REMOVE_GLOBS:
        for p in ROOT.glob(pat):
            if p.exists():
                removed.append(str(p.relative_to(ROOT)))
                if not dry:
                    p.unlink()

    for pat in FLAG_GLOBS:
        for p in ROOT.glob(pat):
            if ".venv" in p.parts or ".git" in p.parts or "internal" in p.parts:
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                lower = line.lower()
                if any(word in lower for word in ("claude", " ai ", "llm-generated", "prompt claude")):
                    flagged.append(f"{p.relative_to(ROOT)}:{i}  {line.strip()[:100]}")

    print("=== REMOVED ===" if not dry else "=== WOULD REMOVE (dry run) ===")
    for r in removed:
        print(f"  - {r}")
    print()
    print(f"=== FLAGGED for manual review ({len(flagged)} lines) ===")
    for f in flagged[:50]:
        print(f"  {f}")
    if len(flagged) > 50:
        print(f"  ... and {len(flagged) - 50} more")
    print()
    if dry:
        print("This was a DRY RUN. To actually delete, run with --go.")
    else:
        print("Done. Review the flagged lines manually and edit them.")


if __name__ == "__main__":
    main()
