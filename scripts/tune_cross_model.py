"""Focused tuning for the strongest cross-model segmentation family.

The goal is reproducible local model selection around the current best method,
not an open-ended search. It uses the same YouTube chapter ground truth,
sentence cap, and metrics as scripts/run_eval.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_eval as official  # noqa: E402


MAX_SENTENCES = 800


def _mean(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = sorted({key for row in rows for key, value in row.items() if isinstance(value, (int, float))})
    return {key: round(float(np.mean([row[key] for row in rows if key in row])), 4) for key in keys}


def _reference_boundaries(chapters: list[dict[str, Any]], sentences: list[dict[str, Any]]) -> list[int]:
    starts = np.array([float(s.get("start", 0.0)) for s in sentences], dtype=np.float32)
    n = len(sentences)
    boundaries = []
    for chapter in chapters[1:]:
        idx = int(np.searchsorted(starts, float(chapter["start_sec"]), side="left"))
        boundaries.append(max(1, min(idx, n - 1)))
    return sorted(set(boundaries))


def _load_examples(primary_model: str, verbose: bool) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for gt_file in sorted(official.GT_YOUTUBE.glob("*.json")):
        if gt_file.name.startswith("_"):
            continue
        vid = gt_file.stem
        gt = official._load_ground_truth(vid, use_youtube=True)
        sentences = official._load_sentences(vid)
        vecs = official._load_embeddings(vid, primary_model)
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
                "vid": vid,
                "sentences": sents,
                "vecs": vecs[:n],
                "n": n,
                "n_segments": max(2, len(chapters)),
                "ref": ref,
            }
        )
        if verbose:
            print(f"{vid}: n={n} segments={max(2, len(chapters))} ref={len(ref)}")
    return examples


def _score_prediction(pred: list[int], ref: list[int], n_units: int) -> dict[str, float]:
    scores = official.evaluate(pred, ref, n_units).as_dict()
    for tolerance in (1, 2, 3, 5):
        _, _, f1 = official.tolerance_f1(pred, ref, n_units, tolerance=tolerance)
        scores[f"f1_t{tolerance}"] = round(float(f1), 4)
    return scores


def _evaluate_grid(
    examples: list[dict[str, Any]],
    secondary_model: str,
    windows: list[int],
    fracs: list[float],
    min_lens: list[int],
    verbose: bool,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, dict[str, float]]]]:
    raw_cache: dict[tuple[str, int, float], list[int]] = {}
    per_video: dict[str, dict[str, dict[str, float]]] = {}
    summary: dict[str, dict[str, float]] = {}

    for window in windows:
        for frac in fracs:
            for ex in examples:
                key = (ex["vid"], window, frac)
                raw_cache[key] = official.cross_model_conservative(
                    ex["vecs"],
                    ex["vid"],
                    ex["n_segments"],
                    secondary_model=secondary_model,
                    window=window,
                    frac=frac,
                )

            for min_len in min_lens:
                method = f"cross_{secondary_model}_w{window}_frac{int(round(frac * 100))}_minlen{min_len}"
                rows = []
                per_video[method] = {}
                for ex in examples:
                    raw = raw_cache[(ex["vid"], window, frac)]
                    pred = official.min_seg_filter(raw, ex["n"], min_seg=min_len)
                    scores = _score_prediction(pred, ex["ref"], ex["n"])
                    per_video[method][ex["vid"]] = scores
                    rows.append(scores)
                summary[method] = _mean(rows)
                if verbose:
                    s = summary[method]
                    print(f"{method}: Pk={s['pk']:.4f} WD={s['wd']:.4f} F1@2={s['f1_t2']:.4f}")

    return summary, per_video


def run(args: argparse.Namespace) -> dict[str, Any]:
    examples = _load_examples(args.primary_model, args.verbose)
    if not examples:
        raise RuntimeError("No examples loaded.")
    summary, per_video = _evaluate_grid(
        examples=examples,
        secondary_model=args.secondary_model,
        windows=args.windows,
        fracs=args.fracs,
        min_lens=args.min_lens,
        verbose=args.verbose,
    )
    ordered = sorted(summary.items(), key=lambda kv: (kv[1]["pk"], kv[1]["wd"]))
    return {
        "meta": {
            "primary_model": args.primary_model,
            "secondary_model": args.secondary_model,
            "n_videos": len(examples),
            "gt_mode": "youtube_gt",
            "max_sentences": MAX_SENTENCES,
            "windows": args.windows,
            "fracs": args.fracs,
            "min_lens": args.min_lens,
        },
        "summary": summary,
        "results": per_video,
        "best_method": {"name": ordered[0][0], **ordered[0][1]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-model", default="bge_large")
    parser.add_argument("--secondary-model", default="e5large")
    parser.add_argument("--windows", type=int, nargs="+", default=[7, 9, 11, 13, 15])
    parser.add_argument("--fracs", type=float, nargs="+", default=[0.60, 0.64, 0.66, 0.68, 0.70, 0.72, 0.74, 0.76])
    parser.add_argument("--min-lens", type=int, nargs="+", default=[8, 9, 10, 11, 12, 13, 14, 15])
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_cross_model_tuning.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    best = report["best_method"]
    print(f"Wrote {args.output}")
    print(f"Best: {best['name']} Pk={best['pk']:.4f} WD={best['wd']:.4f} F1@2={best['f1_t2']:.4f}")


if __name__ == "__main__":
    main()
