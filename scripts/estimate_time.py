"""
Estimate remaining transcription time based on manifest and completed files.

Usage:
    python scripts/estimate_time.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HOST = "154.12.38.116"
PORT = 21115
KEY = f"{Path.home()}/.ssh/id_rsa"


def _ssh(cmd: str) -> str:
    import subprocess
    r = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-i", KEY, "-p", str(PORT),
         f"root@{HOST}", cmd],
        capture_output=True, text=True, timeout=15,
    )
    return r.stdout.strip()


def main():
    manifest_path = ROOT / "data" / "manifest.jsonl"
    if not manifest_path.exists():
        print("data/manifest.jsonl not found")
        sys.exit(1)

    records = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            records[r["id"]] = r

    try:
        done_raw = _ssh("ls /workspace/transcripts/ 2>/dev/null")
        done_ids = set(v.strip() for v in done_raw.splitlines() if v.strip())
        current_raw = _ssh("tail -1 /workspace/transcribe.log 2>/dev/null")
    except Exception as e:
        print(f"SSH error: {e}")
        sys.exit(1)

    total = len(records)
    done = len(done_ids)
    remaining_ids = [vid for vid in records if vid not in done_ids]

    # Try to find which video is currently being transcribed
    current_vid = None
    if "Transcribing" in current_raw:
        parts = current_raw.split()
        for p in parts:
            if p.strip(".") in records:
                current_vid = p.strip(".")
                break

    print(f"Progress: {done}/{total} done")
    if current_vid:
        print(f"Current: {current_vid} ({records[current_vid]['duration_sec']/60:.0f} min audio)")
    print()

    # Estimate remaining time: from completed files, compute throughput
    total_remaining_sec = 0
    for vid in remaining_ids:
        if vid == current_vid:
            # Assume halfway done
            total_remaining_sec += records[vid]["duration_sec"] / 2
        else:
            total_remaining_sec += records[vid]["duration_sec"]

    # Assume 18x realtime on GPU
    REALTIME_FACTOR = 18.0
    estimated_gpu_s = total_remaining_sec / REALTIME_FACTOR
    # Add ~5min per large file for VAD preprocessing (files > 1800s)
    n_large = sum(1 for vid in remaining_ids if records.get(vid, {}).get("duration_sec", 0) > 1800)
    estimated_vad_s = n_large * 600  # 10 min per large file

    total_estimated_s = estimated_gpu_s + estimated_vad_s
    total_estimated_min = total_estimated_s / 60

    print(f"Remaining audio: {total_remaining_sec/3600:.1f}h")
    print(f"Large files (>30min): {n_large}")
    print(f"Estimated remaining time: {total_estimated_min:.0f} min (~{total_estimated_min/60:.1f}h)")
    print()
    print("Remaining videos:")
    for vid in remaining_ids:
        dur = records.get(vid, {}).get("duration_sec", 0)
        current_marker = " << IN PROGRESS" if vid == current_vid else ""
        print(f"  {vid:<20} {dur/60:5.0f} min{current_marker}")


if __name__ == "__main__":
    main()
