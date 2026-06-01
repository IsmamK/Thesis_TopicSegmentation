"""Candidate-ranker segmentation experiment.

This script is intentionally standalone: it does not replace the official
evaluation pipeline. It tests whether a supervised boundary ranker can improve
over the current cross-model unsupervised segmenters while keeping the same
YouTube chapter evaluation setup.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lecseg.features.text_embeddings import smooth_embeddings  # noqa: E402
from lecseg.metrics import evaluate, tolerance_f1  # noqa: E402
from lecseg.models.divisive import divisive_seg  # noqa: E402


MAX_SENTENCES = 800
DEFAULT_MODELS = ("bge_large", "e5large", "bge", "e5", "mpnet", "stella")
CACHE_VERSION = 2


@dataclass
class VideoExample:
    video_id: str
    n_sentences: int
    target_boundaries: int
    reference: list[int]
    candidates: list[int]
    features: np.ndarray
    labels_tol2: np.ndarray
    labels_tol3: np.ndarray


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalise01(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return values
    lo = float(np.nanmin(values))
    hi = float(np.nanmax(values))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(values, dtype=np.float64)
    return (values - lo) / (hi - lo)


def _l2_normalise(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


def _load_manifest(data_dir: Path) -> list[str]:
    manifest = data_dir / "manifest.jsonl"
    ids: list[str] = []
    with manifest.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            ids.append(json.loads(line)["id"])
    return ids


def _load_sentences(data_dir: Path, video_id: str) -> list[dict[str, Any]]:
    obj = _read_json(data_dir / "sentences" / video_id / "sentences.json")
    return obj["sentences"]


def _boundary_seconds_to_sentence_indices(
    boundaries_sec: list[float],
    sentences: list[dict[str, Any]],
    n_sentences: int,
) -> list[int]:
    starts = np.array([float(s.get("start", 0.0)) for s in sentences[:n_sentences]])
    ends = np.array([float(s.get("end", s.get("start", 0.0))) for s in sentences[:n_sentences]])
    centers = (starts + ends) / 2.0
    refs: list[int] = []
    for sec in boundaries_sec:
        sec_f = float(sec)
        if sec_f <= 0:
            continue
        idx = int(np.searchsorted(centers, sec_f, side="left"))
        idx = max(1, min(idx, n_sentences - 1))
        refs.append(idx)
    return sorted(set(refs))


def _load_reference(data_dir: Path, video_id: str, sentences: list[dict[str, Any]], n_sentences: int) -> list[int]:
    gt = _read_json(data_dir / "gt" / f"{video_id}.json")
    return _boundary_seconds_to_sentence_indices(gt.get("boundaries_sec", []), sentences, n_sentences)


def _load_embeddings(data_dir: Path, video_id: str, models: tuple[str, ...]) -> dict[str, np.ndarray]:
    loaded: dict[str, np.ndarray] = {}
    for model in models:
        path = data_dir / "embeddings" / model / video_id / "embeddings.npy"
        if path.exists():
            loaded[model] = np.load(path)
    return loaded


def _adjacent_gap_scores(embeddings: np.ndarray) -> np.ndarray:
    if len(embeddings) < 2:
        return np.zeros(0, dtype=np.float64)
    normed = _l2_normalise(embeddings)
    return _normalise01(1.0 - np.sum(normed[:-1] * normed[1:], axis=1))


def _window_gap_scores(embeddings: np.ndarray, window: int) -> np.ndarray:
    n = len(embeddings)
    if n < 2:
        return np.zeros(0, dtype=np.float64)
    normed = _l2_normalise(embeddings)
    scores = np.zeros(n - 1, dtype=np.float64)
    for boundary in range(1, n):
        left_start = max(0, boundary - window)
        right_end = min(n, boundary + window)
        left = normed[left_start:boundary]
        right = normed[boundary:right_end]
        if len(left) == 0 or len(right) == 0:
            continue
        l_vec = left.mean(axis=0)
        r_vec = right.mean(axis=0)
        denom = max(float(np.linalg.norm(l_vec) * np.linalg.norm(r_vec)), 1e-12)
        scores[boundary - 1] = 1.0 - float(np.dot(l_vec, r_vec) / denom)
    return _normalise01(scores)


def _top_gap_candidates(score: np.ndarray, limit: int) -> list[int]:
    if score.size == 0:
        return []
    limit = min(limit, score.size)
    order = np.argsort(-score)[:limit]
    return [int(i + 1) for i in order if i + 1 > 0]


def _load_prosody_scores(data_dir: Path, video_id: str, n_sentences: int) -> np.ndarray:
    path = data_dir / "prosody" / video_id / "prosody.json"
    if not path.exists():
        return np.zeros(max(0, n_sentences - 1), dtype=np.float64)
    obj = _read_json(path)
    rows = obj.get("sentences", obj if isinstance(obj, list) else [])
    pause = np.zeros(max(0, n_sentences - 1), dtype=np.float64)
    for i, row in enumerate(rows[: max(0, n_sentences - 1)]):
        if isinstance(row, dict):
            pause[i] = float(row.get("pause_after", row.get("pause", 0.0)) or 0.0)
    return _normalise01(pause)


def _load_shot_scores(data_dir: Path, video_id: str, sentences: list[dict[str, Any]], n_sentences: int) -> np.ndarray:
    path = data_dir / "shots" / video_id / "shots.json"
    if not path.exists():
        return np.zeros(max(0, n_sentences - 1), dtype=np.float64)
    obj = _read_json(path)
    shots = obj.get("shots", obj.get("boundaries", obj if isinstance(obj, list) else []))
    starts = np.array([float(s.get("start", 0.0)) for s in sentences[:n_sentences]])
    scores = np.zeros(max(0, n_sentences - 1), dtype=np.float64)
    for shot in shots:
        if isinstance(shot, dict):
            sec = float(shot.get("timestamp_s", shot.get("time", shot.get("start", 0.0))) or 0.0)
            prob = float(shot.get("probability", shot.get("score", 1.0)) or 1.0)
        else:
            sec = float(shot)
            prob = 1.0
        idx = int(np.searchsorted(starts, sec, side="left"))
        if 1 <= idx < n_sentences:
            scores[idx - 1] = max(scores[idx - 1], prob)
    return _normalise01(scores)


def _collect_candidates_and_scores(
    embeddings_by_model: dict[str, np.ndarray],
    target_boundaries: int,
) -> tuple[list[int], dict[str, dict[int, float]], Counter[int], dict[int, set[str]]]:
    candidate_votes: Counter[int] = Counter()
    candidate_models: dict[int, set[str]] = defaultdict(set)
    source_scores: dict[str, dict[int, float]] = {}

    for model, emb in embeddings_by_model.items():
        n = len(emb)
        if n < 3:
            continue

        for window in (1, 5, 9, 13):
            matrix = emb if window == 1 else smooth_embeddings(emb, window=window)
            over_boundaries = min(n - 1, max(target_boundaries * 6, target_boundaries + 20, 30))
            if over_boundaries < 1:
                continue
            try:
                pred = divisive_seg(matrix, n_segments=over_boundaries + 1)
            except Exception:
                pred = []
            key = f"{model}_div_w{window}"
            source_scores[key] = {}
            if pred:
                for rank, boundary in enumerate(pred):
                    b = int(boundary)
                    if 1 <= b < n:
                        score = 1.0 - (rank / max(1, len(pred)))
                        candidate_votes[b] += 2
                        candidate_models[b].add(model)
                        source_scores[key][b] = max(source_scores[key].get(b, 0.0), score)

        for gap_name, gap in {
            "adj": _adjacent_gap_scores(emb),
            "win3": _window_gap_scores(emb, 3),
            "win5": _window_gap_scores(emb, 5),
            "win9": _window_gap_scores(emb, 9),
        }.items():
            key = f"{model}_{gap_name}"
            source_scores[key] = {}
            for b in _top_gap_candidates(gap, max(target_boundaries * 8, 50)):
                score = float(gap[b - 1])
                candidate_votes[b] += 1
                candidate_models[b].add(model)
                source_scores[key][b] = max(source_scores[key].get(b, 0.0), score)

    candidates = sorted(candidate_votes)
    return candidates, source_scores, candidate_votes, candidate_models


def _nearest_distance(boundary: int, others: list[int], n_sentences: int) -> float:
    distances = [abs(boundary - other) for other in others if other != boundary]
    if not distances:
        return 1.0
    return min(distances) / max(1, n_sentences)


def _build_features(
    candidates: list[int],
    n_sentences: int,
    target_boundaries: int,
    source_scores: dict[str, dict[int, float]],
    votes: Counter[int],
    models_for_candidate: dict[int, set[str]],
    prosody: np.ndarray,
    shots: np.ndarray,
) -> np.ndarray:
    keys = _feature_source_keys(DEFAULT_MODELS)
    rows: list[list[float]] = []
    max_vote = max(votes.values(), default=1)
    for b in candidates:
        source_values = [float(source_scores.get(key, {}).get(b, 0.0)) for key in keys]
        nonzero = [v for v in source_values if v > 0]
        gap_index = b - 1
        row = [
            b / max(1, n_sentences),
            min(b, n_sentences - b) / max(1, n_sentences),
            math.log1p(n_sentences),
            target_boundaries / max(1, n_sentences),
            votes[b] / max(1, max_vote),
            len(models_for_candidate.get(b, set())) / max(1, len(DEFAULT_MODELS)),
            float(np.mean(nonzero)) if nonzero else 0.0,
            float(np.max(nonzero)) if nonzero else 0.0,
            _nearest_distance(b, candidates, n_sentences),
            float(prosody[gap_index]) if 0 <= gap_index < len(prosody) else 0.0,
            float(shots[gap_index]) if 0 <= gap_index < len(shots) else 0.0,
        ]
        row.extend(source_values)
        rows.append(row)
    return np.asarray(rows, dtype=np.float64)


def _feature_source_keys(models: tuple[str, ...]) -> list[str]:
    keys: list[str] = []
    for model in models:
        keys.extend([f"{model}_div_w{window}" for window in (1, 5, 9, 13)])
        keys.extend([f"{model}_{gap_name}" for gap_name in ("adj", "win3", "win5", "win9")])
    return sorted(keys)


def _labels(candidates: list[int], reference: list[int], tolerance: int) -> np.ndarray:
    labels = []
    for b in candidates:
        labels.append(any(abs(b - ref) <= tolerance for ref in reference))
    return np.asarray(labels, dtype=np.int32)


def _make_example(data_dir: Path, video_id: str, models: tuple[str, ...]) -> VideoExample | None:
    sentences = _load_sentences(data_dir, video_id)
    embeddings_by_model = _load_embeddings(data_dir, video_id, models)
    if not embeddings_by_model:
        return None
    n = min([len(sentences), MAX_SENTENCES, *[len(v) for v in embeddings_by_model.values()]])
    if n < 5:
        return None
    sentences = sentences[:n]
    embeddings_by_model = {model: emb[:n] for model, emb in embeddings_by_model.items()}
    reference = _load_reference(data_dir, video_id, sentences, n)
    reference = [b for b in reference if 1 <= b < n]
    if not reference:
        return None
    target = len(reference)
    candidates, source_scores, votes, candidate_models = _collect_candidates_and_scores(embeddings_by_model, target)
    candidates = [b for b in candidates if 1 <= b < n]
    prosody = _load_prosody_scores(data_dir, video_id, n)
    shots = _load_shot_scores(data_dir, video_id, sentences, n)
    features = _build_features(candidates, n, target, source_scores, votes, candidate_models, prosody, shots)
    return VideoExample(
        video_id=video_id,
        n_sentences=n,
        target_boundaries=target,
        reference=reference,
        candidates=candidates,
        features=features,
        labels_tol2=_labels(candidates, reference, 2),
        labels_tol3=_labels(candidates, reference, 3),
    )


def _select_boundaries(
    candidates: list[int],
    scores: np.ndarray,
    n_sentences: int,
    k: int,
    min_seg: int,
    nms_window: int,
) -> list[int]:
    if not candidates or k <= 0:
        return []
    order = np.argsort(-scores)
    accepted: list[int] = []
    for idx in order:
        b = int(candidates[int(idx)])
        if any(abs(b - a) <= nms_window for a in accepted):
            continue
        trial = sorted(accepted + [b])
        points = [0, *trial, n_sentences]
        lengths = [points[i + 1] - points[i] for i in range(len(points) - 1)]
        if min(lengths) < min_seg:
            continue
        accepted.append(b)
        if len(accepted) >= k:
            break
    return sorted(accepted)


def _mean_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = sorted({k for row in rows for k in row})
    return {key: float(np.mean([row[key] for row in rows if key in row])) for key in keys}


def _evaluate_predictions(examples: list[VideoExample], predictions: dict[str, list[int]]) -> dict[str, float]:
    rows = []
    for ex in examples:
        pred = predictions[ex.video_id]
        metrics = evaluate(pred, ex.reference, ex.n_sentences)
        row = metrics.as_dict()
        row["f1_tol2"] = tolerance_f1(pred, ex.reference, ex.n_sentences, tolerance=2)[2]
        rows.append(row)
    return _mean_metrics(rows)


def _candidate_oracle(examples: list[VideoExample], tolerance: int) -> tuple[dict[str, float], float]:
    predictions: dict[str, list[int]] = {}
    recalls = []
    for ex in examples:
        selected: list[int] = []
        hit = 0
        for ref in ex.reference:
            near = [b for b in ex.candidates if abs(b - ref) <= tolerance]
            if near:
                hit += 1
                selected.append(min(near, key=lambda b: abs(b - ref)))
        predictions[ex.video_id] = sorted(set(selected))
        recalls.append(hit / max(1, len(ex.reference)))
    return _evaluate_predictions(examples, predictions), float(np.mean(recalls))


def _vote_scores(ex: VideoExample) -> np.ndarray:
    if ex.features.size == 0:
        return np.zeros(0, dtype=np.float64)
    vote = ex.features[:, 4]
    mean_source = ex.features[:, 6]
    max_source = ex.features[:, 7]
    prosody = ex.features[:, 9]
    shots = ex.features[:, 10]
    return _normalise01((0.45 * vote) + (0.30 * max_source) + (0.15 * mean_source) + (0.05 * prosody) + (0.05 * shots))


def _evaluate_score_family(
    examples: list[VideoExample],
    score_by_video: dict[str, np.ndarray],
    prefix: str,
) -> dict[str, dict[str, float]]:
    results: dict[str, dict[str, float]] = {}
    for frac in (0.55, 0.65, 0.70, 0.75, 0.85, 1.00):
        for min_seg in (8, 10, 12, 15):
            for nms in (2, 3, 5):
                predictions = {}
                for ex in examples:
                    k = max(1, int(round(ex.target_boundaries * frac)))
                    predictions[ex.video_id] = _select_boundaries(
                        ex.candidates,
                        score_by_video[ex.video_id],
                        ex.n_sentences,
                        k,
                        min_seg,
                        nms,
                    )
                name = f"{prefix}_frac{int(frac * 100)}_min{min_seg}_nms{nms}"
                results[name] = _evaluate_predictions(examples, predictions)
    return results


def _train_leave_one_out(examples: list[VideoExample], label_name: str) -> dict[str, dict[str, np.ndarray]]:
    from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    labels_attr = "labels_tol2" if label_name == "tol2" else "labels_tol3"
    model_factories = {
        "logreg": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(class_weight="balanced", C=0.35, max_iter=2000, random_state=13),
        ),
        "gb": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            GradientBoostingClassifier(n_estimators=90, learning_rate=0.05, max_depth=2, random_state=13),
        ),
        "extra": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesClassifier(
                n_estimators=300,
                min_samples_leaf=4,
                class_weight="balanced",
                random_state=13,
                n_jobs=-1,
            ),
        ),
    }

    scores: dict[str, dict[str, np.ndarray]] = {name: {} for name in model_factories}
    for holdout in examples:
        train = [ex for ex in examples if ex.video_id != holdout.video_id]
        x_train = np.vstack([ex.features for ex in train if len(ex.candidates) > 0])
        y_train = np.concatenate([getattr(ex, labels_attr) for ex in train if len(ex.candidates) > 0])
        for name, factory in model_factories.items():
            clf = factory()
            clf.fit(x_train, y_train)
            if hasattr(clf, "predict_proba"):
                scores[name][holdout.video_id] = clf.predict_proba(holdout.features)[:, 1]
            else:
                raw = clf.decision_function(holdout.features)
                scores[name][holdout.video_id] = _normalise01(raw)
    return scores


def _load_or_build_examples(
    data_dir: Path,
    models: tuple[str, ...],
    cache_path: Path | None,
    verbose: bool,
) -> list[VideoExample]:
    cache_meta = {"version": CACHE_VERSION, "models": list(models), "max_sentences": MAX_SENTENCES}
    if cache_path and cache_path.exists():
        with cache_path.open("rb") as handle:
            cached = pickle.load(handle)
        if cached.get("meta") == cache_meta:
            if verbose:
                print(f"Loaded cached examples from {cache_path}")
            return cached["examples"]

    examples: list[VideoExample] = []
    for video_id in _load_manifest(data_dir):
        ex = _make_example(data_dir, video_id, models)
        if ex is None:
            continue
        examples.append(ex)
        if verbose:
            pos2 = int(ex.labels_tol2.sum())
            print(
                f"{video_id}: n={ex.n_sentences} ref={len(ex.reference)} "
                f"candidates={len(ex.candidates)} pos_tol2={pos2}"
            )

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("wb") as handle:
            pickle.dump({"meta": cache_meta, "examples": examples}, handle)
        if verbose:
            print(f"Cached examples to {cache_path}")

    return examples


def run(data_dir: Path, models: tuple[str, ...], cache_path: Path | None, verbose: bool) -> dict[str, Any]:
    examples = _load_or_build_examples(data_dir, models, cache_path, verbose)

    if not examples:
        raise RuntimeError("No usable examples were loaded.")

    results: dict[str, Any] = {
        "meta": {
            "n_videos": len(examples),
            "models": list(models),
            "max_sentences": MAX_SENTENCES,
            "eval_gt": "youtube_chapters",
            "training": "leave_one_video_out",
        },
        "candidate_stats": {
            "mean_candidates": float(np.mean([len(ex.candidates) for ex in examples])),
            "mean_reference_boundaries": float(np.mean([len(ex.reference) for ex in examples])),
        },
        "methods": {},
        "oracle": {},
    }

    for tol in (1, 2, 3, 5, 10):
        metrics, recall = _candidate_oracle(examples, tol)
        results["oracle"][f"candidate_oracle_tol{tol}"] = {
            "candidate_recall": recall,
            **metrics,
        }

    vote_scores = {ex.video_id: _vote_scores(ex) for ex in examples}
    results["methods"].update(_evaluate_score_family(examples, vote_scores, "candidate_vote"))

    for label_name in ("tol2", "tol3"):
        loo_scores = _train_leave_one_out(examples, label_name)
        for clf_name, score_map in loo_scores.items():
            results["methods"].update(_evaluate_score_family(examples, score_map, f"rank_{clf_name}_{label_name}"))

    best = min(results["methods"].items(), key=lambda item: (item[1]["pk"], item[1]["wd"]))
    results["best_method"] = {"name": best[0], **best[1]}
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_candidate_ranker.json")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "candidate_ranker_examples.pkl")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--models", nargs="*", default=list(DEFAULT_MODELS))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    cache_path = None if args.no_cache else args.cache
    results = run(args.data_dir, tuple(args.models), cache_path, args.verbose)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print(f"Wrote {args.output}")
    print(
        "Best: {name} Pk={pk:.4f} WD={wd:.4f} BS={boundary_similarity:.4f} F1@2={f1_tol2:.4f}".format(
            **results["best_method"]
        )
    )


if __name__ == "__main__":
    main()
