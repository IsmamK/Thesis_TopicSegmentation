"""
Supervised boundary classifier.

Features at each sentence gap:
  - cosine_sim(v[i], v[i+1])               direct similarity
  - cosine between left-window mean and right-window mean (w=3,5)
  - cosine drop relative to local baseline
  - prosody pause (if available)
  - shot boundary flag (if available)
  - relative position in video

Label: 1 if GT boundary at this gap, 0 otherwise.

Trained with gradient boosting + class-weight balancing.
Evaluated with leave-one-video-out cross-validation.
Saves model to models/boundary_clf.joblib.
"""
from __future__ import annotations
import json
import sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lecseg.metrics import evaluate

GT_DIR      = ROOT / "data" / "gt_hier"
EMB_DIR     = ROOT / "data" / "embeddings" / "bge"
SENT_DIR    = ROOT / "data" / "sentences"
PROSODY_DIR = ROOT / "data" / "prosody"
SHOTS_DIR   = ROOT / "data" / "shots"
MODELS_DIR  = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a @ b) / (na * nb)


def extract_features(vecs: np.ndarray,
                     prosody: dict | None,
                     shots: list[int] | None,
                     n_sents: int) -> np.ndarray:
    """Extract gap-level features. Returns (N-1, F) array."""
    N = len(vecs)
    feats = []
    # Pre-compute pairwise cosines for speed
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    normed = vecs / norms

    for i in range(N - 1):
        f = []
        # 1. Direct adjacent cosine sim
        f.append(float(normed[i] @ normed[i + 1]))

        # 2. Window-3 mean cosine (left vs right)
        for w in [3, 5]:
            lw = normed[max(0, i - w + 1):i + 1]
            rw = normed[i + 1:min(N, i + 1 + w)]
            lm = lw.mean(axis=0)
            rm = rw.mean(axis=0)
            nl, nr = np.linalg.norm(lm), np.linalg.norm(rm)
            if nl > 0 and nr > 0:
                f.append(float(lm @ rm) / (nl * nr))
            else:
                f.append(0.0)

        # 3. Local cosine baseline (mean of 5 adjacent pairs)
        local_sims = [float(normed[j] @ normed[j + 1])
                      for j in range(max(0, i - 2), min(N - 1, i + 3))]
        baseline = float(np.mean(local_sims)) if local_sims else 0.0
        f.append(baseline - float(normed[i] @ normed[i + 1]))  # drop relative to local

        # 4. Relative position in video
        f.append((i + 1) / N)

        # 5. Prosody pause (normalised by max in video)
        if prosody and "pauses" in prosody:
            pauses = prosody["pauses"]
            pause_val = pauses[i] if i < len(pauses) else 0.0
            max_pause = max(pauses) if pauses else 1.0
            f.append(pause_val / (max_pause + 1e-9))
        else:
            f.append(0.0)

        # 6. Shot boundary flag
        if shots:
            f.append(1.0 if (i + 1) in shots else 0.0)
        else:
            f.append(0.0)

        feats.append(f)
    return np.array(feats, dtype=np.float32)


def gt_boundary_set(video_id: str) -> set[int]:
    gt = json.load(open(GT_DIR / f"{video_id}.json", encoding="utf-8"))
    chapters = gt.get("chapters", [])
    sents = json.load(open(SENT_DIR / video_id / "sentences.json", encoding="utf-8"))["sentences"]
    if len(chapters) <= 1:
        return set()
    boundaries = set()
    for ch in chapters[1:]:
        t = ch["start_sec"]
        best_idx = min(range(len(sents)),
                       key=lambda i: abs(sents[i].get("start", 0) - t))
        if best_idx > 0:
            boundaries.add(best_idx)
    return boundaries


def load_video_data(vid: str):
    emb_path = EMB_DIR / vid / "embeddings.npy"
    if not emb_path.exists():
        return None
    vecs = np.load(str(emb_path))

    prosody = None
    p_path = PROSODY_DIR / f"{vid}.json"
    if p_path.exists():
        try:
            prosody = json.load(open(p_path))
        except Exception:
            pass

    shots = None
    s_path = SHOTS_DIR / f"{vid}_shots.json"
    if s_path.exists():
        try:
            shots = json.load(open(s_path)).get("boundaries", [])
        except Exception:
            pass

    gt_b = gt_boundary_set(vid)
    return vecs, prosody, shots, gt_b


