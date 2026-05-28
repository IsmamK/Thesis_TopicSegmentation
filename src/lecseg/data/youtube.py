"""
YouTube download helpers for LECSEG.

Exists because yt-dlp's API is verbose; this module wraps it into three
idempotent functions (download_video, extract_audio, load_chapters) that the
top-level script can call in parallel without duplicating work.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _video_id(url: str) -> str:
    """Extract the bare YouTube video ID from any YouTube URL."""
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not match:
        raise ValueError(f"Cannot parse video ID from: {url}")
    return match.group(1)


def video_dir(raw_root: Path, url: str) -> Path:
    return raw_root / _video_id(url)


# ---------------------------------------------------------------------------
# Download video + info.json
# ---------------------------------------------------------------------------

def download_video(url: str, out_dir: Path) -> Path:
    """
    Download the best MP4 (video+audio) for *url* into *out_dir*.

    Returns the path to the downloaded MP4.
    Idempotent: skips if video.mp4 already exists.
    """
    dest = out_dir / "video.mp4"
    if dest.exists():
        return dest

    out_dir.mkdir(parents=True, exist_ok=True)
    vid_id = _video_id(url)

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--sleep-interval", "8",
        "--max-sleep-interval", "20",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--write-info-json",
        "--no-write-thumbnail",
        "-o", str(out_dir / "video.%(ext)s"),
        f"https://www.youtube.com/watch?v={vid_id}",
    ]
    subprocess.run(cmd, check=True)

    # yt-dlp may name it video.mp4 or video.webm — rename if needed
    candidates = list(out_dir.glob("video.*"))
    mp4_candidates = [p for p in candidates if p.suffix == ".mp4"]
    if not mp4_candidates:
        other = [p for p in candidates if p.suffix not in (".json",)]
        if other:
            other[0].rename(dest)
    return dest


# ---------------------------------------------------------------------------
# Extract mono 16kHz WAV
# ---------------------------------------------------------------------------

def extract_audio(out_dir: Path) -> Path:
    """
    Use ffmpeg to extract mono 16kHz WAV from *out_dir/video.mp4*.

    Returns the path to audio.wav.
    Idempotent: skips if audio.wav already exists.
    """
    src = out_dir / "video.mp4"
    dest = out_dir / "audio.wav"
    if dest.exists():
        return dest
    if not src.exists():
        raise FileNotFoundError(f"video.mp4 missing in {out_dir}")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return dest


# ---------------------------------------------------------------------------
# Load chapter metadata from info.json
# ---------------------------------------------------------------------------

def load_chapters(out_dir: Path) -> list[dict]:
    """
    Return the chapters list from the yt-dlp info.json, or [] if none.

    Each chapter dict has at least: title, start_time, end_time (seconds).
    """
    candidates = list(out_dir.glob("*.info.json"))
    if not candidates:
        return []
    info = json.loads(candidates[0].read_text(encoding="utf-8"))
    return info.get("chapters") or []


def duration_seconds(out_dir: Path) -> float | None:
    """Return video duration in seconds from info.json, or None."""
    candidates = list(out_dir.glob("*.info.json"))
    if not candidates:
        return None
    info = json.loads(candidates[0].read_text(encoding="utf-8"))
    return info.get("duration")
