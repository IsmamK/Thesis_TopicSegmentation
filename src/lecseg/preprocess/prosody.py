"""
T18 — Prosody feature extraction (pauses, pitch).

Extracts pause duration and pitch (F0) features from audio files.
Uses librosa for pitch extraction; pause detection from Whisper segment gaps.

Usage:
    from lecseg.preprocess.prosody import extract_pauses, extract_pitch, prosody_features
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def extract_pauses(
    transcript: dict,
    sentence_times: list[float],
    min_pause_s: float = 0.3,
) -> np.ndarray:
    """
    Extract pause duration before each sentence from Whisper transcript.

    A pause is the gap between the end of one Whisper segment and the start of the next.

    Args:
        transcript:     Whisper transcript dict with 'segments' list
        sentence_times: list of sentence start times (seconds)
        min_pause_s:    minimum gap to count as a pause

    Returns:
        np.ndarray of shape (n_sentences,), float32 — pause duration in seconds.
        0.0 if no significant pause before that sentence.
    """
    segments = transcript.get("segments", [])
    if not segments:
        return np.zeros(len(sentence_times), dtype=np.float32)

    # Build pause events from segment gaps
    pauses: list[tuple[float, float]] = []  # (time, duration)
    for i in range(1, len(segments)):
        gap = segments[i]["start"] - segments[i - 1]["end"]
        if gap >= min_pause_s:
            pauses.append((segments[i]["start"], gap))

    times = np.array(sentence_times)
    pause_features = np.zeros(len(sentence_times), dtype=np.float32)

    for pause_time, pause_dur in pauses:
        idx = int(np.argmin(np.abs(times - pause_time)))
        # keep largest pause if multiple map to same sentence
        pause_features[idx] = max(pause_features[idx], pause_dur)

    return pause_features


def extract_pitch(
    audio_path: Path | str,
    sentence_times: list[float],
    sr: int = 8000,
    hop_length: int = 256,
    chunk_sec: float = 300.0,
) -> np.ndarray:
    """
    Extract mean F0 pitch per sentence using librosa, processing in chunks to
    avoid OOM on long lecture audio files (some >2h at 44kHz).

    Uses 8kHz sample rate — sufficient for speech pitch (F0 < 500Hz) and
    reduces RAM by ~5x vs 44kHz.
    """
    try:
        import librosa  # type: ignore
    except ImportError:
        return np.zeros(len(sentence_times), dtype=np.float32)

    pitch_per_sentence = np.zeros(len(sentence_times), dtype=np.float32)
    sent_times = np.array(sentence_times)
    duration = sent_times[-1] + 10.0 if len(sent_times) else 0.0

    try:
        offset = 0.0
        all_f0, all_times = [], []
        while offset < duration:
            y_chunk, sr_actual = librosa.load(
                str(audio_path), sr=sr, mono=True,
                offset=offset, duration=chunk_sec,
            )
            if len(y_chunk) == 0:
                break
            f0_chunk, _, _ = librosa.pyin(
                y_chunk,
                fmin=librosa.note_to_hz("C2"),
                fmax=librosa.note_to_hz("C7"),
                sr=sr_actual, hop_length=hop_length,
            )
            f0_chunk = np.nan_to_num(f0_chunk, nan=0.0)
            t_chunk = librosa.frames_to_time(
                np.arange(len(f0_chunk)), sr=sr_actual, hop_length=hop_length
            ) + offset
            all_f0.append(f0_chunk)
            all_times.append(t_chunk)
            offset += chunk_sec

        if not all_f0:
            return pitch_per_sentence

        f0 = np.concatenate(all_f0)
        times_f0 = np.concatenate(all_times)

        for i, t_start in enumerate(sent_times):
            t_end = sent_times[i + 1] if i + 1 < len(sent_times) else times_f0[-1]
            mask = (times_f0 >= t_start) & (times_f0 < t_end) & (f0 > 0)
            if mask.any():
                pitch_per_sentence[i] = float(np.mean(f0[mask]))

    except MemoryError:
        pass  # return zeros — pauses feature still valid

    return pitch_per_sentence


def prosody_features(
    transcript: dict,
    sentence_times: list[float],
    audio_path: Path | str | None = None,
    min_pause_s: float = 0.3,
) -> np.ndarray:
    """
    Combine pause and pitch features into a (n_sentences, 2) array.

    Column 0: pause duration (seconds) before each sentence
    Column 1: mean F0 pitch (Hz) — zeros if audio_path is None or librosa unavailable

    Args:
        transcript:     Whisper transcript dict
        sentence_times: sentence start times
        audio_path:     path to audio file for pitch (optional)
        min_pause_s:    minimum pause threshold

    Returns:
        np.ndarray of shape (n_sentences, 2), float32
    """
    pauses = extract_pauses(transcript, sentence_times, min_pause_s)

    if audio_path is not None:
        pitch = extract_pitch(audio_path, sentence_times)
    else:
        pitch = np.zeros(len(sentence_times), dtype=np.float32)

    return np.stack([pauses, pitch], axis=1).astype(np.float32)


def prosody_and_save(
    transcript_path: Path | str,
    sentences_path: Path | str,
    out_path: Path | str,
    audio_path: Path | str | None = None,
) -> np.ndarray:
    """Extract prosody features and save as .npy."""
    transcript = json.loads(Path(transcript_path).read_text(encoding="utf-8"))
    sentences_data = json.loads(Path(sentences_path).read_text(encoding="utf-8"))
    sentence_list = sentences_data.get("sentences", sentences_data) if isinstance(sentences_data, dict) else sentences_data
    sentence_times = [s["start"] for s in sentence_list]

    feats = prosody_features(transcript, sentence_times, audio_path)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(out_path), feats)
    return feats


def prosody_all(
    transcripts_dir: Path | str,
    sentences_dir: Path | str,
    prosody_dir: Path | str,
    audio_dir: Path | str | None = None,
    force: bool = False,
) -> dict[str, tuple[int, int]]:
    """
    Extract prosody features for all videos.

    Returns:
        dict mapping video_id -> (n_sentences, n_features)
    """
    transcripts_dir = Path(transcripts_dir)
    sentences_dir = Path(sentences_dir)
    prosody_dir = Path(prosody_dir)
    prosody_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for t_path in sorted(transcripts_dir.glob("*/transcript.json")):
        video_id = t_path.parent.name
        s_path = sentences_dir / video_id / "sentences.json"
        if not s_path.exists():
            continue

        out_path = prosody_dir / f"{video_id}_prosody.npy"
        if out_path.exists() and not force:
            feats = np.load(str(out_path))
        else:
            a_path = None
            if audio_dir is not None:
                a_candidates = list(Path(audio_dir).glob(f"{video_id}.*"))
                if a_candidates:
                    a_path = a_candidates[0]
            feats = prosody_and_save(t_path, s_path, out_path, a_path)

        results[video_id] = (feats.shape[0], feats.shape[1])

    return results
