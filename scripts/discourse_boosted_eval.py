"""Discourse-boosted cross-model segmenter.

Takes the cross-model conservative method (our best Pk/WD) and boosts
boundary scores at positions where discourse transition markers are detected.
The boost increases candidate score at marker positions, potentially improving
recall of real boundaries without hurting precision as much as forced placement.

Usage:
    python scripts/discourse_boosted_eval.py [--model bge_large] [--boost 0.3] [--verbose]
"""

import argparse
import json
import re
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from lecseg.metrics import evaluate

# Discourse marker patterns (same as discourse_marker_segmenter.py)
TRANSITION_PATTERNS = [
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
    r"\b(so |)(to summarize|to recap|in summary|in conclusion|to conclude|wrapping up)",
    r"\b(so |)(we'?ve (now |)covered|we'?ve (now |)seen|we'?ve (now |)learned|we'?ve looked at)",
    r"\b(now |so |)(having (covered|seen|discussed|introduced)|with that (in mind|out of the way|said))",
    r"\b(let'?s (look at|turn to|switch to|go to) (the |this |our |)(next|new) (slide|figure|diagram|example|problem))",
    r"\b(the |this |)(next |following |)(slide|figure|diagram|graph|table|chart|equation) (shows|illustrates|presents|gives)",
    r"^(okay|alright|so|right)[,\.]? (today|in this|for this|let'?s)",
    r"\b(i'?d like to |i want to |let me )(introduce|present|discuss|explain|show you|walk you through)",
    r"\bthe (focus|goal|aim|objective|purpose) of (this|today'?s) (lecture|section|part|video)",
]
COMPILED = [re.compile(p, re.IGNORECASE) for p in TRANSITION_PATTERNS]


def detect_discourse_markers(sentences):
    hits = set()
    for i, sent in enumerate(sentences):
        for pat in COMPILED:
            if pat.search(sent.strip()):
                hits.add(i)
                break
    return hits


def cosine_depth_scores(embs, window=9):
    n = len(embs)
    scores = np.zeros(n)
    w = window // 2
    for i in range(w, n - w):
        left = embs[max(0, i - w):i].mean(axis=0)
        right = embs[i:min(n, i + w)].mean(axis=0)
        nl, nr = np.linalg.norm(left), np.linalg.norm(right)
        if nl > 1e-9 and nr > 1e-9:
            scores[i] = 1.0 - float(np.dot(left, right) / (nl * nr))
    return scores


def cross_model_scores(embs_a, embs_b, window=9):
    """Compute combined depth scores from two embedding models."""
    sa = cosine_depth_scores(embs_a, window)
    sb = cosine_depth_scores(embs_b, window)
    # Normalise each to [0,1] then average
    def norm(s):
        mn, mx = s.min(), s.max()
        return (s - mn) / (mx - mn + 1e-9)
    return (norm(sa) + norm(sb)) / 2.0


def pick_boundaries(scores, n_targets, min_len=11, boost_positions=None, boost=0.3):
    """Select top-scoring boundary positions with minimum segment length.

    boost_positions: set of indices where discourse markers were detected
    boost: additive score boost for those positions
    """
    n = len(scores)
    s = scores.copy()
    if boost_positions:
        for pos in boost_positions:
            if 0 < pos < n:
                s[pos] = min(1.0, s[pos] + boost)

    # Zero out edges and positions too close to each other
    s[:min_len] = 0.0
    s[n - min_len:] = 0.0

    boundaries = []
    s_work = s.copy()
    for _ in range(n_targets):
        idx = int(np.argmax(s_work))
        if s_work[idx] <= 0:
            break
        boundaries.append(idx)
        # Suppress neighbourhood
        for d in range(-min_len, min_len + 1):
            j = idx + d
            if 0 <= j < n:
                s_work[j] = 0.0
    return sorted(boundaries)


def load_embeddings(vid_id, model):
    for p in [
        Path(f"data/embeddings/{model}/{vid_id}/embeddings.npy"),
        Path(f"data/emb_text/{model}/{vid_id}/embeddings.npy"),
    ]:
        if p.exists():
            return np.load(str(p))
    return None


