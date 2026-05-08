"""Update task status. Usage:
  python scripts/mark_progress.py T05 doing
  python scripts/mark_progress.py T05 blocked "GPU is not available"
  python scripts/mark_progress.py T05 skipped
"""
from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROG = ROOT / "progress.yaml"
VALID = {"todo", "doing", "blocked", "done", "skipped"}


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    tid = sys.argv[1].upper()
    status = sys.argv[2].lower()
    reason = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
    if status not in VALID:
        print(f"status must be one of {sorted(VALID)}")
        sys.exit(1)
    data = yaml.safe_load(PROG.read_text(encoding="utf-8"))
    if tid not in data["tasks"]:
        print(f"Unknown task: {tid}")
        sys.exit(1)
    data["tasks"][tid]["status"] = status
    if status == "blocked" and reason:
        data["tasks"][tid]["blocker"] = reason
    if status == "done":
        data["tasks"][tid]["completed_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    if status == "doing":
        data["tasks"][tid]["started_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    PROG.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"{tid} → {status}")


if __name__ == "__main__":
    main()
