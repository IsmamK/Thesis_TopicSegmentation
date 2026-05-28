"""
T12 — Auto-annotate subtopics using LLM (Ollama) from Whisper transcripts.

Run:
    python scripts/autoannotate.py                    # all 30 videos, primary draft
    python scripts/autoannotate.py --double           # second LLM run (different temp) for 10 videos
    python scripts/autoannotate.py --video-id XYZ     # single video

Reads:
    data/transcripts/<video_id>/transcript.json
    data/gt/<video_id>.json

Writes:
    data/gt_hier/<video_id>.json          (status: "draft")
    data/gt_hier/double/<video_id>.json   (status: "draft", annotator: "llm_b")

The annotate.py Streamlit tool detects status=="draft" and loads these as
pre-filled suggestions for human review.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

ROOT = Path(__file__).resolve().parent.parent
GT_DIR = ROOT / "data" / "gt"
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"
GT_HIER = ROOT / "data" / "gt_hier"
GT_HIER_DOUBLE = GT_HIER / "double"
MANIFEST = ROOT / "data" / "manifest.jsonl"

console = Console()
app = typer.Typer(add_completion=False)

# 10 videos selected for double-annotation (first 10 from manifest)
DOUBLE_ANNOTATION_COUNT = 10


def load_video_ids() -> list[str]:
    if MANIFEST.exists():
        return [json.loads(l)["id"] for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [p.name for p in (ROOT / "data" / "raw").iterdir() if p.is_dir() and not p.name.startswith(".")]


def load_gt(video_id: str) -> dict:
    p = GT_DIR / f"{video_id}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_transcript(video_id: str) -> list[dict] | None:
    p = TRANSCRIPT_DIR / video_id / "transcript.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))["segments"]


def extract_chapter_text(segments: list[dict], start_sec: float, end_sec: float) -> str:
    """Concatenate transcript text that falls within [start_sec, end_sec)."""
    parts = []
    for seg in segments:
        if seg["end"] <= start_sec:
            continue
        if seg["start"] >= end_sec:
            break
        parts.append(seg["text"])
    return " ".join(parts).strip()


def fmt_sec(s: float) -> str:
    s = int(s)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def parse_time(s: str) -> float | None:
    s = s.strip()
    parts = s.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(s)
    except (ValueError, IndexError):
        return None


def build_prompt(ch_title: str, ch_start: float, ch_end: float, text: str, temperature_hint: str = "") -> str:
    duration_min = (ch_end - ch_start) / 60
    return f"""You are an expert lecture analyst. Analyze this lecture chapter and identify subtopic boundaries.

Chapter title: "{ch_title}"
Chapter time: {fmt_sec(ch_start)} → {fmt_sec(ch_end)} ({duration_min:.1f} minutes)
{temperature_hint}
Transcript:
{text[:4000]}

