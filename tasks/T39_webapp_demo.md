# T39 — Web App Demo (Streamlit)

**Phase 10 · Deliverables · Estimated time: 1.5 days · Owner: Alimool**

---

## 🎯 What you are doing
A Streamlit app that lets anyone paste a YouTube URL and get back the video with AI-generated chapter timestamps + titles. Looks great on a projector for the defense demo.

## ✅ How to know you are done
- `streamlit run webapp/app.py` launches a browser.
- Pasting a YouTube URL → 2-min wait → renders the video with clickable chapter timestamps.
- Dark mode works.

---

## 📝 Steps

### Ask Claude

> Execute T39. Write `webapp/app.py`.
>
> Page flow:
> 1. Title + 2-line project summary.
> 2. YouTube URL input + "Segment" button.
> 3. On click: download audio (yt-dlp) → transcribe (faster-whisper) → run pipeline end-to-end → display:
>    - YouTube embed with chapter jump-to links.
>    - Collapsed tree: Chapter → subtopics.
>    - A confidence bar per boundary.
>    - Download-JSON button.
> 4. Cache heavy operations (embed, transcribe) in `data/webapp_cache/` keyed by video id.
> 5. Show rich progress while processing.
>
> Use session_state so re-submitting the same URL is instant.

### Verify

```
streamlit run webapp/app.py
```

Open http://localhost:8501 and try a short YouTube lecture.

---

## ➡️ When done

```
python scripts/mark_done.py T39
python scripts/today.py
```
