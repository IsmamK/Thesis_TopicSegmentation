"""Boundary-time alignment sweep for official segmentation methods."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_eval as official  # noqa: E402


MAX_SENTENCES = 800


def _reference_boundaries(chapters: list[dict[str, Any]], sentences: list[dict[str, Any]], mode: str) -> list[int]:
    starts = np.array([float(s.get("start", 0.0)) for s in sentences], dtype=np.float64)
    ends = np.array([float(s.get("end", s.get("start", 0.0))) for s in sentences], dtype=np.float64)
    centers = (starts + ends) / 2.0
    n = len(sentences)
    bounds: list[int] = []
    for chapter in chapters[1:]:
        t = float(chapter["start_sec"])
        if mode == "start_left":
            idx = int(np.searchsorted(starts, t, side="left"))
        elif mode == "start_right":
            idx = int(np.searchsorted(starts, t, side="right"))
        elif mode == "start_nearest":
            idx = int(np.argmin(np.abs(starts - t)))
        elif mode == "center_left":
            idx = int(np.searchsorted(centers, t, side="left"))
        elif mode == "center_nearest":
            idx = int(np.argmin(np.abs(centers - t)))
        elif mode == "contains_before":
            hits = np.where((starts <= t) & (t <= ends))[0]
            idx = int(hits[0]) if len(hits) else int(np.searchsorted(starts, t, side="left"))
        elif mode == "contains_after":
            hits = np.where((starts <= t) & (t <= ends))[0]
            idx = int(hits[0] + 1) if len(hits) else int(np.searchsorted(starts, t, side="left"))
        else:
            raise ValueError(mode)
        bounds.append(max(1, min(idx, n - 1)))
    return sorted(set(bounds))


def _load_examples(primary_model: str, gt_mode: str, align_mode: str) -> list[dict[str, Any]]:
    gt_dir = official.GT_YOUTUBE if gt_mode == "youtube" else official.GT_HIER
    examples = []
    for gt_file in sorted(gt_dir.glob("*.json")):
        if gt_file.name.startswith("_"):
            continue
        vid = gt_file.stem
        gt = official._load_ground_truth(vid, use_youtube=(gt_mode == "youtube"), draft_ok=True)
        sentences = official._load_sentences(vid)
        vecs = official._load_embeddings(vid, primary_model)
        if gt is None or sentences is None or vecs is None:
            continue
        n = min(len(sentences), len(vecs), MAX_SENTENCES)
        sents = sentences[:n]
        chapters = gt.get("chapters", [])
        ref = _reference_boundaries(chapters, sents, align_mode)
        if not ref:
            continue
        examples.append({"vid": vid, "sentences": sents, "vecs": vecs[:n], "n": n, "n_segments": max(2, len(chapters)), "ref": ref})
    return examples


def _score(pred: list[int], ref: list[int], n: int) -> dict[str, float]:
    scores = official.evaluate(pred, ref, n).as_dict()
    for t in (1, 2, 3, 5):
        _, _, f1 = official.tolerance_f1(pred, ref, n, tolerance=t)
        scores[f"f1_t{t}"] = round(float(f1), 4)
    return scores


def _mean(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = sorted({k for row in rows for k, v in row.items() if isinstance(v, (int, float))})
    return {k: round(float(np.mean([row[k] for row in rows if k in row])), 4) for k in keys}


def run(args: argparse.Namespace) -> dict[str, Any]:
    summary: dict[str, dict[str, float]] = {}
    results: dict[str, dict[str, dict[str, float]]] = {}
    for align in args.align_modes:
        examples = _load_examples(args.primary_model, args.gt_mode, align)
        for method in args.methods:
            method_name = f"{method}__align_{align}"
            rows = []
            results[method_name] = {}
            for ex in examples:
                raw = official._run_method(method, ex["sentences"], ex["vecs"], ex["n_segments"], None, None, 4, ex["vid"])
                scores = _score(raw, ex["ref"], ex["n"])
                results[method_name][ex["vid"]] = scores
                rows.append(scores)
            summary[method_name] = _mean(rows)
    ordered = sorted(summary.items(), key=lambda kv: (kv[1]["pk"], kv[1]["wd"]))
    return {
        "meta": {
            "gt_mode": args.gt_mode,
            "primary_model": args.primary_model,
            "align_modes": args.align_modes,
            "methods": args.methods,
        },
        "summary": summary,
        "results": results,
        "best_method": {"name": ordered[0][0], **ordered[0][1]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-model", default="bge_large")
    parser.add_argument("--gt-mode", choices=("youtube", "hier"), default="youtube")
    parser.add_argument("--methods", nargs="+", default=["cross_e5_frac70_minlen11"])
    parser.add_argument(
        "--align-modes",
        nargs="+",
        default=["start_left", "start_right", "start_nearest", "center_left", "center_nearest", "contains_before", "contains_after"],
    )
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_alignment_sweep.json")
    args = parser.parse_args()
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    best = report["best_method"]
    print(f"Wrote {args.output}")
    print(f"Best: {best['name']} Pk={best['pk']:.4f} WD={best['wd']:.4f} BS={best['boundary_similarity']:.4f} F1@2={best['f1_t2']:.4f}")


if __name__ == "__main__":
    main()
