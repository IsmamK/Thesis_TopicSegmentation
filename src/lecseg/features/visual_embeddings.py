"""
T20 — Visual embeddings (CLIP on keyframes).

Extracts CLIP image embeddings from video keyframes for visual coherence
features. Keyframes are extracted at regular intervals or at detected
shot boundaries (T16, when available).

The CLIP model is ViT-B/32 by default (OpenAI CLIP).
Embeddings are 512-dim float32, L2-normalised.

Usage:
    from lecseg.features.visual_embeddings import embed_keyframes, extract_keyframes

    frames = extract_keyframes("data/videos/vid.mp4", fps=1)
    vecs = embed_keyframes(frames)  # (N, 512) array

Note: Requires `clip` package: pip install git+https://github.com/openai/CLIP.git
Gracefully falls back to zero vectors if CLIP is unavailable (for testing).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

CLIP_DIM = 512
_clip_model = None
_clip_preprocess = None


def _try_load_clip(model_name: str = "ViT-B/32"):
    """Try to load CLIP model; returns (model, preprocess) or (None, None)."""
    global _clip_model, _clip_preprocess
    if _clip_model is not None:
        return _clip_model, _clip_preprocess
    try:
        import clip
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _clip_model, _clip_preprocess = clip.load(model_name, device=device)
        return _clip_model, _clip_preprocess
    except ImportError:
        return None, None


def embed_keyframes(
    frames: list,
    model_name: str = "ViT-B/32",
    batch_size: int = 32,
) -> np.ndarray:
    """
    Embed a list of PIL images using CLIP.

    Args:
        frames:     list of PIL Image objects
        model_name: CLIP model variant
        batch_size: encoding batch size

    Returns:
        np.ndarray of shape (N, 512), float32, L2-normalised.
        Returns zero array if CLIP is unavailable.
    """
    if not frames:
        return np.zeros((0, CLIP_DIM), dtype=np.float32)

    model, preprocess = _try_load_clip(model_name)
    if model is None:
        # CLIP not available — return zero embeddings (graceful fallback)
        return np.zeros((len(frames), CLIP_DIM), dtype=np.float32)

    import torch
    device = next(model.parameters()).device

    all_vecs = []
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i + batch_size]
        images = torch.stack([preprocess(img) for img in batch]).to(device)
        with torch.no_grad():
            vecs = model.encode_image(images).float().cpu().numpy()
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / np.maximum(norms, 1e-8)
        all_vecs.append(vecs)

    return np.concatenate(all_vecs, axis=0).astype(np.float32)


def extract_keyframes(
    video_path: Path | str,
    fps: float = 1.0,
    max_frames: int = 1000,
) -> tuple[list, list[float]]:
    """
    Extract keyframes from a video at `fps` frames per second.

    Requires ffmpeg and opencv-python.

    Args:
        video_path: path to video file
        fps:        frames per second to extract
        max_frames: maximum number of frames to extract

    Returns:
        (frames, timestamps) — list of PIL Images and their timestamps in seconds.
    """
    try:
        import cv2
        from PIL import Image
    except ImportError:
        raise ImportError("pip install opencv-python Pillow")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(1, int(video_fps / fps))

    frames, timestamps = [], []
    frame_idx = 0

    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            frames.append(pil_img)
            timestamps.append(frame_idx / video_fps)
        frame_idx += 1

    cap.release()
    return frames, timestamps


def embed_video(
    video_path: Path | str,
    out_path: Path | str | None = None,
    fps: float = 1.0,
    model_name: str = "ViT-B/32",
) -> tuple[np.ndarray, list[float]]:
    """
    Extract keyframes from a video and embed them with CLIP.

    Args:
        video_path: path to video file
        out_path:   save embeddings as .npy (None = don't save)
        fps:        keyframe extraction rate
        model_name: CLIP model

    Returns:
        (embeddings, timestamps) — (N, 512) array and list of timestamps.
    """
    frames, timestamps = extract_keyframes(video_path, fps=fps)
    vecs = embed_keyframes(frames, model_name=model_name)

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(out_path), vecs)
        ts_path = out_path.with_suffix(".json")
        ts_path.write_text(json.dumps(timestamps), encoding="utf-8")

    return vecs, timestamps
