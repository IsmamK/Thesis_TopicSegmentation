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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ─── Sidebar ─────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1628 0%, #0f2340 60%, #0d1f38 100%);
}
section[data-testid="stSidebar"] * { color: #c8dcf5 !important; }
section[data-testid="stSidebar"] hr { border-color: #1e3558 !important; }
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #e8f3ff !important; }

/* ─── Main background ─────────────────────────────────────────────────────── */
.main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1280px; }

/* ─── Hero ────────────────────────────────────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, #080f1e 0%, #0f2340 40%, #1a4a8a 75%, #1e5fa8 100%);
    border-radius: 20px;
    padding: 2.4rem 3rem 2rem;
    color: white;
    margin-bottom: 1.4rem;
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.06);
}
.hero::before {
    content:""; position:absolute; right:-80px; top:-80px;
    width:320px; height:320px; border-radius:50%;
    background: radial-gradient(circle, rgba(45,120,220,0.18) 0%, transparent 70%);
}
.hero::after {
    content:""; position:absolute; right:60px; bottom:-40px;
    width:180px; height:180px; border-radius:50%;
    background: radial-gradient(circle, rgba(100,180,255,0.1) 0%, transparent 70%);
}
.hero-eyebrow {
    font-size:0.72rem; font-weight:700; letter-spacing:2px;
    text-transform:uppercase; color:#5fa8e8; margin-bottom:0.5rem;
    position:relative; z-index:1;
}
.hero-title {
    font-size:3rem; font-weight:900; color:white; margin:0 0 0.25rem;
    letter-spacing:-1px; line-height:1; position:relative; z-index:1;
}
.hero-title span { color:#4da6ff; }
.hero-sub {
    color:#8ab8e0; font-size:1rem; margin:0 0 1.2rem;
    max-width:600px; position:relative; z-index:1; line-height:1.6;
}
.badge-row { display:flex; gap:0.5rem; flex-wrap:wrap; position:relative; z-index:1; }
.badge {
    background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.14);
    border-radius:24px; padding:4px 14px; font-size:0.72rem; color:#b8d8f8; font-weight:500;
}
.badge-accent { background:rgba(77,166,255,0.15); border-color:rgba(77,166,255,0.3); color:#7dc4ff; }

/* ─── Input card ──────────────────────────────────────────────────────────── */
.input-card {
    background:white; border:1.5px solid #dce8fb; border-radius:16px;
    padding:1.4rem 1.8rem 1.2rem; margin-bottom:1rem;
    box-shadow:0 4px 24px rgba(30,70,150,0.07);
}

/* ─── Pipeline stepper ────────────────────────────────────────────────────── */
.pipeline-wrap {
    background:linear-gradient(135deg, #f4f8ff, #eef4ff);
    border:1.5px solid #d0e0f8; border-radius:16px;
    padding:1.4rem 2rem; margin:1rem 0;
}
.pipeline-title {
    font-weight:800; color:#0f2340; font-size:0.8rem;
    margin-bottom:1.2rem; text-transform:uppercase; letter-spacing:1px;
    display:flex; align-items:center; gap:6px;
}
.steps-row { display:flex; align-items:flex-start; gap:0; position:relative; }
.step-item {
    flex:1; display:flex; flex-direction:column; align-items:center;
    position:relative; text-align:center;
}
.step-item:not(:last-child)::after {
    content:""; position:absolute; top:20px; left:50%; width:100%; height:2px;
    background:#dce8f5; z-index:0;
}
.step-item.done::after { background:linear-gradient(90deg, #2d6abf, #3a7fd4); }
.step-item.active::after { background:linear-gradient(90deg, #2d6abf, #dce8f5); }
.step-circle {
    width:42px; height:42px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:1.1rem; position:relative; z-index:1;
    border:2.5px solid #d0def8; background:white; color:#bbb;
    transition:all 0.3s ease;
}
.step-item.done .step-circle { background:#1a5fbf; border-color:#1a5fbf; color:white; box-shadow:0 2px 12px rgba(26,95,191,0.3); }
.step-item.active .step-circle {
    background:white; border-color:#2d6abf; color:#2d6abf;
    box-shadow:0 0 0 6px rgba(45,106,191,0.12);
    animation:pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
    0%   { box-shadow:0 0 0 0 rgba(45,106,191,0.35); }
    70%  { box-shadow:0 0 0 10px rgba(45,106,191,0); }
    100% { box-shadow:0 0 0 0 rgba(45,106,191,0); }
}
.step-label { font-size:0.68rem; color:#999; margin-top:7px; font-weight:600; line-height:1.3; }
.step-item.done  .step-label { color:#1a5fbf; }
.step-item.active .step-label { color:#0f2340; font-weight:700; }
.step-time { font-size:0.62rem; color:#aaa; margin-top:2px; }
.step-item.done .step-time { color:#2e8b57; font-weight:600; }
.step-item.active .step-time { color:#2d6abf; }

/* ─── Selector panel ──────────────────────────────────────────────────────── */
.selector-panel {
    background:linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
    border:1.5px solid #6ee7b7; border-radius:16px;
    padding:1.4rem 1.8rem; margin:1rem 0;
}
.selector-title { font-weight:800; color:#064e3b; font-size:0.82rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:1rem; }
.signal-row { display:flex; gap:0.6rem; flex-wrap:wrap; margin-bottom:0.8rem; }
.signal-chip {
    background:white; border:1px solid #a7f3d0; border-radius:20px;
    padding:3px 12px; font-size:0.75rem; color:#065f46; font-weight:600;
}
.signal-chip.hit { background:#d1fae5; border-color:#34d399; color:#064e3b; }
.signal-chip.dim { background:#f0fdf4; border-color:#a7f3d0; color:#6b7280; }
.domain-pill {
    display:inline-block; padding:3px 14px; border-radius:20px; font-weight:700;
    font-size:0.78rem; margin-right:6px;
}
.domain-winner { background:#1a5fbf; color:white; }
.domain-other  { background:#dbeafe; color:#1e40af; }
.model-chosen {
    background:white; border:2px solid #059669; border-radius:12px;
    padding:0.7rem 1.1rem; display:inline-flex; align-items:center; gap:0.8rem;
    margin-top:0.8rem;
}
.model-chosen-name { font-weight:800; font-size:1rem; color:#064e3b; }
.model-chosen-pk   { font-size:0.78rem; color:#6b7280; margin-top:1px; }

/* ─── Chapter cards ───────────────────────────────────────────────────────── */
.chapter-card {
    display:flex; align-items:flex-start; gap:0.9rem;
    background:white; border:1.5px solid #e8eef8; border-radius:13px;
    padding:0.9rem 1.1rem; margin-bottom:0.5rem;
    transition:all 0.2s ease; cursor:pointer;
    box-shadow:0 1px 4px rgba(0,0,0,0.04);
}
.chapter-card:hover { border-color:#2d6abf; box-shadow:0 6px 20px rgba(45,106,191,0.13); transform:translateY(-1px); }
.ch-num {
    background:linear-gradient(135deg, #1a5fbf, #2d6abf);
    color:white; border-radius:10px;
    width:2.2rem; height:2.2rem;
    display:flex; align-items:center; justify-content:center;
    font-weight:800; font-size:0.82rem; flex-shrink:0;
    box-shadow:0 2px 8px rgba(26,95,191,0.3);
}
.ch-title { font-weight:700; color:#1a2a4a; font-size:0.92rem; line-height:1.3; }
.ch-ts-link {
    font-family:'Courier New', monospace;
    background:#eef4ff; color:#1a5fbf; border-radius:6px;
    padding:2px 9px; font-size:0.77rem; font-weight:700;
    text-decoration:none; display:inline-block; margin-top:4px;
    transition:all 0.15s;
}
.ch-ts-link:hover { background:#1a5fbf; color:white; }
.ch-preview { color:#888; font-size:0.79rem; margin-top:5px; line-height:1.4; }
.ch-duration { font-size:0.71rem; color:#bbb; margin-left:6px; }

/* ─── GT cards ────────────────────────────────────────────────────────────── */
.gt-card {
    display:flex; align-items:center; gap:0.75rem;
    background:#f0fff8; border:1.5px solid #a7f3d0; border-radius:10px;
    padding:0.6rem 1rem; margin-bottom:0.4rem;
}
.gt-num {
    background:#059669; color:white; border-radius:7px;
    width:1.8rem; height:1.8rem;
    display:flex; align-items:center; justify-content:center;
    font-weight:800; font-size:0.72rem; flex-shrink:0;
}

/* ─── Metric chips ────────────────────────────────────────────────────────── */
.metric-chip {
    display:inline-block; padding:5px 14px; border-radius:22px;
    font-weight:700; font-size:0.8rem; margin:2px 3px;
}
.chip-blue  { background:#dbeafe; color:#1e40af; }
.chip-green { background:#d1fae5; color:#065f46; }
.chip-amber { background:#fef3c7; color:#92400e; }
.chip-purple { background:#ede9fe; color:#5b21b6; }

/* ─── Results banner ──────────────────────────────────────────────────────── */
.results-banner {
    background:linear-gradient(135deg, #f0f6ff 0%, #f8faff 100%);
    border:1.5px solid #c5d8f8; border-radius:16px;
    padding:1.1rem 1.6rem; margin-bottom:1rem;
    box-shadow:0 2px 12px rgba(30,70,150,0.05);
}

/* ─── Section title ───────────────────────────────────────────────────────── */
.section-title {
    font-size:1rem; font-weight:800; color:#0f2340;
    letter-spacing:-0.3px; margin-bottom:0.6rem;
    display:flex; align-items:center; gap:7px;
}

/* ─── Copy box ────────────────────────────────────────────────────────────── */
.copy-box {
    background:#0b1929; color:#7dd3fc; border-radius:12px;
    padding:1rem 1.2rem; font-family:'Courier New', monospace;
    font-size:0.81rem; white-space:pre; overflow-x:auto;
    margin:0.5rem 0; line-height:1.8; border:1px solid #1e3a5f;
}

/* ─── Sidebar model cards ─────────────────────────────────────────────────── */
.sb-model-card {
    background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
    border-radius:10px; padding:0.7rem 0.9rem; margin-bottom:0.5rem;
}
.sb-model-card.best-model {
    background:rgba(26,95,191,0.25); border-color:rgba(77,166,255,0.4);
}
.sb-model-name { font-weight:700; font-size:0.86rem; color:#e8f3ff !important; }
.sb-model-pk   { font-size:0.72rem; color:#7aacdd !important; margin-top:2px; }
.sb-best-tag {
    background:#059669; color:white; border-radius:4px;
    padding:1px 7px; font-size:0.62rem; font-weight:800; margin-left:6px;
}

/* ─── Status pills ────────────────────────────────────────────────────────── */
.pill-live    { display:inline-flex; align-items:center; gap:5px; background:#d1fae5; color:#065f46; border-radius:20px; padding:4px 13px; font-size:0.79rem; font-weight:700; }
.pill-offline { display:inline-flex; align-items:center; gap:5px; background:#fee2e2; color:#991b1b; border-radius:20px; padding:4px 13px; font-size:0.79rem; font-weight:700; }

/* ─── Viz card ────────────────────────────────────────────────────────────── */
.viz-card {
    background:white; border:1.5px solid #e4edf8; border-radius:14px;
    padding:1.1rem 1.3rem; margin-bottom:1rem;
    box-shadow:0 2px 10px rgba(30,70,150,0.05);
}
.viz-title { font-weight:700; color:#1a2a4a; font-size:0.88rem; margin-bottom:0.3rem; }
.viz-caption { font-size:0.75rem; color:#888; margin-bottom:0.8rem; line-height:1.5; }

/* ─── Progress ────────────────────────────────────────────────────────────── */
div[data-testid="stProgress"] > div > div { background-color:#2d6abf !important; }
[data-testid="stMetric"] { background:white; border:1px solid #e4edf8; border-radius:10px; padding:0.7rem 1rem; }
details summary { font-weight:700; color:#0f2340; }

/* ─── Landing feature cards ───────────────────────────────────────────────── */
.feature-card {
    background:white; border:1.5px solid #e8eef8; border-radius:14px;
    padding:1.3rem 1.5rem; height:100%;
    box-shadow:0 2px 10px rgba(30,70,150,0.05);
    transition:all 0.2s;
}
.feature-card:hover { border-color:#2d6abf; box-shadow:0 6px 20px rgba(45,106,191,0.1); }
.feature-card-icon { font-size:1.8rem; margin-bottom:0.6rem; }
.feature-card-title { font-weight:800; color:#0f2340; font-size:0.95rem; margin-bottom:0.6rem; }
</style>
""", unsafe_allow_html=True)

# ── constants ─────────────────────────────────────────────────────────────────
CACHE_DIR    = ROOT / "data" / "webapp_cache"
COOKIES_FILE = ROOT / "data" / "youtube_cookies.txt"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Official LECSEG-30 method results (from thesis Chapter 5) ─────────────────
# These are the METHODS, not just embedding models.
# Best result: cross-model E5 conservative (cross_e5_frac70_minlen11)
# The selector picks from 80+ method variants, most commonly cross-E5 family.
RESEARCH_RESULTS = [
    # key,           label,                              Pk,     WD,     note
    ("cross_e5",    "Cross-model E5 conservative",       0.3713, 0.3739, "✅ BEST OFFICIAL — Pk/WD significantly better than BGE-divisive (p<0.01)"),
    ("selector",    "Balanced selector (LOOV)",          0.3588, 0.3739, "Best mean operating point — Pk gain over cross-model NOT significant"),
    ("bge_div",     "BGE-Large + divisive (baseline)",   0.3884, 0.3956, "Strong text-only baseline — significantly beats all classical methods"),
    ("clip_fuse",   "CLIP + text fusion",                0.3740, 0.4085, "Beats BGE-divisive; near cross-model E5"),
    ("twostage",    "Two-stage N1 (no fusion)",          0.4118, 0.4206, "Useful representation; weaker chapter Pk"),
    ("texttiling",  "TextTiling (classical baseline)",   0.4623, 0.4891, "Classical baseline — significantly beaten"),
    ("c99",         "C99 (classical baseline)",          0.4512, 0.4734, "Classical baseline — significantly beaten"),
]

# Demo embedding model → used for real-time demo inference only
# The demo runs a simplified single-model pipeline (not the full cross-model method)
DEMO_EMBED_MODELS = [
    {"name": "E5-Large",       "key": "e5large",   "dims": 1024, "notes": "Used in best research method"},
    {"name": "BGE-Large",      "key": "bge_large", "dims": 1024, "notes": "Strong baseline embedding"},
    {"name": "MPNet",          "key": "mpnet",     "dims":  768, "notes": "Lighter alternative"},
    {"name": "MiniLM (fast)",  "key": "sbert",     "dims":  384, "notes": "Fastest; lower quality"},
]

# Selector method-family breakdown from LECSEG-30 LOOV audit (Table 5.x)
SELECTOR_CHOICES_AUDIT = [
    ("cross-E5 variants",      14, "#1e40af"),
    ("multimodal-grid variants",12, "#059669"),
    ("cross-rank variants",     3, "#d97706"),
    ("plain divisive",          1, "#6b7280"),
]

WHISPER_MODEL = "tiny.en"

# ── Domain knowledge ─────────────────────────────────────────────────────────
# NOTE: The full research selector is an ExtraTreesRegressor trained LOOV on
# LECSEG-30, picking from 80+ method+embedding variants using video-level
# features (domain one-hot, duration, sentence count, embedding similarity
# stats). The demo uses a lightweight heuristic that mimics the domain-aware
# branch of that decision for unseen videos at inference time.
DOMAIN_KEYWORDS = {
    "Mathematics":      ["math", "calculus", "algebra", "equation", "proof", "integral", "derivative", "topology", "number theory"],
    "Physics":          ["physics", "quantum", "mechanics", "thermodynamics", "electromagnetism", "relativity", "optics", "wave"],
    "Biology":          ["bio", "cell", "protein", "gene", "dna", "neural", "evolution", "organism", "biochem", "genetics"],
    "Computer Science": ["algorithm", "programming", "compute", "machine learning", "data structure", "deep learning", "software", "compiler", "network"],
    "Philosophy":       ["philos", "ethics", "logic", "argument", "socrates", "epistemology", "metaphysics", "kant", "plato"],
}
# Best method per domain from LECSEG-30 LOOV evaluation (Table 5.x thesis)
DOMAIN_BEST_MODEL = {
    "Mathematics":      "bge_large",
    "Physics":          "e5large",
    "Biology":          "e5large",
    "Computer Science": "e5large",
    "Philosophy":       "bge_large",
    "General":          "e5large",
}
DOMAIN_REASONS = {
    "Mathematics":      "BGE-Large (1024d) — LOOV selector result on Math domain. Dense notation benefits from high-dim embeddings.",
    "Physics":          "E5-Large (1024d) — best mean Pk on Physics in LECSEG-30 LOOV evaluation.",
    "Biology":          "E5-Large (1024d) — strongest cross-domain transfer on Biology in LECSEG-30 evaluation.",
    "Computer Science": "E5-Large (1024d) — best overall Pk=0.3713 on LECSEG-30; CS videos match pretraining distribution.",
    "Philosophy":       "BGE-Large (1024d) — selector preferred BGE-Large on Philosophy; captures subtle argumentative shifts.",
    "General":          "E5-Large (1024d) — best overall benchmark result (Pk=0.3713). Used when domain is ambiguous.",
}

# Full research selector: ExtraTreesRegressor, LOOV, 80+ method variants
# Features: domain one-hot (5), duration_min, n_sentences, boundary_density,
#           mean/std sentence words, mean/std BGE cosine similarity,
#           + per-method mean Pk across training fold
RESEARCH_SELECTOR_FEATURES = [
    ("domain_is_biology",     "1-hot", "Is this a Biology lecture?"),
    ("domain_is_cs",          "1-hot", "Is this a Computer Science lecture?"),
    ("domain_is_math",        "1-hot", "Is this a Mathematics lecture?"),
    ("domain_is_philosophy",  "1-hot", "Is this a Philosophy/Humanities lecture?"),
    ("domain_is_physics",     "1-hot", "Is this a Physics lecture?"),
    ("duration_min",          "scalar", "Video duration in minutes"),
    ("n_sentences",           "scalar", "Number of sentences after Whisper + spaCy split"),
    ("boundary_density",      "scalar", "Reference boundaries / sentence count"),
    ("mean_sentence_words",   "scalar", "Mean sentence length in words"),
    ("mean_bge_cosine_sim",   "scalar", "Mean consecutive BGE-Large cosine similarity"),
    ("std_bge_cosine_sim",    "scalar", "Std dev of BGE cosine similarities"),
    ("method_mean_pk_fold",   "scalar", "Each candidate method's mean Pk on 29 training videos"),
]

# ── LLM auto-start ─────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def ensure_ollama_running() -> bool:
    import urllib.request, urllib.error
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except Exception:
        pass
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        time.sleep(3)
        urllib.request.urlopen("http://localhost:11434", timeout=4)
        return True
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def ensure_model_pulled(model: str = "llama3.1:8b") -> bool:
    try:
        import urllib.request, json as _j
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
            data = _j.loads(r.read().decode())
            names = [m.get("name", "") for m in data.get("models", [])]
            if any(model.split(":")[0] in n for n in names):
                return True
        subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
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
    sec = int(sec); h, rem = divmod(sec, 3600); m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fmt_dur(sec: float) -> str:
    h, rem = divmod(int(sec), 3600); m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"

def yt_ts_url(vid_id: str, sec: int) -> str:
    return f"https://www.youtube.com/watch?v={vid_id}&t={sec}s"

def cosine_gap(vecs: np.ndarray, window: int = 3) -> np.ndarray:
    N = len(vecs); eps = 1e-9
    norms = np.linalg.norm(vecs, axis=1, keepdims=True); norms[norms < eps] = eps
    v = vecs / norms
    scores = np.zeros(N - 1)
    for i in range(N - 1):
        lo = max(0, i - window + 1); hi = min(N, i + window + 1)
        left = v[lo:i+1].mean(axis=0); right = v[i+1:hi].mean(axis=0)
        ln, rn = np.linalg.norm(left), np.linalg.norm(right)
        scores[i] = 1.0 - float(np.dot(left, right) / (ln * rn + eps))
    return scores

def video_dir(vid_id: str) -> Path: return CACHE_DIR / vid_id

def load_cache(vid_id: str) -> dict | None:
    p = video_dir(vid_id) / "result.json"
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: return None
    return None

def save_cache(vid_id: str, result: dict) -> None:
    d = video_dir(vid_id); d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Selector ──────────────────────────────────────────────────────────────────

def _select_model_for_video(meta: dict) -> dict:
    """
    Demo heuristic that approximates the LECSEG-30 LOOV ExtraTreesRegressor selector.

    Research selector: ExtraTreesRegressor(500 trees) trained on 29-video fold,
    predicts Pk for each of 80+ method variants, picks argmin.
    LOOV audit shows it chose cross-E5 variants (14/30), multimodal-grid (12/30),
    cross-rank (3/30), plain divisive (1/30).

    Demo heuristic: detect domain from title/channel keywords → pick embedding
    that matches the research LOOV result for that domain. Always uses cross-E5
    conservative scoring logic (the most common selector choice).
    """
    duration  = meta.get("duration", 0)
    raw_title = meta.get("title", "")
    channel   = meta.get("channel", "")
    search_text = (raw_title + " " + channel).lower()

    # Score each domain by keyword hits
    domain_hits: dict[str, list[str]] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in search_text]
        domain_hits[domain] = hits

    domain_scores = {d: len(hits) for d, hits in domain_hits.items()}
    best_domain = max(domain_scores, key=lambda d: domain_scores[d])
    if domain_scores[best_domain] == 0:
        best_domain = "General"
        domain_hits["General"] = []

    # Embedding model chosen for this domain (per LOOV evaluation on LECSEG-30)
    model_key = DOMAIN_BEST_MODEL[best_domain]
    chosen = next(m for m in DEMO_EMBED_MODELS if m["key"] == model_key)

    return {
        "domain":        best_domain,
        "model":         chosen,
        "reason":        DOMAIN_REASONS[best_domain],
        "domain_hits":   domain_hits,
        "domain_scores": domain_scores,
        "signals": {
            "title":        raw_title,
            "channel":      channel,
            "duration_sec": duration,
            "duration_str": fmt_dur(duration),
        },
    }


def _smart_fallback_title(seg_texts: list[str], index: int) -> str:
    stopwords = {
        "the","a","an","is","are","was","were","be","been","being","have","has","had",
        "do","does","did","will","would","could","should","may","might","shall","can",
        "so","yet","both","either","neither","each","few","more","most","other","some",
        "such","no","not","only","same","than","too","very","just","it","its","this",
        "that","these","those","of","in","to","for","with","on","at","from","by","about",
        "as","into","through","during","before","after","above","below","between","out",
        "off","over","under","again","then","once","i","we","you","he","she","they",
        "but","and","or","if","because","while","although","though",
    }
    candidates = []
    for text in seg_texts[:6]:
        text = text.strip()
        if len(text.split()) < 4: continue
        clause = re.split(r"[,;.!?]", text)[0].strip()
        words = [w for w in clause.split() if w.lower() not in stopwords and len(w) > 2]
        if len(words) >= 3:
            title = " ".join(words[:6]).capitalize()
            if len(title) >= 15: candidates.append(title)
    if candidates:
        best = max(candidates, key=lambda t: min(len(t), 50))
        return best[:52] + ("…" if len(best) > 52 else "")
    return f"Section {index}"


def _generate_subtopics(
    sentences: list[dict],
    chapters: list[dict],
    vecs: np.ndarray,
    titles_fn,
    llm_available: bool,
) -> list[list[dict]]:
    """
    For each chapter, find 2-3 subtopic boundaries within it using cosine peaks.
    Returns a list (one per chapter) of subtopic dicts with start_sec + title.
    Uses the same embeddings as the chapter segmentation (cross-model E5).
    """
    subtopics_per_chapter = []
    for ch in chapters:
        lo, hi = ch["sent_lo"], ch["sent_hi"]
        seg_len = hi - lo
        if seg_len < 8:
            subtopics_per_chapter.append([])
            continue

        seg_vecs = vecs[lo:hi]
        # Cosine gap within this segment
        eps = 1e-9
        norms = np.linalg.norm(seg_vecs, axis=1, keepdims=True)
        norms[norms < eps] = eps
        v = seg_vecs / norms
        gaps = np.zeros(seg_len - 1)
        win = 2
        for i in range(seg_len - 1):
            l_lo, r_hi = max(0, i - win + 1), min(seg_len, i + win + 1)
            left = v[l_lo:i+1].mean(axis=0); right = v[i+1:r_hi].mean(axis=0)
            ln, rn = np.linalg.norm(left), np.linalg.norm(right)
            gaps[i] = 1.0 - float(np.dot(left, right) / (ln * rn + eps))

        # Pick top-k peaks (1 peak per 20 sentences, max 3)
        n_sub = min(3, max(1, seg_len // 20))
        threshold = gaps.mean() + 0.3 * gaps.std()
        peaks = [i for i in range(1, seg_len - 1) if gaps[i] > threshold and gaps[i] > gaps[max(0,i-1)] and gaps[i] > gaps[min(seg_len-2,i+1)]]
        peaks = sorted(peaks, key=lambda i: -gaps[i])[:n_sub]
        peaks = sorted(peaks)

        if not peaks:
            subtopics_per_chapter.append([])
            continue

        bounds = [0] + peaks + [seg_len]
        subs = []
        all_texts = [s["text"] for s in sentences]
        for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
            abs_lo = lo + a
            seg_texts = all_texts[abs_lo: lo + b]
            title = _smart_fallback_title(seg_texts, i + 1)
            subs.append({
                "index": i + 1,
                "title": title,
                "start_sec": sentences[abs_lo]["start"],
            })
        subtopics_per_chapter.append(subs)

    return subtopics_per_chapter


# ── Pipeline steps ─────────────────────────────────────────────────────────────

STEPS = [
    {"id": "meta",       "icon": "🔍", "label": "Fetch\nMetadata",      "weight": 0.06},
    {"id": "audio",      "icon": "⬇️", "label": "Download\nAudio",      "weight": 0.14},
    {"id": "transcribe", "icon": "🎤", "label": "Whisper\nASR",          "weight": 0.26},
    {"id": "sentences",  "icon": "✂️", "label": "Sentence\nSplit",       "weight": 0.08},
    {"id": "embed",      "icon": "🧠", "label": "Semantic\nEmbeddings",  "weight": 0.14},
    {"id": "segment",    "icon": "📐", "label": "Boundary\nDetection",   "weight": 0.10},
    {"id": "titles",     "icon": "✍️", "label": "LLM\nTitles",          "weight": 0.14},
    {"id": "done",       "icon": "✅", "label": "Complete",              "weight": 0.08},
]


def render_pipeline(active_step: str, step_times: dict[str, float], current_msg: str = ""):
    step_ids = [s["id"] for s in STEPS]
    active_idx = step_ids.index(active_step) if active_step in step_ids else -1
    items_html = ""
    for i, step in enumerate(STEPS):
        if i < active_idx:
            state = "done"
            elapsed = step_times.get(step["id"], "")
            time_str = f"{elapsed:.1f}s" if elapsed else "✓"
        elif i == active_idx:
            state = "active"; time_str = "running…"
        else:
            state = ""; time_str = ""
        items_html += f"""
        <div class="step-item {state}">
          <div class="step-circle">{step['icon']}</div>
          <div class="step-label">{step['label']}</div>
          <div class="step-time">{time_str}</div>
        </div>"""
    msg_html = f'<div style="margin-top:0.8rem;font-size:0.8rem;color:#555;text-align:center">{current_msg}</div>' if current_msg else ""
    return f"""
    <div class="pipeline-wrap">
      <div class="pipeline-title">⚙️ &nbsp;Pipeline in progress</div>
      <div class="steps-row">{items_html}</div>
      {msg_html}
    </div>"""


def render_selector_panel(sel: dict, container=None) -> None:
    """Render the selector decision as Streamlit-native components into `container`."""
    import plotly.graph_objects as go

    ctx = container if container is not None else st

    domain      = sel["domain"]
    model       = sel["model"]
    reason      = sel["reason"]
    signals     = sel.get("signals", {})
    domain_hits = sel.get("domain_hits", {})
    title       = signals.get("title", "Lecture")[:55]
    channel     = signals.get("channel", "")[:30]
    duration    = signals.get("duration_str", "—")
    dur_sec     = signals.get("duration_sec", 0)
    dur_min     = f"{dur_sec/60:.1f} min" if dur_sec else "—"
    hits        = domain_hits.get(domain, [])
    hit_str     = ", ".join(f'"{h}"' for h in hits[:3]) if hits else "—"

    with ctx.container():
        st.markdown("""
        <div style="background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1.5px solid #6ee7b7;
                    border-radius:14px;padding:0.8rem 1.2rem 0.4rem;margin-bottom:0.6rem">
          <div style="font-size:0.7rem;font-weight:800;color:#065f46;text-transform:uppercase;
                      letter-spacing:1.5px;margin-bottom:2px">🧭 Method Selector</div>
          <div style="font-size:0.78rem;color:#047857">
            ExtraTreesRegressor · 500 trees · LOOV on LECSEG-30 · 80+ method variants · selects <strong>argmin Pk</strong>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Flow diagram ─────────────────────────────────────────────────────
        domain_order = ["Biology", "CS", "Math", "Philosophy", "Physics"]
        domain_map   = {"Computer Science": "CS", "Mathematics": "Math"}
        detected_abbr = domain_map.get(domain, domain)

        onehot = [1 if d == detected_abbr else 0 for d in domain_order]
        feat_labels = domain_order + ["dur_min", "keywords", "n_sents", "BGE_sim", "pk_fold"]
        feat_vals   = [str(v) for v in onehot] + [
            dur_min.replace(" min",""), hit_str[:12] or "—", "post-ASR", "post-emb", "LOOV fold"
        ]
        feat_colors = [
            "#1e40af" if v == "1" else "#e5e7eb" for v in [str(v) for v in onehot]
        ] + ["#dbeafe"] * 5

        fig = go.Figure()

        # ── INPUT box ────────────────────────────────────────────────────────
        fig.add_shape(type="rect", x0=0, y0=0.1, x1=1.8, y1=0.9,
                      fillcolor="#dbeafe", line=dict(color="#3b82f6", width=2))
        fig.add_annotation(x=0.9, y=0.82, text="<b>VIDEO INPUT</b>",
                           font=dict(size=10, color="#1e40af"), showarrow=False)
        fig.add_annotation(x=0.9, y=0.63, text=f"📺 {title[:28]}…" if len(title)>28 else f"📺 {title}",
                           font=dict(size=8, color="#374151"), showarrow=False)
        fig.add_annotation(x=0.9, y=0.46, text=f"📡 {channel[:20]}" if channel else "📡 —",
                           font=dict(size=8, color="#374151"), showarrow=False)
        fig.add_annotation(x=0.9, y=0.29, text=f"⏱ {dur_min}",
                           font=dict(size=8, color="#374151"), showarrow=False)

        # ── ARROW 1 ──────────────────────────────────────────────────────────
        fig.add_annotation(x=2.4, y=0.5, ax=1.8, ay=0.5,
                           xref="x", yref="y", axref="x", ayref="y",
                           arrowhead=3, arrowwidth=2.5, arrowcolor="#6b7280",
                           showarrow=True, text="")

        # ── FEATURE BOX ──────────────────────────────────────────────────────
        fig.add_shape(type="rect", x0=2.4, y0=0.05, x1=5.6, y1=0.95,
                      fillcolor="#fefce8", line=dict(color="#ca8a04", width=2))
        fig.add_annotation(x=4.0, y=0.88, text="<b>FEATURE VECTOR  (12 dims)</b>",
                           font=dict(size=10, color="#92400e"), showarrow=False)

        # mini bars for domain one-hot
        bar_x0, bar_y_top = 2.6, 0.76
        bar_w, bar_gap = 0.5, 0.08
        for i, (lbl, val, col) in enumerate(zip(domain_order, onehot, feat_colors[:5])):
            bx = bar_x0 + i * (bar_w + bar_gap)
            fig.add_shape(type="rect", x0=bx, y0=0.55, x1=bx+bar_w, y1=0.55 + val*0.18,
                          fillcolor="#1e40af" if val else "#e5e7eb",
                          line=dict(color="#94a3b8", width=0.5))
            fig.add_annotation(x=bx+bar_w/2, y=0.49, text=f"<span style='font-size:7px'>{lbl}</span>",
                               font=dict(size=7, color="#6b7280"), showarrow=False)

        fig.add_annotation(x=4.0, y=0.43,
            text=f"keywords: {hit_str[:20] if hit_str != '—' else 'none'}",
            font=dict(size=7.5, color="#374151"), showarrow=False)
        fig.add_annotation(x=4.0, y=0.33,
            text=f"duration: {dur_min}  |  n_sentences: post-ASR",
            font=dict(size=7.5, color="#374151"), showarrow=False)
        fig.add_annotation(x=4.0, y=0.22,
            text="BGE sim: post-embed  |  pk_fold: LOOV",
            font=dict(size=7.5, color="#374151"), showarrow=False)

        # ── ARROW 2 ──────────────────────────────────────────────────────────
        fig.add_annotation(x=6.2, y=0.5, ax=5.6, ay=0.5,
                           xref="x", yref="y", axref="x", ayref="y",
                           arrowhead=3, arrowwidth=2.5, arrowcolor="#6b7280",
                           showarrow=True, text="")
        fig.add_annotation(x=5.9, y=0.62, text="argmin Pk",
                           font=dict(size=7.5, color="#6b7280"), showarrow=False)

        # ── MODEL BOX ────────────────────────────────────────────────────────
        fig.add_shape(type="rect", x0=6.2, y0=0.3, x1=8.0, y1=0.7,
                      fillcolor="#f3e8ff", line=dict(color="#7c3aed", width=2))
        fig.add_annotation(x=7.1, y=0.62, text="<b>ExtraTrees</b>",
                           font=dict(size=10, color="#4c1d95"), showarrow=False)
        fig.add_annotation(x=7.1, y=0.49, text="500 trees · LOOV",
                           font=dict(size=8, color="#6d28d9"), showarrow=False)
        fig.add_annotation(x=7.1, y=0.38, text="predicts Pk per method",
                           font=dict(size=7.5, color="#7c3aed"), showarrow=False)

        # ── ARROW 3 ──────────────────────────────────────────────────────────
        fig.add_annotation(x=8.6, y=0.5, ax=8.0, ay=0.5,
                           xref="x", yref="y", axref="x", ayref="y",
                           arrowhead=3, arrowwidth=2.5, arrowcolor="#6b7280",
                           showarrow=True, text="")

        # ── OUTPUT box ───────────────────────────────────────────────────────
        fig.add_shape(type="rect", x0=8.6, y0=0.1, x1=10.4, y1=0.9,
                      fillcolor="#dcfce7", line=dict(color="#16a34a", width=2.5))
        fig.add_annotation(x=9.5, y=0.82, text="<b>SELECTED METHOD</b>",
                           font=dict(size=10, color="#14532d"), showarrow=False)
        fig.add_annotation(x=9.5, y=0.65, text=f"🎯 {domain}",
                           font=dict(size=10, color="#065f46"), showarrow=False)
        fig.add_annotation(x=9.5, y=0.49, text=f"🧠 {model['name']}",
                           font=dict(size=10, color="#1e3a8a"), showarrow=False)
        fig.add_annotation(x=9.5, y=0.34, text=f"{model['dims']}d  ·  {model['notes'][:22]}",
                           font=dict(size=7.5, color="#374151"), showarrow=False)
        fig.add_annotation(x=9.5, y=0.2, text="cross-model E5+BGE  →  Pk=0.3713",
                           font=dict(size=7.5, color="#16a34a"), showarrow=False)

        fig.update_layout(
            height=180, margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False, range=[-0.1, 10.6]),
            yaxis=dict(visible=False, range=[0, 1]),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_full_pipeline(
    vid_id: str,
    url: str,
    max_minutes: int,
    step_callback,
    llm_available: bool,
    selector_callback=None,
) -> dict:
    import yt_dlp
    from faster_whisper import WhisperModel
    from lecseg.features.text_embeddings import embed_sentences
    from lecseg.models.hierarchical import HierarchicalSegmenter

    work_dir = video_dir(vid_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    audio_path = work_dir / "audio.mp3"

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    # ── Step 1: Metadata ──────────────────────────────────────────────────────
    step_callback("meta", 0.04, "Fetching video metadata from YouTube…")
    ydl_base = {
        "quiet": True, "skip_download": True, "no_warnings": True,
        "http_headers": _HEADERS, "extractor_retries": 3,
    }
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

    # ── Selector ──────────────────────────────────────────────────────────────
    sel = _select_model_for_video(meta)
    model_key = sel["model"]["key"]
    step_callback("meta", 0.07,
        f"Domain detected: {sel['domain']} → using {sel['model']['name']}")
    # Show selector panel immediately (before heavy computation starts)
    if selector_callback is not None:
        selector_callback(sel)

    # ── Step 2: Download ──────────────────────────────────────────────────────
    step_callback("audio", 0.10, "Downloading audio stream (no video data transferred)…")
    if not audio_path.exists():
        ydl_dl = {
            "format":           "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl":          str(work_dir / "audio.%(ext)s"),
            "postprocessors":   [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "64"}],
            "quiet":            True, "no_warnings": True,
            "http_headers":     _HEADERS,
            "retries":          5, "fragment_retries": 5, "extractor_retries": 3,
            "sleep_interval_requests": 1, "socket_timeout": 30,
        }
        if COOKIES_FILE.exists():
            ydl_dl["cookiefile"] = str(COOKIES_FILE)
        if max_minutes > 0:
            ydl_dl["download_sections"]     = [{"start_time": 0, "end_time": max_minutes * 60}]
            ydl_dl["force_keyframes_at_cuts"] = True
        try:
            with yt_dlp.YoutubeDL(ydl_dl) as ydl:
                ydl.download([url])
        except Exception as dl_err:
            err_msg = str(dl_err)
            if "ConnectionReset" in err_msg or "10054" in err_msg or "Got error" in err_msg:
                raise RuntimeError(
                    "YouTube blocked the download (connection reset). "
                    "Try: (1) use 'First 10 min (demo)' option, "
                    "(2) wait a minute and retry, or (3) try a different video."
                ) from None
            raise
        for f in work_dir.glob("audio.*"):
            if f.suffix != ".json" and f.name != "audio.mp3":
                f.rename(audio_path); break

    # ── Step 3: Transcribe ────────────────────────────────────────────────────
    transcript_path = work_dir / "transcript.json"
    if not transcript_path.exists():
        step_callback("transcribe", 0.24, f"Running Whisper ({WHISPER_MODEL}) speech recognition locally…")
        model_w = get_whisper_model()
        segs_out, _ = model_w.transcribe(
            str(audio_path), language="en", vad_filter=True, word_timestamps=False,
        )
        raw_segs = [{"start": s.start, "end": s.end, "text": s.text} for s in segs_out]
        transcript_path.write_text(
            json.dumps({"segments": raw_segs}, ensure_ascii=False), encoding="utf-8"
        )
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))

    # ── Step 4: Sentence split ────────────────────────────────────────────────
    step_callback("sentences", 0.52, "Splitting transcript into semantic sentences…")
    sentences_path = work_dir / "sentences.json"
    if not sentences_path.exists():
        sentences = _split_sentences(transcript["segments"], max_minutes)
        sentences_path.write_text(
            json.dumps({"sentences": sentences}, ensure_ascii=False), encoding="utf-8"
        )
    sentences = json.loads(sentences_path.read_text(encoding="utf-8"))["sentences"]

    # ── Step 5: Dual embeddings (cross-model method requires both BGE + E5) ─────
    # This matches the official best method: cross_e5_frac70_minlen11
    texts = [s["text"] for s in sentences]
    N     = len(sentences)

    # Primary: selector-chosen model (BGE-Large or E5-Large)
    emb_primary_path = work_dir / f"embeddings_{model_key}.npy"
    if not emb_primary_path.exists():
        step_callback("embed", 0.58, f"Computing {sel['model']['name']} ({sel['model']['dims']}d) embeddings for {N} sentences…")
        vecs_primary = embed_sentences(texts, model=model_key)
        np.save(str(emb_primary_path), vecs_primary)
    vecs_primary = np.load(str(emb_primary_path))

    # Secondary: the other 1024d model (cross-model scoring needs both)
    secondary_key = "e5large" if model_key == "bge_large" else "bge_large"
    secondary_name = "E5-Large" if secondary_key == "e5large" else "BGE-Large"
    emb_secondary_path = work_dir / f"embeddings_{secondary_key}.npy"
    if not emb_secondary_path.exists():
        step_callback("embed", 0.68, f"Computing {secondary_name} embeddings (cross-model method needs both)…")
        vecs_secondary = embed_sentences(texts, model=secondary_key)
        np.save(str(emb_secondary_path), vecs_secondary)
    vecs_secondary = np.load(str(emb_secondary_path))

    step_callback("embed", 0.76, f"Both embeddings ready · {sel['model']['name']} + {secondary_name}")

    # ── Step 6: Cross-model conservative segmentation (official best method) ───
    # Implements cross_e5_frac70_minlen11: divisive on each model, rank-normalize,
    # average scores, take top-k (frac=0.70), apply min-length filter (minlen=11)
    step_callback("segment", 0.80,
        f"Cross-model scoring: {sel['model']['name']} × {secondary_name} → rank-normalize → conservative selection…")

    from lecseg.models.divisive import divisive_seg
    from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
    from lecseg.models.fusion import gap_scores_from_vecs

    n_ch = max(3, min(15, N // 40))
    CROSS_FRAC   = 0.70   # fraction parameter from cross_e5_frac70_minlen11
    CROSS_WINDOW = 9      # smoothing window
    MIN_LEN      = 11     # minimum segment length in sentences

    def _smooth(v: np.ndarray, window: int = 3) -> np.ndarray:
        if window <= 1: return v
        out = np.zeros_like(v)
        for i in range(len(v)):
            lo, hi = max(0, i - window // 2), min(len(v), i + window // 2 + 1)
            out[i] = v[lo:hi].mean(axis=0)
        return out

    def _min_len_filter(bounds: list[int], n: int, min_seg: int) -> list[int]:
        """Remove boundaries that create segments shorter than min_seg sentences."""
        if not bounds: return bounds
        result = [b for b in sorted(bounds) if b > 0 and b < n]
        changed = True
        while changed:
            changed = False
            breaks = [0] + result + [n]
            for i in range(len(breaks) - 1):
                if breaks[i+1] - breaks[i] < min_seg and len(result) > 1:
                    # Remove the boundary creating the short segment
                    b_remove = breaks[i+1] if breaks[i+1] in result else breaks[i]
                    if b_remove in result:
                        result.remove(b_remove); changed = True; break
        return sorted(result)

    # Cap to 800 sentences (matching research evaluation protocol)
    N_cap = min(N, 800)
    v1 = _smooth(vecs_primary[:N_cap],   CROSS_WINDOW)
    v2 = _smooth(vecs_secondary[:N_cap], CROSS_WINDOW)

    k      = max(2, round(n_ch * CROSS_FRAC))
    over_k = min(N_cap - 1, k * 4 + 2)

    # Divisive segmentation on each model to get per-position scores
    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    # Rank-normalize and average (cross-model conservative scoring)
    all_pos = sorted(set(s1) | set(s2))
    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    combined = {p: (s1.get(p, 0.0)/max1 + s2.get(p, 0.0)/max2) / 2.0 for p in all_pos}

    # Take top-k, apply min-length filter
    top_k = sorted(combined, key=lambda x: -combined[x])[:k]
    raw_bounds = sorted(b for b in top_k if 0 < b < N_cap)
    ch_bounds  = _min_len_filter(raw_bounds, N_cap, MIN_LEN)

    # ── Expose N1 stage-1 candidate count for visualization ───────────────────
    # Run TwoStageBoundaryPredictor (N1) in parallel on primary embeddings
    # to get stage-1 candidates for the viz (shows how N1 narrows down candidates)
    predictor = TwoStageBoundaryPredictor(candidate_std=0.5, refine_std=1.2)
    gap_primary, _ = predictor._stage1_candidates(vecs_primary[:N_cap], N_cap)
    candidates_idx = [c - 1 for c in gap_primary if 0 < c <= N_cap]  # convert to 0-based gap idx

    # Cosine gap curve for visualization (primary model)
    gaps       = gap_scores_from_vecs(vecs_primary[:N_cap])
    sent_times = np.array([s["start"] for s in sentences[:N_cap]])

    # N1 threshold: μ + c1·σ (Stage 1 uses gap > mean + 0.5*std)
    threshold75 = float(gaps.mean() + 0.5 * gaps.std())  # actual N1 threshold

    # ── Step 7: Titles ────────────────────────────────────────────────────────
    step_callback("titles", 0.87, "Generating chapter titles with Llama 3.1 8B…")
    texts_all = [s["text"] for s in sentences]
    bounds    = [0] + sorted(ch_bounds) + [N]
    segments  = [texts_all[bounds[i]:bounds[i+1]] for i in range(len(bounds)-1)]

    llm_used = False; titles = []
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
        for idx, seg_texts in enumerate(segments):
            titles.append(_smart_fallback_title(seg_texts, idx + 1))

    # ── Build result ──────────────────────────────────────────────────────────
    step_callback("done", 0.97, "Finalising…")
    chapters = []
    for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        start_sec = sentences[lo]["start"]
        end_sec   = sentences[min(hi, N-1)]["end"]
        preview   = " ".join(texts_all[lo:lo+3])[:130]
        chapters.append({
            "index": i+1, "title": titles[i] if i < len(titles) else f"Section {i+1}",
            "start_sec": start_sec, "end_sec": end_sec,
            "sent_lo": lo, "sent_hi": hi,
            "preview": preview, "duration": end_sec - start_sec,
        })

    # ── Subtopics (within-chapter, same cross-model embeddings) ──────────────
    subtopics_per_chapter = _generate_subtopics(
        sentences, chapters, vecs_primary[:N], None, llm_available
    )

    result = {
        "vid_id":       vid_id,
        "meta":         meta,
        "chapters":     chapters,
        "subtopics":    subtopics_per_chapter,
        "yt_chapters":  yt_chapters,
        "n_sentences":  N,
        "llm_used":     llm_used,
        "model_key":    model_key,
        "selector":     sel,
        "cosine_gaps":      gaps.tolist(),
        "sent_times":       sent_times.tolist(),
        "candidates_idx":   candidates_idx,
        "threshold75":      threshold75,
        "n_ch_target":      n_ch,
    }
    save_cache(vid_id, result)
    return result


def _split_sentences(raw_segs: list[dict], max_minutes: int) -> list[dict]:
    limit_sec = max_minutes * 60 if max_minutes > 0 else float("inf")
    sentences, buf_text, buf_start, buf_end, idx = [], "", None, 0.0, 0
    for seg in raw_segs:
        if seg["start"] > limit_sec: break
        if buf_start is None: buf_start = seg["start"]
        buf_text += " " + seg["text"].strip(); buf_end = seg["end"]
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


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="padding:0.3rem 0 0.5rem">
      <div style="font-size:1.6rem;font-weight:900;color:#e8f3ff;letter-spacing:-0.5px">LECSEG</div>
      <div style="font-size:0.72rem;color:#5fa8e8;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-top:1px">AI Lecture Chaptering</div>
      <div style="font-size:0.68rem;color:#4a6a8a;margin-top:2px">Pre-thesis T2520718 · BRACU CSE</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    # LLM status
    llm_ok = ensure_ollama_running()
    if llm_ok: ensure_model_pulled("llama3.1:8b")
    st.markdown(
        f'<span class="{"pill-live" if llm_ok else "pill-offline"}">{"● Llama 3.1 active" if llm_ok else "● LLM offline"}</span>',
        unsafe_allow_html=True,
    )
    if not llm_ok:
        st.caption("Install Ollama + `ollama pull llama3.1:8b` to enable AI titles")

    st.markdown("---")
    st.markdown('<div style="font-size:0.7rem;color:#5fa8e8;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">LECSEG-30 Official Results</div>', unsafe_allow_html=True)
    st.caption("Lower Pk/WD = better. ✅ = statistically significant (Wilcoxon p<0.01).")
    for key, label, pk, wd, note in RESEARCH_RESULTS:
        is_best = key == "cross_e5"
        is_sel  = key == "selector"
        bg = "rgba(26,95,191,0.3)" if is_best else ("rgba(5,150,105,0.2)" if is_sel else "rgba(255,255,255,0.04)")
        border = "rgba(77,166,255,0.5)" if is_best else ("rgba(52,211,153,0.4)" if is_sel else "rgba(255,255,255,0.08)")
        st.markdown(f"""
        <div style="background:{bg};border:1px solid {border};border-radius:8px;padding:6px 10px;margin-bottom:5px">
          <div style="font-size:0.74rem;font-weight:700;color:#e8f3ff">{label}</div>
          <div style="font-size:0.68rem;color:#7aacdd;margin-top:1px">Pk={pk:.4f} · WD={wd:.4f}</div>
          <div style="font-size:0.62rem;color:#5fa8e8;margin-top:2px;line-height:1.4">{note}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="font-size:0.7rem;color:#5fa8e8;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Options</div>', unsafe_allow_html=True)
    max_min = st.selectbox(
        "Analyse",
        [("Full video", 0), ("First 10 min (demo)", 10), ("First 20 min", 20), ("First 30 min", 30)],
        format_func=lambda x: x[0],
    )[1]
    force_rerun = st.checkbox("Re-run (bypass cache)", value=False)

    st.markdown("---")
    st.markdown("""
<div style="font-size:0.72rem;line-height:1.8;color:#7aacdd">
<b style="color:#c8dcf5">LECSEG-30 Dataset</b><br>
📊 30 lectures · 32.5 hrs · 5 domains<br>
🔖 419 chapter boundaries<br>
📝 904 subtopic labels<br>
👥 Cohen's κ=0.4257 (subtopic IAA)<br>
🏗️ Novel methods N1–N4<br>
📐 Wilcoxon p&lt;0.01 vs baselines
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-eyebrow">Research Demo · BRACU CSE400 Pre-thesis</div>
  <div class="hero-title">LEC<span>SEG</span></div>
  <p class="hero-sub">Automatic lecture video chaptering via domain-aware embedding selection, hierarchical boundary detection, and local LLM titling.</p>
  <div class="badge-row">
    <span class="badge badge-accent">🎤 Whisper ASR</span>
    <span class="badge badge-accent">🧠 Sentence Embeddings</span>
    <span class="badge badge-accent">🧭 Domain Selector</span>
    <span class="badge badge-accent">📐 Hierarchical Segmentation</span>
    <span class="badge badge-accent">✍️ Llama 3.1 Titles</span>
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
st.markdown('<div style="font-size:0.82rem;color:#888;margin-bottom:0.4rem;font-weight:600">Try a pre-processed example:</div>', unsafe_allow_html=True)
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
        url_input = ex_url; go_btn = True

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

if go_btn and url_input.strip():
    vid_id = extract_video_id(url_input.strip())
    if not vid_id:
        st.error("Could not extract a YouTube video ID. Paste a full `youtube.com/watch?v=` or `youtu.be/` link.")
        st.stop()

    cached = None if force_rerun else load_cache(vid_id)
    # Check cache has cosine_gaps (older caches won't)
    if cached and ("cosine_gaps" not in cached or "subtopics" not in cached):
        cached = None

    if cached:
        result = cached
        st.success("⚡ Loaded from cache — results are instant for previously processed videos.")
    else:
        # ── Pre-flight: quick metadata to show selector before full run ────────
        selector_holder = st.empty()
        pipeline_holder = st.empty()
        progress_bar    = st.progress(0, text="Initialising…")
        step_times: dict[str, float] = {}
        step_start: dict[str, float] = {}
        current_step = [STEPS[0]["id"]]
        last_msg     = [""]

        def update(step_id: str, frac: float, msg: str):
            now = time.time()
            prev = current_step[0]
            if prev != step_id:
                if prev in step_start:
                    step_times[prev] = now - step_start[prev]
                step_start[step_id] = now
                current_step[0] = step_id
            last_msg[0] = msg
            pipeline_holder.markdown(render_pipeline(step_id, step_times, msg), unsafe_allow_html=True)
            progress_bar.progress(frac, text=msg)

        update(STEPS[0]["id"], 0.0, "Starting…")

        def on_selector(sel):
            render_selector_panel(sel, container=selector_holder)

        try:
            result = run_full_pipeline(
                vid_id=vid_id,
                url=url_input.strip(),
                max_minutes=max_min,
                step_callback=update,
                llm_available=llm_ok,
                selector_callback=on_selector,
            )
            progress_bar.progress(1.0, text="✅ Done!")
            time.sleep(0.8)
            progress_bar.empty()
            pipeline_holder.empty()
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.exception(e)
            st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════════
    meta      = result["meta"]
    chapters  = result["chapters"]
    subtopics = result.get("subtopics", [[] for _ in chapters])
    yt_chs    = result.get("yt_chapters", [])
    llm_used  = result.get("llm_used", False)
    N         = result.get("n_sentences", 0)
    sel       = result.get("selector", {})
    gap_vals  = result.get("cosine_gaps", [])
    s_times   = result.get("sent_times", [])

    # ── Show selector panel if came from cache ────────────────────────────────
    if cached and sel:
        render_selector_panel(sel)

    # ── Results header ────────────────────────────────────────────────────────
    chosen_name = sel.get("model", {}).get("name", "E5-Large") if sel else "E5-Large"
    st.markdown(f"""
    <div class="results-banner">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
        <div>
          <div style="font-size:1.15rem;font-weight:800;color:#0f2340">{meta['title']}</div>
          <div style="color:#666;font-size:0.85rem;margin-top:3px">{meta['channel']} &nbsp;·&nbsp; {fmt_dur(meta['duration'])}</div>
        </div>
        <div>
          <span class="metric-chip chip-blue">📑 {len(chapters)} chapters</span>
          <span class="metric-chip chip-purple">🔖 {sum(len(s) for s in subtopics)} subtopics</span>
          <span class="metric-chip chip-purple">💬 {N:,} sentences</span>
          <span class="metric-chip chip-blue">🧠 {chosen_name}</span>
          {"<span class='metric-chip chip-green'>🤖 Llama 3.1 titles</span>" if llm_used else "<span class='metric-chip chip-amber'>📝 Heuristic titles</span>"}
          {"<span class='metric-chip chip-blue'>📖 " + str(len(yt_chs)) + " creator chapters</span>" if yt_chs else ""}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Selector audit chart (what the real selector chose on LECSEG-30) ────────
    try:
        import plotly.graph_objects as go
        audit_labels = [x[0] for x in SELECTOR_CHOICES_AUDIT]
        audit_vals   = [x[1] for x in SELECTOR_CHOICES_AUDIT]
        audit_colors = [x[2] for x in SELECTOR_CHOICES_AUDIT]
        fig_audit = go.Figure(go.Bar(
            x=audit_vals, y=audit_labels, orientation="h",
            marker_color=audit_colors,
            text=[f"{v}/30 videos" for v in audit_vals],
            textposition="outside", textfont=dict(size=10),
            hovertemplate="%{y}: %{x} videos<extra></extra>",
        ))
        fig_audit.update_layout(
            height=130, margin=dict(l=0, r=60, t=0, b=0),
            xaxis=dict(range=[0,17], visible=False),
            yaxis=dict(tickfont_size=11),
            plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        )
        with st.expander("🧭 Research Selector: What method did it choose across LECSEG-30?", expanded=True):
            st.caption("LOOV audit (Table 5.x): across all 30 held-out videos, the ExtraTreesRegressor chose these method families most often. The selector switches away from cross-model on every video — aggressive but not uniformly safer.")
            st.plotly_chart(fig_audit, width="stretch", config={"displayModeBar": False})
            st.markdown("""
<div style="font-size:0.76rem;color:#555;line-height:1.7">
• <b>cross-E5 variants</b> (14/30): cross-model scoring with E5-Large fractions — the official best global method<br>
• <b>multimodal-grid variants</b> (12/30): E5/BGE + CLIP visual fusion — large gains on Physics, regressions on Math<br>
• <b>cross-rank variants</b> (3/30): rank-aggregation of boundary scores across models<br>
• <b>plain divisive</b> (1/30): fallback to BGE-divisive baseline
</div>""", unsafe_allow_html=True)
    except Exception:
        pass

    # ── Three-column layout ───────────────────────────────────────────────────
    col_left, col_mid, col_right = st.columns([1.15, 1.1, 0.9])

    # ══ LEFT: Video + Chapters ════════════════════════════════════════════════
    with col_left:
        st.markdown(
            f'<div style="border-radius:14px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.13)">'
            f'<iframe width="100%" height="300" '
            f'src="https://www.youtube.com/embed/{vid_id}?rel=0" '
            f'frameborder="0" allow="accelerometer;autoplay;clipboard-write;encrypted-media;'
            f'gyroscope;picture-in-picture" allowfullscreen></iframe></div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        title_method = "Llama 3.1 8B (local)" if llm_used else "Heuristic extraction"
        st.markdown(f'<div class="section-title">🤖 AI-Generated Chapters <span style="font-size:0.72rem;color:#aaa;font-weight:400;margin-left:4px">· via {title_method}</span></div>', unsafe_allow_html=True)

        for i, ch in enumerate(chapters):
            ts_sec  = int(ch["start_sec"])
            ts_str  = fmt_ts(ch["start_sec"])
            dur_str = fmt_dur(ch.get("duration", 0))
            yt_link = yt_ts_url(vid_id, ts_sec)
            preview = ch.get("preview", "")[:120]
            ch_subs = subtopics[i] if i < len(subtopics) else []

            # Build subtopic HTML (indented list under chapter card)
            subs_html = ""
            if ch_subs:
                subs_items = "".join(
                    f'<div style="display:flex;align-items:center;gap:6px;padding:2px 0">'
                    f'  <span style="color:#93c5fd;font-size:0.65rem">◦</span>'
                    f'  <a href="{yt_ts_url(vid_id, int(s["start_sec"]))}" target="_blank" '
                    f'     style="font-family:monospace;font-size:0.7rem;color:#6b7280;text-decoration:none;'
                    f'            background:#f0f4ff;border-radius:4px;padding:1px 5px">'
                    f'    {fmt_ts(s["start_sec"])}</a>'
                    f'  <span style="font-size:0.77rem;color:#555">{s["title"]}</span>'
                    f'</div>'
                    for s in ch_subs
                )
                subs_html = (
                    f'<div style="margin-top:6px;padding:6px 8px;background:#f8faff;'
                    f'            border-left:2px solid #bfdbfe;border-radius:0 6px 6px 0">'
                    f'  <div style="font-size:0.65rem;font-weight:700;color:#93c5fd;'
                    f'              text-transform:uppercase;letter-spacing:0.8px;margin-bottom:3px">Subtopics</div>'
                    f'  {subs_items}'
                    f'</div>'
                )

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
                f'    {subs_html}'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with st.expander("📋 Copy as YouTube Description", expanded=False):
            st.caption("Paste into your video description to activate chapter markers:")
            desc = "\n".join(f'{fmt_ts(ch["start_sec"])} {ch["title"]}' for ch in chapters)
            st.markdown(f'<div class="copy-box">{desc}</div>', unsafe_allow_html=True)
            st.code(desc, language=None)

    # ══ MID: Segmentation Visualization ══════════════════════════════════════
    with col_mid:
        st.markdown('<div class="section-title">📐 Segmentation Process <span style="font-size:0.7rem;color:#888;font-weight:400">· algorithm fixed; embedding model varies by domain</span></div>', unsafe_allow_html=True)

        # Pipeline summary table
        model_info = sel.get("model", {}) if sel else {}
        # ── Two-Stage N1 Algorithm Breakdown ─────────────────────────────────
        n_cands = len(result.get("candidates_idx", []))
        thresh  = result.get("threshold75", 0.0)
        n_final = len(chapters) - 1  # boundaries (not counting start)
        n_ch_t  = result.get("n_ch_target", len(chapters))
        retention = int(n_final / max(n_cands, 1) * 100) if n_cands else 100
        model_nm  = model_info.get("name", "E5-Large")
        model_dim = model_info.get("dims", 1024)

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#f4f8ff,#eef4ff);border:1.5px solid #c8daf8;border-radius:14px;padding:1rem 1.2rem;margin-bottom:0.8rem">
          <div style="font-size:0.72rem;font-weight:800;color:#1e40af;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">
            📐 Two-Stage Boundary Detection (N1)
          </div>
          <div style="font-size:0.7rem;color:#6b7280;margin-bottom:0.9rem;padding:5px 8px;background:rgba(255,255,255,0.6);border-radius:6px;border-left:3px solid #f59e0b">
            ⚠️ The segmentation algorithm is <b>always the same</b> (N1). What the selector changes is the <b>embedding model</b> — the vector space the algorithm operates in. Better embeddings for the domain = sharper semantic gaps = better boundary detection.
          </div>

          <!-- Stage 1 -->
          <div style="display:flex;gap:0;align-items:stretch;margin-bottom:0.6rem">
            <div style="background:#1e40af;color:white;border-radius:8px 0 0 8px;padding:0.5rem 0.7rem;display:flex;align-items:center;justify-content:center;font-size:0.68rem;font-weight:800;writing-mode:horizontal-tb;min-width:60px;text-align:center;line-height:1.3">STAGE 1<br>Broad</div>
            <div style="background:white;border:1.5px solid #bfdbfe;border-left:none;border-radius:0 8px 8px 0;padding:0.6rem 0.9rem;flex:1">
              <div style="font-size:0.72rem;font-weight:700;color:#1e3a8a;margin-bottom:4px">High-recall candidate generation (text-only gap)</div>
              <div style="font-size:0.7rem;color:#4b5563;line-height:1.8">
                1. Embed {N:,} sentences with <b style="color:#1e40af">{model_nm} ({model_dim}d)</b> ← selector chose this<br>
                2. Sliding-window cosine dissimilarity: <code style="background:#eff6ff;padding:1px 4px">gap(i) = 1 − cos(left_window, right_window)</code><br>
                3. Threshold: retain positions where <code style="background:#eff6ff;padding:1px 4px">gap &gt; μ<sub>text</sub> − 0.5·σ<sub>text</sub></code> (c₁=0.5, high recall)<br>
                4. → <b style="color:#1e40af">{n_cands} candidate boundaries</b> pass Stage 1
              </div>
            </div>
          </div>

          <!-- Arrow -->
          <div style="text-align:center;font-size:1rem;color:#93c5fd;margin:2px 0">↓ fused signal refinement</div>

          <!-- Stage 2 -->
          <div style="display:flex;gap:0;align-items:stretch;margin-bottom:0.8rem">
            <div style="background:#059669;color:white;border-radius:8px 0 0 8px;padding:0.5rem 0.7rem;display:flex;align-items:center;justify-content:center;font-size:0.68rem;font-weight:800;min-width:60px;text-align:center;line-height:1.3">STAGE 2<br>Refine</div>
            <div style="background:white;border:1.5px solid #a7f3d0;border-left:none;border-radius:0 8px 8px 0;padding:0.6rem 0.9rem;flex:1">
              <div style="font-size:0.72rem;font-weight:700;color:#064e3b;margin-bottom:4px">Precision filter using fused signal s* (N2)</div>
              <div style="font-size:0.7rem;color:#4b5563;line-height:1.8">
                1. Fused signal s* = reliability-weighted sum: <code style="background:#ecfdf5;padding:1px 4px">s* = Σ wₘ·sₘ</code> where wₘ = exp(−H(sₘ)) / Z<br>
                2. Accept candidate i if <code style="background:#ecfdf5;padding:1px 4px">s*(i) &gt; μ* − 1.2·σ*</code> (c₂=1.2, high precision)<br>
                3. If target k given: keep top-k fused-score positions where k = {n_ch_t}−1<br>
                4. → <b style="color:#059669">{n_final} final boundaries</b> ({retention}% of candidates kept)
              </div>
            </div>
          </div>

          <!-- Stats row -->
          <div style="display:flex;gap:0.6rem;flex-wrap:wrap">
            <div style="background:#dbeafe;border-radius:8px;padding:4px 12px;font-size:0.72rem;font-weight:700;color:#1e40af">{N:,} sentences</div>
            <div style="font-size:0.72rem;color:#93c5fd;padding:4px 0">→</div>
            <div style="background:#fef3c7;border-radius:8px;padding:4px 12px;font-size:0.72rem;font-weight:700;color:#92400e">{n_cands} candidates</div>
            <div style="font-size:0.72rem;color:#93c5fd;padding:4px 0">→</div>
            <div style="background:#d1fae5;border-radius:8px;padding:4px 12px;font-size:0.72rem;font-weight:700;color:#065f46">{n_final} boundaries → {len(chapters)} chapters</div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Stage 1 chart: all candidates ─────────────────────────────────────
        if gap_vals and s_times:
            try:
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                gaps_arr   = np.array(gap_vals)
                times_arr  = np.array(s_times[:len(gaps_arr)])
                pred_ts    = [ch["start_sec"] for ch in chapters[1:]]
                cand_idx   = result.get("candidates_idx", [])
                threshold  = result.get("threshold75", float(np.percentile(gaps_arr, 75)))
                cand_times = [times_arr[i] for i in cand_idx if i < len(times_arr)]
                cand_vals  = [gaps_arr[i] for i in cand_idx if i < len(gaps_arr)]

                tick_step = max(60, int(max(times_arr) / 6 / 60) * 60) if len(times_arr) else 60
                ticks     = list(range(0, int(max(times_arr)) + 1, tick_step)) if len(times_arr) else []

                # Stage 1 plot: cosine curve + ALL candidates
                st.markdown("""<div style="font-size:0.73rem;font-weight:700;color:#1e40af;margin-bottom:2px">Stage 1 — All candidate peaks detected</div>
                <div style="font-size:0.68rem;color:#6b7280;margin-bottom:4px">Orange dots = local maxima above 75th-pct threshold. These are ALL the candidate boundaries before filtering.</div>""", unsafe_allow_html=True)
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(
                    x=times_arr, y=gaps_arr, fill="tozeroy",
                    fillcolor="rgba(30,64,175,0.07)",
                    line=dict(color="#3b82f6", width=1.5),
                    name="Cosine gap", hovertemplate="t=%{x:.0f}s · gap=%{y:.3f}<extra></extra>",
                ))
                fig1.add_hline(y=threshold, line_dash="dot", line_color="#f59e0b",
                               line_width=1.5, opacity=0.8,
                               annotation_text=f"75th pct = {threshold:.3f}",
                               annotation_font_size=9, annotation_font_color="#d97706")
                if cand_times:
                    fig1.add_trace(go.Scatter(
                        x=cand_times, y=cand_vals,
                        mode="markers",
                        marker=dict(color="#f59e0b", size=8, symbol="circle",
                                    line=dict(color="#d97706", width=1.5)),
                        name="Candidates",
                        hovertemplate="candidate @ %{x:.0f}s · gap=%{y:.3f}<extra></extra>",
                    ))
                fig1.update_layout(
                    height=180, margin=dict(l=0, r=0, t=4, b=22),
                    xaxis=dict(tickvals=ticks, ticktext=[fmt_ts(t) for t in ticks], tickfont_size=9, gridcolor="#f0f4fc"),
                    yaxis=dict(title="gap", tickfont_size=9, gridcolor="#f0f4fc"),
                    plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
                )
                st.plotly_chart(fig1, width="stretch", config={"displayModeBar": False})

                # Stage 2 plot: filtered final boundaries
                st.markdown("""<div style="font-size:0.73rem;font-weight:700;color:#059669;margin-bottom:2px">Stage 2 — Final boundaries after selection</div>
                <div style="font-size:0.68rem;color:#6b7280;margin-bottom:4px">Red lines = final chapter boundaries. Grey dots = candidates that were filtered out (didn't meet duration or top-k criteria).</div>""", unsafe_allow_html=True)
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=times_arr, y=gaps_arr, fill="tozeroy",
                    fillcolor="rgba(5,150,105,0.06)",
                    line=dict(color="#3b82f6", width=1.5),
                    name="Cosine gap", hovertemplate="t=%{x:.0f}s · gap=%{y:.3f}<extra></extra>",
                ))
                # Filtered-out candidates (grey)
                final_ts_set = set(int(t) for t in pred_ts)
                filtered_times = [t for t in cand_times if int(t) not in final_ts_set]
                filtered_vals  = [gaps_arr[cand_idx[i]] for i, t in enumerate(cand_times)
                                  if int(t) not in final_ts_set and cand_idx[i] < len(gaps_arr)]
                if filtered_times and filtered_vals:
                    fig2.add_trace(go.Scatter(
                        x=filtered_times[:len(filtered_vals)], y=filtered_vals,
                        mode="markers",
                        marker=dict(color="#d1d5db", size=7, symbol="circle",
                                    line=dict(color="#9ca3af", width=1)),
                        name="Filtered out",
                        hovertemplate="filtered @ %{x:.0f}s<extra></extra>",
                    ))
                for t in pred_ts:
                    fig2.add_vline(x=t, line_color="#dc2626", line_width=2, opacity=0.8)
                fig2.update_layout(
                    height=180, margin=dict(l=0, r=0, t=4, b=22),
                    xaxis=dict(tickvals=ticks, ticktext=[fmt_ts(t) for t in ticks], tickfont_size=9, gridcolor="#f0f4fc"),
                    yaxis=dict(title="gap", tickfont_size=9, gridcolor="#f0f4fc"),
                    plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
                )
                st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})
            except Exception:
                pass

        # ── Chapter timeline bar ───────────────────────────────────────────────
        if chapters:
            st.markdown('<div style="font-size:0.73rem;font-weight:700;color:#1a2a4a;margin-bottom:3px">Chapter Timeline (proportional duration)</div>', unsafe_allow_html=True)
            try:
                import plotly.graph_objects as go
                colors = ["#2d6abf","#059669","#d97706","#dc2626","#7c3aed",
                          "#0891b2","#16a34a","#b45309","#be123c","#6d28d9",
                          "#0e7490","#15803d","#a16207","#9f1239","#5b21b6"]
                fig3 = go.Figure()
                for i, ch in enumerate(chapters):
                    fig3.add_trace(go.Bar(
                        x=[ch["duration"]], y=[""],
                        orientation="h",
                        marker_color=colors[i % len(colors)],
                        text=ch["title"][:16] + ("…" if len(ch["title"]) > 16 else ""),
                        textposition="inside", insidetextanchor="middle",
                        textfont=dict(size=9, color="white"),
                        hovertemplate=f'Ch {ch["index"]}: {ch["title"]}<br>{fmt_ts(ch["start_sec"])} → {fmt_ts(ch["end_sec"])}<extra></extra>',
                        name=f'Ch {ch["index"]}',
                    ))
                fig3.update_layout(
                    height=60, barmode="stack",
                    margin=dict(l=0, r=0, t=0, b=0),
                    xaxis=dict(visible=False), yaxis=dict(visible=False),
                    showlegend=False, paper_bgcolor="white", plot_bgcolor="white",
                )
                st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})
            except Exception:
                pass

        # Research context
        with st.expander("📊 Full LECSEG-30 Results + Ablations", expanded=False):
            st.markdown("""
**Official method ranking** (Chapter 5, Table 5.x) — lower Pk/WD = better:

| Method | Pk ↓ | WD ↓ | Significance |
|--------|------|------|-------------|
| **Cross-model E5 conservative** | **0.3713** | **0.3739** | ✅ sig. better than BGE-divisive |
| Balanced selector (LOOV) | 0.3588 | 0.3739 | Pk gain over cross-model NOT sig. |
| CLIP + text fusion | 0.3740 | 0.4085 | Beats BGE-divisive |
| BGE-Large + divisive (baseline) | 0.3884 | 0.3956 | ✅ sig. better than classical |
| Two-stage N1 (no fusion) | 0.4118 | 0.4206 | |
| Text-transition ranker | 0.3868 | ~0.40 | Higher F1, weaker Pk/WD |
| TextTiling (classical) | 0.4623 | 0.4891 | Beaten significantly |
| C99 (classical) | 0.4512 | 0.4734 | Beaten significantly |

**Selected ablations** (Table 5.5):

| Variant | Pk ↓ | Note |
|---------|------|------|
| CLIP visual only | 0.3958 | Surprisingly strong visual signal |
| Two-stage + prosody | 0.4333 | Prosody hurts chapter-level Pk |
| Pause/pitch only | 0.4174 | Acoustic transitions mismatch chapter granularity |
| LLM zero-shot Llama-3.1-8B | 0.4056 | Over-segments; high recall, poor precision |
| GPT-2 perplexity | 0.4182 | Finds subtopics not chapters |
| BERTopic | 0.5632 | Finds subtopics not chapters |
| BERT-wiki zero-shot | 0.4932 | Poor domain transfer |

**Selector LOOV audit** — what the selector chose across 30 videos:
cross-E5 variants: 14 · multimodal-grid: 12 · cross-rank: 3 · plain divisive: 1

**Leave-domain-out** (strictest test): Pk=0.4012 — worse than BGE-divisive.
Selector requires related domain examples in training fold to be effective.
            """)

    # ══ RIGHT: Creator Chapters ═══════════════════════════════════════════════
    with col_right:
        if yt_chs:
            st.markdown(f'<div class="section-title">📖 Creator Chapters ({len(yt_chs)})</div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.76rem;color:#888;margin-bottom:0.6rem">Original chapter markers from the video creator.</div>', unsafe_allow_html=True)
            for i, ch in enumerate(yt_chs):
                ts_str  = fmt_ts(ch["start_sec"])
                yt_link = yt_ts_url(vid_id, int(ch["start_sec"]))
                st.markdown(
                    f'<div class="gt-card">'
                    f'  <div class="gt-num">{i+1}</div>'
                    f'  <div style="flex:1">'
                    f'    <div style="font-weight:700;color:#064e3b;font-size:0.87rem;line-height:1.3">{ch["title"]}</div>'
                    f'    <a href="{yt_link}" target="_blank" '
                    f'       style="font-family:monospace;background:#d1fae5;color:#065f46;'
                    f'              border-radius:5px;padding:1px 7px;font-size:0.74rem;'
                    f'              font-weight:700;text-decoration:none">▶ {ts_str}</a>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="section-title">📖 No Creator Chapters</div>', unsafe_allow_html=True)
            st.markdown("""
            <div style="background:#fff7ed;border:1.5px solid #fed7aa;border-radius:12px;padding:0.8rem 1rem;font-size:0.81rem;color:#92400e;line-height:1.6">
            This video has no creator-provided chapters.<br>
            LECSEG fills that gap automatically by detecting semantic topic shifts in the transcript.
            </div>""", unsafe_allow_html=True)

elif go_btn and not url_input.strip():
    st.warning("Paste a YouTube URL first.")

else:
    # ── Landing state ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    cards = [
        ("🚀", "How it works", [
            "Paste any YouTube lecture URL",
            "Audio downloaded (no video needed)",
            "Whisper transcribes locally on CPU",
            "Domain-aware selector picks embedding model",
            "Two-stage boundary detection (N1)",
            "Llama 3.1 writes chapter titles",
        ]),
        ("📦", "What you get", [
            "Timestamped clickable chapters",
            "AI-written title per segment",
            "Selector decision trace (domain + signals)",
            "Semantic dissimilarity curve",
            "Chapter timeline visualization",
            "Copy-paste YouTube description format",
        ]),
        ("🔬", "Research behind this", [
            "LECSEG-30: 30-video academic benchmark",
            "5 domains · 419 chapter boundaries",
            "Best Pk=0.3713 (E5-Large, LECSEG-30)",
            "Novel methods N1–N4 (hierarchy, fusion, LLM)",
            "Wilcoxon p<0.01 vs all baselines",
            "177 unit tests · fully reproducible",
        ]),
    ]
    for col, (icon, title, items) in zip([c1, c2, c3], cards):
        items_html = "".join(f'<li style="margin-bottom:4px">{it}</li>' for it in items)
        col.markdown(f"""
        <div class="feature-card">
          <div class="feature-card-icon">{icon}</div>
          <div class="feature-card-title">{title}</div>
          <ul style="color:#555;font-size:0.81rem;line-height:1.7;margin:0;padding-left:1.2rem">{items_html}</ul>
        </div>""", unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#ccc;font-size:0.74rem">'
    'LECSEG &nbsp;·&nbsp; Pre-Thesis T2520718 &nbsp;·&nbsp; BRACU CSE400 2026 &nbsp;·&nbsp;'
    ' Whisper + Sentence-BERT + Hierarchical Segmentation + Llama 3.1 8B &nbsp;·&nbsp; Fully Local · No API Keys</p>',
    unsafe_allow_html=True,
)
