# T15 — Sentence Splitting from Whisper Output

**Phase 4 · Preprocessing · Estimated time: 1 h · Owner: Alimool**

---

## 🎯 What you are doing
Whisper outputs "segments" (~5-second audio chunks), not sentences. We merge/split those into proper sentences with timestamps. **This sentence timeline is the backbone of every downstream module.**

## ✅ How to know you are done
- `data/sentences/<video_id>.jsonl` exists for all 30, one sentence per line.
- Each sentence has: `idx, start_sec, end_sec, text, word_count`.
- Total sentences across all videos: 5,000–20,000 (rough range).

---

## 📝 Steps

### Ask Claude

> Execute T15. Write `src/lecseg/preprocess/sentencize.py` and `scripts/sentencize_all.py`.
>
> For each `data/whisper/<id>.json`:
> 1. Flatten the words list with their timestamps.
> 2. Re-concatenate into a single string, preserving spacing.
> 3. Use pysbd (`pysbd.Segmenter(language='en')`) to split into sentences.
> 4. For each sentence, recover the `start_sec` = first word's start, `end_sec` = last word's end.
> 5. Filter: drop sentences shorter than 3 words (usually transcription artefacts).
> 6. Write `data/sentences/<id>.jsonl` with one sentence per line.
>
> Also write `data/sentences/stats.csv`: video_id, num_sentences, avg_sent_sec, words_per_sent.

### Verify

```
python -c "import json; s = [json.loads(l) for l in open('data/sentences/<some_id>.jsonl')]; print(len(s), 'sentences;', s[0])"
```

First line should look like: `{"idx":0,"start_sec":3.2,"end_sec":8.1,"text":"Welcome to lecture one.","word_count":4}`.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **pysbd** | Python Sentence Boundary Disambiguation. A rules-based splitter that is robust to messy transcription. |
| **Sentence timeline** | Every sentence has a `start_sec`. The list of start_secs is our "time axis" for everything else. |

---

## ➡️ When done

```
python scripts/mark_done.py T15
python scripts/today.py
```
