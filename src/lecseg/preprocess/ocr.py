"""
T17 — Slide OCR (PaddleOCR).

Extracts text from lecture slide keyframes using PaddleOCR.
Falls back gracefully if PaddleOCR is not installed.

Usage:
    from lecseg.preprocess.ocr import ocr_frame, ocr_video

    texts = ocr_video("data/videos/vid.mp4", fps=0.5)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np


_ocr_engine = None


def _get_ocr():
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine
    try:
        from paddleocr import PaddleOCR  # type: ignore
        _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        return _ocr_engine
    except ImportError:
        return None


def ocr_frame(frame_array: np.ndarray) -> str:
    """
    Run OCR on a single frame (HxWx3 uint8 numpy array).

    Returns:
        Extracted text as a single string (lines joined by space).
        Returns empty string if PaddleOCR is unavailable.
    """
    ocr = _get_ocr()
    if ocr is None:
        return ""

    result = ocr.ocr(frame_array, cls=True)
    if not result or not result[0]:
        return ""

    lines = []
    for line in result[0]:
        if line and len(line) >= 2:
            text, confidence = line[1]
            if confidence > 0.5:
                lines.append(text.strip())

    return " ".join(lines)


def ocr_video(
    video_path: Path | str,
    fps: float = 0.5,
    max_frames: int = 500,
) -> list[dict]:
    """
    Extract text from video keyframes using PaddleOCR.

    Args:
        video_path: path to video file
        fps:        keyframe extraction rate (frames per second)
        max_frames: maximum frames to process

    Returns:
        List of dicts: {frame_idx, timestamp_s, text}
    """
    try:
        import cv2  # type: ignore
    except ImportError:
        raise ImportError("pip install opencv-python")

    video_path = Path(video_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(1, int(video_fps / fps))

    results = []
    frame_idx = 0

    while len(results) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            rgb = frame[:, :, ::-1]  # BGR -> RGB
            text = ocr_frame(rgb)
            if text:
                results.append({
                    "frame_idx": int(frame_idx),
                    "timestamp_s": round(frame_idx / video_fps, 3),
                    "text": text,
                })
        frame_idx += 1

    cap.release()
    return results


def ocr_to_sentences(
    ocr_results: list[dict],
    sentence_times: list[float],
) -> list[str]:
    """
    Assign OCR text to sentences by nearest timestamp.

    Args:
        ocr_results:    output of ocr_video()
        sentence_times: list of sentence start times (seconds)

    Returns:
        List of length n_sentences; each element is concatenated OCR text
        for that sentence (empty string if no OCR text nearby).
    """
    if not ocr_results or not sentence_times:
        return [""] * len(sentence_times)

    times = np.array(sentence_times)
    sentence_texts: list[list[str]] = [[] for _ in range(len(sentence_times))]

    for item in ocr_results:
        ts = item["timestamp_s"]
        idx = int(np.argmin(np.abs(times - ts)))
        sentence_texts[idx].append(item["text"])

    return [" ".join(parts) for parts in sentence_texts]


def ocr_and_save(
    video_path: Path | str,
    out_path: Path | str,
    fps: float = 0.5,
) -> list[dict]:
    """Run OCR on a video and save results to JSON."""
    results = ocr_video(video_path, fps=fps)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def ocr_all(
    videos_dir: Path | str,
    ocr_dir: Path | str,
    fps: float = 0.5,
    force: bool = False,
) -> dict[str, int]:
    """
    Run OCR on all videos in a directory.

    Returns:
        dict mapping video_id -> n_frames_with_text
    """
    videos_dir = Path(videos_dir)
    ocr_dir = Path(ocr_dir)
    ocr_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for video_file in sorted(videos_dir.glob("*.mp4")):
        video_id = video_file.stem
        out_path = ocr_dir / f"{video_id}_ocr.json"
        if out_path.exists() and not force:
            data = json.loads(out_path.read_text(encoding="utf-8"))
        else:
            data = ocr_and_save(video_file, out_path, fps=fps)
        results[video_id] = len(data)

    return results
