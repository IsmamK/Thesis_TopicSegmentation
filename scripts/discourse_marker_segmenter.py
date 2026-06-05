"""Discourse marker forced boundary segmenter.

Detects high-confidence topic-transition phrases in lecture transcripts
and forces those sentence positions as mandatory boundaries, then runs
divisive segmentation between them.

Usage:
    python scripts/discourse_marker_segmenter.py [--model bge_large] [--verbose]
"""

import argparse
import json
import re
import numpy as np
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Discourse marker patterns
# Each pattern is a compiled regex matching a sentence start/body that
# strongly signals a topic transition in lecture speech.
# ---------------------------------------------------------------------------
TRANSITION_PATTERNS = [
    # Explicit topic signals
    r"\bnow (let'?s|we will|we'?re going to|i'?m going to) (talk|discuss|look at|cover|move|explore|examine|consider)",
    r"\bthe next (topic|section|part|thing|concept|idea|question|point) (is|we|i)",
    r"\bmoving on (to|now)",
    r"\blet'?s (now |)move on",
    r"\blet'?s (now |)(turn|shift|look|talk|discuss|consider)",
    r"\bin (this|the next) (section|part|chapter|module|lecture|video)",
    r"\b(today|now) (we'?re? (going to )?(talk|cover|discuss|look at|examine|introduce|start))",
    r"\b(so |now |okay |alright |)(let'?s|we) (now |)(begin|start|introduce) (with|by|our)",
    r"\b(first|second|third|fourth|fifth|next|finally|lastly|additionally|furthermore)[,\.] (let'?s|we|i want|i'?ll)",
    r"\b(topic|concept|idea|section) (number |\#?)(\d+|one|two|three|four|five)",
    r"\bpart (two|three|four|five|2|3|4|5)",
    # Recap / transition signals
    r"\b(so |)(to summarize|to recap|in summary|in conclusion|to conclude|wrapping up)",
    r"\b(so |)(we'?ve (now |)covered|we'?ve (now |)seen|we'?ve (now |)learned|we'?ve looked at)",
    r"\b(now |so |)(having (covered|seen|discussed|introduced)|with that (in mind|out of the way|said))",
    # Slide/visual change signals
    r"\b(let'?s (look at|turn to|switch to|go to) (the |this |our |)(next|new) (slide|figure|diagram|example|problem))",
    r"\b(the |this |)(next |following |)(slide|figure|diagram|graph|table|chart|equation) (shows|illustrates|presents|gives)",
    # Formal lecture openings
    r"^(okay|alright|so|right)[,\.]? (today|in this|for this|let'?s)",
    r"\b(i'?d like to |i want to |let me )(introduce|present|discuss|explain|show you|walk you through)",
    r"\bthe (focus|goal|aim|objective|purpose) of (this|today'?s) (lecture|section|part|video)",
]

COMPILED = [re.compile(p, re.IGNORECASE) for p in TRANSITION_PATTERNS]


def detect_discourse_markers(sentences: List[str]) -> List[int]:
    """Return indices of sentences that match discourse transition patterns."""
    hits = []
    for i, sent in enumerate(sentences):
        text = sent.strip()
        for pat in COMPILED:
            if pat.search(text):
                hits.append(i)
                break
    return hits


def load_embeddings(vid_id: str, model: str) -> np.ndarray | None:
    for path in [
        Path(f"data/embeddings/{model}/{vid_id}/embeddings.npy"),
        Path(f"data/emb_text/{model}/{vid_id}/embeddings.npy"),
    ]:
        if path.exists():
            return np.load(str(path))
    return None


def divisive_between_anchors(embs: np.ndarray, anchors: List[int],
                              n_boundaries: int, min_len: int = 4) -> List[int]:
    """Run divisive segmentation within each span defined by anchors.

    anchors: forced boundaries (inclusive start of new segment)
    n_boundaries: total desired boundaries (anchors + additional)
    """
    n = len(embs)
    # Score every candidate position by cosine depth score
    scores = np.zeros(n)
    w = 5
    for i in range(w, n - w):
        left = embs[max(0, i - w):i].mean(axis=0)
        right = embs[i:min(n, i + w)].mean(axis=0)
        nl, nr = np.linalg.norm(left), np.linalg.norm(right)
        if nl > 1e-9 and nr > 1e-9:
            scores[i] = 1.0 - float(np.dot(left, right) / (nl * nr))

    # Suppress positions near anchors or too close to edges
    anchor_set = set(anchors)
    for a in anchors:
        for delta in range(-min_len, min_len + 1):
            if 0 <= a + delta < n:
                scores[a + delta] = 0.0
    scores[:min_len] = 0.0
    scores[n - min_len:] = 0.0

    # Pick top-scoring candidates for additional boundaries
    extra_needed = max(0, n_boundaries - len(anchors))
    candidate_scores = [(scores[i], i) for i in range(n) if i not in anchor_set]
    candidate_scores.sort(reverse=True)
    extra = [idx for _, idx in candidate_scores[:extra_needed]]

    all_boundaries = sorted(set(anchors) | set(extra))
    return all_boundaries


