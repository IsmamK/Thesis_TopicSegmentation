"""
Quick status report for the LECSEG project.
Shows task completion from progress.yaml and data availability.

Usage:
    python scripts/status.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    import yaml
except ImportError:
    print("pip install pyyaml")
    sys.exit(1)


def _bar(done: int, total: int, width: int = 30) -> str:
    filled = int(done * width / total) if total else 0
    return f"[{'#' * filled}{'.' * (width - filled)}] {done}/{total}"


def main():
    progress_file = ROOT / "progress.yaml"
    if not progress_file.exists():
        print("progress.yaml not found")
        return

    data = yaml.safe_load(progress_file.read_text(encoding="utf-8"))
    tasks = data.get("tasks", {})

    status_counts: dict[str, int] = {}
    for tid, t in tasks.items():
        s = t.get("status", "todo")
        status_counts[s] = status_counts.get(s, 0) + 1

    total = len(tasks)
    done = status_counts.get("done", 0)
    in_prog = status_counts.get("in_progress", 0)

    print("=" * 50)
    print("LECSEG Project Status")
    print("=" * 50)
    print(f"Overall: {_bar(done, total)}")
    print(f"  Done:        {done}")
    print(f"  In progress: {in_prog}")
    print(f"  Todo:        {status_counts.get('todo', 0)}")

    # Per-phase summary
    phases = data.get("phases", [])
    print()
    for phase in phases:
        phase_id = phase["id"]
        phase_name = phase["name"]
        phase_tasks = phase.get("tasks", [])
        phase_done = sum(1 for tid in phase_tasks
                         if tasks.get(tid, {}).get("status") == "done")
        phase_total = len(phase_tasks)
        bar = _bar(phase_done, phase_total, width=15)
        print(f"  Phase {phase_id} ({phase_name:<20}): {bar}")

    # Data availability
    print()
    print("Data:")
    transcripts = list((ROOT / "data" / "transcripts").glob("*/transcript.json"))
    sentences = list((ROOT / "data" / "sentences").glob("*/sentences.json"))
    gt_hier = list((ROOT / "data" / "gt_hier").glob("*.json"))
    gt_reviewed = [f for f in gt_hier
                   if not f.stem.startswith("_") and "iaa" not in f.stem]

    print(f"  Transcripts:      {len(transcripts)}/30")
    print(f"  Sentence files:   {len(sentences)}/30")
    print(f"  GT annotations:   {len(gt_reviewed)}/30")

    # Running tasks
    print()
    in_progress = [(tid, t["title"]) for tid, t in tasks.items()
                   if t.get("status") == "in_progress"]
    if in_progress:
        print("In progress:")
        for tid, title in in_progress:
            print(f"  {tid}: {title}")


if __name__ == "__main__":
    main()
