"""Print a copy-pasteable context block for Claude.

Run: python scripts/resume.py > resume.txt
Then paste the contents of resume.txt into Claude at the start of a new session.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "(git unavailable)"


def main() -> None:
    data = yaml.safe_load((ROOT / "progress.yaml").read_text(encoding="utf-8"))

    done = [f"{tid}: {t['title']}" for tid, t in data["tasks"].items() if t["status"] == "done"]
    doing = [tid for tid, t in data["tasks"].items() if t["status"] == "doing"]
    blocked = [(tid, t.get("blocker", "?")) for tid, t in data["tasks"].items() if t["status"] == "blocked"]
    todo = [tid for tid, t in data["tasks"].items() if t["status"] == "todo"]
    next_id = todo[0] if todo else (doing[0] if doing else None)

    print("=== LECSEG — Resume Context for Claude ===")
    print("I am continuing work on my undergraduate thesis project LECSEG.")
    print("This is the project structure and current state. Read it before doing anything.")
    print()
    print(f"Thesis ID: {data['thesis_id']}")
    print()
    print("## Completed tasks:")
    if done:
        for line in done:
            print(f"  - {line}")
    else:
        print("  (none yet)")
    print()
    print("## Currently in progress:")
    for tid in doing:
        t = data["tasks"][tid]
        owner = t.get("owner", "?")
        print(f"  - {tid} ({owner}): {t['title']}")
    if not doing:
        print("  (nothing started right now)")
    print()
    if blocked:
        print("## Blocked:")
        for tid, reason in blocked:
            print(f"  - {tid}: {reason}")
        print()
    print(f"## Next task to tackle: {next_id}")
    if next_id:
        t = data["tasks"][next_id]
        print(f"  Title: {t['title']}")
        print(f"  Phase: {t['phase']}")
        print(f"  Instructions file: tasks/{next_id}_*.md")
        print()
        print(f"Please read tasks/{next_id}_*.md, then do exactly what it says.")
        print("Read internal/CLAUDE.md first for house rules. Read docs/METHODOLOGY.md for the research plan.")
    print()
    print("## Git state:")
    print(f"  Branch: {git('branch', '--show-current')}")
    print(f"  Last commit: {git('log', '-1', '--oneline')}")
    recent = git("log", "--oneline", "-10").splitlines()
    if recent:
        print("  Recent commits:")
        for line in recent[:10]:
            print(f"    {line}")
    print()
    print("## Key files to read before acting:")
    print("  1. internal/CLAUDE.md            — house rules, do NOT violate them")
    print("  2. docs/NOVELTY_TRACKER.md       — our 7 novelty claims")
    print(f"  3. tasks/{next_id}_*.md          — the task to execute" if next_id else "")
    print("  4. progress.yaml                 — project state")
    print()
    print("=== end of context ===")


if __name__ == "__main__":
    main()
