"""Tell me exactly what to do right now. Run: python scripts/next.py"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    import yaml
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
except ImportError:
    print("Missing dependency. Run: pip install pyyaml rich typer")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    console = Console()
    data = yaml.safe_load((ROOT / "progress.yaml").read_text(encoding="utf-8"))

    # Find the first task that is not done/skipped
    next_id = None
    for tid, t in data["tasks"].items():
        if t["status"] in ("todo", "doing", "blocked"):
            next_id = tid
            break

    if next_id is None:
        console.print("[bold green]All tasks done. Run `python scripts/pre_defense_check.py`.[/]")
        return

    task = data["tasks"][next_id]
    task_file = ROOT / "tasks" / f"{next_id}_*.md"
    # find the actual file (has underscore-name suffix)
    matches = list((ROOT / "tasks").glob(f"{next_id}_*.md"))
    md_path = matches[0] if matches else None

    status_icon = {"todo": "⬜", "doing": "🟡", "blocked": "🟥"}[task["status"]]
    header = (
        f"[bold cyan]▶ {next_id}[/bold cyan]  {status_icon} "
        f"[bold]{task['title']}[/bold]\n"
        f"Owner: [yellow]{task.get('owner') or '— (claim it with: python scripts/claim.py ' + next_id + ' <yourname>)'}[/]\n"
        f"Phase {task['phase']}"
    )
    console.print(Panel(header, border_style="cyan"))

    if md_path and md_path.exists():
        console.print()
        console.print(f"[dim]Reading {md_path.relative_to(ROOT)}…[/dim]\n")
        console.print(Markdown(md_path.read_text(encoding="utf-8")))
    else:
        console.print(f"[yellow]Task file not found for {next_id}. "
                      f"Expected tasks/{next_id}_*.md[/]")

    console.print()
    console.print(Panel(
        f"[bold]When done:[/]   python scripts/mark_done.py {next_id}\n"
        f"[bold]If stuck:[/]   python scripts/mark_progress.py {next_id} blocked \"reason\"\n"
        f"[bold]For Claude:[/] python scripts/resume.py (copy the output)",
        title="Controls",
        border_style="dim",
    ))


if __name__ == "__main__":
    main()
