# T18 — Prosody Feature Extraction (Pauses, Pitch)

**Phase 4 · Preprocessing · Estimated time: 2 h · Owner: Alimool**

---

## 🎯 What you are doing
Computing per-sentence prosody features from the raw audio: pause length before the sentence, pitch change, and speech-rate shift. Humans use these to signal "topic change coming" — the model should too.

## ✅ How to know you are done
- `data/prosody/<video_id>.csv` exists for all 30, one row per sentence, columns: `idx, pause_before_sec, pitch_delta_hz, rate_delta_wpm`.

---

## 📝 Steps

### Ask Claude

> Execute T18. Write `src/lecseg/preprocess/prosody.py` and `scripts/extract_prosody.py`.
>
> For each video, load `data/raw/<id>/audio.wav` (librosa) and read `data/sentences/<id>.jsonl`.
>
> For every sentence i:
> - `pause_before_sec` = sentence[i].start_sec − sentence[i-1].end_sec (0 for the first sentence).
> - `pitch_delta_hz` = median(f0) over 0.5 s right BEFORE sentence start, minus median(f0) over 0.5 s AFTER sentence start. Use librosa's `pyin` or `piptrack`.
> - `rate_delta_wpm` = sentence[i].wpm − mean(sentence[i-3..i-1].wpm).
>
> Save as CSV.

### Verify

```
python -c "import pandas as pd; df = pd.read_csv('data/prosody/<some_id>.csv'); print(df.describe())"
```

`pause_before_sec` should have a median ≈ 0.3–0.8 s and occasional outliers of 3–10 s (those are the topic-shift pauses we care about).

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Prosody** | The music of speech — pitch, rhythm, pauses. Not the words themselves. |
| **f0 (fundamental frequency)** | Pitch — how high/low the voice is. Measured in Hz. |
| **WPM** | Words Per Minute. Speaking rate. |

More: [docs/CONCEPTS.md#prosody](../docs/CONCEPTS.md#prosody)

---

## ➡️ When done

```
python scripts/mark_done.py T18
python scripts/today.py
```
