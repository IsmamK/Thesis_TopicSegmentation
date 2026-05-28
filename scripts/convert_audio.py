"""
Convert all audio.wav files to 16kHz mono MP3 for upload to vast.ai / Colab.

Optimizations:
  - Parallel: runs N FFmpeg processes simultaneously (default: CPU count - 1)
  - 16kHz mono: exactly what Whisper resamples to internally — zero quality loss
  - 32 kbps CBR + libmp3lame: transparent for speech, ~240 KB/min
  - Skips already-converted files
  - Verifies output duration matches source (catches corrupt writes)

Run:
    python scripts/convert_audio.py
    python scripts/convert_audio.py --workers 8
    python scripts/convert_audio.py --bitrate 48k   # slightly larger, slightly safer

Output:
    data/mp3/<video_id>.mp3

After this, upload the entire data/mp3/ folder to vast.ai or Google Drive.
"""

from __future__ import annotations

import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
MP3_DIR = ROOT / "data" / "mp3"
MANIFEST = ROOT / "data" / "manifest.jsonl"

console = Console(highlight=False)
app = typer.Typer(add_completion=False)


def load_video_ids() -> list[str]:
    if MANIFEST.exists():
        return [json.loads(l)["id"] for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [p.name for p in RAW_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")]


def get_duration(path: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def convert_one(video_id: str, bitrate: str, overwrite: bool) -> dict:
    wav = RAW_DIR / video_id / "audio.wav"
    mp3 = MP3_DIR / f"{video_id}.mp3"

    if not wav.exists():
        return {"id": video_id, "ok": False, "reason": "wav not found"}

    if mp3.exists() and not overwrite:
        return {"id": video_id, "ok": True, "reason": "skipped (exists)", "skipped": True}

    t0 = time.time()

    cmd = [
        "ffmpeg",
        "-y",                        # overwrite output
        "-i", str(wav),
        "-ac", "1",                  # mix to mono first
        "-ar", "16000",              # resample to 16 kHz (what Whisper uses internally)
        "-c:a", "libmp3lame",        # best MP3 encoder
        "-b:a", bitrate,             # constant bitrate (32k = 240 KB/min, transparent for speech)
        "-compression_level", "0",   # fastest libmp3lame encode (quality unaffected for CBR)
        str(mp3),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    if result.returncode != 0:
        return {"id": video_id, "ok": False, "reason": result.stderr[-300:]}

    # verify output exists and duration is within 2s of source
    if not mp3.exists():
        return {"id": video_id, "ok": False, "reason": "output file missing after encode"}

    src_dur = get_duration(wav)
    out_dur = get_duration(mp3)
    if src_dur > 0 and abs(src_dur - out_dur) > 2.0:
        mp3.unlink()
        return {
            "id": video_id, "ok": False,
            "reason": f"duration mismatch: src={src_dur:.1f}s out={out_dur:.1f}s — deleted"
        }

    size_mb = mp3.stat().st_size / 1_048_576
    return {
        "id": video_id, "ok": True, "reason": "converted",
        "elapsed": elapsed, "size_mb": size_mb, "duration_sec": out_dur,
    }


@app.command()
def main(
    workers: int = typer.Option(0, "--workers", "-w", help="Parallel FFmpeg jobs (0 = CPU count - 1)"),
    bitrate: str = typer.Option("32k", "--bitrate", "-b", help="MP3 bitrate (32k recommended for speech)"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Re-convert already-done files"),
    video_id: str = typer.Option(None, "--video-id", "-v", help="Convert a single video"),
):
    import os
    if workers <= 0:
        workers = max(1, os.cpu_count() - 1)  # leave 1 core free for system

    MP3_DIR.mkdir(parents=True, exist_ok=True)

    ids = [video_id] if video_id else load_video_ids()
    console.print(f"[bold]Converting {len(ids)} files[/bold] -> 16kHz mono MP3 @ {bitrate}  |  {workers} parallel workers")

    results = []
    t_start = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as prog:
        task = prog.add_task("Converting...", total=len(ids))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(convert_one, vid, bitrate, overwrite): vid for vid in ids}
            for fut in as_completed(futures):
                r = fut.result()
                results.append(r)
                icon = "[green]OK[/green]" if r["ok"] else "[red]FAIL[/red]"
                tag = f"  {r.get('size_mb', 0):.1f} MB  {r.get('elapsed', 0):.0f}s" if r.get("elapsed") else f"  {r['reason']}"
                prog.advance(task)
                prog.print(f"{icon} {r['id']}{tag}")

    total_elapsed = time.time() - t_start

    # Summary table
    ok = [r for r in results if r["ok"] and not r.get("skipped")]
    skipped = [r for r in results if r.get("skipped")]
    failed = [r for r in results if not r["ok"]]

    total_mb = sum(r.get("size_mb", 0) for r in ok)
    total_src_gb = sum((RAW_DIR / r["id"] / "audio.wav").stat().st_size for r in ok if (RAW_DIR / r["id"] / "audio.wav").exists()) / 1_073_741_824

    table = Table(title="Conversion Summary", show_header=True)
    table.add_column("Stat", style="bold")
    table.add_column("Value")
    table.add_row("Converted", str(len(ok)))
    table.add_row("Skipped (already done)", str(len(skipped)))
    table.add_row("Failed", f"[red]{len(failed)}[/red]" if failed else "0")
    table.add_row("Total time", f"{total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")
    table.add_row("Source size", f"{total_src_gb:.2f} GB")
    table.add_row("Output size", f"{total_mb/1024:.2f} GB  ({total_mb:.0f} MB)")
    if total_src_gb > 0 and total_mb > 0:
        table.add_row("Compression ratio", f"{total_src_gb*1024/total_mb:.1f}x smaller")
    console.print(table)

    if failed:
        console.print("\n[red]Failed files:[/red]")
        for r in failed:
            console.print(f"  {r['id']}: {r['reason']}")
        raise SystemExit(1)

    console.print(f"\n[bold green]Output folder:[/bold green] {MP3_DIR}")
    console.print("Upload [bold]data/mp3/[/bold] to vast.ai or Google Drive, then run Whisper.")


if __name__ == "__main__":
    app()
