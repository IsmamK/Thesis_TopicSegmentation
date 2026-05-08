# T11 — Extract Ground-Truth Chapter Timestamps

**Phase 3 · Dataset · Estimated time: 30 min · Owner: Fahmida**

---

## 🎯 What you are doing
Reading the `info.json` files that yt-dlp saved in T10, pulling out each video's YouTube-creator-provided chapter timestamps, and saving them as clean `gt.json` files — one per video.

## 🤔 Why
These timestamps are our **ground truth** — the "correct answer" we compare our model against. Without clean GT, no number in Chapter 4 has meaning.

## ✅ How to know you are done
- For every video, `data/gt/<video_id>.json` exists with keys `boundaries_sec`, `titles`, `num_chapters`.
- A summary CSV `data/gt/gt_summary.csv` lists all videos, their number of chapters, and average chapter duration.

---

## 📝 Steps

### Step 1 — Ask Claude

> Execute T11. Write `src/lecseg/data/gt_from_info.py`. For each `<video_id>/info.json` in `data/raw/`, parse the `chapters` list (YouTube format: list of {start_time, end_time, title}). Save a clean `data/gt/<video_id>.json` with:
> - `boundaries_sec`: list of start times (floats), sorted, EXCLUDING t=0.
> - `titles`: list of chapter titles.
> - `num_chapters`: integer.
>
> Also build `data/gt/gt_summary.csv` with columns: `video_id, num_chapters, duration_sec, avg_chapter_min, min_chapter_min, max_chapter_min`.
>
> Sanity-check rules — flag videos where:
> - num_chapters < 3
> - any chapter shorter than 30 s (likely a timestamp typo by the creator)
> - any chapter longer than 30 min (likely a missing boundary)
>
> Print a list of flagged videos. Do NOT delete them; Fahmida will decide.

### Step 2 — Review the flagged list

For each flagged video, open the YouTube page and decide:
- **Real issue?** → replace the video (go back to T09 for a drop-in replacement) OR fix the `chapters` by hand in `info.json`.
- **False flag?** → keep it, note why in `data/gt/flags_decisions.md`.

### Step 3 — Verify

```
python -c "import json, glob; files = glob.glob('data/gt/*.json'); print(f'{len(files)} gt files'); print('avg chapters:', sum(json.load(open(f))['num_chapters'] for f in files) / len(files))"
```

Should print `30 gt files` and an average of 5–10 chapters.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Ground truth** | The "correct answer" we compare our predictions against. For us: the chapters the YouTube creator wrote. |
| **Boundary** | A single time-point where a chapter ends and the next begins. A video with 5 chapters has 4 boundaries (t=0 is not a boundary). |
| **Outlier** | A value that stands out from the rest. Very short / very long chapters are often typos. |

Learn more: [docs/CONCEPTS.md#ground-truth](../docs/CONCEPTS.md#ground-truth)

---

## ➡️ When done

```
python scripts/mark_done.py T11
python scripts/today.py
```
