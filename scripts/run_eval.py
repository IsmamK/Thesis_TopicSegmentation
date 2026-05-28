"""
T29 — Run full evaluation ablation battery.

Runs all segmentation methods on all videos with ground-truth annotations,
computes all metrics (Pk, WD, BS, F1, H-WD), and saves results.

Methods evaluated:
    Baselines:
        - TextTiling (B1)
        - C99 (B2)
        - CosineSeg (B3)
        - KMeansSeg (B4)
        - BertSeg / cosine-depth (B5)
    Novel:
        - TwoStage (N1+N2 without LLM)
        - TwoStage+LLM (N1+N2+N4)
        - Hierarchical (N1+N2+N3)

Usage:
    python scripts/run_eval.py
    python scripts/run_eval.py --method cosine --verbose
    python scripts/run_eval.py --output results/eval.json
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

GT_HIER = ROOT / "data" / "gt_hier"
GT_YOUTUBE = ROOT / "data" / "gt"
SENTENCES_DIR = ROOT / "data" / "sentences"
EMBEDDINGS_DIR = ROOT / "data" / "embeddings"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

from lecseg.metrics import evaluate, SegmentationScores
from lecseg.baselines.classical import texttiling, c99
from lecseg.baselines.neural import cosine_seg, kmeans_seg, bert_seg
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.models.hierarchical import HierarchicalSegmenter
from lecseg.features.text_embeddings import embed_sentences

import numpy as np


def _load_ground_truth(vid: str, use_youtube: bool = False, draft_ok: bool = False) -> dict | None:
    if use_youtube:
        p = GT_YOUTUBE / f"{vid}.json"
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        # Convert YouTube GT format to gt_hier chapters format
        titles = d.get("titles", [])
        boundaries = [0.0] + list(d.get("boundaries_sec", []))
        chapters = [{"start_sec": s, "title": t} for s, t in zip(boundaries, titles)]
        return {"chapters": chapters, "status": "youtube_gt", "video_id": vid}
    p = GT_HIER / f"{vid}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    allowed = ("reviewed", "done") + (("draft",) if draft_ok else ())
    if d.get("status") not in allowed:
        return None
    return d


def _load_sentences(vid: str) -> list[dict] | None:
    p = SENTENCES_DIR / vid / "sentences.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("sentences", [])


def _load_embeddings(vid: str, model: str = "mpnet") -> np.ndarray | None:
    p = EMBEDDINGS_DIR / model / vid / "embeddings.npy"
    if not p.exists():
        return None
    return np.load(str(p)).astype(np.float32)


def _run_method(
    method: str,
    sentences: list[dict],
    vecs: np.ndarray,
    n_segments: int,
) -> list[int]:
    """Run a named segmentation method and return boundary indices."""
    texts = [s["text"] for s in sentences]
    N = len(sentences)

    if method == "texttiling":
        return texttiling(texts)
    elif method == "c99":
        return c99(texts, n_segments=n_segments)
    elif method == "cosine":
        return cosine_seg(vecs, n_segments=n_segments)
    elif method == "kmeans":
        return kmeans_seg(vecs, n_segments=n_segments)
    elif method == "bert_seg":
        return bert_seg(vecs, n_segments=n_segments)
    elif method == "two_stage":
        p = TwoStageBoundaryPredictor()
        return p.predict(vecs, n_segments=n_segments)
    elif method == "hierarchical":
        seg = HierarchicalSegmenter()
        tree = seg.segment(vecs, n_subtopics=n_segments)
        return tree.chapters
    else:
        raise ValueError(f"Unknown method: {method}")


ALL_METHODS = ["texttiling", "c99", "cosine", "kmeans", "bert_seg",
               "two_stage", "hierarchical"]


def run_eval(
    methods: list[str] = ALL_METHODS,
    embedding_model: str = "mpnet",
    verbose: bool = False,
    output: Path | None = None,
    use_youtube: bool = False,
    draft_ok: bool = False,
) -> dict:
    """
    Run evaluation for all videos and methods.

    Returns nested dict: {method: {video_id: scores_dict}}
    """
    results: dict[str, dict[str, dict]] = {m: {} for m in methods}
    aggregates: dict[str, list] = {m: [] for m in methods}

    # Find all videos with both ground truth and sentences
    gt_source = GT_YOUTUBE if use_youtube else GT_HIER
    gt_files = sorted(gt_source.glob("*.json"))
    gt_files = [f for f in gt_files if not f.name.startswith("_") and f.suffix == ".json"
                and f.name not in ("flags_decisions.md", "gt_summary.csv")]
    if not gt_files:
        print("No ground truth annotations found.")
        return {}

    if use_youtube:
        print(f"Using YouTube chapter GT ({len(gt_files)} videos)")
    elif draft_ok:
        print(f"Using gt_hier annotations (draft+reviewed, {len(gt_files)} videos)")

    for gt_file in gt_files:
        vid = gt_file.stem
        if vid.startswith("_"):
            continue

        gt = _load_ground_truth(vid, use_youtube=use_youtube, draft_ok=draft_ok)
        if gt is None:
            continue

        sents = _load_sentences(vid)
        if sents is None:
            if verbose:
                print(f"  SKIP {vid}: no sentence file")
            continue

        N = len(sents)
        # Cap very long videos at 800 sentences for O(n²) methods (TextTiling, C99)
        MAX_SENTS = 800
        sents_capped = sents[:MAX_SENTS] if N > MAX_SENTS else sents
        vecs_capped = None  # filled below after embedding load
        N_capped = len(sents_capped)
        ref_ch_dicts = gt.get("chapters", [])
        n_segments_ch = max(2, len(ref_ch_dicts))

        # Convert chapter start_sec timestamps -> sentence boundary indices (use capped N)
        sent_starts = np.array([s["start"] for s in sents_capped])
        ref_boundaries = []
        for ch in ref_ch_dicts[1:]:  # skip first chapter (starts at 0)
            t = ch["start_sec"]
            idx = int(np.searchsorted(sent_starts, t, side="left"))
            idx = max(1, min(idx, N_capped - 1))
            ref_boundaries.append(idx)
        ref_boundaries = sorted(set(ref_boundaries))

        # Load or compute embeddings
        vecs = _load_embeddings(vid, embedding_model)
        if vecs is None:
            if verbose:
                print(f"  Computing embeddings for {vid}...")
            texts = [s["text"] for s in sents]
            vecs = embed_sentences(texts, model=embedding_model)
        vecs_capped = vecs[:N_capped]

        if verbose:
            capped_note = f" [capped {N}->{N_capped}]" if N > MAX_SENTS else ""
            print(f"  {vid}: N={N_capped}{capped_note}  n_seg={n_segments_ch}  ref_boundaries={len(ref_boundaries)}")

        for method in methods:
            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_run_method, method, sents_capped, vecs_capped, n_segments_ch)
                    hyp = fut.result(timeout=45)
                scores = evaluate(hyp, ref_boundaries, n_units=N_capped)
                scores_dict = scores.as_dict()
                results[method][vid] = scores_dict
                aggregates[method].append(scores_dict)
            except FuturesTimeout:
                if verbose:
                    print(f"    {method} TIMEOUT (>45s) — skipped")
                results[method][vid] = {"error": "timeout"}
            except Exception as e:
                if verbose:
                    print(f"    {method} FAILED: {e}")
                results[method][vid] = {"error": str(e)}

    # Compute per-method aggregate stats
    summary: dict[str, dict] = {}
    for method in methods:
        agg_list = aggregates[method]
        if not agg_list:
            summary[method] = {}
            continue

        keys = [k for k in agg_list[0] if isinstance(agg_list[0][k], (int, float))]
        summary[method] = {
            k: round(sum(d.get(k, 0) for d in agg_list) / len(agg_list), 4)
            for k in keys
        }

    gt_mode = "youtube_gt" if use_youtube else ("draft_ok" if draft_ok else "reviewed_only")
    report = {"results": results, "summary": summary, "n_videos": len(gt_files), "gt_mode": gt_mode}

    if output is None:
        output = RESULTS_DIR / "eval.json"
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output}")

    # Print summary table
    print("\n=== EVALUATION SUMMARY ===")
    print(f"{'Method':<15} {'Pk':>8} {'WD':>8} {'BS':>8} {'F1':>8}")
    print("-" * 43)
    for method, stats in summary.items():
        print(f"{method:<15} "
              f"{stats.get('pk', 0):>8.4f} "
              f"{stats.get('wd', 0):>8.4f} "
              f"{stats.get('boundary_similarity', 0):>8.4f} "
              f"{stats.get('f1', 0):>8.4f}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Run full ablation evaluation")
    parser.add_argument("--method", nargs="+", default=ALL_METHODS,
                        choices=ALL_METHODS + ["all"],
                        help="Methods to evaluate")
    parser.add_argument("--model", default="mpnet",
                        help="Embedding model (sbert/mpnet/e5/bge)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--youtube-gt", action="store_true",
                        help="Use YouTube chapter GT instead of gt_hier")
    parser.add_argument("--draft-ok", action="store_true",
                        help="Accept draft annotations (not just reviewed)")
    args = parser.parse_args()

    methods = ALL_METHODS if "all" in args.method else args.method
    out = Path(args.output) if args.output else None
    run_eval(methods=methods, embedding_model=args.model, verbose=args.verbose,
             output=out, use_youtube=args.youtube_gt, draft_ok=args.draft_ok)


if __name__ == "__main__":
    main()
