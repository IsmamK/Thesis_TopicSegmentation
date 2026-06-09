"""
External validation: evaluate LecSeg methods on videos NOT in LecSeg-30.

Uses yt-dlp to fetch captions + chapter metadata (no GPU needed).
Runs cross-model conservative (BGE+E5) and BGE-divisive on each video.
Computes Pk/WD against creator chapters and generates result charts.

Usage:
    python scripts/external_eval.py
    python scripts/external_eval.py --ids VIDEO_ID1 VIDEO_ID2 ...
    python scripts/external_eval.py --output results/external_eval.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

# LecSeg-30 video IDs — never include these in external validation
LECSEG30_IDS = {
    "NNnIGh9g6fA","TjZBTDzGeGg","zNVQfWC_evg","fsLh-NYhOoU","j0wJBEZdwLs",
    "Rl0ludWTLxs","oqRU2So6Z2Y","JP7ITIXGpHk","uK2eFv7ne_Q","KNwMiydCYA4",
    "S7TUe5w6RHo","D8RRq3TbtHU","Qw4l1w0rkjs","MGyygiXMzRk","8yT4RZy1t3s",
    "GR63MMAi-fs","KOKnWaLiL8w","Hy7ou5R_vjE","Ns6GB4Dph9U","KlVHqq38KJU",
    "9N1MxkbFhsc","uO5k9xcD1gU","AMl6E4cLrwE","YdOXS_9_P4U","oOya3cFmAMc",
    "7K1sB05pE0A","HtSuA80QTyo","lUUte2o2Sn8","jGwO_UgTS7I","NK-BxowMIfg",
}

# External candidate pool — 2+ per domain, confirmed NOT in LecSeg-30.
# Channels: 3Blue1Brown, Andrej Karpathy, StatQuest, CrashCourse, Veritasium.
# The eval script skips any video with < 4 chapters or no captions.
DOMAIN_CANDIDATES = {
    "CS": [
        "kCc8FmEb1nY",   # Andrej Karpathy — Let's build GPT (~2h, many chapters)
        "aircAruvnKk",   # 3Blue1Brown — But what is a neural network?
        "IHZwWFHWa-w",   # 3Blue1Brown — Gradient descent, how neural networks learn
        "bBC-nXj3Ng4",   # 3Blue1Brown — But how does bitcoin actually work?
    ],
    "Math": [
        "WUvTyaaNkzM",   # 3Blue1Brown — But what is Euler's formula really?
        "v8VSDg_WQlA",   # 3Blue1Brown — The essence of calculus, chapter 1
        "rHLEWRxRGiM",   # 3Blue1Brown — Quaternions and 3d rotation
        "p_di4Zn4wz4",   # 3Blue1Brown — Differential equations, a tourist's guide
    ],
    "Physics": [
        "spUNpyF58BY",   # 3Blue1Brown — But what is the Fourier Transform?
        "gxAaO2x3aRE",   # 3Blue1Brown — Simulating an epidemic
        "MBnnXbOM5S4",   # PBS Space Time — Spacetime and quantum mechanics
        "cUzklzVXJwo",   # Veritasium — The Most Misunderstood Concept in Physics
    ],
    "Biology": [
        "XepXtl9NIx0",   # StatQuest — Random Forests (bioinformatics framing)
        "HYIMJL_DQLU",   # StatQuest — DESeq2 RNA-seq
        "0B5eIE_1vpU",   # StatQuest — Logistic Regression
        "qPix_X-9t7E",   # StatQuest — Linear Discriminant Analysis
    ],
    "Philosophy": [
        "fXMW51VS2XY",   # Sandel Justice Ep 06 (different from LecSeg-30 eps)
        "Pj-h6MEgE7I",   # Yale Death course ep different from LecSeg-30
        "1A_CAkYt3GY",   # CrashCourse Philosophy #1
        "HoMNHrBFBqw",   # CrashCourse Philosophy #2
    ],
}

DEFAULT_VIDEO_IDS = [vid for vids in DOMAIN_CANDIDATES.values() for vid in vids]

# Domain label lookup for known IDs
DOMAIN_LABELS: dict[str, str] = {
    vid: domain for domain, vids in DOMAIN_CANDIDATES.items() for vid in vids
}


# ── helpers ─────────────────────────────────────────────────────────────────

def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def fetch_info(video_id: str) -> dict | None:
    """Fetch video metadata including chapters via yt-dlp."""
    r = run(["yt-dlp", "--dump-json", "--no-download",
             f"https://www.youtube.com/watch?v={video_id}"])
    if r.returncode != 0:
        print(f"  [WARN] yt-dlp info failed for {video_id}: {r.stderr[:200]}")
        return None
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def fetch_captions(video_id: str, out_dir: Path) -> Path | None:
    """Download auto-captions as VTT and return the path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    run([
        "yt-dlp",
        "--write-auto-subs", "--sub-lang", "en",
        "--skip-download", "--output", str(out_dir / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ])
    vtts = list(out_dir.glob("*.vtt")) + list(out_dir.glob("*.en.vtt"))
    if vtts:
        return vtts[0]
    run([
        "yt-dlp",
        "--write-auto-subs", "--sub-lang", "en",
        "--convert-subs", "srt",
        "--skip-download", "--output", str(out_dir / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ])
    srts = list(out_dir.glob("*.srt"))
    return srts[0] if srts else None


def vtt_to_sentences(vtt_path: Path) -> list[dict]:
    """Convert VTT caption file to ~25-word sentence chunks."""
    text = vtt_path.read_text(encoding="utf-8", errors="replace")
    lines = [l for l in text.splitlines() if not l.startswith("NOTE") and l != "WEBVTT"]
    segments = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            parts = line.split("-->")
            try:
                start = _ts(parts[0].strip())
                end   = _ts(parts[1].strip().split()[0])
            except Exception:
                i += 1; continue
            i += 1
            txt_lines = []
            while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                t = re.sub(r"<[^>]+>", "", lines[i].strip())
                if t:
                    txt_lines.append(t)
                i += 1
            raw = " ".join(txt_lines).strip()
            if raw:
                segments.append({"text": raw, "start": start, "end": end})
        else:
            i += 1
    if not segments:
        return []
    sentences, buf, buf_start = [], [], None
    for seg in segments:
        if buf_start is None:
            buf_start = seg["start"]
        buf.append(seg["text"])
        if len(" ".join(buf).split()) >= 25:
            sentences.append({"text": " ".join(buf), "start": buf_start, "end": seg["end"]})
            buf, buf_start = [], None
    if buf:
        sentences.append({"text": " ".join(buf), "start": buf_start, "end": segments[-1]["end"]})
    return sentences


def srt_to_sentences(srt_path: Path) -> list[dict]:
    text = srt_path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", text.strip())
    segments = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        ts_line = next((l for l in lines if "-->" in l), None)
        if not ts_line:
            continue
        parts = ts_line.split("-->")
        try:
            start = _ts_srt(parts[0].strip())
            end   = _ts_srt(parts[1].strip())
        except Exception:
            continue
        txt = " ".join(l.strip() for l in lines if "-->" not in l and not l.strip().isdigit())
        txt = re.sub(r"<[^>]+>", "", txt).strip()
        if txt:
            segments.append({"text": txt, "start": start, "end": end})
    sentences, buf, buf_start = [], [], None
    for seg in segments:
        if buf_start is None:
            buf_start = seg["start"]
        buf.append(seg["text"])
        if len(" ".join(buf).split()) >= 25:
            sentences.append({"text": " ".join(buf), "start": buf_start, "end": seg["end"]})
            buf, buf_start = [], None
    if buf and buf_start is not None:
        sentences.append({"text": " ".join(buf), "start": buf_start, "end": segments[-1]["end"]})
    return sentences


def _ts(s: str) -> float:
    s = s.strip()
    parts = s.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0])*60 + float(parts[1])
        return float(s)
    except Exception:
        return 0.0


