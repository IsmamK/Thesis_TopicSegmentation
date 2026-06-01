"""
T39 — LECSEG YouTube Demo

Paste any YouTube URL → AI-generated chapter timestamps + titles.
Full pipeline: yt-dlp download → Whisper transcription → sentence split
→ SBERT embeddings → hierarchical segmentation → LLM titling.

Run:
    streamlit run scripts/demo.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import hashlib
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
import numpy as np

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LECSEG — AI Lecture Chapters",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.hero {
    background: linear-gradient(135deg, #0f2340 0%, #1a4a8a 60%, #2d6abf 100%);
    border-radius: 16px;
    padding: 2.5rem 3rem 2rem 3rem;
    color: white;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero::after {
    content: "🎓";
    position: absolute;
    right: 2rem; top: 1rem;
    font-size: 5rem;
    opacity: 0.15;
}
.hero h1 { color: white; font-size: 2.4rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.hero .sub { color: #a8c8f0; font-size: 1.05rem; margin: 0; }
.hero .badges { margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.badge {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    color: #d0e8ff;
}

.url-box {
    background: white;
    border: 2px solid #2d6abf;
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 12px rgba(45,106,191,0.08);
}

.chapter-card {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    background: white;
    border: 1px solid #e0eaf8;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: box-shadow 0.2s;
    cursor: pointer;
}
.chapter-card:hover { box-shadow: 0 3px 12px rgba(45,106,191,0.15); }
.chapter-num {
    background: #2d6abf;
    color: white;
    border-radius: 50%;
    width: 2rem; height: 2rem;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem;
    flex-shrink: 0;
}
.chapter-title { font-weight: 600; color: #1a2a4a; font-size: 0.95rem; }
.chapter-ts {
    font-family: monospace;
    background: #eef4ff;
    color: #2d6abf;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 0.82rem;
    font-weight: 600;
}
.chapter-preview { color: #666; font-size: 0.82rem; margin-top: 3px; line-height: 1.4; }

.gt-chapter-card {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    background: #f0fff4;
    border: 1px solid #c3e6cb;
    border-radius: 8px;
    padding: 0.65rem 1rem;
    margin-bottom: 0.5rem;
}
.gt-num {
    background: #2e7d52;
    color: white;
    border-radius: 50%;
    width: 1.8rem; height: 1.8rem;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.78rem;
    flex-shrink: 0;
}

.step-box {
    background: #f8faff;
    border: 1px solid #dde8f8;
    border-radius: 10px;
    padding: 0.6rem 1rem;
    margin: 0.3rem 0;
    font-size: 0.88rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.step-done  { color: #2e7d52; }
.step-run   { color: #1a4a8a; }
.step-wait  { color: #999; }

.metric-pill {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.85rem;
    margin-right: 6px;
}
.pill-green  { background: #dcfce7; color: #166534; }
.pill-yellow { background: #fef9c3; color: #854d0e; }
.pill-red    { background: #fee2e2; color: #991b1b; }
.pill-blue   { background: #dbeafe; color: #1e40af; }

.youtube-embed {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.copy-box {
    background: #1e2d3d;
    color: #7dd3fc;
    border-radius: 8px;
    padding: 0.8rem 1.2rem;
    font-family: monospace;
    font-size: 0.85rem;
    margin: 0.5rem 0;
    white-space: pre-wrap;
    word-break: break-all;
}

.results-header {
    background: linear-gradient(90deg, #f0f6ff, #f8faff);
    border: 1px solid #c8daf8;
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
}

div[data-testid="stProgress"] > div > div { background-color: #2d6abf !important; }
</style>
""", unsafe_allow_html=True)

# ── constants ─────────────────────────────────────────────────────────────────
CACHE_DIR    = ROOT / "data" / "demo_cache"
COOKIES_FILE = ROOT / "data" / "youtube_cookies.txt"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

WHISPER_MODEL = "tiny.en"   # cached locally, fast on CPU
EMBED_MODEL   = "sbert"     # MiniLM 384-dim — fastest

# ── helpers ───────────────────────────────────────────────────────────────────

def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_duration(sec: float) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def ts_to_seconds(ts: str) -> int:
    parts = ts.strip().split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return parts[0] * 60 + parts[1]


def yt_url_with_ts(vid_id: str, seconds: int) -> str:
    return f"https://www.youtube.com/watch?v={vid_id}&t={seconds}s"


