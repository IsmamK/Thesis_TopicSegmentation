"""
T12 — Hierarchical annotation tool (Streamlit).

Run:
    streamlit run scripts/annotate.py

Reads:
    data/manifest.jsonl          — video list
    data/gt/<video_id>.json      — chapter-level ground truth from T11
    data/gt_hier/<video_id>.json — LLM draft (status=="draft") if autoannotate.py was run

Writes:
    data/gt_hier/<video_id>.json         — hierarchical annotation (status: "reviewed")
    data/gt_hier/double/<video_id>.json  — second-annotator copy (optional)
    data/gt_hier/annotation_log.md       — audit trail

Workflow:
    1. Run scripts/transcribe.py  (T14)
    2. Run scripts/autoannotate.py (generates drafts)
    3. Open this tool — drafts are pre-filled, you just review/correct
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Paths (relative to project root, which is one level above scripts/)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.jsonl"
GT_DIR = ROOT / "data" / "gt"
GT_HIER = ROOT / "data" / "gt_hier"
GT_HIER_DOUBLE = GT_HIER / "double"
LOG = GT_HIER / "annotation_log.md"

GT_HIER.mkdir(parents=True, exist_ok=True)
GT_HIER_DOUBLE.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    return [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_gt(video_id: str) -> dict:
    p = GT_DIR / f"{video_id}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"boundaries_sec": [], "titles": [], "num_chapters": 0, "duration_sec": 0}


def load_hier(video_id: str, double: bool = False) -> dict | None:
    p = (GT_HIER_DOUBLE if double else GT_HIER) / f"{video_id}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def save_hier(video_id: str, data: dict, double: bool = False) -> None:
    p = (GT_HIER_DOUBLE if double else GT_HIER) / f"{video_id}.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_log(annotator: str, video_id: str, minutes: float, double: bool) -> None:
    mode = "double" if double else "primary"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"| {ts} | {annotator} | {video_id} | {mode} | {minutes:.1f} min |\n"
    if not LOG.exists():
        LOG.write_text(
            "# Annotation Log\n\n"
            "| timestamp | annotator | video_id | mode | time_spent |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line)


def fmt_sec(s: float) -> str:
    s = int(s)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def parse_time(s: str) -> float | None:
    """Parse HH:MM:SS or MM:SS or bare seconds into float seconds."""
    s = s.strip()
    if not s:
        return None
    parts = s.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="LECSEG Annotator", layout="wide")
st.title("LECSEG — Hierarchical Annotation Tool")


def is_draft(video_id: str, double: bool = False) -> bool:
    p = (GT_HIER_DOUBLE if double else GT_HIER) / f"{video_id}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("status") == "draft"
        except Exception:
            pass
    return False

videos = load_manifest()
if not videos:
    st.error("data/manifest.jsonl not found. Run T10 first.")
    st.stop()

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    annotator = st.text_input("Your annotator ID (e.g. fahmida)", value="annotator1")
    double_mode = st.checkbox("Double-annotation mode (second annotator)")
    st.markdown("---")
    st.markdown("**Annotation rules:**")
    st.markdown(
        "- Mark where the **sub-topic shifts** inside a chapter\n"
        "- Min subtopic length: **60 s**\n"
        "- 2–5 subtopics per chapter\n"
        "- Title: short noun phrase, max 8 words\n"
        "- If unsure, insert anyway"
    )

# Video selector — tag drafts and reviewed in the label
def video_label(v: dict, double: bool) -> str:
    vid = v["id"]
    p = (GT_HIER_DOUBLE if double else GT_HIER) / f"{vid}.json"
    tag = ""
    if p.exists():
        try:
            status = json.loads(p.read_text(encoding="utf-8")).get("status", "")
            tag = " 🔵 draft" if status == "draft" else " ✅ reviewed"
        except Exception:
            pass
    return f"{vid}  [{v.get('domain','?')}]  {v.get('title','')[:45]}{tag}"

vid_ids = [v["id"] for v in videos]
sel_id = st.selectbox(
    "Select video",
    vid_ids,
    format_func=lambda x: video_label(next(v for v in videos if v["id"] == x), double_mode),
)

gt = load_gt(sel_id)
chapters = gt.get("titles", [])
boundaries = [0.0] + gt.get("boundaries_sec", []) + [gt.get("duration_sec", 0)]
chapter_starts = boundaries[:-1]

# YouTube embed
yt_url = next((v["url"] for v in videos if v["id"] == sel_id), "")
# extract plain video ID for embed
import re
m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", yt_url)
if m:
    embed_id = m.group(1)
    st.markdown(
        f'<iframe width="700" height="394" src="https://www.youtube.com/embed/{embed_id}" '
        f'frameborder="0" allowfullscreen></iframe>',
        unsafe_allow_html=True,
    )

# Load existing annotation if any
existing = load_hier(sel_id, double=double_mode)

st.markdown("---")

# Show a banner if this is an LLM draft awaiting review
if is_draft(sel_id, double=double_mode):
    st.info(
        "**LLM draft loaded.** Subtopics below were pre-filled by the auto-annotator. "
        "Review each chapter: adjust timestamps or titles as needed, then click **Save annotation**.",
        icon="🤖",
    )

st.subheader(f"Chapters ({len(chapters)}) — enter subtopics for each")

start_time = time.time()

all_subtopics: list[dict] = []

for ch_idx, (ch_title, ch_start) in enumerate(zip(chapters, chapter_starts)):
    ch_end = boundaries[ch_idx + 1]
    st.markdown(
        f"**Chapter {ch_idx + 1}: {ch_title}** "
        f"— {fmt_sec(ch_start)} → {fmt_sec(ch_end)}"
    )

    # Pre-fill existing subtopics for this chapter
    prefill = ""
    if existing:
        subs = [s for s in existing.get("subtopics", []) if s.get("chapter_idx") == ch_idx]
        prefill = "\n".join(f"{fmt_sec(s['start_sec'])} | {s['title']}" for s in subs)

    raw = st.text_area(
        f"Subtopics for chapter {ch_idx + 1} (one per line: HH:MM:SS | Title)",
        value=prefill,
        height=120,
        key=f"sub_{sel_id}_{ch_idx}",
        help="Format: 00:03:45 | Introduction to Newton's Laws",
    )

    for line in raw.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        time_part, _, title_part = line.partition("|")
        t = parse_time(time_part)
        if t is None:
            st.warning(f"Cannot parse time: {time_part.strip()!r}")
            continue
        all_subtopics.append({"start_sec": t, "chapter_idx": ch_idx, "title": title_part.strip()})

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    if st.button("Save annotation", type="primary"):
        hier_data = {
            "video_id": sel_id,
            "annotator": annotator,
            "status": "reviewed",
            "double_mode": double_mode,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "chapters": [
                {"start_sec": s, "title": t}
                for s, t in zip(chapter_starts, chapters)
            ],
            "subtopics": sorted(all_subtopics, key=lambda x: x["start_sec"]),
        }
        save_hier(sel_id, hier_data, double=double_mode)
        elapsed_min = (time.time() - start_time) / 60
        append_log(annotator, sel_id, elapsed_min, double=double_mode)
        st.success(f"Saved! ({len(all_subtopics)} subtopics, {elapsed_min:.1f} min spent)")

with col2:
    def count_by_status(directory: Path, status: str) -> int:
        n = 0
        for p in directory.glob("*.json"):
            try:
                if json.loads(p.read_text(encoding="utf-8")).get("status") == status:
                    n += 1
            except Exception:
                pass
        return n

    reviewed_primary = count_by_status(GT_HIER, "reviewed")
    draft_primary = count_by_status(GT_HIER, "draft")
    reviewed_double = count_by_status(GT_HIER_DOUBLE, "reviewed")
    draft_double = count_by_status(GT_HIER_DOUBLE, "draft")

    st.metric("Primary reviewed", f"{reviewed_primary}/30")
    st.metric("Primary drafts pending", f"{draft_primary}")
    st.metric("Double reviewed", f"{reviewed_double}/10 target")
    st.metric("Double drafts pending", f"{draft_double}")
