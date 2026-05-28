"""
Run on vast.ai: transcribe all MP3s with Whisper large-v3 on RTX 5090.

Usage:
    python3 vast_transcribe.py

Reads:  /workspace/mp3/*.mp3
Writes: /workspace/transcripts/<video_id>/transcript.json
        /workspace/transcripts/<video_id>/transcript.txt
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import json
import time
from pathlib import Path

# Preload CUDA libraries before ctranslate2 imports them
_cuda_lib_path = "/usr/local/lib/python3.12/dist-packages/nvidia"
for _lib in [
    f"{_cuda_lib_path}/cublas/lib/libcublas.so.12",
    f"{_cuda_lib_path}/cublas/lib/libcublasLt.so.12",
    f"{_cuda_lib_path}/cudnn/lib/libcudnn.so.9",
]:
    try:
        ctypes.CDLL(_lib)
    except OSError:
        pass

MP3_DIR = Path("/workspace/mp3")
OUT_DIR = Path("/workspace/transcripts")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def transcribe_all():
    from faster_whisper import WhisperModel

    print("Loading Whisper large-v3 on CUDA float16...")
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    print("Model loaded.\n")

    mp3_files = sorted(MP3_DIR.glob("*.mp3"))
    print(f"Found {len(mp3_files)} MP3 files\n")

    done, failed = 0, 0
    total_start = time.time()

    for mp3 in mp3_files:
        video_id = mp3.stem
        out_dir = OUT_DIR / video_id
        out_json = out_dir / "transcript.json"

        if out_json.exists():
            print(f"SKIP {video_id} (already done)")
            done += 1
            continue

        print(f"Transcribing {video_id} ...", flush=True)
        t0 = time.time()

        try:
            segments_iter, info = model.transcribe(
                str(mp3),
                language="en",
                word_timestamps=False,
                beam_size=1,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )

            segments = []
            for seg in segments_iter:
                segments.append({
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text.strip(),
                })

            data = {
                "video_id": video_id,
                "language": info.language,
                "duration_sec": round(info.duration, 1),
                "segments": segments,
            }

            out_dir.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            (out_dir / "transcript.txt").write_text(
                "\n".join(s["text"] for s in segments)
            )

            elapsed = time.time() - t0
            speed = info.duration / elapsed
            print(f"  OK  {len(segments)} segments  {elapsed:.0f}s  ({speed:.1f}x realtime)")
            done += 1

        except Exception as exc:
            print(f"  FAIL {video_id}: {exc}")
            failed += 1

    total = time.time() - total_start
    print(f"\nDone. Transcribed: {done}  Failed: {failed}  Total time: {total/60:.1f} min")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    transcribe_all()
