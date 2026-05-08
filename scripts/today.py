"""
👋 The ONE command you run every day.

Run: python scripts/today.py

Shows you:
  1. Where you are in the project (visual progress bar)
  2. Exactly what to do now (the next task + prompt to give Claude)
  3. How to give Claude context so it knows what we've been doing
  4. The concept learning link for today's topic
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime

import io
import os

# Fix Windows console Unicode (emojis, box-drawing chars)
if sys.platform == "win32":
    import io, os
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass

try:
    import yaml
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
    from rich import box
    from rich.text import Text
    from rich.columns import Columns
except ImportError:
    print("Missing dependency. In your activated venv, run: pip install pyyaml rich typer")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
PROG = ROOT / "progress.yaml"

ICON = {"todo": "⬜", "doing": "🟡", "blocked": "🟥", "done": "✅", "skipped": "⏭️"}
COLOR = {"todo": "white", "doing": "yellow", "blocked": "red", "done": "green", "skipped": "dim"}


def load():
    return yaml.safe_load(PROG.read_text(encoding="utf-8"))


def fat_bar(done: int, total: int, width: int = 50) -> str:
    filled = int(width * done / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def find_next(tasks):
    """Find the first task that is 'doing', otherwise the first 'todo'."""
    doing = next((tid for tid, t in tasks.items() if t["status"] == "doing"), None)
    if doing:
        return doing, "resume"
    todo = next((tid for tid, t in tasks.items() if t["status"] == "todo"), None)
    if todo:
        return todo, "start"
    return None, None


def main() -> None:
    data = load()
    console = Console(force_terminal=True)
    tasks = data["tasks"]

    total = len(tasks)
    done = sum(1 for t in tasks.values() if t["status"] == "done")
    pct = int(100 * done / total)

    # 1) Banner
    header = Text()
    header.append("👋 LECSEG — Daily Startup\n", style="bold cyan")
    header.append(f"Today is {datetime.now().strftime('%A, %d %B %Y')}\n", style="dim")
    header.append(f"Thesis {data['thesis_id']} · BracU CSE400\n")
    header.append(f"Progress: {done}/{total} tasks ({pct}%)", style="bold green" if pct > 0 else "bold")
    console.print(Panel(header, box=box.DOUBLE, border_style="cyan"))

    # 2) Visual progress bar
    console.print()
    console.print("[bold]Overall progress[/]")
    console.print(f"  [green]{fat_bar(done, total, 50)}[/green]  {done}/{total} ({pct}%)")
    console.print()

    # 3) Phase-by-phase
    phase_table = Table(title="Phase progress", box=box.SIMPLE_HEAVY)
    phase_table.add_column("#", style="cyan", width=3)
    phase_table.add_column("Phase", style="bold")
    phase_table.add_column("Progress", width=35)
    phase_table.add_column("Done", justify="right")
    phase_table.add_column("Status", justify="center")
    for ph in data["phases"]:
        tids = ph["tasks"]
        d = sum(1 for tid in tids if tasks[tid]["status"] == "done")
        n = len(tids)
        bar_color = "green" if d == n else ("yellow" if d > 0 else "white")
        status_icon = "✅" if d == n else ("🟡" if d > 0 else "⬜")
        phase_table.add_row(
            str(ph["id"]), ph["name"],
            f"[{bar_color}]{fat_bar(d, n, 25)}[/{bar_color}]",
            f"{d}/{n}", status_icon,
        )
    console.print(phase_table)
    console.print()

    # 4) What to do now
    next_id, action = find_next(tasks)
    if next_id is None:
        console.print(Panel(
            "[bold green]🎉 ALL 47 TASKS COMPLETE.[/]\n\n"
            "Run [bold]python scripts/pre_defense_check.py[/] for the final checklist.",
            title="✅ Done",
            border_style="green",
        ))
        return

    t = tasks[next_id]
    owner = t.get("owner") or "(unclaimed)"
    phase_name = next((ph["name"] for ph in data["phases"] if ph["id"] == t["phase"]), "?")
    verb = "Resume" if action == "resume" else "Start"

    matches = list((ROOT / "tasks").glob(f"{next_id}_*.md"))
    task_file = matches[0].relative_to(ROOT).as_posix() if matches else f"tasks/{next_id}_*.md"

    # The "what to do NOW" panel
    what = Text()
    what.append(f"▶ {verb} task {next_id}\n", style="bold yellow")
    what.append(f"  {t['title']}\n\n", style="bold white")
    what.append(f"  Phase:    ", style="dim")
    what.append(f"{t['phase']} · {phase_name}\n")
    what.append(f"  Owner:    ", style="dim")
    what.append(f"{owner}\n")
    what.append(f"  File:     ", style="dim")
    what.append(f"{task_file}\n")
    console.print(Panel(what, title="🎯 What you do now", border_style="yellow"))

    # 5) Three clear action boxes side-by-side
    boxes = []

    # Box A: Read the task
    a = Text()
    a.append("1. Read the task\n", style="bold cyan")
    a.append(f"\npython scripts/show.py {next_id}\n", style="green")
    a.append("\nOr open:\n", style="dim")
    a.append(f"{task_file}", style="dim")
    boxes.append(Panel(a, title="Step 1", border_style="cyan"))

    # Box B: Run it with Claude
    b = Text()
    b.append("2. Work on it\n", style="bold magenta")
    b.append("\nOpen Claude Code in this folder.\n", style="dim")
    b.append("Copy-paste this prompt:\n\n", style="dim")
    b.append(f"Execute task {next_id}.\n", style="green")
    b.append("Read internal/CLAUDE.md\n", style="green")
    b.append(f"and tasks/{next_id}_*.md first.\n", style="green")
    b.append("\n(or run the task manually —\n", style="dim")
    b.append("see the task file for steps)", style="dim")
    boxes.append(Panel(b, title="Step 2", border_style="magenta"))

    # Box C: Finish it
    c = Text()
    c.append("3. When done\n", style="bold green")
    c.append(f"\npython scripts/mark_done.py {next_id}\n", style="green")
    c.append("python scripts/today.py\n", style="green")
    c.append("\n(or if stuck:)\n", style="dim")
    c.append(f"python scripts/mark_progress.py \\\n   {next_id} blocked \"why\"", style="yellow")
    boxes.append(Panel(c, title="Step 3", border_style="green"))

    console.print(Columns(boxes, equal=True, expand=True))
    console.print()

    # 6) Context block for Claude
    console.print(Panel(
        "[bold]Need to resume with Claude after a break?[/]\n\n"
        "Run [green]python scripts/context.py[/] — it prints a copy-pasteable\n"
        "context block. Paste it to Claude at the start of a new session.\n\n"
        "[dim]Tip: for a full visual HTML dashboard, run\n"
        "python scripts/visualize_progress.py[/]",
        title="💬 Resuming with Claude",
        border_style="blue",
    ))
    console.print()

    # 7) Learn-the-concept link
    concept_map = {
        "T01": "docs/CONCEPTS.md#environment", "T02": "docs/CONCEPTS.md#project-layout",
        "T03": "docs/CONCEPTS.md#python-packages", "T04": "docs/CONCEPTS.md#llms",
        "T05": "docs/CONCEPTS.md#smoke-tests",
        "T06": "docs/CONCEPTS.md#literature-review", "T07": "docs/CONCEPTS.md#literature-review",
        "T08": "docs/CONCEPTS.md#novelty", "T09": "docs/CONCEPTS.md#dataset",
        "T10": "docs/CONCEPTS.md#dataset",
        "T11": "docs/CONCEPTS.md#ground-truth", "T12": "docs/CONCEPTS.md#annotation",
        "T13": "docs/CONCEPTS.md#agreement",
        "T14": "docs/CONCEPTS.md#asr", "T15": "docs/CONCEPTS.md#sentence-splitting",
        "T16": "docs/CONCEPTS.md#shot-boundary", "T17": "docs/CONCEPTS.md#ocr",
        "T18": "docs/CONCEPTS.md#prosody",
        "T19": "docs/CONCEPTS.md#text-embeddings", "T20": "docs/CONCEPTS.md#visual-embeddings",
        "T21": "docs/CONCEPTS.md#alignment",
        "T22": "docs/CONCEPTS.md#metrics", "T23": "docs/CONCEPTS.md#baselines",
        "T24": "docs/CONCEPTS.md#baselines",
        "T25": "docs/CONCEPTS.md#fusion", "T26": "docs/CONCEPTS.md#boundary-prediction",
        "T27": "docs/CONCEPTS.md#hierarchical-output", "T28": "docs/CONCEPTS.md#llm-refinement",
        "T29": "docs/CONCEPTS.md#ablations",
        "T30": "docs/CONCEPTS.md#statistics", "T31": "docs/CONCEPTS.md#error-analysis",
    }
    concept_link = concept_map.get(next_id, "docs/CONCEPTS.md")
    console.print(Panel(
        f"[bold]Don't know the concepts for {next_id}?[/]\n\n"
        f"Read: [green]{concept_link}[/]\n\n"
        "Unfamiliar term anywhere in the project? → [green]docs/GLOSSARY.md[/]",
        title="📚 Learn before you build",
        border_style="blue",
    ))


if __name__ == "__main__":
    main()
