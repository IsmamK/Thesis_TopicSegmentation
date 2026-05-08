# T16 — Visual Shot-Boundary Detection (TransNetV2)

**Phase 4 · Preprocessing · Estimated time: 2 h for 30 videos on GPU; 8 h on CPU · Owner: Alimool**

---

## 🎯 What you are doing
Running TransNetV2, an open-source neural shot-boundary detector, on every video. "Shot boundaries" = frames where the visual changes dramatically (slide change, speaker switch, cut). These are a strong visual signal that a chapter might change.

## ✅ How to know you are done
- `data/shots/<video_id>.json` exists for all 30 videos, with a list of shot boundaries (seconds).
- Average 30–100 shot boundaries per hour of video is normal for lectures.

---

## 📝 Steps

### Step 1 — Install TransNetV2

TransNetV2 is not on PyPI. We download its weights + wrapper.

> Execute T16. Write `src/lecseg/preprocess/shots.py` and `scripts/detect_shots.py`.
>
> Use TransNetV2 from https://github.com/soCzech/TransNetV2 — clone its `inference` folder, use the pre-trained weights (`transnetv2-weights/`), wrap it in our module.
>
> For each video:
> 1. Run TransNetV2 on the full video (model takes frames resized to 48×27).
> 2. Post-process with `predictions_to_scenes`.
> 3. Save `data/shots/<id>.json` with `{"boundaries_sec": [...], "shot_count": int}`.
>
> Idempotent — skip if file exists.

### Step 2 — Verify

```
python -c "import json; d = json.load(open('data/shots/<some_id>.json')); print(d['shot_count'], 'shots,', d['boundaries_sec'][:5], '...')"
```

Expected: `~80 shots, [12.4, 34.7, 56.1, ...]` for a 1-hour slide-based lecture.

### Step 3 — Eyeball one video

Open one video at 3 shot-boundary timestamps (not 0, not the end). Does the slide / speaker genuinely change there? If yes, TransNetV2 is working. If it fires inside a single still slide, the model needs a higher confidence threshold.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Shot** | A continuous run of frames without a visual cut. In a lecture, usually one slide. |
| **Shot boundary** | The exact second the visual changes. |
| **TransNetV2** | A 2020 neural model for shot-boundary detection. Strong, free, open-source. |

More: [docs/CONCEPTS.md#shot-boundary](../docs/CONCEPTS.md#shot-boundary)

---

## ➡️ When done

```
python scripts/mark_done.py T16
python scripts/today.py
```
