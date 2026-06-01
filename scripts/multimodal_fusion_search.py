"""Focused multimodal fusion search for lecture topic segmentation.

This script tests the strongest remaining multimodal hypothesis: keep the
current best cross-text-embedding candidate family, then add aligned OCR
slide-text change, prosody, and shot-change scores before selecting boundaries.
It uses the same 30-video YouTube chapter evaluation setup as the official
result unless another ground-truth mode is explicitly requested.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_eval as official  # noqa: E402
from lecseg.features.text_embeddings import smooth_embeddings  # noqa: E402
from lecseg.models.divisive import divisive_seg  # noqa: E402


MAX_SENTENCES = 800
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_'-]*")


def _normalise01(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return x
    lo = float(np.nanmin(x))
    hi = float(np.nanmax(x))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text) if len(t) > 2}


def _reference_boundaries(chapters: list[dict[str, Any]], sentences: list[dict[str, Any]], mode: str) -> list[int]:
    starts = np.array([float(s.get("start", 0.0)) for s in sentences], dtype=np.float64)
    ends = np.array([float(s.get("end", s.get("start", 0.0))) for s in sentences], dtype=np.float64)
    centers = (starts + ends) / 2.0
    n = len(sentences)
    boundaries: list[int] = []
    for chapter in chapters[1:]:
        t = float(chapter["start_sec"])
        if mode == "start_left":
            idx = int(np.searchsorted(starts, t, side="left"))
        elif mode == "start_nearest":
            idx = int(np.argmin(np.abs(starts - t)))
        elif mode == "center_nearest":
            idx = int(np.argmin(np.abs(centers - t)))
        elif mode == "contains":
            hits = np.where((starts <= t) & (t <= ends))[0]
            idx = int(hits[0] + 1) if len(hits) else int(np.searchsorted(starts, t, side="left"))
        else:
            raise ValueError(f"unknown alignment mode: {mode}")
        boundaries.append(max(1, min(idx, n - 1)))
    return sorted(set(boundaries))


def _load_examples(primary_model: str, gt_mode: str, align_mode: str, verbose: bool) -> list[dict[str, Any]]:
    gt_dir = official.GT_YOUTUBE if gt_mode == "youtube" else official.GT_HIER
    examples: list[dict[str, Any]] = []
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
            print(f"{vid}: n={n} seg={max(2, len(chapters))} ref={len(ref)}")
    return examples


def _cross_scores(ex: dict[str, Any], secondary_model: str, window: int, frac: float, over_mult: int) -> dict[int, float]:
    n = ex["n"]
    k = max(2, round(ex["n_segments"] * frac))
    over_k = min(n - 1, k * over_mult + 2)
    v1 = smooth_embeddings(ex["vecs"][:n], window=window)
    v2_raw = official.load_embeddings_model(ex["vid"], secondary_model)
    if v2_raw is None:
        _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
        return {int(b): float(s) for b, s in s1.items()}
    n2 = min(n, len(v2_raw))
    v2 = smooth_embeddings(v2_raw[:n2], window=window)
    _, s1 = divisive_seg(v1[:n2], n_segments=min(over_k, n2 - 1), return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=min(over_k, n2 - 1), return_scores=True)
    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    all_pos = sorted(set(s1) | set(s2))
    return {int(p): float((s1.get(p, 0.0) / max1 + s2.get(p, 0.0) / max2) / 2.0) for p in all_pos}


def _ocr_gap_scores(ex: dict[str, Any]) -> np.ndarray:
    path = ROOT / "data" / "ocr" / f"{ex['vid']}_ocr.json"
    n = ex["n"]
    if not path.exists():
        return np.zeros(max(0, n - 1), dtype=np.float64)
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return np.zeros(max(0, n - 1), dtype=np.float64)
    if not isinstance(rows, list) or len(rows) < 3:
        return np.zeros(max(0, n - 1), dtype=np.float64)

    duration = max(float(s.get("end", s.get("start", 0.0))) for s in ex["sentences"])
    starts = np.array([float(s.get("start", 0.0)) for s in ex["sentences"]], dtype=np.float64)
    scores = np.zeros(max(0, n - 1), dtype=np.float64)

    prev_tokens: set[str] | None = None
    prev_text = ""
    for i, row in enumerate(rows):
        text = str(row.get("slide_text", "") if isinstance(row, dict) else "")
        toks = _tokens(text)
        if prev_tokens is not None:
            union = toks | prev_tokens
            inter = toks & prev_tokens
            jaccard_dist = 1.0 - (len(inter) / max(1, len(union)))
            changed = 0.0 if text.strip().lower() == prev_text.strip().lower() else 1.0
            conf = float(row.get("confidence", 0.5) if isinstance(row, dict) else 0.5)
            score = (0.70 * jaccard_dist + 0.30 * changed) * max(0.1, min(conf, 1.0))
            t = (i / max(1, len(rows) - 1)) * duration
            idx = int(np.searchsorted(starts, t, side="left"))
            if 1 <= idx < n:
                scores[idx - 1] = max(scores[idx - 1], score)
                # Give near-frame credit; sampled OCR frames do not have exact timestamps.
                if idx - 2 >= 0:
                    scores[idx - 2] = max(scores[idx - 2], score * 0.5)
                if idx < n - 1:
                    scores[idx] = max(scores[idx], score * 0.5)
        prev_tokens = toks
        prev_text = text
    return _normalise01(scores)


def _score_array_from_dict(score_map: dict[int, float], n: int) -> np.ndarray:
    arr = np.zeros(max(0, n - 1), dtype=np.float64)
    for b, score in score_map.items():
        if 1 <= b < n:
            arr[b - 1] = max(arr[b - 1], float(score))
    return _normalise01(arr)


def _select_from_scores(scores: np.ndarray, n_segments: int, frac: float, min_len: int, nms: int) -> list[int]:
    n = len(scores) + 1
    k = max(1, round(n_segments * frac))
    ranked = list(np.argsort(-scores) + 1)
    selected: list[int] = []
    for b in ranked:
        b = int(b)
        if any(abs(b - old) < nms for old in selected):
            continue
        trial = sorted(selected + [b])
        pts = [0, *trial, n]
        if min(pts[i + 1] - pts[i] for i in range(len(pts) - 1)) < min_len:
            continue
        selected.append(b)
        if len(selected) >= k:
            break
    return sorted(selected)


def _mean(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = sorted({k for row in rows for k, v in row.items() if isinstance(v, (int, float))})
    return {k: round(float(np.mean([row[k] for row in rows if k in row])), 4) for k in keys}


def _eval_prediction(pred: list[int], ref: list[int], n: int) -> dict[str, float]:
    scores = official.evaluate(pred, ref, n).as_dict()
    for tolerance in (1, 2, 3, 5):
        _, _, f1 = official.tolerance_f1(pred, ref, n, tolerance=tolerance)
        scores[f"f1_t{tolerance}"] = round(float(f1), 4)
    return scores


def run(args: argparse.Namespace) -> dict[str, Any]:
    examples = _load_examples(args.primary_model, args.gt_mode, args.align_mode, args.verbose)
    if not examples:
        raise RuntimeError("No examples loaded.")

    base_cache: dict[tuple[str, int, float, int], dict[int, float]] = {}
    ocr_cache = {ex["vid"]: _ocr_gap_scores(ex) for ex in examples}
    pros_cache = {ex["vid"]: official._load_prosody(ex["vid"], ex["n"]) for ex in examples}
    shot_cache = {ex["vid"]: official._load_shot_gap_scores(ex["vid"], ex["n"], ex["sentences"]) for ex in examples}

    summary: dict[str, dict[str, float]] = {}
    per_video: dict[str, dict[str, dict[str, float]]] = {}

    for window in args.windows:
        for frac in args.fracs:
            for over_mult in args.over_mults:
                for ex in examples:
                    key = (ex["vid"], window, frac, over_mult)
                    base_cache[key] = _cross_scores(ex, args.secondary_model, window, frac, over_mult)

                for w_ocr in args.ocr_weights:
                    for w_pros in args.prosody_weights:
                        for w_shot in args.shot_weights:
                            for min_len in args.min_lens:
                                for nms in args.nms:
                                    method = (
                                        f"mm_w{window}_frac{int(frac*100)}_over{over_mult}"
                                        f"_ocr{int(w_ocr*100)}_pros{int(w_pros*100)}_shot{int(w_shot*100)}"
                                        f"_min{min_len}_nms{nms}"
                                    )
                                    rows = []
                                    per_video[method] = {}
                                    for ex in examples:
                                        base_map = base_cache[(ex["vid"], window, frac, over_mult)]
                                        base_arr = _score_array_from_dict(base_map, ex["n"])
                                        fused = base_arr.copy()
                                        weight_sum = 1.0
                                        if w_ocr:
                                            fused += w_ocr * ocr_cache[ex["vid"]]
                                            weight_sum += w_ocr
                                        pros = pros_cache[ex["vid"]]
                                        if w_pros and pros is not None:
                                            fused += w_pros * _normalise01(pros[: len(fused)])
                                            weight_sum += w_pros
                                        shot = shot_cache[ex["vid"]]
                                        if w_shot and shot is not None:
                                            fused += w_shot * _normalise01(shot[: len(fused)])
                                            weight_sum += w_shot
                                        fused = _normalise01(fused / weight_sum)
                                        if args.candidate_only:
                                            mask = np.zeros_like(fused)
                                            for b in base_map:
                                                if 1 <= b < ex["n"]:
                                                    mask[b - 1] = 1.0
                                            fused = fused * mask
                                        pred = _select_from_scores(fused, ex["n_segments"], frac, min_len, nms)
                                        scores = _eval_prediction(pred, ex["ref"], ex["n"])
                                        per_video[method][ex["vid"]] = scores
                                        rows.append(scores)
                                    summary[method] = _mean(rows)
                                    if args.verbose:
                                        s = summary[method]
                                        print(f"{method}: Pk={s['pk']:.4f} WD={s['wd']:.4f} F1@2={s['f1_t2']:.4f}")

    ordered = sorted(summary.items(), key=lambda kv: (kv[1]["pk"], kv[1]["wd"]))
    return {
        "meta": {
            "n_videos": len(examples),
            "gt_mode": args.gt_mode,
            "align_mode": args.align_mode,
            "primary_model": args.primary_model,
            "secondary_model": args.secondary_model,
        },
        "summary": summary,
        "results": per_video,
        "best_method": {"name": ordered[0][0], **ordered[0][1]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-model", default="bge_large")
    parser.add_argument("--secondary-model", default="e5large")
    parser.add_argument("--gt-mode", choices=("youtube", "hier"), default="youtube")
    parser.add_argument("--align-mode", choices=("start_left", "start_nearest", "center_nearest", "contains"), default="start_left")
    parser.add_argument("--windows", type=int, nargs="+", default=[9, 11])
    parser.add_argument("--fracs", type=float, nargs="+", default=[0.65, 0.70, 0.75])
    parser.add_argument("--over-mults", type=int, nargs="+", default=[4, 6])
    parser.add_argument("--ocr-weights", type=float, nargs="+", default=[0.0, 0.15, 0.30, 0.50])
    parser.add_argument("--prosody-weights", type=float, nargs="+", default=[0.0, 0.10])
    parser.add_argument("--shot-weights", type=float, nargs="+", default=[0.0, 0.10])
    parser.add_argument("--min-lens", type=int, nargs="+", default=[10, 11, 12, 15])
    parser.add_argument("--nms", type=int, nargs="+", default=[1, 5, 10])
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_multimodal_fusion_search.json")
    parser.add_argument("--candidate-only", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    best = report["best_method"]
    print(f"Wrote {args.output}")
    print(f"Best: {best['name']} Pk={best['pk']:.4f} WD={best['wd']:.4f} BS={best['boundary_similarity']:.4f} F1@2={best['f1_t2']:.4f}")


if __name__ == "__main__":
    main()
