"""Run a TreeSeg-style same-dataset baseline on LECSEG-30.

The public TreeSeg implementation uses an OpenAI embedding endpoint by default.
For a fair, reproducible same-dataset comparison, this script adapts TreeSeg's
published split objective to the local LECSEG sentence embeddings and evaluates
it with the same YouTube chapter ground truth and metrics used by the thesis.

This is a comparison artifact, not a replacement for the official LECSEG result.
"""

from __future__ import annotations

import argparse
import heapq
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_eval as official  # noqa: E402


MAX_SENTENCES = 800


@dataclass(frozen=True)
class SplitCandidate:
    priority: float
    counter: int
    start: int
    end: int
    split: int


def _mean(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = sorted({key for row in rows for key, value in row.items() if isinstance(value, (int, float))})
    return {key: float(np.mean([row[key] for row in rows if key in row])) for key in keys}


def _reference_boundaries(chapters: list[dict[str, Any]], sentences: list[dict[str, Any]]) -> list[int]:
    starts = np.array([float(s.get("start", 0.0)) for s in sentences], dtype=np.float32)
    n = len(sentences)
    boundaries = []
    for chapter in chapters[1:]:
        idx = int(np.searchsorted(starts, float(chapter["start_sec"]), side="left"))
        boundaries.append(max(1, min(idx, n - 1)))
    return sorted(set(boundaries))


def _load_examples(model: str) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for gt_file in sorted(official.GT_YOUTUBE.glob("*.json")):
        if gt_file.name.startswith("_"):
            continue
        video_id = gt_file.stem
        gt = official._load_ground_truth(video_id, use_youtube=True)
        sentences = official._load_sentences(video_id)
        vecs = official._load_embeddings(video_id, model)
        if gt is None or sentences is None or vecs is None:
            continue
        n = min(len(sentences), len(vecs), MAX_SENTENCES)
        sents = sentences[:n]
        chapters = gt.get("chapters", [])
        ref = _reference_boundaries(chapters, sents)
        if not ref:
            continue
        examples.append(
            {
                "video_id": video_id,
                "sentences": sents,
                "vecs": vecs[:n].astype(np.float64),
                "n": n,
                "n_segments": max(2, len(chapters)),
                "ref": ref,
            }
        )
    return examples


def _segment_loss(cumsum: np.ndarray, cumsum_sq: np.ndarray, start: int, end: int, lam: float) -> float:
    n = max(1, end - start)
    total = cumsum[end] - cumsum[start]
    total_sq = cumsum_sq[end] - cumsum_sq[start]
    sse = float(np.sum(total_sq - np.square(total) / n))
    return sse + (lam * (n ** 2))


def _best_split(
    cumsum: np.ndarray,
    cumsum_sq: np.ndarray,
    start: int,
    end: int,
    min_seg: int,
    lam: float,
) -> tuple[int, float] | None:
    if end - start < 2 * min_seg:
        return None
    parent = _segment_loss(cumsum, cumsum_sq, start, end, lam)
    best_split = -1
    best_gain = -float("inf")
    for split in range(start + min_seg, end - min_seg + 1):
        loss = _segment_loss(cumsum, cumsum_sq, start, split, lam)
        loss += _segment_loss(cumsum, cumsum_sq, split, end, lam)
        gain = parent - loss
        if gain > best_gain:
            best_gain = gain
            best_split = split
    if best_split < 0:
        return None
    return best_split, best_gain


def treeseg_objective(vecs: np.ndarray, n_segments: int, min_seg: int, lam: float) -> list[int]:
    n = len(vecs)
    if n < 2 or n_segments < 2:
        return []
    cumsum = np.zeros((n + 1, vecs.shape[1]), dtype=np.float64)
    cumsum[1:] = np.cumsum(vecs, axis=0)
    cumsum_sq = np.zeros((n + 1, vecs.shape[1]), dtype=np.float64)
    cumsum_sq[1:] = np.cumsum(np.square(vecs), axis=0)

    first = _best_split(cumsum, cumsum_sq, 0, n, min_seg, lam)
    if first is None:
        return []
    split, gain = first
    heap: list[tuple[float, int, int, int, int]] = []
    counter = 0
    heapq.heappush(heap, (-gain, counter, 0, n, split))
    counter += 1
    boundaries: list[int] = []

    while heap and len(boundaries) < n_segments - 1:
        neg_gain, _, start, end, split = heapq.heappop(heap)
        boundaries.append(split)
        for child_start, child_end in ((start, split), (split, end)):
            child = _best_split(cumsum, cumsum_sq, child_start, child_end, min_seg, lam)
            if child is None:
                continue
            child_split, child_gain = child
            heapq.heappush(heap, (-child_gain, counter, child_start, child_end, child_split))
            counter += 1
    return sorted(b for b in boundaries if 0 < b < n)


def _score_prediction(pred: list[int], ref: list[int], n_units: int) -> dict[str, float]:
    scores = official.evaluate(pred, ref, n_units).as_dict()
    for tolerance in (1, 2, 3, 5):
        _, _, f1 = official.tolerance_f1(pred, ref, n_units, tolerance=tolerance)
        scores[f"f1_t{tolerance}"] = float(f1)
    return scores


def run(args: argparse.Namespace) -> dict[str, Any]:
    examples = _load_examples(args.model)
    results: dict[str, dict[str, dict[str, float]]] = {}
    summary: dict[str, dict[str, float]] = {}
    for min_seg in args.min_lens:
        for lam in args.lambdas:
            method = f"treeseg_local_{args.model}_min{min_seg}_lam{lam:g}"
            rows = []
            results[method] = {}
            for ex in examples:
                pred = treeseg_objective(ex["vecs"], ex["n_segments"], min_seg, lam)
                metrics = _score_prediction(pred, ex["ref"], ex["n"])
                results[method][ex["video_id"]] = metrics
                rows.append(metrics)
            summary[method] = _mean(rows)
    best = min(summary.items(), key=lambda kv: (kv[1]["pk"], kv[1]["wd"]))
    return {
        "meta": {
            "n_videos": len(examples),
            "embedding_model": args.model,
            "max_sentences": MAX_SENTENCES,
            "min_lens": args.min_lens,
            "lambdas": args.lambdas,
            "source": "TreeSeg public objective adapted to local LECSEG embeddings",
            "tree_seg_repo": "https://github.com/AugmendTech/treeseg",
        },
        "summary": summary,
        "results": results,
        "best_method": {"name": best[0], **best[1]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="bge_large")
    parser.add_argument("--min-lens", type=int, nargs="+", default=[6, 8, 10, 12, 15])
    parser.add_argument("--lambdas", type=float, nargs="+", default=[0.0, 0.0001, 0.001, 0.01])
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_treeseg_same_dataset.json")
    args = parser.parse_args()

    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    best = report["best_method"]
    print(f"Wrote {args.output}")
    print(f"Best: {best['name']} Pk={best['pk']:.4f} WD={best['wd']:.4f} F1@2={best['f1_t2']:.4f}")


if __name__ == "__main__":
    main()
