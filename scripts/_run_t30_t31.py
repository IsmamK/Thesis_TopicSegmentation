"""Run T30 (bootstrap CIs + Wilcoxon) and T31 (error analysis) on results/eval.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lecseg.eval.stats import bootstrap_ci, wilcoxon_test, compare_methods
from lecseg.eval.error_analysis import analyse_errors, summarise_errors, BoundaryErrors

EVAL = ROOT / "results" / "eval.json"
OUT_STATS = ROOT / "results" / "stats.json"
OUT_ERRORS = ROOT / "results" / "error_analysis.json"

data = json.loads(EVAL.read_text(encoding="utf-8"))
results = data["results"]  # {method: {video_id: {metric: value}}}

METRICS = ["pk", "wd", "f1", "boundary_similarity"]
METHODS = list(results.keys())
videos = sorted(next(iter(results.values())).keys())

# --- T30: Bootstrap CIs for each method/metric ---
stats_out = {"methods": {}, "comparisons": {}}

for method in METHODS:
    stats_out["methods"][method] = {}
    for metric in METRICS:
        scores = [results[method][v].get(metric, 0.0) for v in videos
                  if isinstance(results[method][v], dict)]
        ci = bootstrap_ci(scores)
        stats_out["methods"][method][metric] = {
            "mean": ci[0], "ci_lo": ci[1], "ci_hi": ci[2], "n": len(scores)
        }

# Wilcoxon comparisons
for base, novel in [("cosine", "two_stage"), ("cosine", "hierarchical"),
                    ("bert_seg", "two_stage"), ("bert_seg", "hierarchical"),
                    ("c99", "hierarchical")]:
    if base in results and novel in results:
        key = f"{base}_vs_{novel}"
        stats_out["comparisons"][key] = compare_methods(results, base, novel)

OUT_STATS.write_text(json.dumps(stats_out, indent=2), encoding="utf-8")
print(f"T30 done -> {OUT_STATS}")

print("\n=== Bootstrap 95% CI Summary ===")
print(f"{'Method':<15} {'Pk mean':>10} {'Pk CI':>18} {'F1 mean':>10} {'F1 CI':>18}")
for method in METHODS:
    pk = stats_out["methods"][method]["pk"]
    f1 = stats_out["methods"][method]["f1"]
    print(f"{method:<15} {pk['mean']:>10.4f} [{pk['ci_lo']:.4f},{pk['ci_hi']:.4f}]  "
          f"{f1['mean']:>10.4f} [{f1['ci_lo']:.4f},{f1['ci_hi']:.4f}]")

print("\n=== Wilcoxon p-values ===")
for key, comp in stats_out["comparisons"].items():
    if "error" in comp:
        continue
    print(f"\n{key}:")
    for metric, m in comp["metrics"].items():
        sig = "**" if m["significant"] else "  "
        print(f"  {metric:<20} delta={m['delta']:+.4f}  p={m['p_value']:.4f} {sig}")

# --- T31: Error analysis — re-run each method to get actual boundary predictions ---
print("\n=== T31: Running per-method error analysis ===")

import numpy as np
from lecseg.baselines.classical import texttiling, c99
from lecseg.baselines.neural import cosine_seg, kmeans_seg, bert_seg
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.models.hierarchical import HierarchicalSegmenter

GT_HIER = ROOT / "data" / "gt_hier"
SENTENCES_DIR = ROOT / "data" / "sentences"
EMBEDDINGS_DIR = ROOT / "data" / "embeddings"

def _sent_times(sentences):
    return [(s["start"], s["end"]) for s in sentences]

def _ts_to_sent_idx(ts_sec, sent_times_list):
    import bisect
    starts = [s for s, _ in sent_times_list]
    idx = bisect.bisect_right(starts, ts_sec) - 1
    return max(0, min(idx, len(starts) - 1))

def _run_method(method, texts, vecs, n_segments):
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
        return TwoStageBoundaryPredictor().predict(vecs, n_segments=n_segments)
    elif method == "hierarchical":
        seg = HierarchicalSegmenter()
        tree = seg.segment(vecs, n_subtopics=n_segments)
        return tree.chapters
    return []

errors_out = {"per_method": {}, "summaries": {}}

for method in METHODS:
    method_errors = []
    for vid in videos:
        sent_path = SENTENCES_DIR / vid / "sentences.json"
        emb_path = EMBEDDINGS_DIR / "mpnet" / vid / "embeddings.npy"
        gt_path = GT_HIER / f"{vid}.json"
        if not all(p.exists() for p in [sent_path, emb_path, gt_path]):
            continue

        sent_data = json.loads(sent_path.read_text(encoding="utf-8"))
        sentences = sent_data.get("sentences", [])
        n_units = len(sentences)
        if n_units < 5:
            continue

        vecs = np.load(str(emb_path)).astype(np.float32)
        gt_data = json.loads(gt_path.read_text(encoding="utf-8"))
        st = _sent_times(sentences)

        ref_bounds_sec = [ch["start_sec"] for ch in gt_data.get("chapters", []) if ch["start_sec"] > 0]
        ref_bounds = [_ts_to_sent_idx(s, st) for s in ref_bounds_sec]
        if not ref_bounds:
            continue

        n_seg = len(ref_bounds) + 1
        try:
            texts = [s["text"] for s in sentences]
            pred_bounds = _run_method(method, texts, vecs, n_seg)
        except Exception as e:
            print(f"  {method}/{vid}: {e}")
            continue

        err = analyse_errors(pred_bounds, ref_bounds, n_units, tolerance=2, video_id=vid)
        method_errors.append(err.as_dict())

    errors_out["per_method"][method] = method_errors

    be_list = []
    for e in method_errors:
        be = BoundaryErrors(
            video_id=e["video_id"], n_units=e["n_units"],
            predicted=e["true_positives"] + e["false_positives"],
            reference=e["true_positives"] + e["false_negatives"],
            tolerance=2,
            true_positives=e["true_positives"],
            false_positives=e["false_positives"],
            false_negatives=e["false_negatives"],
            near_misses=[tuple(x) for x in e["near_misses"]],
        )
        be_list.append(be)
    summary = summarise_errors(be_list)
    errors_out["summaries"][method] = summary
    print(f"  {method}: {len(method_errors)} videos, macro_F1={summary.get('macro_f1',0):.4f}, "
          f"FP={summary.get('total_fp',0)}, FN={summary.get('total_fn',0)}")

OUT_ERRORS.write_text(json.dumps(errors_out, indent=2), encoding="utf-8")
print(f"\nT31 done -> {OUT_ERRORS}")

print("\n=== Error Analysis Summary ===")
print(f"{'Method':<15} {'macro_P':>8} {'macro_R':>8} {'macro_F1':>8} {'FP':>6} {'FN':>6} {'NM':>6}")
for method in METHODS:
    s = errors_out["summaries"].get(method, {})
    if not s:
        continue
    print(f"{method:<15} {s.get('macro_precision',0):>8.4f} {s.get('macro_recall',0):>8.4f} "
          f"{s.get('macro_f1',0):>8.4f} {s.get('total_fp',0):>6} {s.get('total_fn',0):>6} "
          f"{s.get('total_near_misses',0):>6}")
