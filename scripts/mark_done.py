"""Mark a task as done. Run: python scripts/mark_done.py T01"""
from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROG = ROOT / "progress.yaml"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/mark_done.py T<NN>")
        sys.exit(1)
    tid = sys.argv[1].upper()
    data = yaml.safe_load(PROG.read_text(encoding="utf-8"))
    if tid not in data["tasks"]:
        print(f"Unknown task: {tid}")
        sys.exit(1)
    data["tasks"][tid]["status"] = "done"
    data["tasks"][tid]["completed_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    PROG.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"✅ {tid} marked done. Run `python scripts/next.py` for the next one.")


if __name__ == "__main__":
    main()
