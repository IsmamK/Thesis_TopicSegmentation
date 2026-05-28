"""
T16 — Visual shot-boundary detection (TransNetV2).

Detects shot boundaries in lecture videos using TransNetV2.
Falls back to uniform frame sampling if TransNetV2 is unavailable.

Usage:
    from lecseg.preprocess.shot_detection import detect_shots, shots_to_boundaries

    shots = detect_shots("data/videos/vid.mp4")
    boundaries = shots_to_boundaries(shots, fps=25.0)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np


def detect_shots(
    video_path: Path | str,
    threshold: float = 0.5,
    batch_size: int = 16,
) -> list[dict]:
    """
    Detect shot boundaries using TransNetV2.

    Args:
        video_path: path to video file
        threshold:  probability threshold for declaring a shot boundary
        batch_size: batch size for TransNetV2 inference

    Returns:
        List of dicts with keys: frame_idx, timestamp_s, probability
        Falls back to empty list if TransNetV2 is unavailable.
    """
    video_path = Path(video_path)
    try:
        import transnetv2  # type: ignore
        import tensorflow as tf  # type: ignore  # noqa: F401
        return _detect_transnetv2(video_path, threshold, batch_size)
    except ImportError:
        return _detect_fallback(video_path, threshold)


def _detect_transnetv2(
    video_path: Path,
    threshold: float,
    batch_size: int,
) -> list[dict]:
    import transnetv2  # type: ignore

    model = transnetv2.TransNetV2()
    video_frames, single_frame_preds, _ = model.predict_video(str(video_path))

    shots = []
    for frame_idx, prob in enumerate(single_frame_preds.flatten()):
        if float(prob) >= threshold:
            shots.append({
                "frame_idx": int(frame_idx),
                "probability": float(prob),
            })
    return shots


def _detect_fallback(
    video_path: Path,
    threshold: float,
    sample_every: int = 10,
) -> list[dict]:
    """Fallback: ffmpeg scene-change detection.

    Uses ffmpeg's built-in scene filter which is O(n) and handles H.264
    efficiently — avoids the OpenCV cap.set() seek problem on compressed video.
    Falls back to OpenCV pixel-diff if ffmpeg is unavailable.
    """
    shots = _detect_ffmpeg(video_path, threshold)
    if shots is not None:
        return shots
    # OpenCV fallback (slow on H.264 but kept for completeness)
    return _detect_opencv(video_path, threshold, sample_every)


def _detect_ffmpeg(video_path: Path, threshold: float) -> list[dict] | None:
    """Use ffmpeg scene change filter — fast, handles any codec."""
    import subprocess
    import re

    scene_thresh = max(0.05, min(0.95, threshold * 0.6))
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"select='gt(scene,{scene_thresh})',showinfo",
        "-vsync", "0", "-f", "null", "-",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    # Parse "pts_time:X.XXX" from showinfo output on stderr
    shots = []
    fps = 25.0
    fps_match = re.search(r"(\d+(?:\.\d+)?) fps", result.stderr)
    if fps_match:
        fps = float(fps_match.group(1))

    for line in result.stderr.splitlines():
        if "pts_time:" in line and "showinfo" in line:
            m = re.search(r"pts_time:(\d+(?:\.\d+)?)", line)
            if m:
                ts = float(m.group(1))
                frame_idx = int(ts * fps)
                shots.append({
                    "frame_idx": frame_idx,
                    "timestamp_s": ts,
                    "probability": threshold,
                })
    return shots


def _detect_opencv(
    video_path: Path,
    threshold: float,
    sample_every: int = 10,
) -> list[dict]:
    """OpenCV pixel-difference fallback (slow on H.264)."""
    try:
        import cv2  # type: ignore
    except ImportError:
        return []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    shots = []
    prev_frame = None

    for frame_idx in range(0, total_frames, sample_every):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        if prev_frame is not None:
            diff = float(np.mean(np.abs(gray - prev_frame)))
            if diff > threshold * 0.2:
                shots.append({
                    "frame_idx": int(frame_idx),
                    "probability": min(1.0, diff * 5.0),
                })
        prev_frame = gray

    cap.release()
    return shots


def shots_to_timestamps(
    shots: list[dict],
    video_path: Path | str,
) -> list[float]:
    """Convert shot boundary frame indices to timestamps in seconds."""
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        cap.release()
    except ImportError:
        fps = 25.0

    return [s["frame_idx"] / fps for s in shots]


def shots_to_boundaries(
    shots: list[dict],
    n_sentences: int,
    sentence_times: list[float],
) -> list[int]:
    """
    Map shot boundary timestamps to sentence indices.

    For each shot boundary, find the nearest sentence by timestamp.

    Args:
        shots:          output of detect_shots()
        n_sentences:    total number of sentences
        sentence_times: list of sentence start times (seconds)

    Returns:
        Sorted list of sentence boundary indices (0-based, exclusive of 0 and n_sentences).
    """
    if not shots or not sentence_times:
        return []

    times = np.array(sentence_times)
    boundaries = set()
    for shot in shots:
        # frame_idx → approximate timestamp (assume 25fps if not provided)
        ts = shot.get("timestamp_s", shot["frame_idx"] / 25.0)
        idx = int(np.argmin(np.abs(times - ts)))
        if 0 < idx < n_sentences:
            boundaries.add(idx)

    return sorted(boundaries)


def detect_and_save(
    video_path: Path | str,
    out_path: Path | str,
    threshold: float = 0.5,
) -> list[dict]:
    """Detect shots in a video and save results to JSON."""
    shots = detect_shots(video_path, threshold=threshold)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(shots, indent=2), encoding="utf-8")
    return shots


def detect_all(
    videos_dir: Path | str,
    shots_dir: Path | str,
    threshold: float = 0.5,
    force: bool = False,
) -> dict[str, int]:
    """
    Detect shots in all videos in a directory.

    Returns:
        dict mapping video_id -> n_shots
    """
    videos_dir = Path(videos_dir)
    shots_dir = Path(shots_dir)
    shots_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for video_file in sorted(videos_dir.glob("*.mp4")):
        video_id = video_file.stem
        out_path = shots_dir / f"{video_id}_shots.json"
        if out_path.exists() and not force:
            shots = json.loads(out_path.read_text(encoding="utf-8"))
        else:
            shots = detect_and_save(video_file, out_path, threshold=threshold)
        results[video_id] = len(shots)

    return results
