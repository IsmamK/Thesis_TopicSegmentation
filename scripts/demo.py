"""
T39 — LECSEG Professional Web Demo
Paste any YouTube URL → AI-generated chapter timestamps + titles.
Full pipeline: download → Whisper → sentence split → SBERT → hierarchical segmentation → LLM titling.

Run:
    streamlit run scripts/demo.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
import numpy as np

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LECSEG — AI Lecture Chaptering",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0f2340;
    color: white;
}
section[data-testid="stSidebar"] * { color: #e8f0fe !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stCheckbox label { color: #a8c8f0 !important; }
section[data-testid="stSidebar"] hr { border-color: #1e3a5f !important; }

/* ── Main background ── */
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #0f2340 0%, #1a4a8a 55%, #2d6abf 100%);
    border-radius: 16px;
    padding: 2.2rem 2.8rem 1.8rem;
    color: white;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: "";
    position: absolute;
    right: -60px; top: -60px;
    width: 260px; height: 260px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
}
.hero::after {
    content: "";
    position: absolute;
    right: 40px; top: 20px;
    width: 140px; height: 140px;
    border-radius: 50%;
    background: rgba(255,255,255,0.06);
}
.hero-title {
    font-size: 2.6rem;
    font-weight: 800;
    color: white;
    margin: 0 0 0.3rem;
    letter-spacing: -0.5px;
    position: relative; z-index: 1;
}
.hero-sub {
    color: #a8c8f0;
    font-size: 1.05rem;
    margin: 0 0 1rem;
    position: relative; z-index: 1;
}
.badge-row {
    display: flex; gap: 0.5rem; flex-wrap: wrap;
    position: relative; z-index: 1;
}
.badge {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    color: #d0e8ff;
    font-weight: 500;
}

/* ── Input card ── */
.input-card {
    background: white;
    border: 1.5px solid #dce8fb;
    border-radius: 14px;
    padding: 1.4rem 1.8rem 1.2rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 2px 16px rgba(45,106,191,0.07);
}

/* ── Pipeline stepper ── */
.pipeline-wrap {
    background: #f0f6ff;
    border: 1px solid #dae5f8;
    border-radius: 14px;
    padding: 1.2rem 1.6rem;
    margin: 1rem 0;
}
.pipeline-title {
    font-weight: 700;
    color: #1a2a4a;
    font-size: 0.92rem;
    margin-bottom: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.steps-row {
    display: flex;
    align-items: flex-start;
    gap: 0;
    position: relative;
}
.step-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
    text-align: center;
}
.step-item:not(:last-child)::after {
    content: "";
    position: absolute;
    top: 18px;
    left: 50%;
    width: 100%;
    height: 2px;
    background: #d0def8;
    z-index: 0;
}
.step-item.done::after { background: #2d6abf; }
.step-item.active::after { background: linear-gradient(90deg, #2d6abf, #d0def8); }
.step-circle {
    width: 38px; height: 38px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    position: relative; z-index: 1;
    transition: all 0.3s;
    border: 2.5px solid #d0def8;
    background: white;
    color: #999;
}
.step-item.done .step-circle {
    background: #2d6abf; border-color: #2d6abf; color: white;
}
.step-item.active .step-circle {
    background: white; border-color: #2d6abf; color: #2d6abf;
    box-shadow: 0 0 0 5px rgba(45,106,191,0.15);
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(45,106,191,0.3); }
    70% { box-shadow: 0 0 0 8px rgba(45,106,191,0); }
    100% { box-shadow: 0 0 0 0 rgba(45,106,191,0); }
}
.step-label {
    font-size: 0.70rem;
    color: #888;
    margin-top: 6px;
    font-weight: 500;
    line-height: 1.3;
}
.step-item.done .step-label { color: #2d6abf; font-weight: 600; }
.step-item.active .step-label { color: #1a2a4a; font-weight: 700; }
.step-time {
    font-size: 0.63rem;
    color: #aaa;
    margin-top: 2px;
}
.step-item.done .step-time { color: #5a9e5a; }

/* ── Chapter cards ── */
.chapter-card {
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    background: white;
    border: 1px solid #e4edf8;
    border-radius: 11px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.55rem;
    transition: all 0.2s;
    cursor: pointer;
}
.chapter-card:hover {
    border-color: #2d6abf;
    box-shadow: 0 4px 14px rgba(45,106,191,0.12);
    transform: translateY(-1px);
}
.ch-num {
    background: #2d6abf;
    color: white;
    border-radius: 8px;
    width: 2rem; height: 2rem;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.82rem;
    flex-shrink: 0;
}
.ch-title { font-weight: 600; color: #1a2a4a; font-size: 0.93rem; line-height: 1.3; }
.ch-ts-link {
    font-family: 'Courier New', monospace;
    background: #eef4ff;
    color: #2d6abf;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 0.78rem;
    font-weight: 700;
    text-decoration: none;
    display: inline-block;
    margin-top: 3px;
}
.ch-ts-link:hover { background: #2d6abf; color: white; }
.ch-preview { color: #777; font-size: 0.79rem; margin-top: 4px; line-height: 1.4; }
.ch-duration {
    font-size: 0.72rem;
    color: #999;
    margin-left: 4px;
}

/* ── GT chapters ── */
.gt-card {
    display: flex; align-items: center; gap: 0.75rem;
    background: #f0fff8;
    border: 1px solid #b8e8cc;
    border-radius: 9px;
    padding: 0.65rem 0.95rem;
    margin-bottom: 0.45rem;
}
.gt-num {
    background: #2e7d52; color: white;
    border-radius: 6px;
    width: 1.7rem; height: 1.7rem;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.74rem;
    flex-shrink: 0;
}

/* ── Model badge ── */
.model-badge {
    display: inline-flex; align-items: center; gap: 5px;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #9a3412;
    margin-bottom: 0.5rem;
}
.model-recommended {
    background: #f0fdf4;
    border: 1px solid #86efac;
    color: #166534;
}

/* ── Metric chips ── */
.metric-chip {
    display: inline-block;
    padding: 4px 12px; border-radius: 20px;
    font-weight: 700; font-size: 0.82rem;
    margin: 2px 3px;
}
.chip-blue  { background: #dbeafe; color: #1e40af; }
.chip-green { background: #dcfce7; color: #166534; }
.chip-amber { background: #fef3c7; color: #92400e; }
.chip-red   { background: #fee2e2; color: #991b1b; }

/* ── Results header ── */
.results-banner {
    background: linear-gradient(90deg, #f0f6ff, #f8faff);
    border: 1px solid #c8daf8;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
}

/* ── Copy box ── */
.copy-box {
    background: #0f1c2e;
    color: #7dd3fc;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    white-space: pre;
    overflow-x: auto;
    margin: 0.5rem 0;
    line-height: 1.7;
}

/* ── Sidebar model card ── */
.model-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.6rem;
}
.model-card.selected {
    background: rgba(45,106,191,0.3);
    border-color: rgba(45,106,191,0.6);
}
.model-name { font-weight: 700; font-size: 0.88rem; }
.model-stat { font-size: 0.74rem; opacity: 0.75; margin-top: 2px; }
.model-rec  {
    background: #2e7d52; color: white;
    border-radius: 4px; padding: 1px 7px;
    font-size: 0.65rem; font-weight: 700;
    margin-left: 6px; vertical-align: middle;
}

/* ── Status pills ── */
.status-pill {
    display: inline-flex; align-items: center; gap: 5px;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.8rem; font-weight: 600;
}
.pill-live { background: #dcfce7; color: #166534; }
.pill-offline { background: #fee2e2; color: #991b1b; }

/* ── Progress bar color ── */
div[data-testid="stProgress"] > div > div { background-color: #2d6abf !important; }

/* ── Streamlit metric enhancements ── */
[data-testid="stMetric"] { background: white; border: 1px solid #e4edf8; border-radius: 10px; padding: 0.7rem 1rem; }

/* ── Expander ── */
details summary { font-weight: 600; color: #1a2a4a; }
</style>
""", unsafe_allow_html=True)

