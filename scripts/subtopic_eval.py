"""Evaluate segmentation methods against reviewed subtopic boundaries."""

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


def _boundaries(items: list[dict[str, Any]], sentences: list[dict[str, Any]]) -> list[int]:
    starts = np.array([float(s.get("start", 0.0)) for s in sentences], dtype=np.float64)
    n = len(sentences)
    out = []
    for item in items[1:]:
        idx = int(np.searchsorted(starts, float(item["start_sec"]), side="left"))
        out.append(max(1, min(idx, n - 1)))
    return sorted(set(out))


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
    for method in args.methods:
        results[method] = {}
        rows = []
        for gt_file in sorted(official.GT_HIER.glob("*.json")):
            if gt_file.name.startswith("_"):
                continue
            vid = gt_file.stem
            gt = official._load_ground_truth(vid, use_youtube=False, draft_ok=args.draft_ok)
            sents = official._load_sentences(vid)
            vecs = official._load_embeddings(vid, args.model)
            if gt is None or sents is None or vecs is None:
                continue
            if not gt.get("subtopics"):
                continue
            n = min(len(sents), len(vecs), MAX_SENTENCES)
            sents_use = sents[:n]
            vecs_use = vecs[:n]
            ref = _boundaries(gt["subtopics"], sents_use)
            if not ref:
                continue
            n_segments = max(2, len(gt["subtopics"]))
            pros = official._load_prosody(vid, n)
            shots = official._load_shot_gap_scores(vid, n, sents_use)
            pred = official._run_method(method, sents_use, vecs_use, n_segments, pros, shots, 4, vid)
            scores = _score(pred, ref, n)
            results[method][vid] = scores
            rows.append(scores)
        summary[method] = _mean(rows)
    ordered = sorted(summary.items(), key=lambda kv: (kv[1]["pk"], kv[1]["wd"]))
    return {
        "meta": {"model": args.model, "draft_ok": args.draft_ok, "target": "gt_hier_subtopics"},
        "summary": summary,
        "results": results,
        "best_method": {"name": ordered[0][0], **ordered[0][1]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="bge_large")
    parser.add_argument("--draft-ok", action="store_true")
    parser.add_argument("--methods", nargs="+", default=["cross_e5_frac70_minlen11", "cross_e5_frac70_minlen10", "divisive", "two_stage_prosody", "hierarchical_prosody"])
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_subtopic_targeted.json")
    args = parser.parse_args()
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    best = report["best_method"]
    print(f"Wrote {args.output}")
    print(f"Best: {best['name']} Pk={best['pk']:.4f} WD={best['wd']:.4f} BS={best['boundary_similarity']:.4f} F1@2={best['f1_t2']:.4f}")


if __name__ == "__main__":
    main()
