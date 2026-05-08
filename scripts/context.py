"""
Generate a copy-pasteable context block to give Claude when resuming work.

Usage:
    python scripts/context.py
    python scripts/context.py > context.txt    # save to file
    python scripts/context.py --clip           # copy to clipboard (needs 'pyperclip')

Paste the printed block into a new Claude chat. Claude will know:
  - what we are building
  - what has been completed
  - what is next
  - where to look for rules
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROG = ROOT / "progress.yaml"


def git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "(git unavailable)"


def main() -> None:
    data = yaml.safe_load(PROG.read_text(encoding="utf-8"))
    tasks = data["tasks"]

    done = [f"{tid}: {t['title']}" for tid, t in tasks.items() if t["status"] == "done"]
    doing = [tid for tid, t in tasks.items() if t["status"] == "doing"]
    blocked = [
        (tid, t.get("blocker", "?")) for tid, t in tasks.items() if t["status"] == "blocked"
    ]
    todo = [tid for tid, t in tasks.items() if t["status"] == "todo"]
    next_id = doing[0] if doing else (todo[0] if todo else None)

    lines: list[str] = []
    lines.append("=== LECSEG — Resume Context for Claude ===")
    lines.append("")
    lines.append("I am continuing work on my undergraduate thesis project.")
    lines.append("Project name: LECSEG (Lecture Video Topic Segmentation).")
    lines.append(f"Thesis ID: {data['thesis_id']} · BracU CSE400.")
    lines.append("")
    lines.append("## Read these BEFORE doing anything ##")
    lines.append("  1. internal/CLAUDE.md          — house rules. Non-negotiable.")
    lines.append("  2. progress.yaml               — source of truth for what's done.")
    lines.append("  3. docs/NOVELTY_TRACKER.md     — our 7 novelty claims N1–N7.")
    lines.append("  4. docs/METHODOLOGY.md         — the research plan.")
    if next_id:
        lines.append(f"  5. tasks/{next_id}_*.md              — the NEXT task to run.")
    lines.append("")
    lines.append("## What we have completed ##")
    if done:
        for line in done:
            lines.append(f"  ✅ {line}")
    else:
        lines.append("  (none yet)")
    lines.append("")
    lines.append("## What is in progress ##")
    if doing:
        for tid in doing:
            t = tasks[tid]
            lines.append(f"  🟡 {tid} ({t.get('owner', '?')}): {t['title']}")
    else:
        lines.append("  (nothing started right now)")
    lines.append("")
    if blocked:
        lines.append("## Blocked ##")
        for tid, reason in blocked:
            lines.append(f"  🟥 {tid}: {reason}")
        lines.append("")
    lines.append(f"## Next task to tackle: {next_id} ##")
    if next_id:
        t = tasks[next_id]
        lines.append(f"  Title: {t['title']}")
        lines.append(f"  Phase: {t['phase']}")
        lines.append(f"  Instructions: tasks/{next_id}_*.md")
        lines.append("")
        lines.append(f"  ⇒ Please read tasks/{next_id}_*.md, then execute it step by step.")
    lines.append("")
    lines.append("## Git state ##")
    lines.append(f"  Branch:      {git('branch', '--show-current')}")
    lines.append(f"  Last commit: {git('log', '-1', '--oneline')}")
    recent = git("log", "--oneline", "-8").splitlines()
    if recent:
        lines.append("  Recent:")
        for line in recent[:8]:
            lines.append(f"    {line}")
    lines.append("")
    lines.append("## Reminders ##")
    lines.append("  - Do NOT mark tasks done yourself; only I run mark_done.py.")
    lines.append("  - Do NOT touch internal/ content unless I ask.")
    lines.append("  - Do NOT write to docs/ in a voice that mentions AI/Claude/LLM.")
    lines.append("  - For anything unclear, stop and ask me.")
    lines.append("")
    lines.append("=== end of context ===")

    text = "\n".join(lines)

    if "--clip" in sys.argv:
        try:
            import pyperclip

            pyperclip.copy(text)
            print("Copied to clipboard.")
            return
        except ImportError:
            print("(Install pyperclip for --clip: pip install pyperclip)\n")

    print(text)


if __name__ == "__main__":
    main()
