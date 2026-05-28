"""
T15 — Sentence splitting from Whisper transcript segments.

Whisper outputs time-aligned segments that roughly correspond to utterances,
but a single segment may contain multiple sentences or a sentence may span
segments. This module re-segments using spaCy's sentence boundary detector
while preserving approximate timestamps via linear interpolation.

Input:  data/transcripts/<video_id>/transcript.json
Output: data/sentences/<video_id>/sentences.json

Each output sentence record:
    {
        "idx":   0,           # 0-based sentence index within video
        "start": 12.5,        # estimated start time (seconds)
        "end":   18.3,        # estimated end time (seconds)
        "text":  "The cat sat on the mat."
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence


def _load_spacy():
    import spacy
    try:
        return spacy.load("en_core_web_sm", disable=["ner", "tagger", "parser", "lemmatizer"])
    except OSError:
        from spacy.lang.en import English
        nlp = English()
        nlp.add_pipe("sentencizer")
        return nlp


def split_transcript(
    transcript_path: Path | str,
    out_path: Path | str | None = None,
    min_tokens: int = 3,
) -> list[dict]:
    """
    Split a Whisper transcript.json into sentence-level records.

    Args:
        transcript_path: path to transcript.json
        out_path:        where to write sentences.json (None = don't write)
        min_tokens:      discard sentence fragments shorter than this

    Returns:
        List of sentence dicts with idx, start, end, text.
    """
    transcript_path = Path(transcript_path)
    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    segments = data.get("segments", [])

    if not segments:
        return []

    nlp = _load_spacy()
    if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")

    sentences: list[dict] = []
    idx = 0

    for seg in segments:
        seg_start: float = seg["start"]
        seg_end: float = seg["end"]
        text: str = seg["text"].strip()

        if not text:
            continue

        doc = nlp(text)
        sent_texts = [s.text.strip() for s in doc.sents if s.text.strip()]

        if not sent_texts:
            continue

        # Assign timestamps: distribute segment time proportionally by char length
        total_chars = max(sum(len(s) for s in sent_texts), 1)
        t = seg_start
        for sent_text in sent_texts:
            if len(sent_text.split()) < min_tokens:
                continue
            duration = (seg_end - seg_start) * len(sent_text) / total_chars
            sentences.append({
                "idx": idx,
                "start": round(t, 3),
                "end": round(t + duration, 3),
                "text": sent_text,
            })
            t += duration
            idx += 1

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"video_id": data.get("video_id"), "sentences": sentences},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return sentences


def split_all(
    transcripts_dir: Path | str = "data/transcripts",
    sentences_dir: Path | str = "data/sentences",
    force: bool = False,
) -> dict[str, int]:
    """
    Process all transcript.json files under transcripts_dir.

    Returns:
        Dict mapping video_id -> sentence count.
    """
    transcripts_dir = Path(transcripts_dir)
    sentences_dir = Path(sentences_dir)
    results: dict[str, int] = {}

    for transcript_json in sorted(transcripts_dir.glob("*/transcript.json")):
        video_id = transcript_json.parent.name
        out_path = sentences_dir / video_id / "sentences.json"

        if out_path.exists() and not force:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            results[video_id] = len(existing.get("sentences", []))
            continue

        sents = split_transcript(transcript_json, out_path)
        results[video_id] = len(sents)
        print(f"  {video_id}: {len(sents)} sentences")

    return results


if __name__ == "__main__":
    import sys
    transcripts_dir = sys.argv[1] if len(sys.argv) > 1 else "data/transcripts"
    sentences_dir = sys.argv[2] if len(sys.argv) > 2 else "data/sentences"
    print(f"Splitting transcripts: {transcripts_dir} -> {sentences_dir}")
    results = split_all(transcripts_dir, sentences_dir)
    total = sum(results.values())
    print(f"\nDone. {len(results)} videos, {total} total sentences.")
