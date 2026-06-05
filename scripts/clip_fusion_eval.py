"""CLIP visual embedding fusion eval.

Adds CLIP cosine depth scores as a new modality signal alongside cross-model
text scoring. CLIP embeddings are precomputed at data/emb_visual/clip/{vid_id}.npy
with shape (N_sentences, 512).

Strategy:
1. Compute CLIP cosine depth scores (same window approach as text)
2. Combine with best cross-model text scores (BGE-large + E5-large depth scores)
3. Grid search weight combos [text_w, clip_w] and report Pk/WD
4. Baseline to beat: cross-model Pk=0.3715 (frac=0.70, minlen=11)

Usage:
    python scripts/clip_fusion_eval.py [--verbose]
"""

import argparse
import json
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from lecseg.metrics import evaluate

CLIP_DIR = Path("data/emb_visual/clip")
EMB_DIR = Path("data/embeddings")
EMB_TEXT_DIR = Path("data/emb_text")
GT_PATH = Path("data/gt")
SENT_DIR = Path("data/sentences")

TEXT_MODELS = ["bge_large", "e5_large_v2"]


def cosine_depth_scores(vecs: np.ndarray, window: int = 3) -> np.ndarray:
    """Compute cosine depth scores at each gap position.

    depth_score[i] = 1 - mean(sim(left_window, right_window))
    where left/right window centres around gap i.
    """
    n = len(vecs)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms < 1e-8, 1e-8, norms)
    vecs_n = vecs / norms

    scores = np.zeros(n - 1, dtype=np.float32)
    for i in range(n - 1):
        left_start = max(0, i - window + 1)
        left_end = i + 1
        right_start = i + 1
        right_end = min(n, i + window + 1)

        left = vecs_n[left_start:left_end]
        right = vecs_n[right_start:right_end]
        if len(left) == 0 or len(right) == 0:
            continue
        sim_mat = left @ right.T
        scores[i] = 1.0 - float(sim_mat.mean())
    return scores


