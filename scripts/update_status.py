"""Regenerate STATUS.md and NEXT.md from progress.yaml.

Run automatically by mark_done/mark_progress, or manually:
  python scripts/update_status.py
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent

ICON = {"todo": "⬜", "doing": "🟡", "blocked": "🟥", "done": "✅", "skipped": "⏭️"}


def bar(d: int, n: int, width: int = 30) -> str:
    filled = int(width * d / n) if n else 0
    return "█" * filled + "░" * (width - filled)


def main() -> None:
    data = yaml.safe_load((ROOT / "progress.yaml").read_text(encoding="utf-8"))
    tasks = data["tasks"]
    total = len(tasks)
    done = sum(1 for t in tasks.values() if t["status"] == "done")
    pct = int(100 * done / total)

    # STATUS.md
    lines = [
        "# 📊 STATUS — Auto-generated, do not edit",
        "",
        f"_Last updated: {datetime.utcnow().isoformat(timespec='minutes')}Z_",
        "",
        f"## Overall progress: **{done} / {total}** tasks complete ({pct}%)",
        "",
        f"`{bar(done, total, 40)}`  **{pct}%**",
        "",
        "## Phases",
        "",
        "| # | Phase | Progress | Done |",
        "|---|---|---|---|",
    ]
    for ph in data["phases"]:
        tids = ph["tasks"]
        d = sum(1 for tid in tids if tasks[tid]["status"] == "done")
        n = len(tids)
        lines.append(f"| {ph['id']} | {ph['name']} | `{bar(d, n)}` | {d}/{n} |")
    lines += ["", "## All tasks", "", "| ID | Status | Title | Owner | Phase |",
              "|---|---|---|---|---|"]
    for tid, t in tasks.items():
        owner = t.get("owner") or "—"
        lines.append(
            f"| [{tid}](tasks/{tid}_) | {ICON[t['status']]} {t['status']} | "
            f"{t['title']} | {owner} | {t['phase']} |"
        )
    (ROOT / "STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # NEXT.md
    next_id = next((tid for tid, t in tasks.items() if t["status"] in ("todo", "doing", "blocked")), None)
    nlines = ["# ⏭️ NEXT — What to do right now (auto-generated)", ""]
    if next_id:
        t = tasks[next_id]
        nlines += [
            f"## Next task: **{next_id} — {t['title']}**",
            "",
            f"- Status: {ICON[t['status']]} {t['status']}",
            f"- Owner: {t.get('owner') or '(unclaimed — run `python scripts/claim.py ' + next_id + ' <yourname>`)'}",
            f"- Phase: {t['phase']}",
            "",
            f"👉 **Open [`tasks/{next_id}_*.md`](tasks/) and follow the instructions.**",
            "",
            "Or run in terminal:",
            "```",
            "python scripts/next.py",
            "```",
        ]
    else:
        nlines += ["## 🎉 All tasks complete!", "", "Run `python scripts/pre_defense_check.py`."]
    (ROOT / "NEXT.md").write_text("\n".join(nlines) + "\n", encoding="utf-8")

    print("Updated STATUS.md and NEXT.md")


if __name__ == "__main__":
    main()
