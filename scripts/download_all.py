"""
T10 — Download all 30 lecture videos, extract audio, write manifest.

Usage:
    python scripts/download_all.py

Reads  : data/video_list.csv  (actually an xlsx renamed .csv)
Writes : data/raw/<video_id>/video.mp4
         data/raw/<video_id>/audio.wav
         data/raw/<video_id>/*.info.json
         data/manifest.jsonl

Idempotent: already-downloaded videos are skipped.
Max 3 parallel downloads (polite throttling).
"""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import openpyxl
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

# Project root is one level up from scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lecseg.data.youtube import (
    _video_id,
    download_video,
    duration_seconds,
    extract_audio,
    load_chapters,
    video_dir,
)

RAW_ROOT = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest.jsonl"
VIDEO_LIST = ROOT / "data" / "video_list.csv"   # actually xlsx
MAX_WORKERS = 1  # sequential to avoid YouTube 429 rate-limits

console = Console()


# ---------------------------------------------------------------------------
# Load video list
# ---------------------------------------------------------------------------

def load_video_list() -> list[dict]:
    # The file may be an xlsx renamed .csv — try both extensions.
    candidate = VIDEO_LIST
    if not candidate.exists():
        raise FileNotFoundError(f"Video list not found: {VIDEO_LIST}")
    # openpyxl refuses .csv; try a sibling .xlsx if the magic bytes say ZIP
    with open(candidate, "rb") as fh:
        magic = fh.read(4)
    if magic == b"PK\x03\x04":  # ZIP/XLSX despite .csv extension
        import shutil, tempfile, os
        tmp = Path(tempfile.mktemp(suffix=".xlsx"))
        shutil.copy(candidate, tmp)
        candidate = tmp

    wb = openpyxl.load_workbook(str(candidate), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    records = []
    for row in rows[1:]:
        if row[0] is None:
            continue
        rec = dict(zip(header, row))
        records.append(rec)
    return records


# ---------------------------------------------------------------------------
# Per-video worker
# ---------------------------------------------------------------------------

def _extract_id(url: str) -> str:
    try:
        return _video_id(str(url))
    except ValueError:
        return re.sub(r"[^A-Za-z0-9_-]", "_", str(url))[:20]


def process_video(rec: dict, progress: Progress, task_id) -> dict | None:
    url = str(rec.get("url", "")).strip()
    if not url:
        return None

    vid_id = _extract_id(url)
    out_dir = RAW_ROOT / vid_id
    label = vid_id

    try:
        progress.update(task_id, description=f"[cyan]DL  {label}")
        download_video(url, out_dir)

        progress.update(task_id, description=f"[yellow]WAV {label}")
        extract_audio(out_dir)

        chapters = load_chapters(out_dir)
        dur = duration_seconds(out_dir)

        entry = {
            "id": vid_id,
            "url": url,
            "domain": str(rec.get("domain", "")).strip().upper(),
            "title": str(rec.get("title", "")).strip(),
            "duration_sec": dur,
            "path": str(out_dir.relative_to(ROOT)),
            "num_chapters": len(chapters),
            "downloaded_at": datetime.utcnow().isoformat() + "Z",
        }
        progress.advance(task_id)
        return entry

    except Exception as exc:
        console.print(f"[red]FAILED {vid_id}: {exc}")
        progress.advance(task_id)
        return None


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    entries = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                e = json.loads(line)
                entries[e["id"]] = e
            except Exception:
                pass
    return entries


def save_manifest(entries: dict[str, dict]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, ensure_ascii=False) for e in entries.values()]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)

    records = load_video_list()
    console.print(f"[bold]Loaded {len(records)} videos from video_list.[/bold]")

    existing = load_manifest()
    console.print(f"Already in manifest: {len(existing)} videos.")

    to_process = [r for r in records if _extract_id(str(r.get("url", ""))) not in existing]
    console.print(f"To download: {len(to_process)} videos.\n")

    if not to_process:
        console.print("[green]All videos already downloaded. Nothing to do.")
        _print_summary(existing)
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Downloading…", total=len(to_process))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(process_video, rec, progress, task_id): rec
                for rec in to_process
            }
            for fut in as_completed(futures):
                entry = fut.result()
                if entry:
                    existing[entry["id"]] = entry
                    save_manifest(existing)  # write incrementally

    _print_summary(existing)


def _print_summary(entries: dict) -> None:
    total = len(entries)
    hours = sum(e.get("duration_sec") or 0 for e in entries.values()) / 3600
    console.print(f"\n[bold green]{total} videos in manifest, total {hours:.1f} h[/bold green]")
    missing_audio = [
        e["id"] for e in entries.values()
        if not (ROOT / e["path"] / "audio.wav").exists()
    ]
    if missing_audio:
        console.print(f"[yellow]Missing audio.wav for: {missing_audio}")


if __name__ == "__main__":
    main()