def run_discourse_segmenter(vid_id: str, model: str, gt_path: Path,
                             verbose: bool = False) -> dict | None:
    """Segment one video using discourse markers + divisive fill."""
    import sys; sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from lecseg.metrics import evaluate

    sent_path = Path(f"data/sentences/{vid_id}/sentences.json")
    if not sent_path.exists():
        return None
    sents = json.load(open(sent_path, encoding="utf-8"))["sentences"]
    texts = [s["text"] for s in sents]
    n = len(texts)

    # Load ground truth (boundaries_sec -> sentence indices)
    gt_file = gt_path / f"{vid_id}.json"
    if not gt_file.exists():
        return None
    gt_data = json.load(open(gt_file, encoding="utf-8"))
    boundaries_sec = gt_data.get("boundaries_sec", [])
    if not boundaries_sec:
        return None
    starts = np.array([s["start"] for s in sents])
    ref_boundaries = []
    for t in boundaries_sec:
        idx = int(np.searchsorted(starts, float(t), side="left"))
        idx = max(1, min(idx, n - 1))
        ref_boundaries.append(idx)
    ref_boundaries = sorted(set(ref_boundaries))
    n_segments = len(ref_boundaries) + 1

    # Detect discourse markers
    marker_positions = detect_discourse_markers(texts)
    if verbose:
        print(f"  {vid_id}: {n} sentences, {n_segments-1} GT boundaries, "
              f"{len(marker_positions)} discourse markers detected")

    # Load embeddings
    embs = load_embeddings(vid_id, model)
    if embs is None or len(embs) != n:
        if verbose:
            print(f"  SKIP {vid_id}: embeddings missing or length mismatch")
        return None

    # Compute boundaries: anchors from discourse markers + fill with divisive
    boundaries = divisive_between_anchors(embs, marker_positions, n_segments - 1)

    # Compute metrics using the project evaluate() function
    pred_list = sorted(set(b for b in boundaries if 0 < b < n))
    scores = evaluate(pred_list, ref_boundaries, n_units=n)

    return {
        "pk": scores.pk, "wd": scores.wd,
        "boundary_similarity": scores.boundary_similarity, "f1_t2": scores.f1,
        "n_markers": len(marker_positions),
        "n_boundaries": len(boundaries),
        "n_gt_boundaries": len(ref_boundaries),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="bge_large")
    parser.add_argument("--gt-mode", default="youtube", choices=["youtube", "hier"])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    gt_path = Path("data/gt") if args.gt_mode == "youtube" else Path("data/gt_hier")
    manifest = [json.loads(l) for l in open("data/manifest.jsonl", encoding="utf-8")]

    results = {}
    for v in manifest:
        vid_id = v["id"]
        r = run_discourse_segmenter(vid_id, args.model, gt_path, args.verbose)
        if r:
            results[vid_id] = r
            if args.verbose:
                print(f"    Pk={r['pk']:.4f} WD={r['wd']:.4f} markers={r['n_markers']}")

    if not results:
        print("No results computed.")
        return

    pks = [r["pk"] for r in results.values()]
    wds = [r["wd"] for r in results.values()]
    bss = [r["boundary_similarity"] for r in results.values()]
    f1s = [r["f1_t2"] for r in results.values()]
    total_markers = sum(r["n_markers"] for r in results.values())

    summary = {
        "mean_pk": round(float(np.mean(pks)), 4),
        "mean_wd": round(float(np.mean(wds)), 4),
        "mean_bs": round(float(np.mean(bss)), 4),
        "mean_f1_t2": round(float(np.mean(f1s)), 4),
        "n_videos": len(results),
        "total_discourse_markers_detected": total_markers,
        "avg_markers_per_video": round(total_markers / len(results), 1),
    }

    out = {
        "method": "discourse_markers_forced",
        "model": args.model,
        "summary": {"discourse_marker_segmenter": summary},
        "per_video": results,
    }
    out_path = Path(f"results/eval_discourse_markers_{args.model}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n== Discourse Marker Segmenter Results ({args.model}) ==")
    print(f"Videos:          {summary['n_videos']}")
    print(f"Total markers:   {summary['total_discourse_markers_detected']} "
          f"(avg {summary['avg_markers_per_video']:.1f}/video)")
    print(f"Mean Pk:         {summary['mean_pk']:.4f}")
    print(f"Mean WD:         {summary['mean_wd']:.4f}")
    print(f"Mean BS:         {summary['mean_bs']:.4f}")
    print(f"Mean F1@2:       {summary['mean_f1_t2']:.4f}")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
