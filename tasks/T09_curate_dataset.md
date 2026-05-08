# T09 — Curate 30-Video Dataset List

**Phase 3 · Dataset · Estimated time: 2 hours (HUMAN work, not AI) · Owner: Fahmida**

---

## 🎯 What you are doing
Hand-picking 30 YouTube lecture videos across 5 subject domains and writing their URLs + metadata into `data/video_list.csv`. This is the **seed** of our LECSEG-30 dataset — novelty claim **N5**.

## 🤔 Why
This is the ONE thing a human must do personally. The quality of our dataset equals the quality of every downstream result. An AI cannot watch videos.

## ✅ How to know you are done
- `data/video_list.csv` has 30 rows across 5 domains.
- Every URL has creator-provided YouTube chapters (check by scrolling the YouTube description for a timestamped list).
- Every video is **≥ 20 minutes** long.
- Every video is in English with clear audio.
- Duration total ≥ 20 hours.

---

## 📝 Steps

### Step 1 — Pick 5 domains (6 videos each)

Suggested:
- **Physics** (mechanics, quantum, thermodynamics)
- **Biology** (cell bio, genetics, ecology)
- **Computer Science** (algorithms, ML, systems)
- **Mathematics** (calculus, linear algebra, statistics)
- **Philosophy / Humanities** (ethics, history of science)

Mix slide-based with chalkboard-based lectures (improves generalization).

### Step 2 — Find videos

Good sources:
- MIT OpenCourseWare (https://www.youtube.com/@mitocw)
- 3Blue1Brown (math)
- Crash Course (various)
- The Organic Chemistry Tutor
- Stanford Online
- CS50 (Harvard)
- Kurzgesagt (has chapters)
- Yale Courses
- Coursera (some free)

**Filter criteria (mandatory):**
- Has "Chapters" in the description (timestamps like `0:00 Intro · 5:30 Newton's Laws ...`)
- 20–120 min long
- English
- At least 3 chapters

### Step 3 — Fill the CSV

Create `data/video_list.csv` with these exact columns:

```csv
url,domain,title,speaker,language,duration_est_min,num_chapters_est,source_channel,notes
https://youtu.be/XXXXXX,physics,Newtonian Mechanics Lecture 1,MIT OCW,en,60,8,MIT OpenCourseWare,chalkboard style
...
```

### Step 4 — Validate

Ask Claude:
> Read `data/video_list.csv`. For each row, fetch the YouTube metadata (yt-dlp can do this without downloading the video: `yt-dlp --skip-download --dump-json <url>`). Verify: (1) video exists, (2) has chapters, (3) English, (4) duration in expected range. Flag failures in a report. Do not download any videos.

Fix any flagged rows.

---

## 🧠 Concepts

| Term | Meaning |
|---|---|
| **Ground truth** | The "correct" answer. For us: the chapter boundaries provided by the video's creator. |
| **Dataset diversity** | Covering many speakers / styles / subjects. Improves generalization claims in Chapter 4. |

---

## ➡️ When done

```
python scripts/mark_done.py T09
python scripts/next.py
```
