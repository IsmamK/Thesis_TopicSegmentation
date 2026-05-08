# T17 — Slide OCR (PaddleOCR)

**Phase 4 · Preprocessing · Estimated time: 3 h for 30 videos · Owner: Alimool**

---

## 🎯 What you are doing
Sampling a keyframe from each shot (T16), running OCR (Optical Character Recognition) on it to extract any text visible on screen (slide titles, bullet points). The slide text is a strong signal: when the slide changes, it usually means a topic shift.

## ✅ How to know you are done
- `data/ocr/<video_id>.json` has one record per shot with the recognized text.
- For slide-based lectures, ≥ 60% of shots have non-empty text.

---

## 📝 Steps

### Step 1 — Install PaddleOCR

```
pip install paddlepaddle paddleocr
```

On Windows with GPU: `pip install paddlepaddle-gpu==2.6.0`.

### Step 2 — Ask Claude

> Execute T17. Write `src/lecseg/preprocess/ocr_slides.py` and `scripts/run_ocr.py`.
>
> For each video:
> 1. For each shot in `data/shots/<id>.json`, pick a keyframe at the **middle** of the shot using ffmpeg.
> 2. Run PaddleOCR on the keyframe (English, angle_cls=True).
> 3. Concatenate the returned text boxes into one string per shot.
> 4. Save `data/ocr/<id>.json` = list of {shot_idx, start_sec, keyframe_time, ocr_text, num_boxes}.
>
> Cache keyframes in `data/raw/<id>/keyframes/` (JPEGs) so re-running does not reshoot ffmpeg.

### Step 3 — Verify

```
python -c "import json; d = json.load(open('data/ocr/<some_id>.json')); print(sum(1 for x in d if x['ocr_text']), '/', len(d), 'shots have text')"
```

For a slide lecture, expect `>60%` non-empty.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **OCR** | Optical Character Recognition. Turns pixels of text (like a slide) into machine-readable text. |
| **Keyframe** | One representative frame picked from a shot. We pick the middle frame. |
| **PaddleOCR** | A strong free multilingual OCR framework built by Baidu. |

More: [docs/CONCEPTS.md#ocr](../docs/CONCEPTS.md#ocr)

---

## ➡️ When done

```
python scripts/mark_done.py T17
python scripts/today.py
```
