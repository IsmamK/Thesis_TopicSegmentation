"""Tests for T16 shot detection, T17 OCR, T18 prosody — no heavy deps required."""
from __future__ import annotations

import numpy as np
import pytest

from lecseg.preprocess.shot_detection import shots_to_boundaries
from lecseg.preprocess.ocr import ocr_to_sentences
from lecseg.preprocess.prosody import extract_pauses, prosody_features


# ── T16 shot detection ────────────────────────────────────────────────────────

def test_shots_to_boundaries_empty():
    result = shots_to_boundaries([], n_sentences=10, sentence_times=list(range(10)))
    assert result == []


def test_shots_to_boundaries_maps_correctly():
    shots = [{"frame_idx": 50, "probability": 0.9, "timestamp_s": 2.0}]
    sentence_times = [0.0, 1.0, 2.1, 3.0, 4.0]
    result = shots_to_boundaries(shots, n_sentences=5, sentence_times=sentence_times)
    assert 2 in result  # nearest sentence to t=2.0 is index 2 (t=2.1)


def test_shots_to_boundaries_excludes_endpoints():
    shots = [{"frame_idx": 0, "timestamp_s": 0.0, "probability": 1.0},
             {"frame_idx": 1000, "timestamp_s": 100.0, "probability": 1.0}]
    sentence_times = [0.0, 10.0, 20.0, 30.0, 100.0]
    result = shots_to_boundaries(shots, n_sentences=5, sentence_times=sentence_times)
    # idx 0 and 4 (last) should be excluded
    assert 0 not in result
    assert 5 not in result


# ── T17 OCR ───────────────────────────────────────────────────────────────────

def test_ocr_to_sentences_empty():
    result = ocr_to_sentences([], sentence_times=[0.0, 1.0, 2.0])
    assert result == ["", "", ""]


def test_ocr_to_sentences_assigns_nearest():
    ocr_results = [
        {"frame_idx": 10, "timestamp_s": 1.05, "text": "Hello World"},
    ]
    sentence_times = [0.0, 1.0, 2.0]
    result = ocr_to_sentences(ocr_results, sentence_times)
    assert result[1] == "Hello World"
    assert result[0] == ""
    assert result[2] == ""


def test_ocr_to_sentences_concatenates_multiple():
    ocr_results = [
        {"frame_idx": 5, "timestamp_s": 0.9, "text": "Introduction"},
        {"frame_idx": 10, "timestamp_s": 1.1, "text": "to AI"},
    ]
    sentence_times = [0.0, 1.0, 2.0]
    result = ocr_to_sentences(ocr_results, sentence_times)
    assert "Introduction" in result[1] or "Introduction" in result[0]


# ── T18 prosody ───────────────────────────────────────────────────────────────

def _make_transcript(*gaps):
    """Build a fake Whisper transcript with specified inter-segment gaps."""
    segments = []
    t = 0.0
    for i, gap in enumerate(gaps):
        segments.append({"start": t, "end": t + 1.0, "text": f"seg{i}"})
        t += 1.0 + gap
    segments.append({"start": t, "end": t + 1.0, "text": "last"})
    return {"segments": segments}


def test_extract_pauses_no_pauses():
    transcript = _make_transcript(0.0, 0.0, 0.0)
    sentence_times = [0.0, 1.0, 2.0, 3.0]
    pauses = extract_pauses(transcript, sentence_times, min_pause_s=0.3)
    assert pauses.shape == (4,)
    assert pauses.sum() == 0.0


def test_extract_pauses_detects_gap():
    transcript = _make_transcript(0.0, 2.0, 0.0)  # 2s gap after segment 1
    sentence_times = [0.0, 1.0, 2.0, 3.5, 4.5]
    pauses = extract_pauses(transcript, sentence_times, min_pause_s=0.3)
    assert pauses.max() >= 2.0


def test_prosody_features_shape():
    transcript = _make_transcript(1.0, 0.1, 0.5)
    sentence_times = [0.0, 2.0, 4.0, 5.5]
    feats = prosody_features(transcript, sentence_times, audio_path=None)
    assert feats.shape == (4, 2)
    assert feats.dtype == np.float32


def test_prosody_features_pause_col_nonzero():
    transcript = _make_transcript(0.0, 3.0, 0.0)
    sentence_times = [0.0, 1.0, 2.1, 4.5]
    feats = prosody_features(transcript, sentence_times, audio_path=None)
    # column 0 = pauses; at least one should be > 0
    assert feats[:, 0].max() > 0
    # column 1 = pitch; all zero since no audio
    assert feats[:, 1].sum() == 0.0