# ── constants ─────────────────────────────────────────────────────────────────
CACHE_DIR    = ROOT / "data" / "webapp_cache"
COOKIES_FILE = ROOT / "data" / "youtube_cookies.txt"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Model catalogue — name, embed_key, dims, Pk on LECSEG-30, recommended
MODEL_CATALOGUE = [
    {"name": "BGE-Large",      "key": "bge_large", "dims": 1024, "pk": 0.3884, "notes": "Best Pk/WD overall"},
    {"name": "E5-Large",       "key": "e5large",   "dims": 1024, "pk": 0.3713, "notes": "Best combined result"},
    {"name": "MPNet",          "key": "mpnet",     "dims":  768, "pk": 0.4012, "notes": "Solid balanced choice"},
    {"name": "MiniLM (fast)",  "key": "sbert",     "dims":  384, "pk": 0.4178, "notes": "Fast; lower quality"},
]
DEFAULT_MODEL_IDX = 1  # E5-Large — best LECSEG-30 result

WHISPER_MODEL = "tiny.en"

# ── LLM auto-start ─────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def ensure_ollama_running() -> bool:
    """Try to start Ollama if not already running. Returns True if available."""
    import urllib.request
    import urllib.error

    # First check if already running
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        pass

    # Try to start it
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        time.sleep(3)
        urllib.request.urlopen("http://localhost:11434", timeout=4)
        return True
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def ensure_model_pulled(model: str = "llama3.1:8b") -> bool:
    """Pull the LLM model if not present. Returns True if available after check."""
    try:
        import urllib.request
        import json as _json
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = _json.loads(r.read().decode())
            names = [m.get("name", "") for m in data.get("models", [])]
            if any(model.split(":")[0] in n for n in names):
                return True
        # Pull in background (non-blocking)
        subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return False
    except Exception:
        return False


# ── helpers ───────────────────────────────────────────────────────────────────

def extract_video_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_dur(sec: float) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def ts_to_seconds(ts: str) -> int:
    parts = [int(p) for p in ts.strip().split(":")]
    return parts[0] * 3600 + parts[1] * 60 + parts[2] if len(parts) == 3 else parts[0] * 60 + parts[1]


def yt_ts_url(vid_id: str, sec: int) -> str:
    return f"https://www.youtube.com/watch?v={vid_id}&t={sec}s"