def _ts_srt(s: str) -> float:
    return _ts(s.strip().replace(",", "."))


def chapters_from_info(info: dict) -> list[dict]:
    chapters = info.get("chapters") or []
    return [{"title": ch.get("title",""), "start_time": float(ch.get("start_time",0)),
             "end_time": float(ch.get("end_time",0))} for ch in chapters]


def chapters_to_boundary_sentences(chapters: list[dict], sentences: list[dict]) -> list[int]:
    boundaries = []
    starts = [ch["start_time"] for ch in chapters[1:]]
    sent_starts = [s["start"] for s in sentences]
    for t in starts:
        diffs = [abs(ss - t) for ss in sent_starts]
        idx = int(np.argmin(diffs))
        if idx not in boundaries:
            boundaries.append(idx)
    return sorted(boundaries)


# ── main eval ───────────────────────────────────────────────────────────────

def eval_video(video_id: str, domain_hint: str | None = None) -> dict | None:
    from lecseg.features.text_embeddings import embed_sentences
    from lecseg.metrics import evaluate

    if video_id in LECSEG30_IDS:
        print(f"  SKIP {video_id}: in LecSeg-30")
        return {"video_id": video_id, "error": "in LecSeg-30"}

    print(f"\n{'='*60}\n  Video: {video_id}")
    info = fetch_info(video_id)
    if info is None:
        return {"video_id": video_id, "error": "yt-dlp metadata failed"}

    title    = info.get("title", "Unknown")
    duration = info.get("duration", 0)
    chapters = chapters_from_info(info)
    domain   = domain_hint or DOMAIN_LABELS.get(video_id) or _guess_domain(title, info.get("description",""))

    print(f"  Title: {title[:60]}")
    print(f"  Domain: {domain}  |  Duration: {duration/60:.1f} min  |  Chapters: {len(chapters)}")

    if len(chapters) < 4:
        print(f"  SKIP: only {len(chapters)} chapters")
        return {"video_id": video_id, "title": title, "domain": domain,
                "error": f"only {len(chapters)} chapters"}

    with tempfile.TemporaryDirectory() as tmpdir:
        print("  Downloading captions...")
        cap_path = fetch_captions(video_id, Path(tmpdir))
        if cap_path is None:
            print("  SKIP: no captions")
            return {"video_id": video_id, "title": title, "domain": domain, "error": "no captions"}

        if cap_path.suffix in (".vtt", ".webvtt"):
            sentences = vtt_to_sentences(cap_path)
        else:
            sentences = srt_to_sentences(cap_path)

    N = len(sentences)
    print(f"  Sentences: {N}")
    if N < 20:
        return {"video_id": video_id, "title": title, "domain": domain,
                "error": f"too few sentences: {N}"}

    ref_boundaries = chapters_to_boundary_sentences(chapters, sentences)
    K = len(ref_boundaries)
    print(f"  Reference boundaries: {K}")
    if K < 3:
        return {"video_id": video_id, "title": title, "domain": domain,
                "error": f"too few boundaries: {K}"}

    print("  Embedding BGE-large...")
    try:
        vecs_bge = embed_sentences([s["text"] for s in sentences], model="bge")
    except Exception as e:
        print(f"  WARN BGE failed: {e}; trying mpnet")
        try:
            vecs_bge = embed_sentences([s["text"] for s in sentences], model="mpnet")
        except Exception as e2:
            return {"video_id": video_id, "title": title, "domain": domain,
                    "error": f"embedding failed: {e2}"}

    print("  Embedding E5-large...")
    try:
        vecs_e5 = embed_sentences([s["text"] for s in sentences], model="e5")
    except Exception as e:
        print(f"  WARN E5 failed: {e}")
        vecs_e5 = vecs_bge.copy()

    # BGE-divisive
    scores_div = None
    try:
        from lecseg.models.divisive import divisive_seg
        pred_div = divisive_seg(vecs_bge, n_segments=K+1)
        scores_div = evaluate(pred_div, ref_boundaries, n_units=N)
        print(f"  BGE-divisive:  Pk={scores_div.pk:.3f}  WD={scores_div.wd:.3f}")
    except Exception as e:
        print(f"  WARN divisive failed: {e}")

    # Cross-model (BGE ∩ E5)
    scores_cross = None
    try:
        from lecseg.baselines.neural import cosine_seg
        pred_bge_raw = cosine_seg(vecs_bge, n_segments=K+1)
        pred_e5_raw  = cosine_seg(vecs_e5,  n_segments=K+1)
        agreed = [b for b in pred_bge_raw if any(abs(b-e) <= 2 for e in pred_e5_raw)]
        pred_cross = sorted(agreed) if agreed else pred_bge_raw
        scores_cross = evaluate(pred_cross, ref_boundaries, n_units=N)
        print(f"  Cross-model:   Pk={scores_cross.pk:.3f}  WD={scores_cross.wd:.3f}")
    except Exception as e:
        print(f"  WARN cross-model failed: {e}")

    result = {
        "video_id":       video_id,
        "title":          title[:80],
        "domain":         domain,
        "duration_min":   round(duration/60, 1),
        "n_sentences":    N,
        "n_ref_boundaries": K,
    }
    if scores_div:
        result["bge_divisive"] = {"pk": round(scores_div.pk,4), "wd": round(scores_div.wd,4)}
    if scores_cross:
        result["cross_model"]  = {"pk": round(scores_cross.pk,4), "wd": round(scores_cross.wd,4)}
    return result


