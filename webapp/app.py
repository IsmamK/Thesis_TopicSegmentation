"""LECSEG — Streamlit demo application.

Run:
    streamlit run webapp/app.py

This is a thin UI on top of `src/lecseg/cli.py`. The user can paste a YouTube
URL (or upload a local video), watch the pipeline run, and explore the
hierarchical chapter / subtopic output side-by-side with the video.

Built in T39. The full feature set is added incrementally — this file is the
skeleton.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────
# Page config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="LECSEG — Lecture Video Segmenter",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────
st.sidebar.title("🎓 LECSEG")
st.sidebar.markdown(
    "Hierarchical multimodal lecture-video topic segmentation."
)
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "Choose input",
    ("YouTube URL", "Upload video", "Use a demo lecture"),
    index=2,
)

with st.sidebar.expander("Advanced settings"):
    asr_model = st.selectbox(
        "ASR model", ["faster-whisper-small", "faster-whisper-medium", "whisper-base"]
    )
    use_visual = st.checkbox("Use visual modality", value=True)
    use_ocr = st.checkbox("Use OCR modality", value=True)
    use_prosody = st.checkbox("Use prosody modality", value=True)
    refine_with_llm = st.checkbox("Refine with local LLM", value=True)

# ─────────────────────────────────────────
# Main panel
# ─────────────────────────────────────────
st.title("Lecture Video Topic Segmenter")
st.caption(
    "Open, multimodal, hierarchical. Paste a lecture URL and explore the "
    "chapter / subtopic structure."
)

col_video, col_outline = st.columns([2, 1])

with col_video:
    if mode == "YouTube URL":
        url = st.text_input("Paste a YouTube lecture URL")
        run = st.button("Segment this lecture", type="primary", disabled=not url)
    elif mode == "Upload video":
        uploaded = st.file_uploader("Drop a .mp4 or .mkv file", type=["mp4", "mkv"])
        run = st.button("Segment this lecture", type="primary", disabled=not uploaded)
    else:
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")  # placeholder
        st.info("Demo lecture placeholder. Replace with a real \dataset{} item before T39.")
        run = st.button("Segment this lecture", type="primary")

with col_outline:
    st.subheader("Chapter / Subtopic outline")
    outline_placeholder = st.empty()

# ─────────────────────────────────────────
# Pipeline run (stub)
# ─────────────────────────────────────────
if run:
    progress = st.progress(0, text="Initialising pipeline…")
    stages = [
        ("Downloading audio", 10),
        ("Transcribing (ASR)", 35),
        ("Splitting sentences", 45),
        ("Computing embeddings", 60),
        ("Detecting shots and OCR", 75),
        ("Fusing modalities", 85),
        ("Predicting boundaries", 92),
        ("Refining with local LLM", 99),
        ("Done", 100),
    ]
    import time

    for label, pct in stages:
        progress.progress(pct, text=label)
        time.sleep(0.4)

    # ----- Mock output -----
    chapters = [
        {"start": 0,    "end": 540,  "title": "Introduction to the topic",
         "subtopics": [
            {"start": 0,   "end": 220, "title": "Motivation"},
            {"start": 220, "end": 540, "title": "Outline of the lecture"},
         ]},
        {"start": 540,  "end": 1620, "title": "Core algorithm",
         "subtopics": [
            {"start": 540,  "end": 900,  "title": "Setup"},
            {"start": 900,  "end": 1280, "title": "Main step"},
            {"start": 1280, "end": 1620, "title": "Worked example"},
         ]},
        {"start": 1620, "end": 2400, "title": "Wrap-up and Q&A",
         "subtopics": []},
    ]

    with col_outline:
        outline_placeholder.empty()
        for ch in chapters:
            with st.expander(
                f"📖 {_fmt(ch['start'])} — {ch['title']}", expanded=True
            ):
                for sub in ch["subtopics"]:
                    st.markdown(f"  • `{_fmt(sub['start'])}` {sub['title']}")

    st.success("Segmentation complete. (This is a stub — real pipeline lands in T39.)")


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────
def _fmt(seconds: int) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