def cosine_gap_scores(vecs: np.ndarray, window: int = 3) -> np.ndarray:
    N   = len(vecs)
    eps = 1e-9
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms < eps] = eps
    v = vecs / norms
    scores = np.zeros(N - 1)
    for i in range(N - 1):
        lo    = max(0, i - window + 1)
        hi    = min(N, i + window + 1)
        left  = v[lo : i + 1].mean(axis=0)
        right = v[i + 1 : hi].mean(axis=0)
        ln, rn = np.linalg.norm(left), np.linalg.norm(right)
        sim   = float(np.dot(left, right) / (ln * rn + eps))
        scores[i] = 1.0 - sim
    return scores


@st.cache_resource(show_spinner=False)
def get_whisper_model():
    from faster_whisper import WhisperModel
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def video_cache_path(vid_id: str) -> Path:
    return CACHE_DIR / vid_id


def load_cached_result(vid_id: str) -> dict | None:
    p = video_cache_path(vid_id) / "result.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_cached_result(vid_id: str, result: dict) -> None:
    d = video_cache_path(vid_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                   encoding="utf-8")


def run_full_pipeline(
    vid_id: str,
    url: str,
    progress_callback,
    max_minutes: int = 0,  # 0 = no limit
) -> dict:
    """
    Full pipeline: download → transcribe → embed → segment → title.
    Returns result dict with chapters list.
    """
    import yt_dlp
    from faster_whisper import WhisperModel
    from lecseg.features.text_embeddings import embed_sentences
    from lecseg.models.hierarchical import HierarchicalSegmenter
    from lecseg.refine.llm_refine import LLMRefiner

    work_dir = video_cache_path(vid_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    audio_path = work_dir / "audio.mp3"

    # ── Step 1: Get video metadata ────────────────────────────────────────────
    progress_callback(0.05, "Fetching video metadata…")
    ydl_opts_info = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }
    if COOKIES_FILE.exists():
        ydl_opts_info["cookiefile"] = str(COOKIES_FILE)

    meta = {}
    yt_chapters = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            meta = {
                "title":    info.get("title", "Lecture"),
                "channel":  info.get("uploader", ""),
                "duration": info.get("duration", 0),
                "thumb":    info.get("thumbnail", ""),
            }
            raw_chapters = info.get("chapters") or []
            yt_chapters  = [
                {"title": c["title"], "start_sec": c["start_time"]}
                for c in raw_chapters
            ]
    except Exception as e:
        meta = {"title": "Lecture", "channel": "", "duration": 0, "thumb": ""}

    # ── Step 2: Download audio ─────────────────────────────────────────────────
    progress_callback(0.12, "Downloading audio…")
    if not audio_path.exists():
        ydl_opts_dl = {
            "format":           "bestaudio/best",
            "outtmpl":          str(work_dir / "audio.%(ext)s"),
            "postprocessors":   [{"key": "FFmpegExtractAudio",
                                  "preferredcodec": "mp3",
                                  "preferredquality": "64"}],
            "quiet":            True,
            "no_warnings":      True,
        }
        if COOKIES_FILE.exists():
            ydl_opts_dl["cookiefile"] = str(COOKIES_FILE)
        if max_minutes > 0:
            ydl_opts_dl["download_sections"] = [
                {"start_time": 0, "end_time": max_minutes * 60}
            ]
            # postprocessor to cut
            ydl_opts_dl["force_keyframes_at_cuts"] = True

        with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
            ydl.download([url])

        # rename whatever ext was saved to audio.mp3
        for f in work_dir.glob("audio.*"):
            if f.suffix != ".json" and f.name != "audio.mp3":
                f.rename(audio_path)
                break

    # ── Step 3: Transcribe ─────────────────────────────────────────────────────
    transcript_path = work_dir / "transcript.json"
    if not transcript_path.exists():
        progress_callback(0.25, f"Transcribing with Whisper {WHISPER_MODEL}…  (this takes ~1-3 min on CPU)")
        model = get_whisper_model()
        segments_out, _ = model.transcribe(
            str(audio_path),
            language="en",
            vad_filter=True,
            word_timestamps=True,
        )
        segs = []
        for seg in segments_out:
            segs.append({
                "text":  seg.text.strip(),
                "start": seg.start,
                "end":   seg.end,
            })
        transcript_path.write_text(json.dumps({"segments": segs}, ensure_ascii=False),
                                   encoding="utf-8")

    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))

    # ── Step 4: Sentence splitting ─────────────────────────────────────────────
    sentences_path = work_dir / "sentences.json"
    if not sentences_path.exists():
        progress_callback(0.50, "Splitting into sentences…")
        raw_segs = transcript["segments"]
        # Simple sentence-level split: group short segments into proper sentences
        sentences = _split_to_sentences(raw_segs, max_minutes)
        sentences_path.write_text(json.dumps({"sentences": sentences}, ensure_ascii=False),
                                  encoding="utf-8")

    sentences = json.loads(sentences_path.read_text(encoding="utf-8"))["sentences"]

    # ── Step 5: Embeddings ─────────────────────────────────────────────────────
    embeddings_path = work_dir / "embeddings.npy"
    if not embeddings_path.exists():
        progress_callback(0.60, "Computing semantic embeddings (Sentence-BERT)…")
        texts = [s["text"] for s in sentences]
        vecs  = embed_sentences(texts, model=EMBED_MODEL)
        np.save(str(embeddings_path), vecs)

    vecs = np.load(str(embeddings_path))
    N    = len(sentences)

    # ── Step 6: Segmentation ───────────────────────────────────────────────────
    progress_callback(0.78, "Running hierarchical segmentation…")
    n_chapters  = max(3, min(15, N // 40))
    n_subtopics = n_chapters * 2

    from lecseg.models.hierarchical import HierarchicalSegmenter
    seg  = HierarchicalSegmenter()
    tree = seg.segment(vecs, n_chapters=n_chapters, n_subtopics=n_subtopics)
    chapter_boundaries = tree.chapters  # list of sentence indices

    # ── Step 7: LLM Titling ────────────────────────────────────────────────────
    progress_callback(0.88, "Generating chapter titles with Llama 3.1…")
    texts_all = [s["text"] for s in sentences]
    bounds    = [0] + sorted(chapter_boundaries) + [N]
    segments  = [texts_all[bounds[i]:bounds[i+1]] for i in range(len(bounds)-1)]

    refiner = LLMRefiner(model="llama3.1:8b")
    titles  = []
    if refiner._is_available():
        for seg_texts in segments:
            title = refiner.title_segment(seg_texts, max_words=7)
            titles.append(title)
    else:
        # Fallback: use first non-filler sentence as title
        for seg_texts in segments:
            for t in seg_texts[:5]:
                clean = t.strip().rstrip(".!?,;")
                if len(clean.split()) >= 4:
                    titles.append(clean[:55] + ("…" if len(clean) > 55 else ""))
                    break
            else:
                titles.append(f"Section {len(titles)+1}")

    # ── Step 8: Build result ───────────────────────────────────────────────────
    progress_callback(0.97, "Finalising…")
    chapters = []
    for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        start_sec = sentences[lo]["start"]
        end_sec   = sentences[min(hi, N-1)]["end"]
        preview   = " ".join(texts_all[lo : lo + 2])[:120]
        chapters.append({
            "index":     i + 1,
            "title":     titles[i] if i < len(titles) else f"Section {i+1}",
            "start_sec": start_sec,
            "end_sec":   end_sec,
            "sent_lo":   lo,
            "sent_hi":   hi,
            "preview":   preview,
        })

    result = {
        "vid_id":      vid_id,
        "meta":        meta,
        "chapters":    chapters,
        "yt_chapters": yt_chapters,
        "n_sentences": N,
        "llm_used":    refiner._is_available(),
    }
    save_cached_result(vid_id, result)
    return result


def _split_to_sentences(raw_segs: list[dict], max_minutes: int) -> list[dict]:
    """Merge Whisper segments into ~sentence-length units."""
    import re as _re
    limit_sec = max_minutes * 60 if max_minutes > 0 else float("inf")
    sentences = []
    buf_text  = ""
    buf_start = None
    buf_end   = 0.0
    idx       = 0

    for seg in raw_segs:
        if seg["start"] > limit_sec:
            break
        if buf_start is None:
            buf_start = seg["start"]
        buf_text += " " + seg["text"].strip()
        buf_end   = seg["end"]

        # flush on sentence-ending punctuation or long accumulation
        if _re.search(r"[.!?]\s*$", buf_text.strip()) or len(buf_text.split()) >= 30:
            clean = buf_text.strip()
            if clean:
                sentences.append({"idx": idx, "start": buf_start,
                                   "end": buf_end, "text": clean})
                idx += 1
            buf_text  = ""
            buf_start = None

    if buf_text.strip() and buf_start is not None:
        sentences.append({"idx": idx, "start": buf_start,
                           "end": buf_end, "text": buf_text.strip()})
    return sentences


def estimate_time(duration_sec: float) -> str:
    # Whisper tiny.en: ~0.15x real time on CPU for short audio
    whisper_min = duration_sec * 0.15 / 60
    total_min   = whisper_min + 0.5  # embedding + segmentation
    if total_min < 1.5:
        return "~1 minute"
    return f"~{int(total_min)+1} minutes"


# ═══════════════════════════════════════════════════════════════════════════
# MAIN UI
# ═══════════════════════════════════════════════════════════════════════════

# ── hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>LECSEG &mdash; AI Lecture Chapter Generator</h1>
  <p class="sub">Paste any YouTube lecture URL. Get AI-generated chapter timestamps and titles in minutes.</p>
  <div class="badges">
    <span class="badge">🎤 Whisper Speech Recognition</span>
    <span class="badge">🧠 Sentence-BERT Embeddings</span>
    <span class="badge">⚡ Hierarchical Segmentation</span>
    <span class="badge">✍️ Llama 3.1 Titling</span>
    <span class="badge">📖 Pre-Thesis Research — T2520718</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── URL input ─────────────────────────────────────────────────────────────────
with st.container():
    st.markdown('<div class="url-box">', unsafe_allow_html=True)

    col_url, col_btn = st.columns([5, 1])
    with col_url:
        url_input = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            label_visibility="collapsed",
        )
    with col_btn:
        go_btn = st.button("▶  Generate Chapters", type="primary",
                           use_container_width=True)

    adv1, adv2, adv3 = st.columns(3)
    with adv1:
        max_min = st.selectbox(
            "Analyse",
            [("Full video", 0), ("First 10 min (fast demo)", 10),
             ("First 20 min", 20), ("First 30 min", 30)],
            format_func=lambda x: x[0],
            index=0,
        )[1]
    with adv2:
        force_rerun = st.checkbox("Re-run (ignore cache)", value=False)
    with adv3:
        st.markdown(
            '<span style="color:#888;font-size:0.82rem;line-height:3">'
            'Results cached after first run — instant on re-visit</span>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ── DEMO SHORTCUTS ────────────────────────────────────────────────────────────
st.markdown("**Try a pre-processed example:**")
ex_cols = st.columns(4)
EXAMPLES = [
    ("MIT Calculus", "https://www.youtube.com/watch?v=7K1sB05pE0A"),
    ("Harvard Ethics", "https://www.youtube.com/watch?v=8yT4RZy1t3s"),
    ("MIT Biochemistry", "https://www.youtube.com/watch?v=9N1MxkbFhsc"),
    ("MIT DNA Structure", "https://www.youtube.com/watch?v=AMl6E4cLrwE"),
]
for col, (label, ex_url) in zip(ex_cols, EXAMPLES):
    if col.button(f"📺 {label}", use_container_width=True):
        url_input = ex_url
        go_btn    = True

# ── PROCESSING ────────────────────────────────────────────────────────────────
if go_btn and url_input.strip():
    vid_id = extract_video_id(url_input.strip())
    if not vid_id:
        st.error("Could not recognise a YouTube video ID in that URL. "
                 "Please paste a standard youtube.com/watch?v= or youtu.be/ link.")
        st.stop()

    # Check cache
    cached = None if force_rerun else load_cached_result(vid_id)

    if cached:
        result = cached
        st.success("✅ Loaded from cache — results are instant for previously processed videos.")
    else:
        # Estimate time and warn
        info_holder = st.empty()
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(url_input.strip(), download=False)
                dur  = info.get("duration", 0)
                if max_min > 0:
                    dur = min(dur, max_min * 60)
                est  = estimate_time(dur)
                title_preview = info.get("title", "")[:60]
        except Exception:
            dur, est, title_preview = 0, "~2 minutes", ""

        info_holder.info(
            f"**Processing:** _{title_preview}_\n\n"
            f"Estimated time: **{est}** "
            f"({'first ' + str(max_min) + ' min only' if max_min else 'full video'})\n\n"
            f"The pipeline runs: audio download → Whisper transcription "
            f"→ semantic embeddings → hierarchical segmentation → LLM titling."
        )

        progress_bar  = st.progress(0, text="Starting pipeline…")
        status_holder = st.empty()

        def update_progress(frac: float, msg: str):
            progress_bar.progress(frac, text=msg)
            status_holder.markdown(
                f'<div class="step-box step-run">⚙️ {msg}</div>',
                unsafe_allow_html=True,
            )

        try:
            result = run_full_pipeline(
                vid_id=vid_id,
                url=url_input.strip(),
                progress_callback=update_progress,
                max_minutes=max_min,
            )
            progress_bar.progress(1.0, text="Done!")
            info_holder.empty()
            status_holder.empty()
            progress_bar.empty()
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            st.exception(e)
            st.stop()

    # ══════════════════════════════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════════════════════════════
    meta      = result["meta"]
    chapters  = result["chapters"]
    yt_chs    = result.get("yt_chapters", [])
    llm_used  = result.get("llm_used", False)
    N         = result.get("n_sentences", 0)

    # ── stats bar ────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="results-header">
      <strong style="font-size:1.15rem;color:#1a2a4a">{meta['title']}</strong><br>
      <span style="color:#666;font-size:0.88rem">{meta['channel']}</span>
      &nbsp;·&nbsp;
      <span style="color:#666;font-size:0.88rem">{fmt_duration(meta['duration'])}</span>
    </div>
    """, unsafe_allow_html=True)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("AI Chapters found", len(chapters))
    s2.metric("Sentences analysed", f"{N:,}")
    s3.metric("YouTube chapters", len(yt_chs) if yt_chs else "—")
    s4.metric("Titles generated by", "Llama 3.1 🤖" if llm_used else "Fallback 📝")

    st.markdown("---")

    # ── two-column layout ─────────────────────────────────────────────────────
    left_col, right_col = st.columns([1.15, 1])

    # ── LEFT: YouTube embed + AI chapters ─────────────────────────────────────
    with left_col:
        # YouTube embed
        st.markdown(
            f'<div class="youtube-embed">'
            f'<iframe width="100%" height="360" '
            f'src="https://www.youtube.com/embed/{vid_id}?rel=0" '
            f'frameborder="0" allow="accelerometer; autoplay; clipboard-write; '
            f'encrypted-media; gyroscope; picture-in-picture" allowfullscreen>'
            f'</iframe></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### 🤖 AI-Generated Chapters ({len(chapters)})")
        st.caption(
            "Click any timestamp link to jump to that point in the video. "
            + ("Titles generated by Llama 3.1 8B (local)." if llm_used
               else "Titles auto-extracted from transcript.")
        )

        for ch in chapters:
            ts_sec  = int(ch["start_sec"])
            ts_str  = fmt_ts(ch["start_sec"])
            yt_link = yt_url_with_ts(vid_id, ts_sec)
            preview = ch.get("preview", "")[:110]

            st.markdown(
                f'<div class="chapter-card">'
                f'  <div class="chapter-num">{ch["index"]}</div>'
                f'  <div style="flex:1">'
                f'    <div class="chapter-title">{ch["title"]}</div>'
                f'    <div style="margin-top:3px">'
                f'      <a href="{yt_link}" target="_blank" class="chapter-ts">'
                f'        ▶ {ts_str}</a>'
                f'    </div>'
                f'    <div class="chapter-preview">{preview}</div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # YouTube description-format copy box
        st.markdown("#### 📋 Copy as YouTube Description")
        st.caption("Paste this into the video description to add chapter markers:")
        desc_lines = "\n".join(
            f'{fmt_ts(ch["start_sec"])} {ch["title"]}' for ch in chapters
        )
        st.markdown(
            f'<div class="copy-box">{desc_lines}</div>',
            unsafe_allow_html=True,
        )
        st.code(desc_lines, language=None)

    # ── RIGHT: GT comparison + gap curve ─────────────────────────────────────
    with right_col:
        if yt_chs:
            st.markdown(f"### 📖 YouTube Creator Chapters ({len(yt_chs)})")
            st.caption("These are the original chapter markers set by the video creator.")
            for i, ch in enumerate(yt_chs):
                ts_str  = fmt_ts(ch["start_sec"])
                yt_link = yt_url_with_ts(vid_id, int(ch["start_sec"]))
                st.markdown(
                    f'<div class="gt-chapter-card">'
                    f'  <div class="gt-num">{i+1}</div>'
                    f'  <div style="flex:1">'
                    f'    <div style="font-weight:600;color:#1a3a2a">{ch["title"]}</div>'
                    f'    <a href="{yt_link}" target="_blank" '
                    f'       style="font-family:monospace;background:#dcfce7;color:#166534;'
                    f'              border-radius:4px;padding:1px 6px;font-size:0.8rem;'
                    f'              font-weight:600;text-decoration:none">▶ {ts_str}</a>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("### 📖 No YouTube Chapters Available")
            st.caption("This video has no creator-provided chapters — LECSEG fills that gap.")

        # Gap score chart
        emb_path = video_cache_path(vid_id) / "embeddings.npy"
        sent_path = video_cache_path(vid_id) / "sentences.json"
        if emb_path.exists() and sent_path.exists():
            st.markdown("---")
            st.markdown("#### 📉 Semantic dissimilarity curve")
            st.caption(
                "Peaks = where the model detected topic shifts. "
                "Red lines = AI chapter boundaries."
            )
            try:
                import plotly.graph_objects as go
                vecs_plot  = np.load(str(emb_path))
                sents_plot = json.loads(sent_path.read_text())["sentences"]
                gap_scores = cosine_gap_scores(vecs_plot)
                times      = np.array([s["start"] for s in sents_plot[:-1]])

                pred_ts = [ch["start_sec"] for ch in chapters[1:]]  # skip first (t=0)

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=times, y=gap_scores,
                    fill="tozeroy",
                    fillcolor="rgba(45,106,191,0.08)",
                    line=dict(color="#2d6abf", width=1.5),
                    name="Dissimilarity",
                    hovertemplate="Time: %{x:.0f}s<br>Dissim: %{y:.3f}<extra></extra>",
                ))
                for t in pred_ts:
                    fig.add_vline(x=t, line_color="#c0392b", line_width=1.5,
                                  opacity=0.7)

                tick_step = max(60, int(max(times) / 8 / 60) * 60)
                ticks = list(range(0, int(max(times)) + 1, tick_step))
                fig.update_layout(
                    height=250,
                    margin=dict(l=5, r=5, t=10, b=30),
                    xaxis=dict(
                        tickvals=ticks,
                        ticktext=[fmt_ts(t) for t in ticks],
                    ),
                    yaxis=dict(title="Dissim."),
                    plot_bgcolor="#f8fafc",
                    paper_bgcolor="#f8fafc",
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})
            except Exception:
                pass

        # How it works
        st.markdown("---")
        with st.expander("⚙️ How this works", expanded=False):
            st.markdown("""
**Pipeline steps:**

1. **🎤 Audio download** via yt-dlp — audio-only, much smaller than video
2. **📝 Transcription** — OpenAI Whisper tiny.en (runs locally, no API)
3. **✂️ Sentence splitting** — merges Whisper segments into grammatical sentences
4. **🧠 Semantic embedding** — Sentence-BERT converts each sentence to a 384-dim vector
5. **📐 Hierarchical segmentation** — LECSEG's two-stage predictor finds chapter boundaries
   using cosine dissimilarity drops between sentence groups
6. **✍️ Title generation** — Llama 3.1 8B (via Ollama, fully local) reads each segment
   and writes a 3–7 word title

**Key insight:** Sentences within the same topic have similar embeddings.
Sentences across a topic boundary have dissimilar embeddings.
The system finds positions where this dissimilarity spikes.

**Research context:**
This is the T39 demo for pre-thesis project LECSEG (T2520718).
The hierarchical segmenter achieves **Pk = 0.417** on the 30-video LECSEG-30 benchmark,
statistically significantly better than all baselines (p < 0.01, Wilcoxon test).
            """)

elif go_btn and not url_input.strip():
    st.warning("Please paste a YouTube URL above.")

else:
    # Landing state
    st.markdown("---")
    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        st.markdown("""
        **How it works**
        1. Paste any YouTube lecture URL above
        2. The system downloads just the audio
        3. Whisper transcribes it locally
        4. LECSEG detects topic boundaries
        5. Llama 3.1 generates chapter titles
        """)
    with lc2:
        st.markdown("""
        **What you get**
        - Clickable timestamps linking to each chapter
        - AI-written title for each segment
        - Comparison with YouTube creator chapters (if they exist)
        - Ready-to-paste YouTube description format
        - Semantic dissimilarity curve showing how the AI reasoned
        """)
    with lc3:
        st.markdown("""
        **Research behind this**
        - 30-video benchmark across 5 academic domains
        - Best Pk = 0.417 (vs random baseline 0.5)
        - Statistically significant: p < 0.01
        - 177 unit tests, fully reproducible pipeline
        - Novel: hierarchical segmentation + reliability-weighted fusion
        """)

# ── footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#aaa;font-size:0.78rem">'
    'LECSEG &nbsp;·&nbsp; Pre-Thesis T2520718 &nbsp;·&nbsp; 2026 &nbsp;·&nbsp;'
    ' Whisper + Sentence-BERT + Hierarchical Segmentation + Llama 3.1'
    '</p>',
    unsafe_allow_html=True,
)