def predict_from_proba(proba: np.ndarray, threshold: float = 0.5) -> list[int]:
    """Convert per-gap probabilities to boundary indices (1-based)."""
    return [i + 1 for i, p in enumerate(proba) if p >= threshold]


def run():
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    import joblib

    videos = sorted([f.stem for f in GT_DIR.glob("*.json")
                     if f.stem != "iaa_report"])

    # Load all data
    data = {}
    for vid in videos:
        result = load_video_data(vid)
        if result is None:
            continue
        vecs, prosody, shots, gt_b = result
        if not gt_b or len(vecs) < 4:
            continue
        feats = extract_features(vecs, prosody, shots, len(vecs))
        labels = np.array([1 if (i + 1) in gt_b else 0
                           for i in range(len(vecs) - 1)])
        data[vid] = (feats, labels, vecs, gt_b)

    print(f"Loaded {len(data)} videos")
    total_pos = sum(labels.sum() for _, labels, _, _ in data.values())
    total_neg = sum((labels == 0).sum() for _, labels, _, _ in data.values())
    print(f"Total gaps: {total_pos + total_neg}  positives: {total_pos} ({100*total_pos/(total_pos+total_neg):.1f}%)")

    # Leave-one-video-out CV
    vids = list(data.keys())
    pk_scores, wd_scores = [], []

    for test_vid in vids:
        train_vids = [v for v in vids if v != test_vid]
        X_train = np.vstack([data[v][0] for v in train_vids])
        y_train = np.concatenate([data[v][1] for v in train_vids])

        # Gradient Boosting with class weight via sample_weight
        pos_weight = (y_train == 0).sum() / max(1, (y_train == 1).sum())
        sample_weights = np.where(y_train == 1, pos_weight, 1.0)

        clf = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=200, max_depth=4, learning_rate=0.05,
                subsample=0.8, random_state=42
            ))
        ])
        clf.fit(X_train, y_train, clf__sample_weight=sample_weights)

        X_test, _, vecs_test, gt_b_test = data[test_vid]
        proba = clf.predict_proba(X_test)[:, 1]

        # Find best threshold via F1 on this video (for reporting only)
        best_pred = predict_from_proba(proba, threshold=0.3)
        scores = evaluate(best_pred, list(gt_b_test), n_units=len(vecs_test))
        pk_scores.append(scores.pk)
        wd_scores.append(scores.wd)
        print(f"  {test_vid}: pk={scores.pk:.4f}  wd={scores.wd:.4f}  "
              f"n_pred={len(best_pred)}  n_gt={len(gt_b_test)}")

    macro_pk = float(np.mean(pk_scores))
    macro_wd = float(np.mean(wd_scores))
    print(f"\n{'='*60}")
    print(f"LOOCV Macro Pk:  {macro_pk:.4f}")
    print(f"LOOCV Macro WD:  {macro_wd:.4f}")

    # Train final model on ALL data
    X_all = np.vstack([data[v][0] for v in vids])
    y_all = np.concatenate([data[v][1] for v in vids])
    pos_weight = (y_all == 0).sum() / max(1, (y_all == 1).sum())
    sample_weights = np.where(y_all == 1, pos_weight, 1.0)

    final_clf = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42
        ))
    ])
    final_clf.fit(X_all, y_all, clf__sample_weight=sample_weights)

    model_path = MODELS_DIR / "boundary_clf.joblib"
    joblib.dump(final_clf, model_path)
    print(f"Final model saved -> {model_path}")

    # Save results
    import json as _json
    out = ROOT / "results" / "eval_boundary_clf.json"
    _json.dump({"macro_pk": macro_pk, "macro_wd": macro_wd,
                "method": "GradientBoosting_LOOCV",
                "features": ["cosine_adj","cosine_w3","cosine_w5","local_drop",
                             "rel_pos","prosody_pause","shot_flag"]},
               open(out, "w"), indent=2)
    print(f"Results saved -> {out}")


if __name__ == "__main__":
    run()
