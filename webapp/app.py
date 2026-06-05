"""LECSEG Streamlit demo.

This app is a deployable benchmark explorer for real LECSEG assets. It does not
pretend to transcribe arbitrary new YouTube videos inside a Streamlit session.
Instead, it lets a user select or paste a known LECSEG lecture URL, runs a real
local segmentation method from the repository, compares it with creator
chapters, and exports usable chapter JSON.

Run:
    streamlit run webapp/app.py
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from lecseg.metrics import evaluate, tolerance_f1  # noqa: E402

import run_eval as legacy_eval  # noqa: E402


DATA = ROOT / "data"
RESULTS = ROOT / "results"
METHODS = {
    "BGE-divisive baseline": "divisive",
    "Cross-model conservative": "cross_e5_frac70_minlen11",
    "Conservative smoothed BGE": "divisive_smooth9_frac70",
    "Two-stage predictor": "two_stage",
    "Hierarchical segmenter": "hierarchical",
}


st.set_page_config(
    page_title="LECSEG Lecture Segmenter",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.25rem; padding-bottom: 2rem; }
        .metric-card {
            border: 1px solid #d7dde8;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            background: #fbfcff;
        }
        .small-muted { color: #5d6678; font-size: 0.9rem; }
        .chapter-row {
            border-left: 4px solid #2f5d8c;
            padding: 0.55rem 0.75rem;
            margin: 0.3rem 0;
            background: #f6f8fc;
            border-radius: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_manifest() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    manifest = DATA / "manifest.jsonl"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


@st.cache_data(show_spinner=False)
def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_modern_metrics() -> pd.DataFrame:
    path = RESULTS / "modern_metrics_summary.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def youtube_id(url_or_id: str) -> str:
    text = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{8,16}", text):
        return text
    patterns = [
        r"v=([A-Za-z0-9_-]{8,16})",
        r"youtu\.be/([A-Za-z0-9_-]{8,16})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{8,16})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def fmt_time(seconds: float | int) -> str:
    seconds = int(round(float(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def seconds_to_sentence(boundaries_sec: list[float], sentences: list[dict[str, Any]]) -> list[int]:
    starts = np.array([float(s.get("start", 0.0)) for s in sentences])
    out = []
    for sec in boundaries_sec:
        idx = int(np.searchsorted(starts, float(sec), side="left"))
        idx = max(1, min(idx, len(sentences) - 1))
        out.append(idx)
    return sorted(set(out))


def sentence_to_seconds(boundaries: list[int], sentences: list[dict[str, Any]]) -> list[float]:
    out = []
    for boundary in boundaries:
        if 0 < boundary < len(sentences):
            out.append(float(sentences[boundary].get("start", 0.0)))
    return out


@st.cache_data(show_spinner=False)
def load_video_assets(video_id: str) -> dict[str, Any]:
    gt = load_json(str(DATA / "gt" / f"{video_id}.json"))
    sent_obj = load_json(str(DATA / "sentences" / video_id / "sentences.json"))
    return {"gt": gt, "sentences": sent_obj["sentences"]}


@st.cache_data(show_spinner=True)
def run_method(video_id: str, method: str, embedding_model: str = "bge_large") -> dict[str, Any]:
    assets = load_video_assets(video_id)
    gt = assets["gt"]
    sentences = assets["sentences"]
    emb_path = DATA / "embeddings" / embedding_model / video_id / "embeddings.npy"
    if not emb_path.exists():
        raise FileNotFoundError(f"Missing embeddings: {emb_path}")
    vecs = np.load(emb_path).astype(np.float32)
    n = min(len(sentences), len(vecs))
    sentences = sentences[:n]
    vecs = vecs[:n]
    ref = seconds_to_sentence([float(x) for x in gt.get("boundaries_sec", []) if float(x) > 0], sentences)
    n_segments = max(2, len(ref) + 1)
    prosody_gap = legacy_eval._load_prosody(video_id, n)  # noqa: SLF001
    shot_gap = legacy_eval._load_shot_gap_scores(video_id, n, sentences)  # noqa: SLF001
    hyp = legacy_eval._run_method(  # noqa: SLF001
        method,
        sentences,
        vecs,
        n_segments,
        prosody_gap=prosody_gap,
        shot_gap=shot_gap,
        chunk_size=4,
        vid=video_id,
    )
    hyp = sorted(set(int(x) for x in hyp if 0 < int(x) < n))
    scores = evaluate(hyp, ref, n)
    f1_by_tol = {}
    for tol in [1, 2, 3, 5, 10]:
        _, _, f1 = tolerance_f1(hyp, ref, n, tolerance=tol)
        f1_by_tol[f"F1@{tol}"] = float(f1)
    return {
        "hyp_sent": hyp,
        "hyp_sec": sentence_to_seconds(hyp, sentences),
        "ref_sent": ref,
        "ref_sec": [float(x) for x in gt.get("boundaries_sec", []) if float(x) > 0],
        "scores": scores.as_dict(),
        "f1_by_tol": f1_by_tol,
        "n_sentences": n,
    }


def make_chapters(boundaries_sec: list[float], sentences: list[dict[str, Any]], duration: float, titles: list[str] | None = None) -> list[dict[str, Any]]:
    clean = [float(x) for x in boundaries_sec if 0 < float(x) < duration]
    points = [0.0] + sorted(set(clean)) + [duration]
    chapters = []
    for i in range(len(points) - 1):
        start = points[i]
        end = points[i + 1]
        title = titles[i] if titles and i < len(titles) else infer_title(start, sentences)
        chapters.append({"start_sec": start, "end_sec": end, "title": title})
    return chapters


def infer_title(start_sec: float, sentences: list[dict[str, Any]]) -> str:
    candidates = [s for s in sentences if float(s.get("start", 0.0)) >= start_sec]
    text = candidates[0]["text"] if candidates else "Segment"
    words = re.findall(r"[A-Za-z0-9]+", text)[:8]
    return " ".join(words) if words else "Segment"


def timeline_plot(gt_sec: list[float], pred_sec: list[float], duration: float) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 2.8))
    ax.hlines(1, 0, duration, color="#d8deea", linewidth=10, label="Video")
    for sec in gt_sec:
        ax.vlines(sec, 0.82, 1.18, color="#2f5d8c", linewidth=2)
    for sec in pred_sec:
        ax.vlines(sec, 0.48, 0.75, color="#b84a39", linewidth=2)
    ax.text(0, 1.22, "Creator chapters", color="#2f5d8c", fontsize=10, va="bottom")
    ax.text(0, 0.42, "Predicted", color="#b84a39", fontsize=10, va="top")
    ax.set_xlim(0, max(duration, 1))
    ax.set_ylim(0.25, 1.35)
    ax.set_yticks([])
    ax.set_xlabel("Time in lecture")
    ticks = np.linspace(0, duration, 7)
    ax.set_xticks(ticks)
    ax.set_xticklabels([fmt_time(x) for x in ticks])
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    return fig


def chapter_table(chapters: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Start": fmt_time(ch["start_sec"]),
                "End": fmt_time(ch["end_sec"]),
                "Title": ch["title"],
            }
            for ch in chapters
        ]
    )


def main() -> None:
    inject_css()
    manifest = load_manifest()
    by_id = {row["id"]: row for row in manifest}

    st.title("LECSEG Lecture Topic Segmenter")
    st.caption("A deployable explorer for the LECSEG-30 benchmark, real chapter references, and real segmentation methods.")

    with st.sidebar:
        st.header("Input")
        url = st.text_input("Paste a LECSEG YouTube URL or video ID")
        selected_id = youtube_id(url) if url else ""
        if not selected_id or selected_id not in by_id:
            labels = [f"{row['domain']} - {row['title']} ({row['id']})" for row in manifest]
            choice = st.selectbox("Or choose a benchmark lecture", labels)
            selected_id = manifest[labels.index(choice)]["id"]
        method_label = st.selectbox("Segmentation method", list(METHODS.keys()), index=1)
        run = st.button("Run segmentation", type="primary")

        st.divider()
        st.subheader("Deployment note")
        st.write(
            "This app runs on cached LECSEG assets. For a brand-new YouTube video, "
            "run the preprocessing pipeline first, then open it here."
        )

    row = by_id[selected_id]
    assets = load_video_assets(selected_id)
    gt = assets["gt"]
    sentences = assets["sentences"]
    duration = float(gt.get("duration_sec", row.get("duration_sec", 0)))
    yt_url = f"https://www.youtube.com/watch?v={selected_id}"

    top_cols = st.columns([1.25, 1, 1, 1])
    top_cols[0].markdown(f"**{row['title']}**")
    top_cols[1].metric("Domain", row["domain"])
    top_cols[2].metric("Duration", fmt_time(duration))
    top_cols[3].metric("Creator chapters", len(gt.get("boundaries_sec", [])))

    video_col, info_col = st.columns([1.6, 1])
    with video_col:
        st.video(yt_url)
    with info_col:
        st.subheader("Creator reference")
        gt_chapters = make_chapters(gt.get("boundaries_sec", []), sentences, duration, gt.get("titles"))
        st.dataframe(chapter_table(gt_chapters), use_container_width=True, height=310)

    if "last_result" not in st.session_state or run:
        with st.spinner("Running real repository segmentation..."):
            st.session_state.last_result = run_method(selected_id, METHODS[method_label])
            st.session_state.last_method = method_label

    result = st.session_state.last_result
    method_used = st.session_state.get("last_method", method_label)
    pred_chapters = make_chapters(result["hyp_sec"], sentences, duration)

    st.subheader("Segmentation result")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Method", method_used)
    m2.metric("Pk", f"{result['scores']['pk']:.4f}")
    m3.metric("WindowDiff", f"{result['scores']['wd']:.4f}")
    m4.metric("F1@2", f"{result['f1_by_tol']['F1@2']:.4f}")
    m5.metric("Predicted boundaries", len(result["hyp_sec"]))

    tab_timeline, tab_chapters, tab_metrics, tab_export = st.tabs(
        ["Timeline", "Predicted chapters", "Metric context", "Export"]
    )

    with tab_timeline:
        st.pyplot(timeline_plot(result["ref_sec"], result["hyp_sec"], duration), clear_figure=True)
        st.write(
            "Blue ticks are creator chapter references. Red ticks are predicted boundaries. "
            "This directly shows near misses, under-segmentation, and over-segmentation."
        )

    with tab_chapters:
        st.dataframe(chapter_table(pred_chapters), use_container_width=True, height=420)

    with tab_metrics:
        st.write("Tolerance F1 shows how exact-boundary scoring changes as the allowed boundary window widens.")
        st.bar_chart(pd.DataFrame([result["f1_by_tol"]]).T.rename(columns={0: "F1"}))
        modern = load_modern_metrics()
        if not modern.empty:
            st.write("Dataset-level modern metric summary")
            keep = ["label", "pk", "wd", "sent_f1_t2", "sent_f1_t10", "time_f1_30s", "mean_best_tiou", "abs_count_error"]
            st.dataframe(modern[keep], use_container_width=True)

    with tab_export:
        payload = {
            "video_id": selected_id,
            "url": yt_url,
            "method": method_used,
            "metrics": result["scores"],
            "f1_by_tolerance": result["f1_by_tol"],
            "predicted_chapters": pred_chapters,
            "creator_reference_chapters": gt_chapters,
        }
        st.download_button(
            "Download segmentation JSON",
            data=json.dumps(payload, indent=2),
            file_name=f"lecseg_{selected_id}_{METHODS[method_used]}.json",
            mime="application/json",
        )
        st.code(json.dumps(payload["predicted_chapters"][:3], indent=2), language="json")


if __name__ == "__main__":
    main()
