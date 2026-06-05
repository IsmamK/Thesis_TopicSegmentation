"""Modern boundary and segment metrics for the defended LECSEG methods.

This script is intentionally separate from ``scripts/run_eval.py``.  The main
pipeline remains stable, while this analysis adds defense-friendly metrics:

- sentence-boundary F1 at wider tolerances
- time-boundary F1 at 10/30/60 seconds
- boundary count error
- segment temporal-IoU style F1

The output is meant for thesis tables, defense slides, and examiner questions
about whether a low strict F1@2 invalidates the segmentation result.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from lecseg.metrics import evaluate, tolerance_f1  # noqa: E402

import run_eval as legacy_eval  # noqa: E402


DEFAULT_METHODS = [
    "divisive",
    "cross_e5_frac70_minlen11",
    "divisive_smooth9_frac70",
    "two_stage",
    "hierarchical",
]

METHOD_LABELS = {
    "divisive": "BGE-divisive baseline",
    "cross_e5_frac70_minlen11": "Cross-model conservative",
    "divisive_smooth9_frac70": "Conservative smoothed BGE",
    "two_stage": "Two-stage predictor",
    "hierarchical": "Hierarchical segmenter",
}

SENT_TOLERANCES = [1, 2, 3, 5, 10]
TIME_TOLERANCES = [10, 30, 60]
IOU_THRESHOLDS = [0.3, 0.5, 0.7]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest_ids() -> list[str]:
    manifest = ROOT / "data" / "manifest.jsonl"
    if manifest.exists():
        ids: list[str] = []
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ids.append(json.loads(line)["id"])
        return ids
    return sorted(p.stem for p in (ROOT / "data" / "gt").glob("*.json"))


def _load_sentences(video_id: str) -> list[dict[str, Any]] | None:
    path = ROOT / "data" / "sentences" / video_id / "sentences.json"
    if not path.exists():
        return None
    return _read_json(path)["sentences"]


def _load_gt(video_id: str) -> dict[str, Any] | None:
    path = ROOT / "data" / "gt" / f"{video_id}.json"
    if not path.exists():
        return None
    return _read_json(path)


def _load_embeddings(video_id: str, model: str) -> np.ndarray | None:
    path = ROOT / "data" / "embeddings" / model / video_id / "embeddings.npy"
    if not path.exists():
        return None
    return np.load(path).astype(np.float32)


def _boundary_seconds_to_sentence_indices(boundaries_sec: list[float], sentences: list[dict[str, Any]]) -> list[int]:
    starts = np.array([float(s.get("start", 0.0)) for s in sentences], dtype=np.float64)
    n = len(sentences)
    indices: list[int] = []
    for sec in boundaries_sec:
        if float(sec) <= 0:
            continue
        idx = int(np.searchsorted(starts, float(sec), side="left"))
        idx = max(1, min(idx, n - 1))
        indices.append(idx)
    return sorted(set(indices))


def _sentence_indices_to_seconds(boundaries: list[int], sentences: list[dict[str, Any]], duration_sec: float) -> list[int]:
    secs: list[int] = []
    n = len(sentences)
    for b in sorted(set(int(x) for x in boundaries)):
        if not (0 < b < n):
            continue
        sec = float(sentences[b].get("start", sentences[b - 1].get("end", 0.0)))
        secs.append(max(1, min(int(round(sec)), int(math.ceil(duration_sec)) - 1)))
    return sorted(set(secs))


def _segments_from_boundaries(boundaries_sec: list[float], duration_sec: float) -> list[tuple[float, float]]:
    clean = sorted(set(float(b) for b in boundaries_sec if 0 < float(b) < duration_sec))
    points = [0.0] + clean + [float(duration_sec)]
    return [(points[i], points[i + 1]) for i in range(len(points) - 1) if points[i + 1] > points[i]]


def _iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def _segment_scores(
    pred_boundaries_sec: list[float],
    ref_boundaries_sec: list[float],
    duration_sec: float,
) -> dict[str, float]:
    pred_segments = _segments_from_boundaries(pred_boundaries_sec, duration_sec)
    ref_segments = _segments_from_boundaries(ref_boundaries_sec, duration_sec)
    best_ious = [max((_iou(p, r) for r in ref_segments), default=0.0) for p in pred_segments]
    out = {"mean_best_tiou": float(mean(best_ious)) if best_ious else 0.0}
    for threshold in IOU_THRESHOLDS:
        matched_ref: set[int] = set()
        tp = 0
        for pred in pred_segments:
            best_idx = -1
            best_score = -1.0
            for idx, ref in enumerate(ref_segments):
                if idx in matched_ref:
                    continue
                score = _iou(pred, ref)
                if score > best_score:
                    best_idx = idx
                    best_score = score
            if best_idx >= 0 and best_score >= threshold:
                tp += 1
                matched_ref.add(best_idx)
        precision = tp / len(pred_segments) if pred_segments else 0.0
        recall = tp / len(ref_segments) if ref_segments else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[f"seg_f1_iou{str(threshold).replace('.', '')}"] = float(f1)
    return out


def _run_one_method(
    method: str,
    video_id: str,
    sentences: list[dict[str, Any]],
    n_segments: int,
    embedding_model: str,
) -> list[int]:
    vecs = _load_embeddings(video_id, embedding_model)
    if vecs is None:
        raise FileNotFoundError(f"Missing embeddings for {embedding_model}/{video_id}")
    n = min(len(sentences), len(vecs))
    sentences_use = sentences[:n]
    vecs_use = vecs[:n]
    prosody_gap = legacy_eval._load_prosody(video_id, n)  # noqa: SLF001
    shot_gap = legacy_eval._load_shot_gap_scores(video_id, n, sentences_use)  # noqa: SLF001
    return legacy_eval._run_method(  # noqa: SLF001
        method,
        sentences_use,
        vecs_use,
        n_segments,
        prosody_gap=prosody_gap,
        shot_gap=shot_gap,
        chunk_size=4,
        vid=video_id,
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _latex_table(summary_rows: list[dict[str, Any]], path: Path) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Modern boundary and segment metrics for defended operating points. Lower Pk, WD, and count error are better; higher F1 and tIoU are better.}",
        r"\label{tab:modern_metrics}",
        r"\resizebox{\linewidth}{!}{%",
        r"\begin{tabular}{lrrrrrrrr}",
        r"\toprule",
        r"Method & Pk & WD & F1@2 & F1@5 & F1@10 & F1@30s & tIoU & Count Err. \\",
        r"\midrule",
    ]
    for row in summary_rows:
        lines.append(
            f"{row['label']} & {row['pk']:.4f} & {row['wd']:.4f} & "
            f"{row['sent_f1_t2']:.4f} & {row['sent_f1_t5']:.4f} & "
            f"{row['sent_f1_t10']:.4f} & {row['time_f1_30s']:.4f} & "
            f"{row['mean_best_tiou']:.4f} & {row['abs_count_error']:.2f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"}", r"\end{table}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    parser.add_argument("--embedding-model", default="bge_large")
    parser.add_argument("--max-videos", type=int, default=None)
    args = parser.parse_args()

    video_ids = _load_manifest_ids()
    if args.max_videos:
        video_ids = video_ids[: args.max_videos]

    per_video: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for video_id in video_ids:
        sentences = _load_sentences(video_id)
        gt = _load_gt(video_id)
        if not sentences or not gt:
            continue
        duration_sec = float(gt.get("duration_sec") or max(float(s.get("end", 0.0)) for s in sentences))
        ref_sec = [float(x) for x in gt.get("boundaries_sec", []) if float(x) > 0]
        ref_sent = _boundary_seconds_to_sentence_indices(ref_sec, sentences)
        n_segments = max(2, len(ref_sent) + 1)

        for method in args.methods:
            try:
                hyp_sent = _run_one_method(method, video_id, sentences, n_segments, args.embedding_model)
                hyp_sent = sorted(set(int(x) for x in hyp_sent if 0 < int(x) < len(sentences)))
                hyp_sec = _sentence_indices_to_seconds(hyp_sent, sentences, duration_sec)
                scores = evaluate(hyp_sent, ref_sent, len(sentences))

                row: dict[str, Any] = {
                    "video_id": video_id,
                    "method": method,
                    "label": METHOD_LABELS.get(method, method),
                    "pk": float(scores.pk),
                    "wd": float(scores.wd),
                    "boundary_similarity": float(scores.boundary_similarity),
                    "n_reference": len(ref_sent),
                    "n_predicted": len(hyp_sent),
                    "count_error": len(hyp_sent) - len(ref_sent),
                    "abs_count_error": abs(len(hyp_sent) - len(ref_sent)),
                    "boundary_ratio": len(hyp_sent) / max(1, len(ref_sent)),
                }
                for tol in SENT_TOLERANCES:
                    p, r, f1 = tolerance_f1(hyp_sent, ref_sent, len(sentences), tolerance=tol)
                    row[f"sent_precision_t{tol}"] = float(p)
                    row[f"sent_recall_t{tol}"] = float(r)
                    row[f"sent_f1_t{tol}"] = float(f1)
                for tol in TIME_TOLERANCES:
                    p, r, f1 = tolerance_f1(hyp_sec, [int(round(x)) for x in ref_sec], int(math.ceil(duration_sec)) + 1, tolerance=tol)
                    row[f"time_precision_{tol}s"] = float(p)
                    row[f"time_recall_{tol}s"] = float(r)
                    row[f"time_f1_{tol}s"] = float(f1)
                row.update(_segment_scores(hyp_sec, ref_sec, duration_sec))
                per_video.append(row)
            except Exception as exc:  # keep analysis running and record failures
                failures.append({"video_id": video_id, "method": method, "error": str(exc)})

    summary_rows: list[dict[str, Any]] = []
    for method in args.methods:
        rows = [r for r in per_video if r["method"] == method]
        if not rows:
            continue
        numeric_keys = [k for k, v in rows[0].items() if isinstance(v, (int, float))]
        summary = {
            "method": method,
            "label": METHOD_LABELS.get(method, method),
            "n_videos": len(rows),
        }
        for key in numeric_keys:
            summary[key] = float(mean(float(r[key]) for r in rows))
        summary_rows.append(summary)

    result = {
        "meta": {
            "methods": args.methods,
            "embedding_model": args.embedding_model,
            "sentence_tolerances": SENT_TOLERANCES,
            "time_tolerances_seconds": TIME_TOLERANCES,
            "iou_thresholds": IOU_THRESHOLDS,
            "note": "Reruns selected defended operating points to evaluate strict and relaxed boundary/segment metrics.",
        },
        "summary": summary_rows,
        "failures": failures,
    }

    out_json = ROOT / "results" / "modern_metrics_summary.json"
    out_per_video = ROOT / "results" / "modern_metrics_per_video.csv"
    out_summary = ROOT / "results" / "modern_metrics_summary.csv"
    out_tex = ROOT / "thesis" / "tables" / "modern_metrics.tex"

    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _write_csv(out_per_video, per_video)
    _write_csv(out_summary, summary_rows)
    _latex_table(summary_rows, out_tex)

    print(f"Wrote {out_json}")
    print(f"Wrote {out_per_video}")
    print(f"Wrote {out_summary}")
    print(f"Wrote {out_tex}")
    if failures:
        print(f"Recorded {len(failures)} method/video failures")
    print("\n=== MODERN METRIC SUMMARY ===")
    for row in sorted(summary_rows, key=lambda r: r["pk"]):
        print(
            f"{row['label']:<30} Pk={row['pk']:.4f} WD={row['wd']:.4f} "
            f"F1@2={row['sent_f1_t2']:.4f} F1@10={row['sent_f1_t10']:.4f} "
            f"F1@30s={row['time_f1_30s']:.4f} tIoU={row['mean_best_tiou']:.4f} "
            f"count_err={row['abs_count_error']:.2f}"
        )


if __name__ == "__main__":
    main()