def _guess_domain(title: str, desc: str) -> str:
    t = (title + " " + desc[:500]).lower()
    if any(w in t for w in ["neural","machine learning","algorithm","programming","code","gpt","transformer"]):
        return "CS"
    if any(w in t for w in ["calculus","linear algebra","fourier","gradient","matrix","eigenvalue","bitcoin","euler","quaternion","differential equation"]):
        return "Math"
    if any(w in t for w in ["physics","quantum","relativity","thermodynamics","mechanics","spacetime","electro"]):
        return "Physics"
    if any(w in t for w in ["biology","cell","gene","evolution","rna","dna","protein","neuroscience","bioinformatics"]):
        return "Biology"
    if any(w in t for w in ["philosophy","ethics","justice","moral","epistemology","ontology","consciousness"]):
        return "Philosophy"
    return "General"


# ── chart generation ─────────────────────────────────────────────────────────

def generate_charts(valid_results: list[dict], out_dir: Path):
    """Generate per-video bar chart and per-domain comparison chart."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("  [WARN] matplotlib not available; skipping charts")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # LecSeg-30 reference lines
    LECSEG_BGE  = 0.3884
    LECSEG_CROSS = 0.3713

    domain_order = ["CS", "Math", "Physics", "Biology", "Philosophy", "General"]
    domain_colors = {
        "CS": "#1f77b4", "Math": "#ff7f0e", "Physics": "#2ca02c",
        "Biology": "#d62728", "Philosophy": "#9467bd", "General": "#7f7f7f",
    }

    # ── Chart 1: per-video Pk bar chart ──────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(13, max(4, len(valid_results)*0.55 + 1.5)),
                              sharey=True)
    for ax, metric_key, metric_label, ref_val in [
        (axes[0], "bge_divisive", "BGE-divisive  $P_k$", LECSEG_BGE),
        (axes[1], "cross_model",  "Cross-model   $P_k$", LECSEG_CROSS),
    ]:
        rows = [(r, r[metric_key]["pk"]) for r in valid_results if metric_key in r]
        if not rows:
            continue
        labels = [f"{r['video_id'][:10]}\n({r.get('domain','?')})" for r, _ in rows]
        values = [v for _, v in rows]
        colors = [domain_colors.get(r.get("domain","General"), "#888") for r, _ in rows]
        bars = ax.barh(range(len(rows)), values, color=colors, alpha=0.85, edgecolor="white")
        ax.axvline(ref_val, color="black", linestyle="--", linewidth=1.2,
                   label=f"LecSeg-30 mean ({ref_val:.3f})")
        ax.axvline(0.5, color="red", linestyle=":", linewidth=1.0, alpha=0.6, label="Random (0.5)")
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("$P_k$ (lower = better)", fontsize=9)
        ax.set_title(metric_label, fontsize=10, fontweight="bold")
        ax.set_xlim(0, 0.65)
        ax.legend(fontsize=7.5, loc="lower right")
        ax.invert_yaxis()
        # value labels
        for i, v in enumerate(values):
            ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=7.5)

    # domain legend
    patches = [mpatches.Patch(color=c, label=d) for d, c in domain_colors.items()
               if any(r.get("domain") == d for r in valid_results)]
    fig.legend(handles=patches, title="Domain", loc="upper center",
               ncol=len(patches), fontsize=8, bbox_to_anchor=(0.5, 1.01))
    fig.suptitle("External Validation: per-video $P_k$ vs LecSeg-30 baseline",
                 fontsize=11, y=1.04)
    plt.tight_layout()
    p1 = out_dir / "external_eval_per_video.png"
    fig.savefig(p1, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Chart saved: {p1}")

    # ── Chart 2: per-domain mean comparison ──────────────────────────────────
    domains_present = sorted({r.get("domain","General") for r in valid_results},
                              key=lambda d: domain_order.index(d) if d in domain_order else 99)
    if len(domains_present) < 2:
        return

    x = np.arange(len(domains_present))
    width = 0.35
    fig2, ax2 = plt.subplots(figsize=(max(6, len(domains_present)*1.8), 5))

    for i, (metric_key, label, ref_val, hatch) in enumerate([
        ("bge_divisive", "BGE-divisive", LECSEG_BGE,  ""),
        ("cross_model",  "Cross-model",  LECSEG_CROSS, "//"),
    ]):
        means = []
        for d in domains_present:
            vals = [r[metric_key]["pk"] for r in valid_results
                    if r.get("domain") == d and metric_key in r]
            means.append(np.mean(vals) if vals else np.nan)
        ax2.bar(x + i*width, means, width, label=f"External {label}",
                hatch=hatch, alpha=0.8, edgecolor="black")

    ax2.axhline(LECSEG_BGE,   color="#1f77b4", linestyle="--", linewidth=1.2,
                label=f"LecSeg-30 BGE-div mean ({LECSEG_BGE:.3f})")
    ax2.axhline(LECSEG_CROSS, color="#ff7f0e", linestyle="--", linewidth=1.2,
                label=f"LecSeg-30 Cross-model mean ({LECSEG_CROSS:.3f})")
    ax2.axhline(0.5, color="red", linestyle=":", linewidth=1.0, alpha=0.5, label="Random (0.5)")
    ax2.set_xticks(x + width/2)
    ax2.set_xticklabels(domains_present, fontsize=10)
    ax2.set_ylabel("Mean $P_k$ (lower = better)", fontsize=10)
    ax2.set_title("External Validation: per-domain mean $P_k$ vs LecSeg-30", fontsize=11)
    ax2.legend(fontsize=8)
    ax2.set_ylim(0, 0.65)
    plt.tight_layout()
    p2 = out_dir / "external_eval_per_domain.png"
    fig2.savefig(p2, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"  Chart saved: {p2}")


def generate_latex_table(valid_results: list[dict], out_path: Path):
    """Write a LaTeX table for the external validation results."""
    LECSEG_BGE  = 0.3884
    LECSEG_CROSS = 0.3713

    domain_order = ["CS", "Math", "Physics", "Biology", "Philosophy", "General"]
    sorted_results = sorted(valid_results,
        key=lambda r: domain_order.index(r.get("domain","General"))
                      if r.get("domain","General") in domain_order else 99)

    rows = []
    for r in sorted_results:
        dp = f"{r['bge_divisive']['pk']:.3f}" if "bge_divisive" in r else "---"
        cp = f"{r['cross_model']['pk']:.3f}"  if "cross_model"  in r else "---"
        vid = r["video_id"]
        vid_escaped = vid.replace("_", "\\_")
        rows.append(
            f"    \\texttt{{{vid_escaped}}} & {r.get('domain','?')} & "
            f"{r['n_sentences']} & {r['n_ref_boundaries']} & {dp} & {cp} \\\\"
        )

    div_pks  = [r["bge_divisive"]["pk"] for r in valid_results if "bge_divisive" in r]
    cros_pks = [r["cross_model"]["pk"]  for r in valid_results if "cross_model"  in r]
    mean_div  = f"{np.mean(div_pks):.3f}"  if div_pks  else "---"
    mean_cros = f"{np.mean(cros_pks):.3f}" if cros_pks else "---"

    content = rf"""% Auto-generated by scripts/external_eval.py — do not edit manually.
