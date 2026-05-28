"""Visual progress dashboard. Run: python scripts/dashboard.py"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Missing dependency. Run: pip install pyyaml rich typer")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
    from rich import box
    from rich.text import Text
except ImportError:
    print("Missing dependency. Run: pip install pyyaml rich typer")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
PROG = ROOT / "progress.yaml"

STATUS_ICON = {
    "todo": "[ ]", "doing": "[~]", "in_progress": "[~]", "blocked": "[!]", "done": "[x]", "skipped": "[-]",
}
STATUS_COLOR = {
    "todo": "white", "doing": "yellow", "in_progress": "yellow", "blocked": "red",
    "done": "green", "skipped": "dim",
}


def load() -> dict:
    if not PROG.exists():
        print(f"progress.yaml not found at {PROG}")
        sys.exit(1)
    return yaml.safe_load(PROG.read_text(encoding="utf-8"))


def main() -> None:
    data = load()
    console = Console()

    total = len(data["tasks"])
    done = sum(1 for t in data["tasks"].values() if t["status"] == "done")
    doing = [tid for tid, t in data["tasks"].items() if t["status"] == "doing"]
    blocked = [tid for tid, t in data["tasks"].items() if t["status"] == "blocked"]

    # Header
    pct = int(100 * done / total)
    header = Text()
    header.append("LECSEG - ", style="bold cyan")
    header.append(f"Thesis {data['thesis_id']} | ", style="dim")
    header.append(f"{done}/{total} tasks complete ({pct}%)\n", style="bold")
    console.print(Panel(header, box=box.DOUBLE, border_style="cyan"))

    # Overall progress bar
    with Progress(
        TextColumn("[bold]Overall "),
        BarColumn(bar_width=50),
        MofNCompleteColumn(),
        TextColumn("  {task.percentage:>3.0f}%"),
        console=console, transient=False,
    ) as p:
        t = p.add_task("overall", total=total, completed=done)
        p.update(t, completed=done)

    console.print()

    # Phase-by-phase breakdown
    phase_table = Table(title="Phase progress", box=box.SIMPLE_HEAVY, show_lines=False)
    phase_table.add_column("#", style="cyan", width=3)
    phase_table.add_column("Phase", style="bold")
    phase_table.add_column("Progress", width=40)
    phase_table.add_column("Done", justify="right")

    for ph in data["phases"]:
        tids = ph["tasks"]
        d = sum(1 for tid in tids if data["tasks"][tid]["status"] == "done")
        n = len(tids)
        filled = int(30 * d / n) if n else 0
        bar = "#" * filled + "." * (30 - filled)
        color = "green" if d == n else "yellow" if d > 0 else "white"
        phase_table.add_row(
            str(ph["id"]), ph["name"], f"[{color}]{bar}[/{color}]", f"{d}/{n}",
        )
    console.print(phase_table)
    console.print()

    # Currently in-progress or blocked
    if doing or blocked:
        live_table = Table(title="In progress / blocked", box=box.ROUNDED)
        live_table.add_column("ID", style="cyan")
        live_table.add_column("Task", style="bold")
        live_table.add_column("Status")
        live_table.add_column("Owner")
        for tid in doing + blocked:
            t = data["tasks"][tid]
            status = t["status"]
            owner = t.get("owner") or "-"
            live_table.add_row(
                tid, t["title"],
                f"[{STATUS_COLOR[status]}]{STATUS_ICON[status]} {status}[/]",
                str(owner),
            )
        console.print(live_table)
        console.print()

    # Next actionable task
    next_task = next(
        (tid for tid, t in data["tasks"].items() if t["status"] == "todo"), None
    )
    if next_task:
        t = data["tasks"][next_task]
        console.print(Panel(
            f"[bold yellow]>> Next up:[/bold yellow] [cyan]{next_task}[/cyan] - {t['title']}\n"
            f"  Run: [bold]python scripts/next.py[/bold] to see the full instructions.",
            title="What should I do now?",
            border_style="yellow",
        ))
    else:
        console.print(Panel(
            "[bold green]Every task is complete. Time to defend.[/bold green]\n"
            "Run: [bold]python scripts/pre_defense_check.py[/bold] for the final checklist.",
            border_style="green",
        ))

    # Full task list (compact)
    console.print()
    console.print("[dim]All tasks (use `python scripts/show.py T<NN>` to read one):[/dim]")
    for ph in data["phases"]:
        line = Text()
        line.append(f"Phase {ph['id']} ", style="cyan")
        line.append(f"{ph['name']:<22} ", style="bold")
        for tid in ph["tasks"]:
            icon = STATUS_ICON[data["tasks"][tid]["status"]]
            line.append(f"{icon}{tid} ", style=STATUS_COLOR[data["tasks"][tid]["status"]])
        console.print(line)


if __name__ == "__main__":
    main()
