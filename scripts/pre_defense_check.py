"""
Final pre-defense checklist. Runs only when every task is done.

Run: python scripts/pre_defense_check.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

ROOT = Path(__file__).resolve().parent.parent


def check(path: str) -> bool:
    return (ROOT / path).exists()


CHECKS = [
    ("Thesis PDF", "thesis/main.pdf"),
    ("IEEE paper PDF", "paper/ieee.pdf"),
    ("Slides PDF", "slides/defense.pdf"),
    ("Poster PDF", "poster/poster.pdf"),
    ("Dataset release", "data/release/LECSEG-30/"),
    ("Bibliography", "thesis/bibliography/references.bib"),
    ("Novelty tracker", "docs/NOVELTY_TRACKER.md"),
    ("Literature matrix", "docs/LITERATURE_MATRIX.md"),
    ("Defense Q&A", "docs/DEFENSE_QA.md"),
    ("Results folder", "results/"),
    ("Makefile", "Makefile"),
    ("README", "README.md"),
]


def main() -> None:
    console = Console()
    data = yaml.safe_load((ROOT / "progress.yaml").read_text(encoding="utf-8"))
    tasks = data["tasks"]
    not_done = [tid for tid, t in tasks.items() if t["status"] not in ("done", "skipped")]

    console.print(Panel(
        "[bold cyan]🎓 LECSEG Pre-Defense Checklist[/]\n\nThe final wall between you and a great defense.",
        border_style="cyan", box=box.DOUBLE,
    ))

    # Task check
    console.print()
    if not_done:
        console.print(Panel(
            f"[red]{len(not_done)} task(s) not yet complete:[/] {', '.join(not_done)}\n"
            "Finish them before running the rest of this checklist.",
            title="❌ Incomplete tasks", border_style="red",
        ))
    else:
        console.print(Panel("[green]✅ All 47 tasks marked done.[/]", border_style="green"))

    # File check
    table = Table(title="Deliverable files", box=box.ROUNDED)
    table.add_column("Deliverable", style="bold")
    table.add_column("Path")
    table.add_column("Exists?", justify="center")
    all_ok = True
    for name, path in CHECKS:
        ok = check(path)
        table.add_row(name, path, "[green]✅[/]" if ok else "[red]❌[/]")
        if not ok:
            all_ok = False
    console.print()
    console.print(table)

    console.print()
    if all_ok and not not_done:
        console.print(Panel(
            "[bold green]YOU ARE READY.[/]\n\n"
            "Tomorrow:\n"
            "  1. Print poster (A1, matte).\n"
            "  2. USB backup of thesis/main.pdf, slides/defense.pdf, paper/ieee.pdf.\n"
            "  3. Run demo 1×, end to end.\n"
            "  4. Review docs/DEFENSE_QA.md.\n"
            "  5. Sleep 8 hours.",
            title="🎉 Defense-ready", border_style="green",
        ))
        sys.exit(0)
    else:
        console.print(Panel(
            "[yellow]Some items are missing. Fix them first.[/]\n"
            "Run this again once ready.",
            border_style="yellow",
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