def run_one(vid_id, model_a, model_b, gt_path, window, frac, min_len, boost, verbose):
    sent_path = Path(f"data/sentences/{vid_id}/sentences.json")
    if not sent_path.exists():
        return None
    sents = json.load(open(sent_path, encoding="utf-8"))["sentences"]
    texts = [s["text"] for s in sents]
    n = len(texts)

    gt_file = gt_path / f"{vid_id}.json"
    if not gt_file.exists():
        return None
    gt_data = json.load(open(gt_file, encoding="utf-8"))
    boundaries_sec = gt_data.get("boundaries_sec", [])
    if not boundaries_sec:
        return None

    starts = np.array([s["start"] for s in sents])
    ref_boundaries = sorted(set(
        max(1, min(int(np.searchsorted(starts, float(t), side="left")), n - 1))
        for t in boundaries_sec
    ))
    n_targets = max(1, round(len(ref_boundaries) * frac))

    embs_a = load_embeddings(vid_id, model_a)
    embs_b = load_embeddings(vid_id, model_b)
    if embs_a is None or embs_b is None:
        return None
    # Cap at 800 sentences (same as main eval)
    cap = 800
    if n > cap:
        embs_a = embs_a[:cap]
        embs_b = embs_b[:cap]
        texts = texts[:cap]
        n = cap

    marker_positions = detect_discourse_markers(texts)
    scores = cross_model_scores(embs_a, embs_b, window=window)
    boundaries = pick_boundaries(scores, n_targets, min_len=min_len,
                                  boost_positions=marker_positions, boost=boost)

    s = evaluate(boundaries, ref_boundaries, n_units=n)
    if verbose:
        print(f"  {vid_id}: Pk={s.pk:.4f} WD={s.wd:.4f} markers={len(marker_positions)} bounds={len(boundaries)}")
    return {"pk": s.pk, "wd": s.wd, "boundary_similarity": s.boundary_similarity, "f1": s.f1}


def run_grid(model_a, model_b, gt_path, verbose):
    manifest = [json.loads(l) for l in open("data/manifest.jsonl", encoding="utf-8")]
    vids = [v["id"] for v in manifest]

    configs = [
        # (window, frac, min_len, boost, label)
        (9, 0.70, 11, 0.0,  "cross_no_boost"),       # baseline reference
        (9, 0.70, 11, 0.15, "cross_boost15"),
        (9, 0.70, 11, 0.25, "cross_boost25"),
        (9, 0.70, 11, 0.40, "cross_boost40"),
        (9, 0.70, 11, 0.60, "cross_boost60"),
        (9, 0.65, 11, 0.25, "cross_frac65_boost25"),
        (9, 0.75, 11, 0.25, "cross_frac75_boost25"),
        (9, 0.70, 9,  0.25, "cross_min9_boost25"),
        (9, 0.70, 13, 0.25, "cross_min13_boost25"),
    ]

    all_results = {}
    summary = {}

    for window, frac, min_len, boost, label in configs:
        per_video = {}
        for vid_id in vids:
            r = run_one(vid_id, model_a, model_b, gt_path,
                        window, frac, min_len, boost, verbose and boost == 0.25)
            if r:
                per_video[vid_id] = r
        if not per_video:
            continue
        pks = [v["pk"] for v in per_video.values()]
        wds = [v["wd"] for v in per_video.values()]
        bss = [v["boundary_similarity"] for v in per_video.values()]
        f1s = [v["f1"] for v in per_video.values()]
        summary[label] = {
            "pk": round(float(np.mean(pks)), 4),
            "wd": round(float(np.mean(wds)), 4),
            "boundary_similarity": round(float(np.mean(bss)), 4),
            "f1": round(float(np.mean(f1s)), 4),
        }
        all_results[label] = per_video
        print(f"  {label:<30s} Pk={summary[label]['pk']:.4f}  WD={summary[label]['wd']:.4f}  "
              f"BS={summary[label]['boundary_similarity']:.4f}  F1={summary[label]['f1']:.4f}")

    return all_results, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-a", default="bge_large")
    parser.add_argument("--model-b", default="e5large")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    gt_path = Path("data/gt")
    print(f"Running discourse-boosted cross-model grid ({args.model_a} x {args.model_b})...")
    all_results, summary = run_grid(args.model_a, args.model_b, gt_path, args.verbose)

    out = {
        "method": "discourse_boosted_cross_model",
        "model_a": args.model_a,
        "model_b": args.model_b,
        "summary": summary,
        "results": all_results,
    }
    out_path = Path(f"results/eval_discourse_boosted_{args.model_a}_{args.model_b}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved to {out_path}")

    # Report best
    best = min(summary.items(), key=lambda x: x[1]["pk"])
    print(f"\nBest config: {best[0]}  Pk={best[1]['pk']:.4f}  WD={best[1]['wd']:.4f}")
    baseline = summary.get("cross_no_boost", {})
    if baseline:
        print(f"Baseline (no boost): Pk={baseline['pk']:.4f}  WD={baseline['wd']:.4f}")
        print(f"Delta Pk: {best[1]['pk'] - baseline['pk']:+.4f}")


if __name__ == "__main__":
    main()
