"""Show a specific task's instructions in the terminal.

Run: python scripts/show.py T05
"""
from __future__ import annotations
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/show.py T<NN>")
        sys.exit(1)
    tid = sys.argv[1].upper()
    matches = list((ROOT / "tasks").glob(f"{tid}_*.md"))
    if not matches:
        print(f"No task file for {tid}")
        sys.exit(1)
    Console().print(Markdown(matches[0].read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
