"""
Oracle-k experiment: give divisive the exact GT segment count.
Shows the theoretical ceiling of the divisive algorithm — if Pk is still
high here, the algorithm itself is the bottleneck. If Pk is low, k-selection
is the main problem to fix.
"""
from __future__ import annotations
import json
import sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lecseg.models.divisive import divisive_seg
from lecseg.metrics import evaluate

GT_DIR    = ROOT / "data" / "gt_hier"
EMB_DIR   = ROOT / "data" / "embeddings" / "bge"
SENT_DIR  = ROOT / "data" / "sentences"

def gt_boundaries(video_id: str) -> list[int]:
    """Return GT boundary sentence indices (1-based) from chapter timestamps."""
    gt = json.load(open(GT_DIR / f"{video_id}.json", encoding="utf-8"))
    chapters = gt.get("chapters", [])
    sents = json.load(open(SENT_DIR / video_id / "sentences.json", encoding="utf-8"))["sentences"]
    if len(chapters) <= 1:
        return []
    # Map chapter start_sec → nearest sentence index
    boundaries = []
    for ch in chapters[1:]:  # skip first (starts at 0)
        t = ch["start_sec"]
        best_idx = min(range(len(sents)),
                       key=lambda i: abs(sents[i].get("start", 0) - t))
        if best_idx > 0:
            boundaries.append(best_idx)
    return sorted(set(boundaries))

def run():
    videos = sorted([f.stem for f in GT_DIR.glob("*.json")
                     if f.stem != "iaa_report"])

    pk_oracle, pk_divisive = [], []
    results = {}

    for vid in videos:
        emb_path = EMB_DIR / vid / "embeddings.npy"
        if not emb_path.exists():
            continue
        vecs = np.load(str(emb_path))
        gt_b = gt_boundaries(vid)
        if not gt_b:
            continue
        n_segs = len(gt_b) + 1

        # Oracle-k: give divisive the exact number of GT segments
        pred_oracle = divisive_seg(vecs, n_segments=n_segs)
        s_oracle = evaluate(pred_oracle, gt_b, n_units=len(vecs))

        # Current heuristic: use sqrt(len/10) as rough k estimate
        k_heuristic = max(2, round(len(vecs) ** 0.5 / 3))
        pred_heuristic = divisive_seg(vecs, n_segments=k_heuristic)
        s_heuristic = evaluate(pred_heuristic, gt_b, n_units=len(vecs))

        pk_oracle.append(s_oracle.pk)
        pk_divisive.append(s_heuristic.pk)
        results[vid] = {
            "n_gt_segs": n_segs,
            "k_heuristic": k_heuristic,
            "pk_oracle_k": round(s_oracle.pk, 4),
            "pk_heuristic_k": round(s_heuristic.pk, 4),
        }
        print(f"{vid}: gt_k={n_segs}  heur_k={k_heuristic}  "
              f"pk_oracle={s_oracle.pk:.4f}  pk_heuristic={s_heuristic.pk:.4f}")

    print(f"\n{'='*60}")
    print(f"Macro avg  oracle-k   Pk: {np.mean(pk_oracle):.4f}")
    print(f"Macro avg  heuristic  Pk: {np.mean(pk_divisive):.4f}")
    print(f"Gap (ceiling vs current): {np.mean(pk_divisive) - np.mean(pk_oracle):.4f}")
    print(f"\nIf gap is large -> fix k-selection to get big gains.")
    print(f"If oracle-k Pk is still >0.30 -> algorithm needs improvement (finetuning).")

    out = ROOT / "results" / "oracle_k_experiment.json"
    json.dump({"macro_pk_oracle_k": float(np.mean(pk_oracle)),
               "macro_pk_heuristic": float(np.mean(pk_divisive)),
               "gap": float(np.mean(pk_divisive) - np.mean(pk_oracle)),
               "per_video": results}, open(out, "w"), indent=2)
    print(f"\nSaved -> {out}")

if __name__ == "__main__":
    run()