def smooth_scores(scores: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Gaussian smooth with sigma in gap units."""
    w = max(1, int(3 * sigma))
    kernel = np.exp(-0.5 * np.arange(-w, w + 1) ** 2 / (sigma ** 2))
    kernel /= kernel.sum()
    return np.convolve(scores, kernel, mode="same").astype(np.float32)


def load_text_depth_scores(vid_id: str, n: int) -> np.ndarray | None:
    """Load precomputed embeddings for each text model and return averaged depth scores."""
    model_scores = []
    for model in TEXT_MODELS:
        emb = None
        for emb_path in [
            EMB_DIR / model / vid_id / "embeddings.npy",
            EMB_TEXT_DIR / model / vid_id / "embeddings.npy",
        ]:
            if emb_path.exists():
                emb = np.load(str(emb_path))
                break
        if emb is None:
            continue
        cap = min(len(emb), n, 800)
        scores = cosine_depth_scores(emb[:cap])
        scores = smooth_scores(scores)
        model_scores.append(scores[:cap - 1])

    if not model_scores:
        return None

    min_len = min(len(s) for s in model_scores)
    stacked = np.stack([s[:min_len] for s in model_scores], axis=0)
    avg = stacked.mean(axis=0)
    return avg


def load_clip_depth_scores(vid_id: str, n: int) -> np.ndarray | None:
    p = CLIP_DIR / f"{vid_id}.npy"
    if not p.exists():
        return None
    emb = np.load(str(p))
    cap = min(len(emb), n, 800)
    scores = cosine_depth_scores(emb[:cap])
    scores = smooth_scores(scores)
    return scores[:cap - 1]


def normalise01(x: np.ndarray) -> np.ndarray:
    rng = float(x.max() - x.min())
    if rng <= 0:
        return np.zeros_like(x)
    return (x - x.min()) / rng


def pick_boundaries_topk(scores: np.ndarray, n_targets: int,
                          min_len: int = 1) -> list[int]:
    """Pick top n_targets peaks with min_len spacing (NMS-style)."""
    n = len(scores)
    s = scores.copy()
    s[:min_len] = -1e9
    s[n - min_len:] = -1e9
    boundaries = []
    s_work = s.copy()
    for _ in range(n_targets):
        idx = int(np.argmax(s_work))
        if s_work[idx] < -1e8:
            break
        boundaries.append(idx + 1)  # boundary after sentence idx
        for d in range(-min_len, min_len + 1):
            j = idx + d
            if 0 <= j < n:
                s_work[j] = -1e9
    return sorted(boundaries)


def run_video_fusion(vid_id: str, text_w: float, clip_w: float,
                     min_len: int,
                     verbose: bool = False) -> dict | None:
    sent_path = SENT_DIR / vid_id / "sentences.json"
    if not sent_path.exists():
        return None
    sents = json.load(open(sent_path, encoding="utf-8"))["sentences"]
    n = len(sents)

    gt_file = GT_PATH / f"{vid_id}.json"
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

    cap = min(n, 800)
    ref_cap = [b for b in ref_boundaries if b < cap]
    if not ref_cap:
        return None

    text_scores = load_text_depth_scores(vid_id, cap)
    clip_scores = load_clip_depth_scores(vid_id, cap)

    if text_scores is None:
        return None

    min_len_scores = min(len(text_scores), len(clip_scores) if clip_scores is not None else len(text_scores))
    text_n = normalise01(text_scores[:min_len_scores])

    if clip_scores is not None and clip_w > 0:
        clip_n = normalise01(clip_scores[:min_len_scores])
        total = text_w + clip_w
        fused = (text_w / total) * text_n + (clip_w / total) * clip_n
    else:
        fused = text_n

    # Use oracle-k: pick exactly the GT number of boundaries
    n_targets = len(ref_cap)
    boundaries = pick_boundaries_topk(fused, n_targets, min_len)
    boundaries = [b for b in boundaries if 0 < b < cap]

    if not boundaries:
        return None

    scores = evaluate(boundaries, ref_cap, n_units=cap)
    return {"pk": scores.pk, "wd": scores.wd,
            "boundary_similarity": scores.boundary_similarity, "f1": scores.f1}


def grid_search(vids: list[str], verbose: bool = False):
    text_weights = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
    clip_weights = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    min_lens = [5, 9, 11, 13]

    best_pk = 999.0
    best_cfg = None
    best_rows = []

    n_cfg = len(text_weights) * len(clip_weights) * len(min_lens)
    print(f"Grid search: ~{n_cfg} configs × {len(vids)} videos (oracle-k selection)...")

    results_table = []

    for tw in text_weights:
        for cw in clip_weights:
            if tw == 1.0 and cw > 0.0:
                continue  # text-only covered by cw=0
            for ml in min_lens:
                pks, wds = [], []
                for vid_id in vids:
                    r = run_video_fusion(vid_id, tw, cw, ml)
                    if r:
                        pks.append(r["pk"])
                        wds.append(r["wd"])
                if len(pks) < 20:
                    continue
                mean_pk = float(np.mean(pks))
                mean_wd = float(np.mean(wds))
                tag = f"tw{tw:.1f}_cw{cw:.1f}_ml{ml}"
                results_table.append({
                    "tag": tag, "text_w": tw, "clip_w": cw,
                    "min_len": ml,
                    "mean_pk": round(mean_pk, 4),
                    "mean_wd": round(mean_wd, 4),
                    "n": len(pks),
                })
                if mean_pk < best_pk:
                    best_pk = mean_pk
                    best_cfg = tag
                    best_rows = list(zip(vids, pks, wds))

    results_table.sort(key=lambda x: x["mean_pk"])
    return results_table, best_cfg, best_pk, best_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--top", type=int, default=10, help="Show top N configs")
    args = parser.parse_args()

    manifest = [json.loads(l) for l in open("data/manifest.jsonl", encoding="utf-8")]
    vids = [v["id"] for v in manifest]
    print(f"CLIP fusion eval on {len(vids)} videos")
    print(f"CLIP dir: {CLIP_DIR}, files: {len(list(CLIP_DIR.glob('*.npy')))}")

    # Quick check: does CLIP signal differ from random for first video?
    if vids:
        clip_s = load_clip_depth_scores(vids[0], 800)
        if clip_s is not None:
            print(f"CLIP scores sample ({vids[0]}): mean={clip_s.mean():.4f} std={clip_s.std():.4f} min={clip_s.min():.4f} max={clip_s.max():.4f}")
        else:
            print(f"WARNING: No CLIP embeddings for {vids[0]}")

    results_table, best_cfg, best_pk, _ = grid_search(vids, args.verbose)

    print(f"\n== Top {args.top} CLIP Fusion Configs ==")
    print(f"{'Tag':<40} {'Pk':>8} {'WD':>8} {'N':>4}")
    print("-" * 64)
    for row in results_table[:args.top]:
        marker = " <-- BEST" if row["tag"] == best_cfg else ""
        print(f"{row['tag']:<40} {row['mean_pk']:>8.4f} {row['mean_wd']:>8.4f} {row['n']:>4}{marker}")

    # Print text-only baseline for comparison (clip_w=0)
    text_only = [r for r in results_table if r["clip_w"] == 0.0]
    if text_only:
        print(f"\nText-only best: {text_only[0]['tag']} Pk={text_only[0]['mean_pk']:.4f}")

    print(f"\nCross-model reference: Pk=0.3715 (BGE+E5, frac=0.70, minlen=11)")
    print(f"BGE-divisive baseline: Pk=0.3884")
    print(f"Balanced selector:     Pk=0.3588")

    if best_pk < 0.3715:
        print(f"\nCLIP FUSION BEATS cross-model! Best Pk={best_pk:.4f} ({best_cfg})")
    elif best_pk < 0.3884:
        print(f"\nCLIP fusion beats BGE-divisive but not cross-model. Best Pk={best_pk:.4f}")
    else:
        print(f"\nCLIP fusion does not improve over baseline. Best Pk={best_pk:.4f}")

    out = {
        "method": "clip_fusion_eval",
        "top_configs": results_table[:20],
        "best_config": best_cfg,
        "best_pk": best_pk,
    }
    out_path = Path("results/eval_clip_fusion.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
