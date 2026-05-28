"""
T31 — Qualitative error analysis.

For each video, identifies:
    - False positives: predicted boundaries not near any reference boundary
    - False negatives: reference boundaries not detected
    - Near misses: predicted boundaries within tolerance but not exact
    - Error patterns across videos (systematic biases)

Usage:
    from lecseg.eval.error_analysis import analyse_errors, summarise_errors

    errors = analyse_errors(predicted=[10, 25, 40], reference=[12, 27, 45],
                            n_units=60, tolerance=2)
    summary = summarise_errors([errors_vid1, errors_vid2, ...])
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BoundaryErrors:
    """Error analysis for a single video's boundary predictions."""

    video_id: str
    n_units: int
    predicted: list[int]
    reference: list[int]
    tolerance: int

    true_positives: list[int] = field(default_factory=list)
    false_positives: list[int] = field(default_factory=list)
    false_negatives: list[int] = field(default_factory=list)
    near_misses: list[tuple[int, int]] = field(default_factory=list)  # (pred, ref) pairs

    def precision(self) -> float:
        tp = len(self.true_positives)
        fp = len(self.false_positives)
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0

    def recall(self) -> float:
        tp = len(self.true_positives)
        fn = len(self.false_negatives)
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0

    def f1(self) -> float:
        p, r = self.precision(), self.recall()
        return (2 * p * r / (p + r)) if (p + r) > 0 else 0.0

    def as_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "n_units": self.n_units,
            "n_predicted": len(self.predicted),
            "n_reference": len(self.reference),
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "near_misses": self.near_misses,
            "precision": round(self.precision(), 4),
            "recall": round(self.recall(), 4),
            "f1": round(self.f1(), 4),
        }


def analyse_errors(
    predicted: list[int],
    reference: list[int],
    n_units: int,
    tolerance: int = 2,
    video_id: str = "",
) -> BoundaryErrors:
    """
    Classify predicted boundaries into TP, FP, FN, and near-misses.

    Args:
        predicted:  predicted boundary indices (1-based)
        reference:  reference boundary indices (1-based)
        n_units:    total number of units
        tolerance:  boundary tolerance window
        video_id:   optional video identifier

    Returns:
        BoundaryErrors dataclass with classified boundaries.
    """
    pred_set = set(predicted)
    ref_set = set(reference)

    true_positives: list[int] = []
    false_positives: list[int] = []
    near_misses: list[tuple[int, int]] = []

    matched_ref: set[int] = set()

    for p in sorted(pred_set):
        # Check if exact match
        if p in ref_set:
            true_positives.append(p)
            matched_ref.add(p)
        else:
            # Check if near miss (within tolerance)
            near_ref = [r for r in ref_set
                        if abs(p - r) <= tolerance and r not in matched_ref]
            if near_ref:
                closest = min(near_ref, key=lambda r: abs(p - r))
                near_misses.append((p, closest))
                true_positives.append(p)  # count as TP with tolerance
                matched_ref.add(closest)
            else:
                false_positives.append(p)

    false_negatives = sorted(r for r in ref_set if r not in matched_ref)

    return BoundaryErrors(
        video_id=video_id,
        n_units=n_units,
        predicted=sorted(predicted),
        reference=sorted(reference),
        tolerance=tolerance,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        near_misses=near_misses,
    )


def summarise_errors(
    error_list: list[BoundaryErrors],
) -> dict:
    """
    Aggregate error analysis across multiple videos.

    Returns:
        Summary dict with error counts, rates, and patterns.
    """
    if not error_list:
        return {}

    n = len(error_list)
    total_pred = sum(len(e.predicted) for e in error_list)
    total_ref = sum(len(e.reference) for e in error_list)
    total_tp = sum(len(e.true_positives) for e in error_list)
    total_fp = sum(len(e.false_positives) for e in error_list)
    total_fn = sum(len(e.false_negatives) for e in error_list)
    total_nm = sum(len(e.near_misses) for e in error_list)

    macro_prec = sum(e.precision() for e in error_list) / n
    macro_rec = sum(e.recall() for e in error_list) / n
    macro_f1 = sum(e.f1() for e in error_list) / n

    micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = ((2 * micro_prec * micro_rec / (micro_prec + micro_rec))
                if (micro_prec + micro_rec) > 0 else 0.0)

    # Over/under-segmentation analysis
    over_seg = [e.video_id for e in error_list if len(e.predicted) > len(e.reference) * 1.5]
    under_seg = [e.video_id for e in error_list if len(e.predicted) < len(e.reference) * 0.5]

    # Near-miss rate: what fraction of "errors" were actually close?
    near_miss_rate = total_nm / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0

    return {
        "n_videos": n,
        "total_predicted": total_pred,
        "total_reference": total_ref,
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "total_near_misses": total_nm,
        "near_miss_rate": round(near_miss_rate, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "macro_f1": round(macro_f1, 4),
        "micro_precision": round(micro_prec, 4),
        "micro_recall": round(micro_rec, 4),
        "micro_f1": round(micro_f1, 4),
        "over_segmented_videos": over_seg,
        "under_segmented_videos": under_seg,
    }
