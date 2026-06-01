"""Global candidate-subset selector for lecture topic segmentation.

This experiment starts from the high-recall candidate pool built by
``candidate_ranker.py`` and replaces greedy top-k selection with dynamic
programming over the whole segmentation. The goal is to optimize the global
boundary layout that Pk/WindowDiff care about, instead of only ranking
individual candidate gaps.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.candidate_ranker import (  # noqa: E402
    DEFAULT_MODELS,
    VideoExample,
    _evaluate_predictions,
    _load_or_build_examples,
    _normalise01,
)


@dataclass(frozen=True)
class DPParams:
    score_name: str
    frac: float
    min_seg: int
    len_weight: float
    count_bias: float
    max_seg_mult: float
    max_candidates: int

    @property
    def name(self) -> str:
        return (
            f"dp_{self.score_name}_frac{int(round(self.frac * 100))}"
            f"_min{self.min_seg}_lw{self.len_weight:g}"
            f"_cb{self.count_bias:g}_max{self.max_seg_mult:g}"
            f"_cand{self.max_candidates}"
        )


def _score_maps(ex: VideoExample) -> dict[str, np.ndarray]:
    """Return several deterministic score variants for candidates."""
    if ex.features.size == 0:
        empty = np.zeros(0, dtype=np.float64)
        return {"vote": empty}

    pos = ex.features[:, 0]
    edge_distance = ex.features[:, 1]
    vote = ex.features[:, 4]
    model_agreement = ex.features[:, 5]
    mean_source = ex.features[:, 6]
    max_source = ex.features[:, 7]
    isolation = ex.features[:, 8]
    prosody = ex.features[:, 9]
    shots = ex.features[:, 10]

    # Source columns contain per-model/per-signal values. Non-zero density is a
    # useful agreement cue that is less brittle than raw vote count.
    source = ex.features[:, 11:]
    density = (source > 0).mean(axis=1) if source.size else np.zeros_like(vote)
    source_std = source.std(axis=1) if source.size else np.zeros_like(vote)

    # Light position prior: avoid edge boundaries unless the candidate evidence
    # is strong. This is intentionally weak; lectures can start/end abruptly.
    center_prior = np.sqrt(np.clip(edge_distance * 2.0, 0.0, 1.0))
    early_penalty = np.where(pos < 0.04, 0.15, 0.0)
    late_penalty = np.where(pos > 0.96, 0.10, 0.0)

    variants = {
        "vote": 0.45 * vote + 0.25 * max_source + 0.15 * mean_source + 0.10 * model_agreement + 0.05 * density,
        "agreement": 0.30 * vote + 0.30 * model_agreement + 0.20 * density + 0.15 * max_source + 0.05 * mean_source,
        "transition": 0.30 * max_source + 0.20 * mean_source + 0.20 * vote + 0.10 * prosody + 0.10 * shots + 0.10 * density,
        "stable": 0.25 * vote + 0.25 * max_source + 0.20 * model_agreement + 0.15 * mean_source + 0.10 * density + 0.05 * isolation,
        "contrast": 0.35 * max_source + 0.20 * source_std + 0.20 * vote + 0.15 * density + 0.10 * model_agreement,
        "balanced": (
            0.24 * vote
            + 0.22 * max_source
            + 0.16 * mean_source
            + 0.16 * model_agreement
            + 0.10 * density
            + 0.05 * prosody
            + 0.03 * shots
            + 0.04 * center_prior
            - early_penalty
            - late_penalty
        ),
    }
    return {name: _normalise01(np.asarray(values, dtype=np.float64)) for name, values in variants.items()}


def _segment_penalty(length: int, expected: float, min_seg: int, max_seg: float, len_weight: float) -> float:
    if length < min_seg:
        return math.inf
    penalty = 0.0
    if max_seg > 0 and length > max_seg:
        over = (length - max_seg) / max(expected, 1.0)
        penalty += over * over * (len_weight + 0.25)
    if len_weight > 0:
        ratio = (length - expected) / max(expected, 1.0)
        penalty += len_weight * ratio * ratio
    return penalty


def _dp_select(ex: VideoExample, scores: np.ndarray, params: DPParams) -> list[int]:
    all_candidates = [int(b) for b in ex.candidates if 1 <= int(b) < ex.n_sentences]
    if not all_candidates or scores.size == 0:
        return []

    if params.max_candidates > 0 and len(all_candidates) > params.max_candidates:
        keep_idx = np.argsort(-scores)[: params.max_candidates]
        keep_idx = sorted(int(i) for i in keep_idx)
        candidates = [all_candidates[i] for i in keep_idx]
        scores = np.asarray([scores[i] for i in keep_idx], dtype=np.float64)
    else:
        candidates = all_candidates

    # Keep the candidate count close to the known/expected chapter count, matching
    # the official evaluation setting used elsewhere in this project.
    k = max(1, int(round(ex.target_boundaries * params.frac + params.count_bias)))
    k = min(k, len(candidates))

    expected = ex.n_sentences / max(1, k + 1)
    max_seg = expected * params.max_seg_mult if params.max_seg_mult > 0 else 0.0

    # Positions include start and end. Candidate rewards are paid when entering
    # a candidate node; the final end node has no reward.
    positions = [0] + candidates + [ex.n_sentences]
    rewards = np.concatenate([[0.0], np.asarray(scores, dtype=np.float64), [0.0]])
    n_pos = len(positions)

    neg_inf = -1e18
    dp = np.full((k + 2, n_pos), neg_inf, dtype=np.float64)
    back = np.full((k + 2, n_pos), -1, dtype=np.int32)
    dp[0, 0] = 0.0

    for used in range(0, k + 1):
        for j in range(1, n_pos):
            is_end = j == n_pos - 1
            if is_end and used != k:
                continue
            next_used = used if is_end else used
            if next_used > k:
                continue
            reward = 0.0 if is_end else rewards[j]
            best_score = neg_inf
            best_i = -1
            prev_used = used if is_end else used - 1
            if prev_used < 0:
                continue
            for i in range(0, j):
                prev = dp[prev_used, i]
                if prev <= neg_inf / 2:
                    continue
                length = positions[j] - positions[i]
                penalty = _segment_penalty(length, expected, params.min_seg, max_seg, params.len_weight)
                if not math.isfinite(penalty):
                    continue
                candidate_score = prev + reward - penalty
                if candidate_score > best_score:
                    best_score = candidate_score
                    best_i = i
            dp[used, j] = best_score
            back[used, j] = best_i

    end_idx = n_pos - 1
    if dp[k, end_idx] <= neg_inf / 2:
        return _greedy_fallback(ex, candidates, scores, k, params.min_seg)

    selected: list[int] = []
    used = k
    idx = end_idx
    while idx > 0 and used >= 0:
        prev = int(back[used, idx])
        if prev < 0:
            break
        if idx != end_idx:
            selected.append(positions[idx])
            used -= 1
        idx = prev
    return sorted(selected)


def _greedy_fallback(
    ex: VideoExample,
    candidates: list[int],
    scores: np.ndarray,
    k: int,
    min_seg: int,
) -> list[int]:
    accepted: list[int] = []
    for idx in np.argsort(-scores):
        b = candidates[int(idx)]
        trial = sorted(accepted + [b])
        points = [0, *trial, ex.n_sentences]
        if min(points[i + 1] - points[i] for i in range(len(points) - 1)) < min_seg:
            continue
        accepted.append(b)
        if len(accepted) >= k:
            break
    return sorted(accepted)


def _predict(examples: list[VideoExample], params: DPParams) -> dict[str, list[int]]:
    predictions: dict[str, list[int]] = {}
    for ex in examples:
        scores = _score_maps(ex)[params.score_name]
        predictions[ex.video_id] = _dp_select(ex, scores, params)
    return predictions


def _mean_pk_wd(metrics: dict[str, float]) -> tuple[float, float]:
    return float(metrics.get("pk", 1.0)), float(metrics.get("wd", 1.0))


def _grid(preset: str) -> list[DPParams]:
    params: list[DPParams] = []
    if preset == "micro":
        score_names = ("vote", "agreement", "stable", "balanced")
        fracs = (0.65, 0.70, 0.75)
        min_segs = (10, 11)
        len_weights = (0.0, 0.08)
        count_biases = (0.0,)
        max_seg_mults = (0.0, 3.0)
        max_candidates = (50, 80)
    elif preset == "fast":
        score_names = ("vote", "agreement", "stable", "balanced")
        fracs = (0.60, 0.65, 0.70, 0.75)
        min_segs = (8, 10, 11, 12)
        len_weights = (0.0, 0.05, 0.12)
        count_biases = (-1.0, 0.0)
        max_seg_mults = (0.0, 3.0)
        max_candidates = (80, 120)
    else:
        score_names = ("vote", "agreement", "transition", "stable", "contrast", "balanced")
        fracs = (0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.00)
        min_segs = (6, 8, 10, 11, 12, 14, 16)
        len_weights = (0.0, 0.03, 0.08, 0.15, 0.30)
        count_biases = (-1.0, 0.0, 1.0)
        max_seg_mults = (0.0, 2.0, 3.0, 4.0)
        max_candidates = (0, 120)

    for score_name in score_names:
        for frac in fracs:
            for min_seg in min_segs:
                for len_weight in len_weights:
                    for count_bias in count_biases:
                        for max_seg_mult in max_seg_mults:
                            for max_cand in max_candidates:
                                params.append(
                                    DPParams(
                                        score_name=score_name,
                                        frac=frac,
                                        min_seg=min_seg,
                                        len_weight=len_weight,
                                        count_bias=count_bias,
                                        max_seg_mult=max_seg_mult,
                                        max_candidates=max_cand,
                                    )
                                )
    return params


def _evaluate_param(examples: list[VideoExample], params: DPParams) -> dict[str, float]:
    return _evaluate_predictions(examples, _predict(examples, params))


def _global_search(examples: list[VideoExample], grid: list[DPParams]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for params in grid:
        metrics = _evaluate_param(examples, params)
        rows.append({"name": params.name, "params": asdict(params), **metrics})
    rows.sort(key=lambda row: (row.get("pk", 1.0), row.get("wd", 1.0)))
    return rows


def _leave_one_out_search(examples: list[VideoExample], grid: list[DPParams], top_n: int) -> dict[str, Any]:
    # Restrict nested search to the strongest global candidates. This keeps the
    # evaluation practical while still testing whether settings generalize across
    # held-out videos.
    global_rows = _global_search(examples, grid)
    shortlist = [
        DPParams(**row["params"])
        for row in global_rows[:top_n]
    ]

    predictions: dict[str, list[int]] = {}
    chosen: dict[str, str] = {}
    for holdout in examples:
        train = [ex for ex in examples if ex.video_id != holdout.video_id]
        best_params: DPParams | None = None
        best_key = (1.0, 1.0)
        for params in shortlist:
            metrics = _evaluate_param(train, params)
            key = _mean_pk_wd(metrics)
            if key < best_key:
                best_key = key
                best_params = params
        assert best_params is not None
        chosen[holdout.video_id] = best_params.name
        predictions[holdout.video_id] = _predict([holdout], best_params)[holdout.video_id]

    metrics = _evaluate_predictions(examples, predictions)
    return {
        "shortlist_size": top_n,
        "metrics": metrics,
        "chosen_params": chosen,
        "predictions": predictions,
        "global_shortlist": global_rows[:top_n],
    }


def run(
    data_dir: Path,
    models: tuple[str, ...],
    cache_path: Path | None,
    top_n: int,
    preset: str,
    skip_loo: bool,
    verbose: bool,
) -> dict[str, Any]:
    examples = _load_or_build_examples(data_dir, models, cache_path, verbose)
    if not examples:
        raise RuntimeError("No usable examples were loaded.")

    grid = _grid(preset)
    global_rows = _global_search(examples, grid)
    loo = None if skip_loo else _leave_one_out_search(examples, grid, top_n=top_n)

    result = {
        "meta": {
            "n_videos": len(examples),
            "models": list(models),
            "grid_size": len(grid),
            "top_n_for_loo": top_n,
            "preset": preset,
            "eval_gt": "youtube_chapters",
            "selection": "dynamic_programming_candidate_subset",
        },
        "best_global": global_rows[0],
        "top_global": global_rows[:25],
    }
    if loo is not None:
        result["leave_one_out"] = loo
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_dp_candidate_selector.json")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "candidate_ranker_examples.pkl")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--models", nargs="*", default=list(DEFAULT_MODELS))
    parser.add_argument("--top-n", type=int, default=80)
    parser.add_argument("--preset", choices=("micro", "fast", "full"), default="fast")
    parser.add_argument("--skip-loo", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    cache_path = None if args.no_cache else args.cache
    results = run(args.data_dir, tuple(args.models), cache_path, args.top_n, args.preset, args.skip_loo, args.verbose)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")

    best = results["best_global"]
    print(f"Wrote {args.output}")
    print(
        "Best global: {name} Pk={pk:.4f} WD={wd:.4f} BS={boundary_similarity:.4f} F1@2={f1_tol2:.4f}".format(
            **best
        )
    )
    if "leave_one_out" in results:
        loo_metrics = results["leave_one_out"]["metrics"]
        print(
            "LOO selected: Pk={pk:.4f} WD={wd:.4f} BS={boundary_similarity:.4f} F1@2={f1_tol2:.4f}".format(
                **loo_metrics
            )
        )


if __name__ == "__main__":
    main()