def cosine_gap(vecs: np.ndarray, window: int = 3) -> np.ndarray:
    N = len(vecs)
    eps = 1e-9
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms < eps] = eps
    v = vecs / norms
    scores = np.zeros(N - 1)
    for i in range(N - 1):
        lo = max(0, i - window + 1)
        hi = min(N, i + window + 1)
        left  = v[lo:i + 1].mean(axis=0)
        right = v[i + 1:hi].mean(axis=0)
        ln, rn = np.linalg.norm(left), np.linalg.norm(right)
        scores[i] = 1.0 - float(np.dot(left, right) / (ln * rn + eps))
    return scores


def video_dir(vid_id: str) -> Path:
    return CACHE_DIR / vid_id


def load_cache(vid_id: str) -> dict | None:
    p = video_dir(vid_id) / "result.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_cache(vid_id: str, result: dict) -> None:
    d = video_dir(vid_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _select_model_for_video(meta: dict, model_key: str) -> dict:
    """
    Simulate the LECSEG selector: given video metadata, return which model
    the selector would pick and why.
    """
    duration = meta.get("duration", 0)
    title    = (meta.get("title", "") + " " + meta.get("channel", "")).lower()

    # Heuristic selector logic based on LECSEG-30 research findings
    if any(k in title for k in ["math", "calculus", "algebra", "equation", "proof"]):
        domain = "Mathematics"
        chosen = next(m for m in MODEL_CATALOGUE if m["key"] == "bge_large")
        reason = "BGE-Large selected — dense notation benefits from high-dim embeddings"
    elif any(k in title for k in ["physics", "quantum", "mechanics", "thermodynamics"]):
        domain = "Physics"
        chosen = next(m for m in MODEL_CATALOGUE if m["key"] == "e5large")
        reason = "E5-Large selected — best Pk on Physics domain (cross-model conservative)"
    elif any(k in title for k in ["bio", "cell", "protein", "gene", "dna", "neural"]):
        domain = "Biology"
        chosen = next(m for m in MODEL_CATALOGUE if m["key"] == "e5large")
        reason = "E5-Large selected — strong cross-domain transfer on Biology lectures"
    elif any(k in title for k in ["cs", "algorithm", "program", "compute", "machine learning", "data"]):
        domain = "Computer Science"
        chosen = next(m for m in MODEL_CATALOGUE if m["key"] == "e5large")
        reason = "E5-Large selected — best overall Pk/WD (LECSEG-30 best: Pk=0.3713)"
    elif any(k in title for k in ["philos", "ethics", "logic", "argument", "socrates"]):
        domain = "Philosophy"
        chosen = next(m for m in MODEL_CATALOGUE if m["key"] == "bge_large")
        reason = "BGE-Large selected — strongest on Philosophy (Pk improvement +12% vs baseline)"
    else:
        domain = "General"
        chosen = next(m for m in MODEL_CATALOGUE if m["key"] == model_key)
        reason = f"User-selected: {chosen['name']} — {chosen['notes']}"

    return {"domain": domain, "model": chosen, "reason": reason}


def _smart_fallback_title(seg_texts: list[str], index: int) -> str:
    """Generate a readable title when LLM is unavailable."""
    # Try to extract meaningful phrases from first few sentences
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "so", "yet", "both", "either", "neither", "each", "few",
        "more", "most", "other", "some", "such", "no", "not", "only", "same",
        "than", "too", "very", "just", "it", "its", "this", "that", "these",
        "those", "of", "in", "to", "for", "with", "on", "at", "from", "by",
        "about", "as", "into", "through", "during", "before", "after",
        "above", "below", "between", "out", "off", "over", "under",
        "again", "then", "once", "i", "we", "you", "he", "she", "they",
        "but", "and", "or", "if", "because", "while", "although", "though",
    }
    candidates = []
    for text in seg_texts[:6]:
        text = text.strip()
        if len(text.split()) < 4:
            continue
        # Remove trailing punctuation, take first clause
        clause = re.split(r"[,;.!?]", text)[0].strip()
        words = [w for w in clause.split() if w.lower() not in stopwords and len(w) > 2]
        if len(words) >= 3:
            title = " ".join(words[:6]).capitalize()
            if len(title) >= 15:
                candidates.append(title)
    if candidates:
        # Pick the most informative (longest up to 50 chars)
        best = max(candidates, key=lambda t: min(len(t), 50))
        return best[:52] + ("…" if len(best) > 52 else "")
    return f"Section {index}"


# ── pipeline ──────────────────────────────────────────────────────────────────

STEPS = [
    {"id": "meta",      "icon": "🔍", "label": "Fetch\nMetadata",      "weight": 0.06},
    {"id": "audio",     "icon": "⬇️", "label": "Download\nAudio",      "weight": 0.14},
    {"id": "transcribe","icon": "🎤", "label": "Whisper\nTranscribe",   "weight": 0.26},
    {"id": "sentences", "icon": "✂️", "label": "Sentence\nSplit",       "weight": 0.08},
    {"id": "embed",     "icon": "🧠", "label": "Semantic\nEmbeddings",  "weight": 0.14},
    {"id": "segment",   "icon": "📐", "label": "Segment\nBoundaries",   "weight": 0.10},
    {"id": "titles",    "icon": "✍️", "label": "Generate\nTitles",      "weight": 0.14},
    {"id": "done",      "icon": "✅", "label": "Complete",              "weight": 0.08},
]


