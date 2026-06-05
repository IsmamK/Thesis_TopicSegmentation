"""LECSEG Streamlit application.

Run:
    streamlit run webapp/app.py

The app has two modes:
1. Segment any YouTube lecture by following the research pipeline.
2. Benchmark on LecSeg-30 with creator-reference metrics.
"""
from __future__ import annotations

import html
import json
import math
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from lecseg.features.text_embeddings import embed_file
from lecseg.metrics import evaluate, tolerance_f1
from lecseg.preprocess.sentence_split import split_transcript

import run_eval as legacy_eval


DATA = ROOT / "data"
RESULTS = ROOT / "results"
CACHE = DATA / "webapp_cache"
CACHE.mkdir(parents=True, exist_ok=True)

METHODS = {
    "Research default: BGE divisive": "divisive",
    "Conservative smoothed BGE": "divisive_smooth9_frac70",
    "Two-stage predictor (N1/N2)": "two_stage",
    "Hierarchical segmenter (N3)": "hierarchical",
}

MODEL_OPTIONS = {
    "Fast demo (SBERT MiniLM)": "sbert",
    "Research quality (BGE large)": "bge_large",
    "Balanced (BGE base)": "bge",
}


st.set_page_config(
    page_title="LECSEG Lecture Chapter Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1420px; }
        div[data-testid="stMetric"] {
            border: 1px solid #d9e0eb;
            border-radius: 8px;
            padding: 0.8rem 0.9rem;
            background: #fbfcff;
        }
        .status-ok {
            border-left: 4px solid #1f7a4d;
            background: #f1fbf5;
            padding: 0.65rem 0.8rem;
            border-radius: 4px;
        }
        .status-warn {
            border-left: 4px solid #b7791f;
            background: #fff8eb;
            padding: 0.65rem 0.8rem;
            border-radius: 4px;
        }
        .small-muted { color: #596579; font-size: 0.9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def youtube_id(url_or_id: str) -> str:
    text = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{8,16}", text):
        return text
    patterns = [
        r"v=([A-Za-z0-9_-]{8,16})",
        r"youtu\.be/([A-Za-z0-9_-]{8,16})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{8,16})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{8,16})",
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


def parse_time_to_seconds(text: str) -> float | None:
    parts = [p.strip() for p in text.strip().split(":")]
    if not 1 <= len(parts) <= 3:
        return None
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 1:
        return nums[0]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    return nums[0] * 3600 + nums[1] * 60 + nums[2]


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


def infer_title(start_sec: float, sentences: list[dict[str, Any]]) -> str:
    candidates = [s for s in sentences if float(s.get("start", 0.0)) >= start_sec]
    text = candidates[0]["text"] if candidates else "Segment"
    words = re.findall(r"[A-Za-z0-9]+", text)[:9]
    return " ".join(words) if words else "Segment"


def make_chapters(
    boundaries_sec: list[float],
    sentences: list[dict[str, Any]],
    duration: float,
    titles: list[str] | None = None,
) -> list[dict[str, Any]]:
    clean = [float(x) for x in boundaries_sec if 0 < float(x) < duration]
    points = [0.0] + sorted(set(clean)) + [duration]
    chapters = []
    for i in range(len(points) - 1):
        start = points[i]
        end = points[i + 1]
        title = titles[i] if titles and i < len(titles) else infer_title(start, sentences)
        chapters.append(
            {
                "start_sec": round(start, 2),
                "end_sec": round(end, 2),
                "timestamp": fmt_time(start),
                "title": title,
            }
        )
    return chapters


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


def youtube_timestamp_text(chapters: list[dict[str, Any]]) -> str:
    return "\n".join(f"{fmt_time(ch['start_sec'])} {ch['title']}" for ch in chapters)


def timeline_plot(ref_sec: list[float], pred_sec: list[float], duration: float) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 2.8))
    ax.hlines(1, 0, duration, color="#d8deea", linewidth=10)
    if ref_sec:
        for sec in ref_sec:
            ax.vlines(sec, 0.82, 1.18, color="#2f5d8c", linewidth=2)
        ax.text(0, 1.22, "Reference", color="#2f5d8c", fontsize=10, va="bottom")
    for sec in pred_sec:
        ax.vlines(sec, 0.48, 0.75, color="#b84a39", linewidth=2)
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


def with_url_param(url: str, **params: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key, value in params.items():
        query[key] = [value]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def extract_json_object(text: str, marker: str) -> dict[str, Any]:
    pos = text.find(marker)
    if pos < 0:
        return {}
    start = text.find("{", pos)
    if start < 0:
        return {}
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


@st.cache_data(show_spinner=False)
def get_youtube_player(video_id: str) -> dict[str, Any]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return extract_json_object(resp.text, "ytInitialPlayerResponse")


def caption_tracks(player: dict[str, Any]) -> list[dict[str, Any]]:
    return (
        player.get("captions", {})
        .get("playerCaptionsTracklistRenderer", {})
        .get("captionTracks", [])
    )


def choose_caption_track(tracks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not tracks:
        return None
    english = [t for t in tracks if str(t.get("languageCode", "")).startswith("en")]
    pool = english or tracks
    manual = [t for t in pool if t.get("kind") != "asr"]
    return (manual or pool)[0]


def parse_json3_caption(data: dict[str, Any]) -> list[dict[str, Any]]:
    segments = []
    for event in data.get("events", []):
        if "segs" not in event:
            continue
        text = "".join(seg.get("utf8", "") for seg in event.get("segs", [])).strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue
        start = float(event.get("tStartMs", 0)) / 1000.0
        dur = float(event.get("dDurationMs", 0) or 0) / 1000.0
        segments.append({"start": start, "end": start + max(dur, 0.1), "text": text})
    return segments


def parse_xml_caption(text: str) -> list[dict[str, Any]]:
    segments = []
    root = ET.fromstring(text)
    for node in root.findall(".//text"):
        raw = "".join(node.itertext())
        clean = re.sub(r"\s+", " ", html.unescape(raw)).strip()
        if not clean:
            continue
        start = float(node.attrib.get("start", "0"))
        dur = float(node.attrib.get("dur", "0") or 0)
        segments.append({"start": start, "end": start + max(dur, 0.1), "text": clean})
    return segments


def ytdlp_executable() -> str | None:
    found = shutil.which("yt-dlp")
    if found:
        return found
    local = ROOT / ".venv" / "Scripts" / "yt-dlp.exe"
    return str(local) if local.exists() else None


def fetch_caption_with_ytdlp(video_id: str, cache_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    exe = ytdlp_executable()
    if exe is None:
        raise RuntimeError("yt-dlp is not installed.")
    sub_dir = cache_dir / "captions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(sub_dir / "%(id)s.%(ext)s")
    cmd = [
        exe,
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs",
        "en.*",
        "--sub-format",
        "json3",
        "--no-playlist",
        "-o",
        out_template,
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True, capture_output=True, text=True)
    candidates = sorted(sub_dir.glob(f"{video_id}*.json3"), key=lambda p: (".en.json3" not in p.name, len(p.name)))
    if not candidates:
        raise RuntimeError("yt-dlp did not find an English caption track.")
    data = json.loads(candidates[0].read_text(encoding="utf-8"))
    segments = parse_json3_caption(data)
    if not segments:
        raise RuntimeError("yt-dlp downloaded captions, but no transcript text could be parsed.")
    player = get_youtube_player(video_id)
    details = player.get("videoDetails", {}) if player else {}
    metadata = {
        "id": video_id,
        "title": details.get("title", f"YouTube video {video_id}"),
        "duration_sec": float(details.get("lengthSeconds", 0) or segments[-1]["end"]),
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
        "transcript_source": f"yt_dlp_caption:{candidates[0].name}",
    }
    return metadata, {"video_id": video_id, "segments": segments}


def fetch_caption_transcript(video_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    player = get_youtube_player(video_id)
    if not player:
        raise RuntimeError("Could not read YouTube player metadata.")
    track = choose_caption_track(caption_tracks(player))
    if track is None:
        raise RuntimeError("No public caption track was found for this video.")
    base = track["baseUrl"]
    transcript_url = with_url_param(base, fmt="json3")
    resp = requests.get(transcript_url, timeout=30)
    resp.raise_for_status()
    try:
        segments = parse_json3_caption(resp.json())
    except Exception:
        xml_resp = requests.get(base, timeout=30)
        xml_resp.raise_for_status()
        segments = parse_xml_caption(xml_resp.text)
    if not segments:
        raise RuntimeError("Caption track was found, but no transcript text could be parsed.")
    details = player.get("videoDetails", {})
    metadata = {
        "id": video_id,
        "title": details.get("title", f"YouTube video {video_id}"),
        "duration_sec": float(details.get("lengthSeconds", 0) or segments[-1]["end"]),
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
        "transcript_source": "youtube_captions",
        "caption_language": track.get("languageCode", "unknown"),
        "caption_kind": track.get("kind", "manual"),
    }
    transcript = {"video_id": video_id, "segments": segments}
    return metadata, transcript


def transcribe_with_whisper(video_id: str, cache_dir: Path, model_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    exe = ytdlp_executable()
    if exe is None:
        raise RuntimeError("No captions were available and yt-dlp is not installed for Whisper fallback.")
    audio = cache_dir / "audio.m4a"
    if not audio.exists():
        cmd = [
            exe,
            "-f",
            "bestaudio[ext=m4a]/bestaudio",
            "-o",
            str(audio),
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        subprocess.run(cmd, cwd=str(ROOT), check=True, capture_output=True, text=True)
    import whisper

    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio), fp16=False)
    segments = [
        {
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "text": str(seg["text"]).strip(),
        }
        for seg in result.get("segments", [])
        if str(seg.get("text", "")).strip()
    ]
    if not segments:
        raise RuntimeError("Whisper produced no transcript segments.")
    metadata = {
        "id": video_id,
        "title": f"YouTube video {video_id}",
        "duration_sec": float(segments[-1]["end"]),
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
        "transcript_source": f"whisper_{model_name}",
    }
    return metadata, {"video_id": video_id, "segments": segments}


def cache_paths(video_id: str, model_key: str) -> dict[str, Path]:
    base = CACHE / video_id
    return {
        "base": base,
        "metadata": base / "metadata.json",
        "transcript": base / "transcript.json",
        "sentences": base / "sentences.json",
        "embeddings": base / "embeddings" / model_key / "embeddings.npy",
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def estimate_segment_count(sentences: list[dict[str, Any]], duration: float, aggressiveness: str) -> int:
    if aggressiveness == "Short chapters":
        target_seconds = 270
        target_sentences = 55
    elif aggressiveness == "Long chapters":
        target_seconds = 540
        target_sentences = 115
    else:
        target_seconds = 390
        target_sentences = 80
    by_time = max(2, round(max(duration, 1) / target_seconds) + 1)
    by_sent = max(2, round(max(len(sentences), 1) / target_sentences) + 1)
    estimate = round(0.65 * by_time + 0.35 * by_sent)
    return int(max(2, min(25, estimate)))


def prepare_any_video(
    video_id: str,
    model_key: str,
    use_cache: bool,
    allow_whisper: bool,
    whisper_model: str,
) -> dict[str, Any]:
    paths = cache_paths(video_id, model_key)
    paths["base"].mkdir(parents=True, exist_ok=True)
    have_cached = paths["metadata"].exists() and paths["sentences"].exists() and paths["embeddings"].exists()
    if use_cache and have_cached:
        metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
        sentences = json.loads(paths["sentences"].read_text(encoding="utf-8"))["sentences"]
        vecs = np.load(paths["embeddings"]).astype(np.float32)
        return {"metadata": metadata, "sentences": sentences, "vecs": vecs, "cache_hit": True}

    if paths["transcript"].exists() and use_cache:
        metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    else:
        try:
            metadata, transcript = fetch_caption_with_ytdlp(video_id, paths["base"])
        except Exception:
            try:
                metadata, transcript = fetch_caption_transcript(video_id)
            except Exception:
                if not allow_whisper:
                    raise
                metadata, transcript = transcribe_with_whisper(video_id, paths["base"], whisper_model)
        write_json(paths["metadata"], metadata)
        write_json(paths["transcript"], transcript)

    if not paths["sentences"].exists() or not use_cache:
        sentences = split_transcript(paths["transcript"], paths["sentences"])
    else:
        sentences = json.loads(paths["sentences"].read_text(encoding="utf-8"))["sentences"]
    if len(sentences) < 5:
        raise RuntimeError("Transcript is too short after sentence splitting.")

    if not paths["embeddings"].exists() or not use_cache:
        vecs = embed_file(paths["sentences"], paths["embeddings"], model=model_key, batch_size=64)
    else:
        vecs = np.load(paths["embeddings"]).astype(np.float32)
    return {"metadata": metadata, "sentences": sentences, "vecs": vecs, "cache_hit": False}


def run_research_pipeline(
    video_id: str,
    sentences: list[dict[str, Any]],
    vecs: np.ndarray,
    method: str,
    n_segments: int,
) -> dict[str, Any]:
    n = min(len(sentences), len(vecs))
    sentences = sentences[:n]
    vecs = vecs[:n]
    hyp = legacy_eval._run_method(
        method,
        sentences,
        vecs,
        n_segments,
        prosody_gap=None,
        shot_gap=None,
        chunk_size=4,
        vid=video_id,
    )
    hyp = sorted(set(int(x) for x in hyp if 0 < int(x) < n))
    return {
        "hyp_sent": hyp,
        "hyp_sec": sentence_to_seconds(hyp, sentences),
        "n_sentences": n,
        "n_segments": n_segments,
    }


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


@st.cache_data(show_spinner=False)
def load_video_assets(video_id: str) -> dict[str, Any]:
    gt = load_json(str(DATA / "gt" / f"{video_id}.json"))
    sent_obj = load_json(str(DATA / "sentences" / video_id / "sentences.json"))
    return {"gt": gt, "sentences": sent_obj["sentences"]}


@st.cache_data(show_spinner=True)
def run_benchmark_method(video_id: str, method: str, embedding_model: str = "bge_large") -> dict[str, Any]:
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
    prosody_gap = legacy_eval._load_prosody(video_id, n)
    shot_gap = legacy_eval._load_shot_gap_scores(video_id, n, sentences)
    hyp = legacy_eval._run_method(
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


def render_chapter_outputs(
    title: str,
    video_id: str,
    duration: float,
    sentences: list[dict[str, Any]],
    result: dict[str, Any],
    reference_sec: list[float] | None = None,
    reference_titles: list[str] | None = None,
    method_label: str = "",
    metrics: dict[str, float] | None = None,
    f1_by_tol: dict[str, float] | None = None,
) -> None:
    chapters = make_chapters(result["hyp_sec"], sentences, duration)
    ref_chapters = make_chapters(reference_sec or [], sentences, duration, reference_titles) if reference_sec else []

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Method", method_label)
    m2.metric("Sentences", result["n_sentences"])
    m3.metric("Generated chapters", len(chapters))
    m4.metric("Duration", fmt_time(duration))
    if metrics:
        m5.metric("Pk", f"{metrics['pk']:.4f}")
    else:
        m5.metric("Evaluation", "No reference")

    tab_timeline, tab_chapters, tab_export, tab_context = st.tabs(
        ["Timeline", "Generated chapters", "Export", "Research context"]
    )
    with tab_timeline:
        st.pyplot(timeline_plot(reference_sec or [], result["hyp_sec"], duration), clear_figure=True)
        if reference_sec:
            st.caption("Blue ticks are reference chapters; red ticks are generated LecSeg boundaries.")
        else:
            st.caption("Red ticks are generated LecSeg boundaries. No reference chapters are available for arbitrary-video scoring.")

    with tab_chapters:
        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.write("Generated LecSeg chapters")
            st.dataframe(chapter_table(chapters), use_container_width=True, height=430)
        with col_b:
            if ref_chapters:
                st.write("Reference chapters")
                st.dataframe(chapter_table(ref_chapters), use_container_width=True, height=430)
            else:
                st.write("Preview")
                for ch in chapters[:8]:
                    st.markdown(f"**{fmt_time(ch['start_sec'])}**  {ch['title']}")

    with tab_export:
        payload = {
            "video_id": video_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "method": method_label,
            "generated_chapters": chapters,
        }
        st.download_button(
            "Download JSON",
            data=json.dumps(payload, indent=2),
            file_name=f"lecseg_{video_id}_chapters.json",
            mime="application/json",
        )
        st.download_button(
            "Download YouTube timestamps",
            data=youtube_timestamp_text(chapters),
            file_name=f"lecseg_{video_id}_timestamps.txt",
            mime="text/plain",
        )
        st.code(youtube_timestamp_text(chapters), language="text")

    with tab_context:
        if metrics and f1_by_tol:
            st.write("Reference-based metrics")
            cols = st.columns(4)
            cols[0].metric("Pk", f"{metrics['pk']:.4f}")
            cols[1].metric("WindowDiff", f"{metrics['wd']:.4f}")
            cols[2].metric("F1@2", f"{f1_by_tol['F1@2']:.4f}")
            cols[3].metric("F1@10", f"{f1_by_tol['F1@10']:.4f}")
            st.bar_chart(pd.DataFrame([f1_by_tol]).T.rename(columns={0: "F1"}))
        else:
            st.markdown(
                "<div class='status-warn'>For new YouTube videos, the app generates chapters but cannot compute Pk, WindowDiff, or F1 unless a reference chapter file is available.</div>",
                unsafe_allow_html=True,
            )
        modern = load_modern_metrics()
        if not modern.empty:
            keep = ["label", "pk", "wd", "sent_f1_t2", "sent_f1_t10", "time_f1_30s", "mean_best_tiou", "abs_count_error"]
            st.write("LecSeg-30 diagnostic summary")
            st.dataframe(modern[keep], use_container_width=True)


def any_youtube_mode() -> None:
    st.subheader("Segment any YouTube lecture")
    st.caption("Fast path: public YouTube captions. Fallback: Whisper transcription if yt-dlp and FFmpeg are installed.")

    with st.form("any_youtube_form"):
        url = st.text_input("YouTube URL or video ID", placeholder="https://www.youtube.com/watch?v=...")
        col1, col2, col3 = st.columns(3)
        model_label = col1.selectbox("Embedding model", list(MODEL_OPTIONS.keys()), index=0)
        method_label = col2.selectbox("Segmentation method", list(METHODS.keys()), index=0)
        aggressiveness = col3.selectbox("Chapter length", ["Normal chapters", "Short chapters", "Long chapters"], index=0)
        c1, c2, c3 = st.columns(3)
        use_cache = c1.checkbox("Cache this video for demos", value=True)
        force_refresh = c2.checkbox("Reprocess even if cached", value=False)
        allow_whisper = c3.checkbox("Use Whisper if captions missing", value=False)
        whisper_model = st.selectbox("Whisper fallback model", ["base", "small", "medium"], index=0)
        submitted = st.form_submit_button("Generate chapters", type="primary", use_container_width=True)

    if not submitted:
        st.markdown(
            "<div class='status-ok'>Paste a lecture URL, keep caching on, and the next demo run will reuse the saved transcript, sentences, and embeddings.</div>",
            unsafe_allow_html=True,
        )
        cached = sorted(p.name for p in CACHE.iterdir() if p.is_dir())
        if cached:
            st.write("Cached arbitrary videos")
            st.dataframe(pd.DataFrame({"video_id": cached}), use_container_width=True, height=180)
        return

    vid = youtube_id(url)
    if not vid:
        st.error("Could not parse a YouTube video ID from that input.")
        return
    model_key = MODEL_OPTIONS[model_label]
    method = METHODS[method_label]
    paths = cache_paths(vid, model_key)
    if force_refresh and paths["base"].exists():
        for p in [paths["sentences"], paths["embeddings"]]:
            if p.exists():
                p.unlink()

    try:
        with st.status("Following the LecSeg research pipeline...", expanded=True) as status:
            st.write("1. Acquire transcript from YouTube captions, or Whisper fallback if enabled.")
            prepared = prepare_any_video(vid, model_key, use_cache, allow_whisper, whisper_model)
            metadata = prepared["metadata"]
            sentences = prepared["sentences"]
            vecs = prepared["vecs"]
            duration = float(metadata.get("duration_sec", sentences[-1].get("end", 0)))
            st.write(f"2. Sentence splitting complete: {len(sentences)} sentences.")
            st.write(f"3. Text embeddings ready: {vecs.shape[0]} x {vecs.shape[1]} using `{model_key}`.")
            n_segments = estimate_segment_count(sentences, duration, aggressiveness)
            st.write(f"4. Automatic chapter-count estimate: {n_segments} segments.")
            result = run_research_pipeline(vid, sentences, vecs, method, n_segments)
            st.write("5. Boundary prediction and chapter generation complete.")
            status.update(label="LecSeg pipeline complete", state="complete")
    except Exception as exc:
        st.error(str(exc))
        st.info("If captions are unavailable, install yt-dlp and FFmpeg, then enable Whisper fallback. Caption-based processing is much faster.")
        return

    cache_msg = "cache hit" if prepared.get("cache_hit") else "processed now"
    st.markdown(
        f"<div class='status-ok'>Processed `{metadata.get('title', vid)}` using `{metadata.get('transcript_source')}` ({cache_msg}).</div>",
        unsafe_allow_html=True,
    )
    st.video(f"https://www.youtube.com/watch?v={vid}")
    render_chapter_outputs(
        metadata.get("title", vid),
        vid,
        duration,
        sentences,
        result,
        method_label=method_label,
    )


def benchmark_mode() -> None:
    manifest = load_manifest()
    by_id = {row["id"]: row for row in manifest}
    st.subheader("Benchmark LecSeg-30")
    st.caption("Research mode: uses cached benchmark assets and creator-reference chapters, so metrics are available.")
    labels = [f"{row['domain']} - {row['title']} ({row['id']})" for row in manifest]
    col1, col2 = st.columns([2, 1])
    choice = col1.selectbox("Benchmark lecture", labels)
    method_label = col2.selectbox("Method", list(METHODS.keys()), index=0, key="benchmark_method")
    selected_id = manifest[labels.index(choice)]["id"]
    row = by_id[selected_id]
    assets = load_video_assets(selected_id)
    gt = assets["gt"]
    sentences = assets["sentences"]
    duration = float(gt.get("duration_sec", row.get("duration_sec", 0)))
    run_clicked = st.button("Run benchmark segmentation", type="primary")
    state_changed = (
        st.session_state.get("benchmark_video_id") != selected_id
        or st.session_state.get("benchmark_method_code") != METHODS[method_label]
    )
    if run_clicked or state_changed:
        with st.spinner("Running benchmark method..."):
            st.session_state.benchmark_result = run_benchmark_method(selected_id, METHODS[method_label])
            st.session_state.benchmark_method = method_label
            st.session_state.benchmark_video_id = selected_id
            st.session_state.benchmark_method_code = METHODS[method_label]
    result = st.session_state.benchmark_result
    st.video(f"https://www.youtube.com/watch?v={selected_id}")
    render_chapter_outputs(
        row["title"],
        selected_id,
        duration,
        sentences,
        result,
        reference_sec=result["ref_sec"],
        reference_titles=gt.get("titles"),
        method_label=st.session_state.get("benchmark_method", method_label),
        metrics=result["scores"],
        f1_by_tol=result["f1_by_tol"],
    )


def main() -> None:
    inject_css()
    st.title("LECSEG Lecture Chapter Generator")
    st.caption("Generate lecture chapters from YouTube videos using the same pipeline proposed in the thesis.")
    with st.sidebar:
        st.header("Mode")
        mode = st.radio("Choose workflow", ["Segment any YouTube video", "Benchmark LecSeg-30"], index=0)
        st.divider()
        st.subheader("Pipeline used")
        st.write("YouTube video -> transcript -> sentence split -> embeddings -> boundary prediction -> chapters/export")
    if mode == "Segment any YouTube video":
        any_youtube_mode()
    else:
        benchmark_mode()


if __name__ == "__main__":
    main()
