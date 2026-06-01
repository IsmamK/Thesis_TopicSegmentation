"""
Analyze boundary counts per method and video.
Outputs results/boundary_count_analysis.csv and results/boundary_count_summary.csv
"""
from __future__ import annotations
import json
import sys
import csv
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

RESULTS_FILE = ROOT / "results" / "eval_gt_hier.json"
GT_DIR = ROOT / "data" / "gt"
SENTENCES_DIR = ROOT / "data" / "sentences"
OUTPUT_DIR = ROOT / "results"


def fmt(x):
    return f"{x:.3f}" if isinstance(x, float) else str(x)


def main():
    if not RESULTS_FILE.exists():
        print(f"Results file not found: {RESULTS_FILE}")
        sys.exit(1)

    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    results = data["results"]

    rows = []
    for method, vid_results in results.items():
        for vid, scores in vid_results.items():
            if "error" in scores:
                continue
            n_pred = scores.get("n_predicted", None)
            n_ref  = scores.get("n_reference", None)
            if n_pred is None or n_ref is None:
                continue

            # Load GT for duration
            gt_file = GT_DIR / f"{vid}.json"
            duration_min = None
            if gt_file.exists():
                gt = json.loads(gt_file.read_text())
                duration_min = gt.get("duration_sec", 0) / 60.0

            # Load sentence count
            sent_file = SENTENCES_DIR / vid / "sentences.json"
            n_sents = None
            if sent_file.exists():
                sents = json.loads(sent_file.read_text())["sentences"]
                n_sents = len(sents)

            avg_gt_len_s = (n_sents / (n_ref + 1)) if n_sents and n_ref else None
            avg_pred_len_s = (n_sents / (n_pred + 1)) if n_sents and n_pred else None
            avg_gt_len_m = (duration_min / (n_ref + 1)) if duration_min and n_ref else None
            avg_pred_len_m = (duration_min / (n_pred + 1)) if duration_min and n_pred else None
            ratio = round(n_pred / max(1, n_ref), 3)

            rows.append({
                "video_id": vid,
                "method": method,
                "gt_boundaries": n_ref,
                "pred_boundaries": n_pred,
                "boundary_diff": n_pred - n_ref,
                "boundary_ratio": ratio,
                "avg_gt_segment_len_sentences": round(avg_gt_len_s, 1) if avg_gt_len_s else "",
                "avg_pred_segment_len_sentences": round(avg_pred_len_s, 1) if avg_pred_len_s else "",
                "avg_gt_segment_len_minutes": round(avg_gt_len_m, 2) if avg_gt_len_m else "",
                "avg_pred_segment_len_minutes": round(avg_pred_len_m, 2) if avg_pred_len_m else "",
            })

    if not rows:
        print("No rows with n_predicted/n_reference found. Run run_eval.py first.")
        sys.exit(1)

    # Write per-video CSV
    out1 = OUTPUT_DIR / "boundary_count_analysis.csv"
    fieldnames = list(rows[0].keys())
    with open(out1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Written: {out1}")

    # Write summary CSV
    methods = sorted(set(r["method"] for r in rows))
    summary_rows = []
    for method in methods:
        m_rows = [r for r in rows if r["method"] == method]
        pred_vals = [r["pred_boundaries"] for r in m_rows]
        gt_vals   = [r["gt_boundaries"]   for r in m_rows]
        diff_vals = [r["boundary_diff"]   for r in m_rows]
        ratio_vals= [r["boundary_ratio"]  for r in m_rows]
        summary_rows.append({
            "method": method,
            "mean_gt_boundaries":   round(mean(gt_vals), 2),
            "mean_pred_boundaries": round(mean(pred_vals), 2),
            "std_pred_boundaries":  round(stdev(pred_vals) if len(pred_vals) > 1 else 0, 2),
            "mean_boundary_diff":   round(mean(diff_vals), 2),
            "mean_boundary_ratio":  round(mean(ratio_vals), 3),
        })
    out2 = OUTPUT_DIR / "boundary_count_summary.csv"
    with open(out2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)
    print(f"Written: {out2}")

    # Print summary table
    print("\n=== BOUNDARY COUNT SUMMARY ===")
    print(f"{'Method':<25} {'Mean GT':>8} {'Mean Pred':>10} {'Std Pred':>9} {'Mean Diff':>10} {'Mean Ratio':>11}")
    print("-" * 68)
    for r in summary_rows:
        print(f"{r['method']:<25} {r['mean_gt_boundaries']:>8.1f} {r['mean_pred_boundaries']:>10.1f} "
              f"{r['std_pred_boundaries']:>9.1f} {r['mean_boundary_diff']:>10.1f} {r['mean_boundary_ratio']:>11.3f}")


if __name__ == "__main__":
    main()
