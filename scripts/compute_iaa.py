"""
T13 — Compute inter-annotator agreement (Cohen's kappa).

Compares primary annotations (data/gt_hier/) with double annotations
(data/gt_hier/double/) and computes:
    - Cohen's kappa for chapter boundaries
    - Cohen's kappa for subtopic boundaries
    - Boundary-level F1 (tolerance=1 sentence ≈ 30s)

Saves results to data/gt_hier/iaa_report.json.

Usage:
    python scripts/compute_iaa.py
    python scripts/compute_iaa.py --tolerance 2 --verbose
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GT_HIER = ROOT / "data" / "gt_hier"
GT_HIER_DOUBLE = GT_HIER / "double"


def _load_annotation(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _get_boundaries(ann: dict, level: str = "chapter") -> set[int]:
    """Extract boundary positions from annotation dict.

    Supports both second-based timestamps (converted to 30s units) and
    sentence-index based boundaries.
    """
    if level == "chapter":
        bounds = ann.get("chapters", [])
    else:
        bounds = ann.get("subtopics", [])

    # If timestamps in seconds, convert to 30-second units
    result = set()
    for b in bounds:
        if isinstance(b, (int, float)):
            result.add(int(b))
        elif isinstance(b, dict):
            # support both "start_sec" (timestamp) and "start" (sentence index)
            val = b.get("start_sec", b.get("start", None))
            if val is not None:
                result.add(int(val))
    return result


def _cohen_kappa(
    boundaries_a: set[int],
    boundaries_b: set[int],
    n_units: int,
    tolerance: int = 0,
) -> float:
    """
    Compute Cohen's kappa treating each unit as a binary boundary/no-boundary label.

    With tolerance > 0, a boundary in A counts as matching B if any boundary
    in B is within ±tolerance units.

    Returns kappa in [-1, 1]; 1.0 = perfect agreement, 0.0 = chance.
    """
    if n_units == 0:
        return 1.0

    def _matches(b: int, other: set[int], tol: int) -> bool:
        if tol == 0:
            return b in other
        return any(abs(b - o) <= tol for o in other)

    # Build binary vectors
    vec_a = [1 if i in boundaries_a else 0 for i in range(n_units)]
    vec_b = [1 if _matches(i, boundaries_b, tolerance) else 0 for i in range(n_units)]

    # 2x2 confusion matrix
    tp = sum(1 for a, b in zip(vec_a, vec_b) if a == 1 and b == 1)
    tn = sum(1 for a, b in zip(vec_a, vec_b) if a == 0 and b == 0)
    fp = sum(1 for a, b in zip(vec_a, vec_b) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(vec_a, vec_b) if a == 1 and b == 0)
    total = tp + tn + fp + fn

    if total == 0:
        return 1.0

    p_o = (tp + tn) / total  # observed agreement

    # Expected agreement
    p_a1 = (tp + fn) / total  # rate of 1 in A
    p_b1 = (tp + fp) / total  # rate of 1 in B
    p_e = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)

    if p_e == 1.0:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def _boundary_f1(
    pred: set[int],
    ref: set[int],
    n_units: int,
    tolerance: int = 1,
) -> tuple[float, float, float]:
    """Compute precision, recall, F1 with tolerance window."""
    if not pred and not ref:
        return 1.0, 1.0, 1.0
    if not pred:
        return 0.0, 0.0, 0.0
    if not ref:
        return 0.0, 0.0, 0.0

    matched_ref = set()
    tp = 0
    for p in pred:
        for d in range(-tolerance, tolerance + 1):
            if (p + d) in ref and (p + d) not in matched_ref:
                tp += 1
                matched_ref.add(p + d)
                break

    precision = tp / len(pred)
    recall = tp / len(ref)
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)
    return precision, recall, f1


def compute_iaa(
    gt_hier: Path = GT_HIER,
    gt_double: Path = GT_HIER_DOUBLE,
    tolerance: int = 1,
    verbose: bool = False,
) -> dict:
    """
    Compute inter-annotator agreement for all videos with double annotations.

    Returns a dict with per-video and aggregate statistics.
    """
    double_files = sorted(gt_double.glob("*.json"))

    if not double_files:
        print("No double annotations found in", gt_double)
        return {"n_videos": 0, "videos": {}}

    results = {}
    kappas_ch, kappas_sub, f1s_ch, f1s_sub = [], [], [], []

    for df in double_files:
        vid = df.stem
        primary_path = gt_hier / f"{vid}.json"

        if not primary_path.exists():
            if verbose:
                print(f"  SKIP {vid}: no primary annotation")
            continue

        ann_a = _load_annotation(primary_path)
        ann_b = _load_annotation(df)

        # Use total_sentences or infer from last boundary timestamp
        n_units = ann_a.get("total_sentences", ann_a.get("n_units", 0))
        if n_units == 0:
            # Try loading sentence count from sentences dir
            sent_path = ROOT / "data" / "sentences" / vid / "sentences.json"
            if sent_path.exists():
                import json as _json
                sd = _json.loads(sent_path.read_text(encoding="utf-8"))
                sents = sd.get("sentences", sd) if isinstance(sd, dict) else sd
                n_units = len(sents)
            if n_units == 0:
                # Fallback: estimate from max start_sec / 30s per sentence
                all_bounds = (
                    list(ann_a.get("chapters", [])) +
                    list(ann_a.get("subtopics", [])) +
                    list(ann_b.get("chapters", [])) +
                    list(ann_b.get("subtopics", []))
                )
                max_sec = max(
                    (b.get("start_sec", 0) if isinstance(b, dict) else (b if isinstance(b, (int, float)) else 0))
                    for b in all_bounds
                ) if all_bounds else 0
                n_units = max(int(max_sec / 30) + 10, 10)

        ch_a = _get_boundaries(ann_a, "chapter")
        ch_b = _get_boundaries(ann_b, "chapter")
        sub_a = _get_boundaries(ann_a, "subtopic")
        sub_b = _get_boundaries(ann_b, "subtopic")

        kappa_ch = _cohen_kappa(ch_a, ch_b, n_units, tolerance)
        kappa_sub = _cohen_kappa(sub_a, sub_b, n_units, tolerance)
        prec_ch, rec_ch, f1_ch = _boundary_f1(ch_a, ch_b, n_units, tolerance)
        prec_sub, rec_sub, f1_sub = _boundary_f1(sub_a, sub_b, n_units, tolerance)

        vid_result = {
            "n_units": n_units,
            "chapters": {
                "annotator_a": sorted(ch_a),
                "annotator_b": sorted(ch_b),
                "kappa": round(kappa_ch, 4),
                "f1": round(f1_ch, 4),
                "precision": round(prec_ch, 4),
                "recall": round(rec_ch, 4),
            },
            "subtopics": {
                "annotator_a": sorted(sub_a),
                "annotator_b": sorted(sub_b),
                "kappa": round(kappa_sub, 4),
                "f1": round(f1_sub, 4),
                "precision": round(prec_sub, 4),
                "recall": round(rec_sub, 4),
            },
        }
        results[vid] = vid_result

        kappas_ch.append(kappa_ch)
        kappas_sub.append(kappa_sub)
        f1s_ch.append(f1_ch)
        f1s_sub.append(f1_sub)

        if verbose:
            print(f"  {vid}: kappa_ch={kappa_ch:.3f}  kappa_sub={kappa_sub:.3f}  "
                  f"f1_ch={f1_ch:.3f}  f1_sub={f1_sub:.3f}")

    def _mean(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    aggregate = {
        "n_videos": len(results),
        "mean_kappa_chapter": round(_mean(kappas_ch), 4),
        "mean_kappa_subtopic": round(_mean(kappas_sub), 4),
        "mean_f1_chapter": round(_mean(f1s_ch), 4),
        "mean_f1_subtopic": round(_mean(f1s_sub), 4),
        "tolerance": tolerance,
    }

    return {"aggregate": aggregate, "videos": results}


def main():
    parser = argparse.ArgumentParser(description="Compute inter-annotator agreement")
    parser.add_argument("--tolerance", type=int, default=1,
                        help="Boundary tolerance in units (default 1)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output", default=str(GT_HIER / "iaa_report.json"),
                        help="Output JSON path")
    args = parser.parse_args()

    print(f"Computing IAA with tolerance={args.tolerance}...")
    report = compute_iaa(tolerance=args.tolerance, verbose=args.verbose)

    agg = report.get("aggregate", {})
    print(f"\nAggregate results ({agg.get('n_videos', 0)} videos):")
    print(f"  mean kappa (chapters):  {agg.get('mean_kappa_chapter', 0):.4f}")
    print(f"  mean kappa (subtopics): {agg.get('mean_kappa_subtopic', 0):.4f}")
    print(f"  mean F1    (chapters):  {agg.get('mean_f1_chapter', 0):.4f}")
    print(f"  mean F1    (subtopics): {agg.get('mean_f1_subtopic', 0):.4f}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved to {out_path}")


if __name__ == "__main__":
    main()
