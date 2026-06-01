"""
Live progress monitor — shows all running LECSEG tasks with animated bars.
Run in a separate terminal: python scripts/progress_monitor.py
"""
import os, json, time, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
PROGRESS_LOG = ROOT / "docs" / "PROGRESS_LOG.md"

TASKS = {
    "oracle_k":      ("results/oracle_k_experiment.json", "Oracle-k experiment"),
    "boundary_clf":  ("results/eval_boundary_clf.json",   "Boundary classifier LOOCV"),
    "stella_emb":    ("data/embeddings/stella/.done",     "Stella 1.5B embeddings"),
    "contrastive":   ("models/bge_contrastive/.done",     "Contrastive BGE finetuning"),
    "crossencoder":  ("models/crossencoder/.done",        "Cross-encoder finetuning"),
    "eval_stella":   ("results/eval_stella.json",         "Eval: Stella + divisive"),
    "eval_contrast": ("results/eval_contrastive.json",    "Eval: contrastive model"),
    "eval_cross":    ("results/eval_crossencoder.json",   "Eval: cross-encoder"),
}

SPINNER = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
BAR_WIDTH = 20

def get_pk(result_file):
    try:
        d = json.load(open(ROOT / result_file))
        pk = d.get("macro_pk", d.get("summary", {}).get("divisive", {}).get("pk"))
        return f"Pk={pk:.4f}" if pk else "done"
    except Exception:
        return "done"

def draw():
    tick = int(time.time() * 4) % len(SPINNER)
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  LECSEG PROGRESS MONITOR  {datetime.now().strftime('%H:%M:%S')}")
    lines.append(f"{'='*60}")

    for key, (fpath, label) in TASKS.items():
        done = (ROOT / fpath).exists()
        if done:
            result = get_pk(fpath)
            bar = "█" * BAR_WIDTH
            status = f"✅ {result}"
            color = "\033[92m"
        else:
            bar = "░" * BAR_WIDTH
            status = f"{SPINNER[tick]} running..."
            color = "\033[93m"
        reset = "\033[0m"
        lines.append(f"  {color}[{bar}]{reset} {label}")
        lines.append(f"           {status}")

    lines.append(f"{'='*60}")

    # Last log entry
    try:
        log_lines = PROGRESS_LOG.read_text(encoding="utf-8").split("\n")
        last_entry = next((l for l in reversed(log_lines) if l.startswith("## [")), None)
        if last_entry:
            lines.append(f"  Last log: {last_entry}")
    except Exception:
        pass

    lines.append("")
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(lines))

if __name__ == "__main__":
    print("Starting monitor... (Ctrl+C to stop)")
    try:
        while True:
            draw()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