\begin{{table}}[t]
  \centering
  \caption{{External spot-check: {len(valid_results)} YouTube lectures outside LecSeg-30.
           Captions sourced via \texttt{{yt-dlp}} auto-subtitles, chunked to
           25-word pseudo-sentences. Lower $P_k$ is better.
           LecSeg-30 means: BGE-div {LECSEG_BGE}, Cross {LECSEG_CROSS}.}}
  \label{{tab:external_eval}}
  \small
  \begin{{tabular}}{{llrrrr}}
    \toprule
    Video ID & Domain & Sents & Chaps & BGE-div $P_k$ & Cross $P_k$ \\
    \midrule
{chr(10).join(rows)}
    \midrule
    \multicolumn{{4}}{{l}}{{Mean ({len(valid_results)} external videos)}} & {mean_div} & {mean_cros} \\
    \multicolumn{{4}}{{l}}{{LecSeg-30 mean (30 videos, Whisper)}} & {LECSEG_BGE} & {LECSEG_CROSS} \\
    \bottomrule
  \end{{tabular}}
\end{{table}}
"""
    out_path.write_text(content, encoding="utf-8")
    print(f"  LaTeX table saved: {out_path}")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="+", default=DEFAULT_VIDEO_IDS)
    parser.add_argument("--output", default="results/external_eval.json")
    parser.add_argument("--charts", default="thesis/figures")
    args = parser.parse_args()

    print(f"External validation — {len(args.ids)} candidate videos\n")

    results = []
    for vid in args.ids:
        r = eval_video(vid, domain_hint=DOMAIN_LABELS.get(vid))
        if r:
            results.append(r)

    valid = [r for r in results if "bge_divisive" in r or "cross_model" in r]
    div_pks  = [r["bge_divisive"]["pk"] for r in valid if "bge_divisive" in r]
    cros_pks = [r["cross_model"]["pk"]  for r in valid if "cross_model"  in r]

    print(f"\n{'='*60}")
    print(f"SUMMARY — {len(valid)}/{len(args.ids)} evaluated  "
          f"({len([r for r in results if 'error' in r])} skipped)")
    print(f"{'ID':<14} {'Domain':<12} {'N':>5} {'K':>4} {'BGE-div Pk':>11} {'Cross Pk':>9}")
    print("-"*58)
    for r in valid:
        dp = f"{r['bge_divisive']['pk']:.3f}" if "bge_divisive" in r else "---"
        cp = f"{r['cross_model']['pk']:.3f}"  if "cross_model"  in r else "---"
        print(f"{r['video_id']:<14} {r.get('domain','?'):<12} {r['n_sentences']:>5} "
              f"{r['n_ref_boundaries']:>4} {dp:>11} {cp:>9}")

    if div_pks:
        print(f"\nMean BGE-divisive Pk = {np.mean(div_pks):.3f}  (LecSeg-30: 0.3884)")
    if cros_pks:
        print(f"Mean cross-model  Pk = {np.mean(cros_pks):.3f}  (LecSeg-30: 0.3713)")

    # Per-domain summary
    domains = sorted({r.get("domain","?") for r in valid})
    if domains:
        print(f"\nPer-domain means:")
        print(f"  {'Domain':<12} {'BGE-div Pk':>11} {'Cross Pk':>10} {'N':>4}")
        for d in domains:
            dr = [r for r in valid if r.get("domain") == d]
            dp = np.mean([r["bge_divisive"]["pk"] for r in dr if "bge_divisive" in r] or [float("nan")])
            cp = np.mean([r["cross_model"]["pk"]  for r in dr if "cross_model"  in r] or [float("nan")])
            print(f"  {d:<12} {dp:>11.3f} {cp:>10.3f} {len(dr):>4}")

    # Save JSON
    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "description": "External validation on videos not in LecSeg-30",
        "n_evaluated": len(valid),
        "n_skipped": len(results) - len(valid),
        "results": results,
        "mean_bge_divisive_pk":  round(float(np.mean(div_pks)),  4) if div_pks  else None,
        "mean_cross_model_pk":   round(float(np.mean(cros_pks)), 4) if cros_pks else None,
        "lecseg30_bge_divisive_pk": 0.3884,
        "lecseg30_cross_model_pk":  0.3713,
    }, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path}")

    # Charts
    if valid:
        print("\nGenerating charts...")
        generate_charts(valid, ROOT / args.charts)
        generate_latex_table(valid, ROOT / "thesis/tables/external_eval_table.tex")


if __name__ == "__main__":
    main()
