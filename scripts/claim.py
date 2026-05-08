"""Claim a task as owner. Usage: python scripts/claim.py T05 ismam"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROG = ROOT / "progress.yaml"


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python scripts/claim.py T<NN> <yourname>")
        sys.exit(1)
    tid = sys.argv[1].upper()
    owner = sys.argv[2].lower()
    data = yaml.safe_load(PROG.read_text(encoding="utf-8"))
    if tid not in data["tasks"]:
        print(f"Unknown task: {tid}")
        sys.exit(1)
    valid_owners = {m["id"] for m in data["team"]}
    if owner not in valid_owners:
        print(f"Unknown owner '{owner}'. Must be one of {sorted(valid_owners)}")
        sys.exit(1)
    data["tasks"][tid]["owner"] = owner
    if data["tasks"][tid]["status"] == "todo":
        data["tasks"][tid]["status"] = "doing"
    PROG.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"✅ {tid} claimed by {owner}")


if __name__ == "__main__":
    main()
