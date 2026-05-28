"""Tests for T15 sentence splitting from Whisper transcripts."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from lecseg.preprocess.sentence_split import split_transcript


@pytest.fixture
def simple_transcript(tmp_path):
    data = {
        "video_id": "test_vid",
        "language": "en",
        "duration_sec": 30.0,
        "segments": [
            {"start": 0.0, "end": 10.0,
             "text": "Hello everyone. Welcome to this lecture on machine learning."},
            {"start": 10.0, "end": 20.0,
             "text": "Today we will cover neural networks. They are very powerful models."},
            {"start": 20.0, "end": 30.0,
             "text": "Let us begin with the basics of gradient descent."},
        ],
    }
    p = tmp_path / "transcript.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.fixture
def single_sentence_transcript(tmp_path):
    data = {
        "video_id": "test_vid2",
        "language": "en",
        "duration_sec": 10.0,
        "segments": [
            {"start": 0.0, "end": 10.0, "text": "This is a single long sentence that spans the whole segment."},
        ],
    }
    p = tmp_path / "transcript.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.fixture
def empty_transcript(tmp_path):
    data = {"video_id": "empty", "language": "en", "duration_sec": 0.0, "segments": []}
    p = tmp_path / "transcript.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_returns_list(simple_transcript):
    result = split_transcript(simple_transcript)
    assert isinstance(result, list)


def test_sentence_count(simple_transcript):
    result = split_transcript(simple_transcript)
    # 3 segments with 2, 2, 1 sentences respectively = 5 sentences
    assert len(result) >= 4


def test_sentence_fields(simple_transcript):
    result = split_transcript(simple_transcript)
    for s in result:
        assert "idx" in s
        assert "start" in s
        assert "end" in s
        assert "text" in s


def test_idx_sequential(simple_transcript):
    result = split_transcript(simple_transcript)
    for i, s in enumerate(result):
        assert s["idx"] == i


def test_timestamps_ordered(simple_transcript):
    result = split_transcript(simple_transcript)
    for s in result:
        assert s["start"] <= s["end"]
    for i in range(1, len(result)):
        assert result[i]["start"] >= result[i - 1]["start"]


def test_timestamps_within_bounds(simple_transcript):
    result = split_transcript(simple_transcript)
    for s in result:
        assert s["start"] >= 0.0
        assert s["end"] <= 30.0 + 0.01  # slight float tolerance


def test_empty_transcript(empty_transcript):
    result = split_transcript(empty_transcript)
    assert result == []


def test_single_sentence(single_sentence_transcript):
    result = split_transcript(single_sentence_transcript)
    assert len(result) == 1
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == pytest.approx(10.0, abs=0.1)


def test_writes_output_file(simple_transcript, tmp_path):
    out = tmp_path / "sentences.json"
    split_transcript(simple_transcript, out_path=out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "sentences" in data
    assert "video_id" in data
