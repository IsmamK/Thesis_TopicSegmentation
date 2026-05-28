"""
T14 — Transcribe all 30 videos with Whisper large-v3 (faster-whisper).

Run:
    python scripts/transcribe.py
    python scripts/transcribe.py --video-id 8yT4RZy1t3s   # single video

Writes:
    data/transcripts/<video_id>/transcript.json   — word-level segments
    data/transcripts/<video_id>/transcript.txt    — plain text (for inspection)

transcript.json schema:
    {
      "video_id": "...",
      "language": "en",
      "segments": [
        {"start": 0.0, "end": 3.2, "text": "Hello everyone ...", "words": [
          {"word": "Hello", "start": 0.0, "end": 0.4},
          ...
        ]}
      ]
    }
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"
MANIFEST = ROOT / "data" / "manifest.jsonl"

console = Console()
app = typer.Typer(add_completion=False)


def load_video_ids() -> list[str]:
    if MANIFEST.exists():
        ids = []
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                ids.append(json.loads(line)["id"])
        return ids
    # fallback: scan raw dir
    return [p.name for p in RAW_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")]


def transcribe_one(video_id: str, model, device: str) -> dict:
    audio_path = RAW_DIR / video_id / "audio.wav"
    if not audio_path.exists():
        raise FileNotFoundError(f"audio.wav not found for {video_id}")

    segments_out, info = model.transcribe(
        str(audio_path),
        language="en",
        word_timestamps=True,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    segments = []
    for seg in segments_out:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)})
        segments.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": words,
        })

    return {
        "video_id": video_id,
        "language": info.language,
        "duration_sec": round(info.duration, 1),
        "segments": segments,
    }


@app.command()
def main(
    video_id: str = typer.Option(None, "--video-id", "-v", help="Transcribe a single video ID"),
    device: str = typer.Option("auto", "--device", help="cpu / cuda / auto"),
    model_size: str = typer.Option("large-v3", "--model", help="Whisper model size"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip", help="Skip already transcribed videos"),
):
    from faster_whisper import WhisperModel

    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    compute = "float16" if device == "cuda" else "int8"
    console.print(f"[bold]Loading Whisper {model_size}[/bold] on {device} ({compute})")
    model = WhisperModel(model_size, device=device, compute_type=compute)

    ids = [video_id] if video_id else load_video_ids()
    console.print(f"Videos to transcribe: {len(ids)}")

    done, skipped, failed = 0, 0, 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as prog:
        task = prog.add_task("Transcribing...", total=len(ids))

        for vid in ids:
            out_dir = TRANSCRIPT_DIR / vid
            out_json = out_dir / "transcript.json"

            if skip_existing and out_json.exists():
                prog.advance(task)
                skipped += 1
                continue

            prog.update(task, description=f"[cyan]{vid}[/cyan]")
            t0 = time.time()

            try:
                data = transcribe_one(vid, model, device)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

                # plain text for easy inspection
                txt = "\n".join(s["text"] for s in data["segments"])
                (out_dir / "transcript.txt").write_text(txt, encoding="utf-8")

                elapsed = time.time() - t0
                console.print(
                    f"[green]✓[/green] {vid}  "
                    f"{len(data['segments'])} segments  "
                    f"{elapsed:.0f}s"
                )
                done += 1
            except Exception as exc:
                console.print(f"[red]✗[/red] {vid}: {exc}")
                failed += 1

            prog.advance(task)

    console.print(
        f"\n[bold]Done.[/bold] Transcribed: {done}  Skipped: {skipped}  Failed: {failed}"
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    app()
