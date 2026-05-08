"""
Generate an HTML dashboard you can open in a browser to see progress visually.

Run: python scripts/visualize_progress.py
    → writes STATUS.html and opens it in your browser.
"""
from __future__ import annotations
import webbrowser
from pathlib import Path
import yaml
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "STATUS.html"

CSS = """
body { font-family: -apple-system, Segoe UI, sans-serif; background: #0e1116; color: #e6edf3; margin: 0; padding: 2rem; }
h1 { color: #58a6ff; }
.progress-big { height: 28px; background: #21262d; border-radius: 14px; overflow: hidden; margin: 1rem 0; }
.progress-bar { height: 100%; background: linear-gradient(90deg, #3fb950, #2ea043); }
.phase { margin: 0.8rem 0; padding: 0.8rem; border-radius: 8px; background: #161b22; }
.phase-bar { height: 14px; background: #21262d; border-radius: 7px; overflow: hidden; margin-top: 0.4rem; }
.phase-fill { height: 100%; }
.p-done { background: #3fb950; }
.p-some { background: #d29922; }
.p-none { background: #484f58; }
.tasks { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.6rem; }
.task { padding: 0.3rem 0.7rem; border-radius: 6px; font-size: 0.85rem; font-family: ui-monospace, monospace; }
.t-done { background: #0e4429; color: #3fb950; border: 1px solid #238636; }
.t-doing { background: #4a3a0a; color: #d29922; border: 1px solid #bb8009; }
.t-blocked { background: #4a1010; color: #f85149; border: 1px solid #da3633; }
.t-todo { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
.next-box { margin-top: 2rem; padding: 1.4rem; background: #1f2937; border-left: 4px solid #58a6ff; border-radius: 6px; }
.small { color: #8b949e; font-size: 0.85rem; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #30363d; font-size: 0.9rem; }
th { background: #161b22; }
code { background: #1f2937; padding: 0.1rem 0.4rem; border-radius: 4px; }
"""


def main() -> None:
    data = yaml.safe_load((ROOT / "progress.yaml").read_text(encoding="utf-8"))
    tasks = data["tasks"]
    total = len(tasks)
    done = sum(1 for t in tasks.values() if t["status"] == "done")
    pct = int(100 * done / total)
    status_class = {
        "done": "t-done", "doing": "t-doing", "blocked": "t-blocked",
        "todo": "t-todo", "skipped": "t-todo",
    }

    next_id = next((tid for tid, t in tasks.items() if t["status"] in ("todo", "doing", "blocked")), None)

    parts: list[str] = []
    parts.append(f"<!doctype html><html><head><meta charset='utf-8'><title>LECSEG progress</title><style>{CSS}</style></head><body>")
    parts.append(f"<h1>LECSEG — Progress Dashboard</h1>")
    parts.append(f"<div class='small'>Generated {datetime.utcnow().isoformat(timespec='minutes')}Z · Thesis {data['thesis_id']}</div>")
    parts.append(f"<h2>{done} / {total} tasks complete ({pct}%)</h2>")
    parts.append(f"<div class='progress-big'><div class='progress-bar' style='width:{pct}%'></div></div>")

    # Phases
    parts.append("<h2>Phases</h2>")
    for ph in data["phases"]:
        tids = ph["tasks"]
        d = sum(1 for tid in tids if tasks[tid]["status"] == "done")
        n = len(tids)
        fill_pct = int(100 * d / n) if n else 0
        cls = "p-done" if d == n else ("p-some" if d > 0 else "p-none")
        parts.append(f"<div class='phase'><b>Phase {ph['id']}: {ph['name']}</b> <span class='small'>({d}/{n})</span>"
                     f"<div class='phase-bar'><div class='phase-fill {cls}' style='width:{fill_pct}%'></div></div>"
                     "<div class='tasks'>")
        for tid in tids:
            t = tasks[tid]
            cls2 = status_class.get(t["status"], "t-todo")
            parts.append(f"<span class='task {cls2}' title='{t[\"title\"]}'>{tid}</span>")
        parts.append("</div></div>")

    # Next task
    if next_id:
        t = tasks[next_id]
        parts.append(f"<div class='next-box'><h3>▶ Next up: <code>{next_id}</code> — {t['title']}</h3>"
                     f"<p>Open <code>tasks/{next_id}_*.md</code> and follow the steps.</p>"
                     "<p>From the terminal: <code>python scripts/today.py</code></p></div>")

    # Full table
    parts.append("<h2>All tasks</h2><table><tr><th>ID</th><th>Status</th><th>Title</th><th>Owner</th><th>Phase</th></tr>")
    for tid, t in tasks.items():
        owner = t.get("owner") or "—"
        parts.append(f"<tr><td><code>{tid}</code></td><td>{t['status']}</td><td>{t['title']}</td><td>{owner}</td><td>{t['phase']}</td></tr>")
    parts.append("</table></body></html>")

    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT}")
    try:
        webbrowser.open(OUT.as_uri())
    except Exception:
        pass


if __name__ == "__main__":
    main()
