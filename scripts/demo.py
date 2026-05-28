"""
T39 — Web app demo (Streamlit).

Interactive demo for LECSEG: lecture segmentation pipeline.
Users can upload a transcript or select a pre-processed video,
choose a segmentation method, and see results.

Run:
    streamlit run scripts/demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
import numpy as np

from lecseg.baselines.classical import texttiling, c99
from lecseg.baselines.neural import cosine_seg, kmeans_seg
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.models.hierarchical import HierarchicalSegmenter
from lecseg.features.text_embeddings import embed_sentences
from lecseg.metrics import evaluate

st.set_page_config(
    page_title="LECSEG — Lecture Segmentation Demo",
    page_icon="🎓",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar configuration
# ---------------------------------------------------------------------------
st.sidebar.title("LECSEG Settings")

method = st.sidebar.selectbox(
    "Segmentation Method",
    ["Two-Stage (Novel)", "Hierarchical (Novel)", "C99", "TextTiling",
     "Cosine Similarity", "K-Means"],
    index=0,
)

n_segments = st.sidebar.slider("Target Segments", min_value=2, max_value=20, value=5)
embedding_model = st.sidebar.selectbox(
    "Embedding Model", ["sbert", "mpnet"], index=0,
    help="sbert = faster, mpnet = better quality"
)

show_scores = st.sidebar.checkbox("Show gap scores", value=True)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
st.title("🎓 LECSEG — Lecture Topic Segmentation")
st.markdown(
    "Upload a transcript JSON (from Whisper) or paste sentences below, "
    "then choose a segmentation method."
)

# Input area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input")
    input_mode = st.radio("Input mode", ["Upload JSON", "Paste text"], horizontal=True)

    sentences: list[str] = []

    if input_mode == "Upload JSON":
        uploaded = st.file_uploader("Upload transcript.json or sentences.json",
                                    type=["json"])
        if uploaded:
            data = json.loads(uploaded.read())
            if "sentences" in data:
                sentences = [s["text"] for s in data["sentences"]]
            elif "segments" in data:
                sentences = [s["text"] for s in data["segments"]]
            st.success(f"Loaded {len(sentences)} sentences")
    else:
        raw_text = st.text_area(
            "Paste one sentence per line:",
            height=300,
            placeholder="The first sentence of the lecture.\nThe second sentence...",
        )
        if raw_text.strip():
            sentences = [s.strip() for s in raw_text.strip().splitlines()
                         if s.strip()]
            st.info(f"{len(sentences)} sentences detected")

with col2:
    st.subheader("Ground Truth (optional)")
    gt_text = st.text_input(
        "Reference boundary indices (comma-separated, 1-based):",
        placeholder="10, 25, 40, 60",
    )
    ref_boundaries: list[int] = []
    if gt_text.strip():
        try:
            ref_boundaries = [int(x.strip()) for x in gt_text.split(",") if x.strip()]
            st.success(f"{len(ref_boundaries)} reference boundaries")
        except ValueError:
            st.error("Invalid input — use comma-separated integers")


# ---------------------------------------------------------------------------
# Run segmentation
# ---------------------------------------------------------------------------
if st.button("Run Segmentation", type="primary") and sentences:
    N = len(sentences)

    with st.spinner("Computing embeddings..."):
        vecs = embed_sentences(sentences, model=embedding_model)

    with st.spinner("Running segmentation..."):
        if method == "Two-Stage (Novel)":
            predictor = TwoStageBoundaryPredictor()
            boundaries = predictor.predict(vecs, n_segments=n_segments)

        elif method == "Hierarchical (Novel)":
            seg = HierarchicalSegmenter()
            tree = seg.segment(vecs, n_subtopics=n_segments)
            boundaries = tree.subtopics

        elif method == "C99":
            boundaries = c99(sentences, n_segments=n_segments)

        elif method == "TextTiling":
            boundaries = texttiling(sentences)

        elif method == "Cosine Similarity":
            boundaries = cosine_seg(vecs, n_segments=n_segments)

        elif method == "K-Means":
            boundaries = kmeans_seg(vecs, n_segments=n_segments)

        else:
            boundaries = []

    st.subheader("Results")
    st.metric("Segments found", len(boundaries) + 1)

    if boundaries:
        st.write(f"**Boundary positions:** {boundaries}")

    # Show metrics if reference provided
    if ref_boundaries:
        scores = evaluate(boundaries, ref_boundaries, n_units=N)
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        mcol1.metric("Pk", f"{scores.pk:.4f}", delta_color="inverse",
                     help="Lower is better")
        mcol2.metric("WD", f"{scores.wd:.4f}", delta_color="inverse",
                     help="Lower is better")
        mcol3.metric("BS", f"{scores.boundary_similarity:.4f}",
                     help="Higher is better")
        mcol4.metric("F1", f"{scores.f1:.4f}",
                     help="Higher is better")

    # Show segments
    st.subheader("Segmented Text")
    bounds = [0] + sorted(boundaries) + [N]
    for i in range(len(bounds) - 1):
        lo, hi = bounds[i], bounds[i + 1]
        with st.expander(f"Segment {i + 1} (sentences {lo + 1}–{hi})", expanded=(i < 3)):
            seg_text = "\n\n".join(f"**[{lo + j + 1}]** {sentences[lo + j]}"
                                   for j in range(hi - lo))
            st.markdown(seg_text)

elif not sentences and st.session_state.get("run_clicked"):
    st.warning("Please provide input sentences first.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption("LECSEG | Pre-Thesis Project | 2026")
