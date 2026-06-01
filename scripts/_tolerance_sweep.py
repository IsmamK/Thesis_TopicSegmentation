"""Re-evaluate F1 at tolerance 2, 5, 8, 10 sentences."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lecseg.metrics import tolerance_f1

GT_HIER   = ROOT / "data" / "gt_hier"
SENTENCES = ROOT / "data" / "sentences"
EMBEDDINGS= ROOT / "data" / "embeddings"

import numpy as np
from lecseg.baselines.classical import texttiling, c99
from lecseg.baselines.neural import cosine_seg, kmeans_seg, bert_seg
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.models.hierarchical import HierarchicalSegmenter

METHODS = ["texttiling","c99","cosine","kmeans","bert_seg","two_stage","hierarchical"]
TOLERANCES = [2, 5, 8, 10]

def ts_to_sent(ts, sent_times):
    import bisect
    starts = [s for s,_ in sent_times]
    return max(0, bisect.bisect_right(starts, ts) - 1)

def run_method(method, texts, vecs, n_seg):
    if method == "texttiling":  return texttiling(texts)
    if method == "c99":         return c99(texts, n_segments=n_seg)
    if method == "cosine":      return cosine_seg(vecs, n_segments=n_seg)
    if method == "kmeans":      return kmeans_seg(vecs, n_segments=n_seg)
    if method == "bert_seg":    return bert_seg(vecs, n_segments=n_seg)
    if method == "two_stage":   return TwoStageBoundaryPredictor().predict(vecs, n_segments=n_seg)
    if method == "hierarchical":
        tree = HierarchicalSegmenter().segment(vecs, n_subtopics=n_seg)
        return tree.chapters

videos = [p.parent.name for p in sorted((ROOT/"data"/"transcripts").glob("*/transcript.json"))]

# Collect per-video predictions and references once
print("Running methods on 30 videos...")
all_preds = {m: [] for m in METHODS}
all_refs  = []
all_nunits= []

for vid in videos:
    sp = SENTENCES / vid / "sentences.json"
    ep = EMBEDDINGS / "mpnet" / vid / "embeddings.npy"
    gp = GT_HIER / f"{vid}.json"
    if not all(p.exists() for p in [sp, ep, gp]):
        continue

    sents = json.loads(sp.read_text(encoding="utf-8"))["sentences"]
    vecs  = np.load(str(ep)).astype(np.float32)
    gt    = json.loads(gp.read_text(encoding="utf-8"))
    N     = len(sents)
    st    = [(s["start"], s["end"]) for s in sents]

    ref_sec = [ch["start_sec"] for ch in gt.get("chapters",[]) if ch["start_sec"] > 0]
    ref     = [ts_to_sent(s, st) for s in ref_sec]
    if not ref: continue

    all_refs.append(ref)
    all_nunits.append(N)
    n_seg = len(ref) + 1
    texts = [s["text"] for s in sents]

    for m in METHODS:
        try:
            pred = run_method(m, texts, vecs, n_seg)
        except:
            pred = []
        all_preds[m].append(pred)

print(f"Done. {len(all_refs)} videos.\n")

# Compute mean F1 at each tolerance
print(f"{'Method':<15}", end="")
for t in TOLERANCES:
    print(f"  tol={t:>2} F1", end="")
print()
print("-" * (15 + len(TOLERANCES)*12))

for m in METHODS:
    print(f"{m:<15}", end="")
    for tol in TOLERANCES:
        f1s = []
        for pred, ref, N in zip(all_preds[m], all_refs, all_nunits):
            _, _, f1 = tolerance_f1(pred, ref, N, tolerance=tol)
            f1s.append(f1)
        mean_f1 = sum(f1s)/len(f1s) if f1s else 0
        print(f"  {mean_f1:>10.4f}", end="")
    print()