Task: Identify 2–5 subtopic boundaries where the speaker clearly shifts focus within this chapter.
Rules:
- Each subtopic must be at least 60 seconds long
- Title must be a short noun phrase, max 8 words, matching the speaker's language
- First subtopic always starts at the chapter start time ({fmt_sec(ch_start)})
- Timestamps must be within [{fmt_sec(ch_start)}, {fmt_sec(ch_end)}]

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{
  "subtopics": [
    {{"start": "HH:MM:SS", "title": "Short noun phrase"}},
    {{"start": "HH:MM:SS", "title": "Short noun phrase"}}
  ]
}}"""


def call_ollama(prompt: str, model: str, temperature: float) -> str:
    import urllib.request
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 512},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["response"]


def parse_llm_response(response: str, ch_start: float, ch_end: float, ch_idx: int) -> list[dict]:
    """Extract subtopics from LLM JSON response, with fallback parsing."""
    # Try to find JSON block
    match = re.search(r'\{[\s\S]*"subtopics"[\s\S]*\}', response)
    if not match:
        return []
    try:
        data = json.loads(match.group())
        subtopics = []
        for item in data.get("subtopics", []):
            t = parse_time(item.get("start", ""))
            title = item.get("title", "").strip()
            if t is None or not title:
                continue
            # clamp to chapter bounds
            t = max(ch_start, min(t, ch_end - 60))
            subtopics.append({"start_sec": round(t, 1), "chapter_idx": ch_idx, "title": title})
        # ensure first subtopic starts at chapter start
        if subtopics and subtopics[0]["start_sec"] != ch_start:
            subtopics[0]["start_sec"] = ch_start
        return subtopics
    except (json.JSONDecodeError, KeyError):
        return []


def annotate_video(
    video_id: str,
    model: str,
    temperature: float,
    double: bool,
    skip_existing: bool,
) -> bool:
    out_dir = GT_HIER_DOUBLE if double else GT_HIER
    out_path = out_dir / f"{video_id}.json"

    if skip_existing and out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        if existing.get("status") in ("draft", "reviewed"):
            return True  # already done

    gt = load_gt(video_id)
    if not gt:
        console.print(f"[yellow]No GT found for {video_id}[/yellow]")
        return False

    segments = load_transcript(video_id)
    if segments is None:
        console.print(f"[yellow]No transcript for {video_id} — run transcribe.py first[/yellow]")
        return False

    titles = gt.get("titles", [])
    boundaries = [0.0] + gt.get("boundaries_sec", []) + [gt.get("duration_sec", 0)]
    chapter_starts = boundaries[:-1]
    chapter_ends = boundaries[1:]

    annotator_id = "llm_b" if double else "llm_a"
    temp_hint = "Focus on finding nuanced sub-divisions." if double else ""

    all_subtopics: list[dict] = []

    for ch_idx, (ch_title, ch_start, ch_end) in enumerate(zip(titles, chapter_starts, chapter_ends)):
        ch_duration = ch_end - ch_start
        if ch_duration < 120:
            # chapter too short for meaningful subtopics — use chapter itself
            all_subtopics.append({"start_sec": ch_start, "chapter_idx": ch_idx, "title": ch_title})
            continue

        text = extract_chapter_text(segments, ch_start, ch_end)
        if len(text) < 100:
            all_subtopics.append({"start_sec": ch_start, "chapter_idx": ch_idx, "title": ch_title})
            continue

        prompt = build_prompt(ch_title, ch_start, ch_end, text, temp_hint)
        try:
            response = call_ollama(prompt, model, temperature)
            subs = parse_llm_response(response, ch_start, ch_end, ch_idx)
            if subs:
                all_subtopics.extend(subs)
            else:
                # fallback: single subtopic = whole chapter
                all_subtopics.append({"start_sec": ch_start, "chapter_idx": ch_idx, "title": ch_title})
        except Exception as exc:
            console.print(f"  [red]LLM error ch{ch_idx}:[/red] {exc}")
            all_subtopics.append({"start_sec": ch_start, "chapter_idx": ch_idx, "title": ch_title})

    out_dir.mkdir(parents=True, exist_ok=True)
    out_data = {
        "video_id": video_id,
        "annotator": annotator_id,
        "status": "draft",
        "double_mode": double,
        "chapters": [{"start_sec": s, "title": t} for s, t in zip(chapter_starts, titles)],
        "subtopics": sorted(all_subtopics, key=lambda x: x["start_sec"]),
    }
    out_path.write_text(json.dumps(out_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


@app.command()
def main(
    video_id: str = typer.Option(None, "--video-id", "-v"),
    model: str = typer.Option("llama3.1:8b", "--model", "-m", help="Ollama model to use"),
    double: bool = typer.Option(False, "--double", help="Generate second annotator drafts"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip"),
):
    all_ids = load_video_ids()

    if video_id:
        ids = [video_id]
    elif double:
        ids = all_ids[:DOUBLE_ANNOTATION_COUNT]
        console.print(f"Double-annotation mode: processing first {len(ids)} videos")
    else:
        ids = all_ids
        console.print(f"Primary annotation: processing {len(ids)} videos")

    # Use different temperature for double run to get natural variation
    temperature = 0.4 if double else 0.1

    done, failed = 0, 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as prog:
        task = prog.add_task("Annotating...", total=len(ids))

        for vid in ids:
            prog.update(task, description=f"[cyan]{vid}[/cyan]")
            ok = annotate_video(vid, model, temperature, double, skip_existing)
            if ok:
                done += 1
            else:
                failed += 1
            prog.advance(task)

    console.print(f"\n[bold]Done.[/bold] Generated: {done}  Failed: {failed}")
    console.print("Run [bold]streamlit run scripts/annotate.py[/bold] to review drafts.")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    app()
