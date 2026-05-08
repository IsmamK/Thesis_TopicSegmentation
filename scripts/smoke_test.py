from __future__ import annotations

import math
import subprocess
import sys
import time
import traceback
from pathlib import Path
from urllib.request import urlretrieve


FAILURES = []


def check(name: str, fn):
    try:
        result = fn()
        if result is None:
            result = ""
        print(f"[PASS] {name}{': ' + str(result) if result else ''}")
    except Exception as e:
        FAILURES.append(name)
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()


def check_python():
    version = sys.version.split()[0]
    if sys.version_info < (3, 11):
        raise RuntimeError(f"Python >=3.11 required, got {version}")
    return version


def check_imports():
    import torch
    import transformers
    import sentence_transformers
    import faster_whisper
    import segeval
    import librosa

    return f"torch {torch.__version__}"


def check_ffmpeg():
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.splitlines()[0]


def check_pdflatex():
    result = subprocess.run(
        ["pdflatex", "--version"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.splitlines()[0]


def download_audio():
    data_dir = Path("data/smoke")
    data_dir.mkdir(parents=True, exist_ok=True)

    audio_path = data_dir / "jfk.flac"
    url = "https://github.com/SYSTRAN/faster-whisper/raw/master/tests/data/jfk.flac"

    if not audio_path.exists():
        urlretrieve(url, audio_path)

    size_kb = audio_path.stat().st_size / 1024
    if size_kb < 10:
        raise RuntimeError("Downloaded audio looks too small")

    return audio_path


def check_transcription():
    from faster_whisper import WhisperModel

    audio_path = download_audio()

    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), beam_size=1)

    text = " ".join(seg.text.strip() for seg in segments).strip()

    if not text:
        raise RuntimeError("Transcription returned empty text")

    return text[:120]


def check_sbert():
    import numpy as np
    from sentence_transformers import SentenceTransformer

    sentences = [
        "Lecture topic segmentation divides long lectures into coherent sections.",
        "Sentence embeddings help compare semantic similarity between text segments.",
        "The weather today is unrelated to lecture segmentation.",
    ]

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(sentences)

    if len(embeddings.shape) != 2:
        raise RuntimeError(f"Expected 2D embedding matrix, got {embeddings.shape}")

    def cosine(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    sim_01 = cosine(embeddings[0], embeddings[1])
    sim_02 = cosine(embeddings[0], embeddings[2])

    if not math.isfinite(sim_01) or not math.isfinite(sim_02):
        raise RuntimeError("Cosine similarity is not finite")

    return f"embedding shape = {embeddings.shape}, sim01={sim_01:.3f}, sim02={sim_02:.3f}"


def check_ollama():
    import ollama

    response = ollama.generate(
        model="llama3.1:8b",
        prompt="Reply with exactly one word: OK",
    )

    text = response.get("response", "").strip()

    if not text:
        raise RuntimeError("Ollama returned empty response")

    return text


def main():
    start = time.time()

    check("Python version", check_python)
    check("Imports: torch, transformers, sentence_transformers, faster_whisper, segeval, librosa", check_imports)
    check("ffmpeg available", check_ffmpeg)
    check("pdflatex available", check_pdflatex)
    check("Downloaded sample audio and transcribed with faster-whisper tiny.en", check_transcription)
    check("SBERT embedding and cosine similarity", check_sbert)
    check("Ollama llama3.1:8b responds", check_ollama)

    total = time.time() - start
    print(f"Total: {total:.1f}s")

    if FAILURES:
        print("❌ Smoke test failed.")
        print("Failed checks:", ", ".join(FAILURES))
        sys.exit(1)

    print("✅ All checks passed.")


if __name__ == "__main__":
    main()