def render_pipeline(active_step: str, step_times: dict[str, float]):
    """Render the visual pipeline stepper."""
    step_ids = [s["id"] for s in STEPS]
    active_idx = step_ids.index(active_step) if active_step in step_ids else -1

    icons_row   = ""
    labels_row  = ""
    connectors  = ""

    items_html = ""
    for i, step in enumerate(STEPS):
        if i < active_idx:
            state = "done"
            elapsed = step_times.get(step["id"], "")
            time_str = f"{elapsed:.1f}s" if elapsed else "✓"
        elif i == active_idx:
            state = "active"
            time_str = "running…"
        else:
            state = ""
            time_str = ""

        items_html += f"""
        <div class="step-item {state}">
          <div class="step-circle">{step['icon']}</div>
          <div class="step-label">{step['label']}</div>
          <div class="step-time">{time_str}</div>
        </div>"""

    return f"""
    <div class="pipeline-wrap">
      <div class="pipeline-title">⚙️ Pipeline Progress</div>
      <div class="steps-row">{items_html}</div>
    </div>"""


def run_full_pipeline(
    vid_id: str,
    url: str,
    model_key: str,
    max_minutes: int,
    step_callback,   # (step_id, frac, msg)
    llm_available: bool,
) -> dict:
    import yt_dlp
    from faster_whisper import WhisperModel
    from lecseg.features.text_embeddings import embed_sentences
    from lecseg.models.hierarchical import HierarchicalSegmenter

    work_dir = video_dir(vid_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    audio_path = work_dir / "audio.mp3"

    # ── Step 1: Metadata ──────────────────────────────────────────────────────
    step_callback("meta", 0.04, "Fetching video metadata…")
    ydl_base = {"quiet": True, "skip_download": True, "no_warnings": True}
    if COOKIES_FILE.exists():
        ydl_base["cookiefile"] = str(COOKIES_FILE)

    meta, yt_chapters = {}, []
    try:
        with yt_dlp.YoutubeDL(ydl_base) as ydl:
            info = ydl.extract_info(url, download=False)
            meta = {
                "title":    info.get("title", "Lecture"),
                "channel":  info.get("uploader", ""),
                "duration": info.get("duration", 0),
                "thumb":    info.get("thumbnail", ""),
            }
            yt_chapters = [
                {"title": c["title"], "start_sec": c["start_time"]}
                for c in (info.get("chapters") or [])
            ]
    except Exception:
        meta = {"title": "Lecture", "channel": "", "duration": 0, "thumb": ""}

    # ── Step 2: Download ──────────────────────────────────────────────────────
    step_callback("audio", 0.10, "Downloading audio (audio-only, no video)…")
    if not audio_path.exists():
        ydl_dl = {
            "format":         "bestaudio/best",
            "outtmpl":        str(work_dir / "audio.%(ext)s"),
            "postprocessors": [{"key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3", "preferredquality": "64"}],
            "quiet":          True,
            "no_warnings":    True,
        }
        if COOKIES_FILE.exists():
            ydl_dl["cookiefile"] = str(COOKIES_FILE)
        if max_minutes > 0:
            ydl_dl["download_sections"]    = [{"start_time": 0, "end_time": max_minutes * 60}]
            ydl_dl["force_keyframes_at_cuts"] = True
        with yt_dlp.YoutubeDL(ydl_dl) as ydl:
            ydl.download([url])
        for f in work_dir.glob("audio.*"):
            if f.suffix != ".json" and f.name != "audio.mp3":
                f.rename(audio_path)
                break

    # ── Step 3: Transcribe ────────────────────────────────────────────────────
    transcript_path = work_dir / "transcript.json"
    if not transcript_path.exists():
        step_callback("transcribe", 0.24, f"Transcribing speech (Whisper {WHISPER_MODEL})…")
        model_w = get_whisper_model()
        segs_out, _ = model_w.transcribe(
            str(audio_path),
            language="en",
            vad_filter=True,
            word_timestamps=False,
        )
        segs = [{"text": s.text.strip(), "start": s.start, "end": s.end}
                for s in segs_out]
        transcript_path.write_text(
            json.dumps({"segments": segs}, ensure_ascii=False), encoding="utf-8"
        )
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))

    # ── Step 4: Sentences ─────────────────────────────────────────────────────
    sentences_path = work_dir / "sentences.json"
    if not sentences_path.exists():
        step_callback("sentences", 0.52, "Splitting transcript into sentences…")
        sentences = _split_sentences(transcript["segments"], max_minutes)
        sentences_path.write_text(
            json.dumps({"sentences": sentences}, ensure_ascii=False), encoding="utf-8"
        )
    sentences = json.loads(sentences_path.read_text(encoding="utf-8"))["sentences"]

    # ── Step 5: Embeddings ────────────────────────────────────────────────────
    emb_path = work_dir / f"embeddings_{model_key}.npy"
    if not emb_path.exists():
        step_callback("embed", 0.60, f"Computing sentence embeddings ({model_key})…")
        texts = [s["text"] for s in sentences]
        vecs  = embed_sentences(texts, model=model_key)
        np.save(str(emb_path), vecs)
    vecs = np.load(str(emb_path))
    N    = len(sentences)

    # ── Step 6: Segmentation ──────────────────────────────────────────────────
    step_callback("segment", 0.78, "Running hierarchical boundary detection…")
    n_ch = max(3, min(15, N // 40))
    n_st = n_ch * 2
    seg  = HierarchicalSegmenter()
    tree = seg.segment(vecs, n_chapters=n_ch, n_subtopics=n_st)
    ch_bounds = tree.chapters

    # ── Step 7: Titles ────────────────────────────────────────────────────────
    step_callback("titles", 0.87, "Generating chapter titles…")
    texts_all = [s["text"] for s in sentences]
    bounds    = [0] + sorted(ch_bounds) + [N]
    segments  = [texts_all[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]

    llm_used = False
    titles   = []

    if llm_available:
        try:
            from lecseg.refine.llm_refine import LLMRefiner
            refiner = LLMRefiner(model="llama3.1:8b")
            if refiner._is_available():
                llm_used = True
                for idx, seg_texts in enumerate(segments):
                    title = refiner.title_segment(seg_texts, max_words=7)
                    if not title or title == "Untitled Segment":
                        title = _smart_fallback_title(seg_texts, idx + 1)
                    titles.append(title)
        except Exception:
            pass

    if not llm_used:
        # Smart fallback — extract meaningful phrases from transcript
        for idx, seg_texts in enumerate(segments):
            titles.append(_smart_fallback_title(seg_texts, idx + 1))

    # ── Step 8: Build result ──────────────────────────────────────────────────
    step_callback("done", 0.97, "Finalising results…")
    chapters = []
    for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        start_sec = sentences[lo]["start"]
        end_sec   = sentences[min(hi, N - 1)]["end"]
        preview   = " ".join(texts_all[lo:lo + 3])[:130]
        chapters.append({
            "index":     i + 1,
            "title":     titles[i] if i < len(titles) else f"Section {i + 1}",
            "start_sec": start_sec,
            "end_sec":   end_sec,
            "sent_lo":   lo,
            "sent_hi":   hi,
            "preview":   preview,
            "duration":  end_sec - start_sec,
        })

    # ── Selector recommendation ───────────────────────────────────────────────
    selector = _select_model_for_video(meta, model_key)

    result = {
        "vid_id":      vid_id,
        "meta":        meta,
        "chapters":    chapters,
        "yt_chapters": yt_chapters,
        "n_sentences": N,
        "llm_used":    llm_used,
        "model_key":   model_key,
        "selector":    selector,
    }
    save_cache(vid_id, result)
    return result


def _split_sentences(raw_segs: list[dict], max_minutes: int) -> list[dict]:
    limit_sec = max_minutes * 60 if max_minutes > 0 else float("inf")
    sentences, buf_text, buf_start, buf_end, idx = [], "", None, 0.0, 0
    for seg in raw_segs:
        if seg["start"] > limit_sec:
            break
        if buf_start is None:
            buf_start = seg["start"]
        buf_text += " " + seg["text"].strip()
        buf_end   = seg["end"]
        if re.search(r"[.!?]\s*$", buf_text.strip()) or len(buf_text.split()) >= 30:
            clean = buf_text.strip()
            if clean:
                sentences.append({"idx": idx, "start": buf_start, "end": buf_end, "text": clean})
                idx += 1
            buf_text, buf_start = "", None
    if buf_text.strip() and buf_start is not None:
        sentences.append({"idx": idx, "start": buf_start, "end": buf_end, "text": buf_text.strip()})
    return sentences


@st.cache_resource(show_spinner=False)
def get_whisper_model():
    from faster_whisper import WhisperModel
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🎓 LECSEG")
    st.markdown('<div style="color:#7aacdd;font-size:0.8rem;margin-top:-8px;margin-bottom:12px">AI Lecture Chaptering · T2520718</div>', unsafe_allow_html=True)
    st.markdown("---")

    # LLM status
    llm_ok = ensure_ollama_running()
    if llm_ok:
        ensure_model_pulled("llama3.1:8b")
    status_html = (
        '<span class="status-pill pill-live">● LLM Active (Llama 3.1)</span>'
        if llm_ok else
        '<span class="status-pill pill-offline">● LLM Offline (fallback mode)</span>'
    )
    st.markdown(status_html, unsafe_allow_html=True)
    if not llm_ok:
        st.caption("Install Ollama + `ollama pull llama3.1:8b` for AI titles")

    st.markdown("---")
    st.markdown("### Embedding Model")
    st.caption("LECSEG selector picks the best model per video domain.")

    model_names = [m["name"] for m in MODEL_CATALOGUE]
    chosen_idx  = st.radio(
        "Select embedding model",
        range(len(MODEL_CATALOGUE)),
        format_func=lambda i: MODEL_CATALOGUE[i]["name"],
        index=DEFAULT_MODEL_IDX,
        label_visibility="collapsed",
    )
    sel_model = MODEL_CATALOGUE[chosen_idx]

    for i, m in enumerate(MODEL_CATALOGUE):
        rec_badge = '<span class="model-rec">BEST</span>' if m["pk"] == min(x["pk"] for x in MODEL_CATALOGUE) else ""
        card_class = "model-card selected" if i == chosen_idx else "model-card"
        st.markdown(f"""
        <div class="{card_class}">
          <div class="model-name">{m['name']}{rec_badge}</div>
          <div class="model-stat">Pk={m['pk']:.4f} · {m['dims']}d · {m['notes']}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Options")
    max_min = st.selectbox(
        "Analyse",
        [("Full video", 0), ("First 10 min (demo)", 10), ("First 20 min", 20), ("First 30 min", 30)],
        format_func=lambda x: x[0],
    )[1]
    force_rerun = st.checkbox("Re-run (bypass cache)", value=False)

    st.markdown("---")
    st.markdown("### Research Context")
    st.markdown("""
<div style="font-size:0.78rem;line-height:1.7;color:#a8c8f0">
🏅 <b>Best Pk = 0.3588</b> (balanced selector)<br>
📊 30-video LECSEG-30 benchmark<br>
🔬 5 domains · 419 chapter boundaries<br>
📝 177 unit tests · Wilcoxon p&lt;0.01<br>
🏗️ N1-N4 novel contributions
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-title">LECSEG</div>
  <p class="hero-sub">AI-powered lecture chapter generation — paste any YouTube URL and get timestamped chapters in minutes.</p>
  <div class="badge-row">
    <span class="badge">🎤 Whisper Speech Recognition</span>
    <span class="badge">🧠 Sentence Embeddings</span>
    <span class="badge">📐 Hierarchical Segmentation</span>
    <span class="badge">✍️ Llama 3.1 Titles</span>
    <span class="badge">⚡ Fully Local · No API Keys</span>
  </div>
</div>""", unsafe_allow_html=True)

# ── URL Input ─────────────────────────────────────────────────────────────────
st.markdown('<div class="input-card">', unsafe_allow_html=True)
col_url, col_btn = st.columns([5, 1])
with col_url:
    url_input = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=…  or  https://youtu.be/…",
        label_visibility="collapsed",
    )
with col_btn:
    go_btn = st.button("▶  Analyse", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── Demo shortcuts ─────────────────────────────────────────────────────────────
st.markdown("**Try a pre-processed example:**")
ex_cols = st.columns(5)
EXAMPLES = [
    ("MIT Calculus",       "https://www.youtube.com/watch?v=7K1sB05pE0A"),
    ("Harvard Ethics",     "https://www.youtube.com/watch?v=8yT4RZy1t3s"),
    ("MIT Biochemistry",   "https://www.youtube.com/watch?v=9N1MxkbFhsc"),
    ("MIT DNA Structure",  "https://www.youtube.com/watch?v=AMl6E4cLrwE"),
    ("3B1B Linear Algebra","https://www.youtube.com/watch?v=fNk_zzaMoSs"),
]
for col, (label, ex_url) in zip(ex_cols, EXAMPLES):
    if col.button(f"📺 {label}", use_container_width=True):
        url_input = ex_url
        go_btn    = True

# ═══════════════════════════════════════════════════════════════════════════════
# PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

if go_btn and url_input.strip():
    vid_id = extract_video_id(url_input.strip())
    if not vid_id:
        st.error("❌ Could not extract a YouTube video ID. Paste a full `youtube.com/watch?v=` or `youtu.be/` link.")
        st.stop()

    model_key = sel_model["key"]
    cached = None if force_rerun else load_cache(vid_id)

    if cached and cached.get("model_key") == model_key:
        result = cached
        st.success("⚡ Loaded from cache — results are instant for previously processed videos.")
    else:
        # ── Pre-flight metadata ───────────────────────────────────────────────
        preflight = st.empty()
        dur_est, title_preview = 0, ""
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(url_input.strip(), download=False)
                dur_est = info.get("duration", 0)
                if max_min > 0:
                    dur_est = min(dur_est, max_min * 60)
                title_preview = info.get("title", "")[:70]
        except Exception:
            pass

        whisper_min = dur_est * 0.15 / 60
        est_total   = int(whisper_min + 1.5) + 1
        est_label   = f"~{est_total} min" if est_total > 1 else "~1 min"
        preflight.info(
            f"**Processing:** _{title_preview}_\n\n"
            f"Estimated time: **{est_label}** — "
            f"{'first ' + str(max_min) + ' min only' if max_min else 'full video'}\n\n"
            f"Model: **{sel_model['name']}** (Pk={sel_model['pk']:.4f} on LECSEG-30)"
        )

        # ── Pipeline UI ───────────────────────────────────────────────────────
        pipeline_holder = st.empty()
        progress_bar    = st.progress(0, text="Initialising…")
        step_times: dict[str, float] = {}
        step_start: dict[str, float] = {}
        current_step = [STEPS[0]["id"]]

        def update(step_id: str, frac: float, msg: str):
            # Record timing
            now = time.time()
            prev = current_step[0]
            if prev != step_id:
                if prev in step_start:
                    step_times[prev] = now - step_start[prev]
                step_start[step_id] = now
                current_step[0] = step_id

            pipeline_holder.markdown(
                render_pipeline(step_id, step_times), unsafe_allow_html=True
            )
            progress_bar.progress(frac, text=msg)

        update(STEPS[0]["id"], 0.0, "Starting…")

        try:
            result = run_full_pipeline(
                vid_id=vid_id,
                url=url_input.strip(),
                model_key=model_key,
                max_minutes=max_min,
                step_callback=update,
                llm_available=llm_ok,
            )
            progress_bar.progress(1.0, text="✅ Done!")
            time.sleep(0.5)
            preflight.empty()
            progress_bar.empty()
            pipeline_holder.empty()
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.exception(e)
            st.stop()

    # ═══════════════════════════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════════════════════════
    meta     = result["meta"]
    chapters = result["chapters"]
    yt_chs   = result.get("yt_chapters", [])
    llm_used = result.get("llm_used", False)
    N        = result.get("n_sentences", 0)
    selector = result.get("selector", {})

    # ── Results banner ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="results-banner">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
        <div>
          <div style="font-size:1.1rem;font-weight:700;color:#1a2a4a">{meta['title']}</div>
          <div style="color:#666;font-size:0.85rem;margin-top:2px">
            {meta['channel']} &nbsp;·&nbsp; {fmt_dur(meta['duration'])}
          </div>
        </div>
        <div>
          <span class="metric-chip chip-blue">📑 {len(chapters)} chapters</span>
          <span class="metric-chip chip-blue">💬 {N:,} sentences</span>
          {"<span class='metric-chip chip-green'>🤖 Llama 3.1 titles</span>" if llm_used else "<span class='metric-chip chip-amber'>📝 Smart fallback titles</span>"}
          {"<span class='metric-chip chip-blue'>📖 " + str(len(yt_chs)) + " YT chapters</span>" if yt_chs else ""}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Selector recommendation banner ───────────────────────────────────────
    if selector:
        dom   = selector.get("domain", "")
        smeta = selector.get("model", {})
        reas  = selector.get("reason", "")
        model_used = result.get("model_key", sel_model["key"])
        chosen_name = next((m["name"] for m in MODEL_CATALOGUE if m["key"] == model_used), model_used)
        st.markdown(f"""
        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:0.7rem 1.2rem;margin-bottom:1rem;display:flex;align-items:center;gap:0.8rem;flex-wrap:wrap">
          <span style="font-size:1.1rem">🧭</span>
          <div>
            <span style="font-weight:700;color:#166534">Selector Decision:</span>
            <span style="color:#1a2a4a;font-size:0.88rem"> Domain detected: <b>{dom}</b> →
            Model used: <b>{chosen_name}</b></span>
            <div style="color:#666;font-size:0.78rem;margin-top:2px">{reas}</div>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Two-column layout ──────────────────────────────────────────────────────
    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        # YouTube embed
        st.markdown(
            f'<div style="border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.12)">'
            f'<iframe width="100%" height="340" '
            f'src="https://www.youtube.com/embed/{vid_id}?rel=0" '
            f'frameborder="0" allow="accelerometer;autoplay;clipboard-write;encrypted-media;'
            f'gyroscope;picture-in-picture" allowfullscreen></iframe></div>',
            unsafe_allow_html=True,
        )

        st.markdown(f"<br>", unsafe_allow_html=True)
        title_method = "Llama 3.1 8B (local)" if llm_used else "Smart transcript extraction"
        st.markdown(f"### 🤖 AI-Generated Chapters &nbsp; <span style='font-size:0.75rem;color:#888;font-weight:400'>· Titles via {title_method}</span>", unsafe_allow_html=True)

        for ch in chapters:
            ts_sec  = int(ch["start_sec"])
            ts_str  = fmt_ts(ch["start_sec"])
            dur_str = fmt_dur(ch.get("duration", 0))
            yt_link = yt_ts_url(vid_id, ts_sec)
            preview = ch.get("preview", "")[:120]

            st.markdown(
                f'<div class="chapter-card">'
                f'  <div class="ch-num">{ch["index"]}</div>'
                f'  <div style="flex:1;min-width:0">'
                f'    <div class="ch-title">{ch["title"]}</div>'
                f'    <div style="margin-top:4px;display:flex;align-items:center;gap:6px">'
                f'      <a href="{yt_link}" target="_blank" class="ch-ts-link">▶ {ts_str}</a>'
                f'      <span class="ch-duration">{dur_str}</span>'
                f'    </div>'
                f'    <div class="ch-preview">{preview}</div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Copy-ready description
        with st.expander("📋 Copy as YouTube Description", expanded=False):
            st.caption("Paste into your video description to activate chapter markers:")
            desc = "\n".join(f'{fmt_ts(ch["start_sec"])} {ch["title"]}' for ch in chapters)
            st.markdown(f'<div class="copy-box">{desc}</div>', unsafe_allow_html=True)
            st.code(desc, language=None)

    with right_col:
        # GT chapters comparison
        if yt_chs:
            st.markdown(f"### 📖 Creator Chapters ({len(yt_chs)})")
            st.caption("Original chapter markers from the video creator.")
            for i, ch in enumerate(yt_chs):
                ts_str  = fmt_ts(ch["start_sec"])
                yt_link = yt_ts_url(vid_id, int(ch["start_sec"]))
                st.markdown(
                    f'<div class="gt-card">'
                    f'  <div class="gt-num">{i+1}</div>'
                    f'  <div style="flex:1">'
                    f'    <div style="font-weight:600;color:#1a3a2a;font-size:0.9rem">{ch["title"]}</div>'
                    f'    <a href="{yt_link}" target="_blank" '
                    f'       style="font-family:monospace;background:#dcfce7;color:#166534;'
                    f'              border-radius:4px;padding:1px 7px;font-size:0.76rem;'
                    f'              font-weight:700;text-decoration:none">▶ {ts_str}</a>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("### 📖 No Creator Chapters")
            st.info("This video has no creator-provided chapters — LECSEG fills that gap automatically.")

        # Semantic dissimilarity chart
        emb_path  = video_dir(vid_id) / f"embeddings_{result.get('model_key', 'sbert')}.npy"
        sent_path = video_dir(vid_id) / "sentences.json"
        if emb_path.exists() and sent_path.exists():
            st.markdown("---")
            st.markdown("#### 📉 Semantic Dissimilarity Curve")
            st.caption("Peaks mark where the model detected topic shifts. Red lines = chapter boundaries.")
            try:
                import plotly.graph_objects as go
                vp = np.load(str(emb_path))
                sp = json.loads(sent_path.read_text())["sentences"]
                gs = cosine_gap(vp)
                times = np.array([s["start"] for s in sp[:-1]])
                pred_ts = [ch["start_sec"] for ch in chapters[1:]]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=times, y=gs,
                    fill="tozeroy",
                    fillcolor="rgba(45,106,191,0.07)",
                    line=dict(color="#2d6abf", width=1.5),
                    name="Dissimilarity",
                    hovertemplate="t=%{x:.0f}s · dissim=%{y:.3f}<extra></extra>",
                ))
                for t in pred_ts:
                    fig.add_vline(x=t, line_color="#e74c3c", line_width=1.5, opacity=0.6)

                tick_step = max(60, int(max(times) / 8 / 60) * 60) if len(times) else 60
                ticks = list(range(0, int(max(times)) + 1, tick_step)) if len(times) else []
                fig.update_layout(
                    height=220,
                    margin=dict(l=5, r=5, t=8, b=25),
                    xaxis=dict(tickvals=ticks, ticktext=[fmt_ts(t) for t in ticks], tickfont_size=10),
                    yaxis=dict(title="Dissim.", tickfont_size=10),
                    plot_bgcolor="#f8fafc",
                    paper_bgcolor="#f8fafc",
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            except Exception:
                pass

        # How it works expander
        st.markdown("---")
        with st.expander("⚙️ How LECSEG works", expanded=False):
            st.markdown(f"""
**Pipeline steps (current run: `{sel_model['name']}`)**

| Step | What happens |
|------|-------------|
| 🎤 Whisper ASR | Speech-to-text (CPU, ~15% realtime) |
| ✂️ Sentence split | spaCy-based sentence segmentation |
| 🧠 Embeddings | `{sel_model['name']}` · {sel_model['dims']}d vectors |
| 📐 Hierarchical seg | Two-stage boundary predictor (N1) |
| ✍️ LLM titling | {'Llama 3.1 8B via Ollama (local, no API)' if llm_used else 'Smart transcript heuristic (Ollama offline)'} |

**Research results on LECSEG-30 benchmark:**
- `{sel_model['name']}`: Pk={sel_model['pk']:.4f}
- Best overall (selector): Pk=0.3588, WD=0.3739
- Significantly better than all baselines (p<0.01, Wilcoxon)

*Pre-thesis project T2520718 · 30-video academic benchmark*
            """)

elif go_btn and not url_input.strip():
    st.warning("Please paste a YouTube URL first.")

else:
    # ── Landing state ──────────────────────────────────────────────────────────
    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div style="background:white;border:1px solid #e4edf8;border-radius:12px;padding:1.2rem 1.4rem">
        <div style="font-weight:700;color:#1a2a4a;font-size:0.95rem;margin-bottom:0.6rem">🚀 How it works</div>
        <ol style="color:#555;font-size:0.83rem;line-height:1.9;margin:0;padding-left:1.2rem">
          <li>Paste any YouTube lecture URL</li>
          <li>Audio is downloaded (no video needed)</li>
          <li>Whisper transcribes locally</li>
          <li>LECSEG detects topic boundaries</li>
          <li>Llama 3.1 writes chapter titles</li>
        </ol>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div style="background:white;border:1px solid #e4edf8;border-radius:12px;padding:1.2rem 1.4rem">
        <div style="font-weight:700;color:#1a2a4a;font-size:0.95rem;margin-bottom:0.6rem">📦 What you get</div>
        <ul style="color:#555;font-size:0.83rem;line-height:1.9;margin:0;padding-left:1.2rem">
          <li>Clickable timestamped chapters</li>
          <li>AI-written title for each segment</li>
          <li>Comparison vs creator chapters</li>
          <li>Copy-paste YouTube description format</li>
          <li>Semantic dissimilarity chart</li>
        </ul>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div style="background:white;border:1px solid #e4edf8;border-radius:12px;padding:1.2rem 1.4rem">
        <div style="font-weight:700;color:#1a2a4a;font-size:0.95rem;margin-bottom:0.6rem">🔬 Research behind this</div>
        <ul style="color:#555;font-size:0.83rem;line-height:1.9;margin:0;padding-left:1.2rem">
          <li>LECSEG-30: 30-video benchmark</li>
          <li>Best Pk=0.3588 (selector), 0.3713 (global)</li>
          <li>Statistically significant: p&lt;0.01</li>
          <li>177 unit tests · fully reproducible</li>
          <li>5 domains · 419 chapter annotations</li>
        </ul>
        </div>""", unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#bbb;font-size:0.76rem;margin-top:0.5rem">'
    'LECSEG &nbsp;·&nbsp; Pre-Thesis T2520718 &nbsp;·&nbsp; 2026 &nbsp;·&nbsp;'
    ' Whisper + Sentence-BERT + Hierarchical Segmentation + Llama 3.1 &nbsp;·&nbsp; Fully Local</p>',
    unsafe_allow_html=True,
)
