"""
T29 — Run full evaluation ablation battery.

Runs all segmentation methods on all videos with ground-truth annotations,
computes all metrics (Pk, WD, BS, F1, H-WD), and saves results.

Methods evaluated:
    Baselines:
        - TextTiling (B1)
        - C99 (B2)
        - CosineSeg (B3)
        - KMeansSeg (B4)
        - BertSeg / cosine-depth (B5)
    Novel:
        - TwoStage (N1+N2 without LLM)
        - TwoStage+LLM (N1+N2+N4)
        - Hierarchical (N1+N2+N3)

Usage:
    python scripts/run_eval.py
    python scripts/run_eval.py --method cosine --verbose
    python scripts/run_eval.py --output results/eval.json
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

GT_HIER = ROOT / "data" / "gt_hier"
GT_YOUTUBE = ROOT / "data" / "gt"
SENTENCES_DIR = ROOT / "data" / "sentences"
EMBEDDINGS_DIR = ROOT / "data" / "embeddings"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

from lecseg.metrics import evaluate, SegmentationScores, tolerance_f1
from lecseg.baselines.classical import texttiling, c99
from lecseg.baselines.neural import cosine_seg, kmeans_seg, bert_seg
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.models.hierarchical import HierarchicalSegmenter
from lecseg.models.divisive import divisive_seg, divisive_seg_constrained
from lecseg.models.fusion import ReliabilityWeightedFusion, gap_scores_from_vecs
from lecseg.features.text_embeddings import embed_sentences, smooth_embeddings, smooth_embeddings_gaussian, block_embed_sentences
from lecseg.features.chunking import chunk_vecs, chunk_boundaries_to_sentences

import numpy as np

PROSODY_DIR = ROOT / "data" / "prosody"
SHOTS_DIR = ROOT / "data" / "shots"

try:
    from lecseg.refine.llm_refine import LLMRefiner  # noqa: F401
    _HAS_LLM = True
except Exception:
    _HAS_LLM = False


def _load_prosody(vid: str, n_sentences: int) -> np.ndarray | None:
    """Return per-gap prosody boundary score array of length n_sentences-1, or None.

    Combines THREE prosody signals (all per-gap, [0,1] normalised):
      - pause_after: long pause after sentence i suggests topic break
      - pitch_std:   high pitch variance signals speaker preparing topic shift
      - pitch_reset: large change in mean pitch between sentence i and i+1
                     (drop back to baseline = new topic start)
    Fused as: 0.5*pause + 0.3*pitch_std + 0.2*pitch_reset
    """
    p = PROSODY_DIR / f"{vid}.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, list) or len(data) == 0:
        return None

    pauses = np.array([float(d.get("pause_after", 0.0) or 0.0) for d in data], dtype=np.float32)
    pitch_std = np.array([float(d.get("pitch_std", 0.0) or 0.0) for d in data], dtype=np.float32)
    mean_pitch = np.array([float(d.get("mean_pitch", 0.0) or 0.0) for d in data], dtype=np.float32)

    L = min(len(pauses) - 1, n_sentences - 1)
    if L <= 0:
        return None

    # Per-gap signals: gap i sits between sentence i and i+1
    pause_g = pauses[:L]
    # pitch_std per gap: average of adjacent sentences' std (high variance near transitions)
    pstd_g = 0.5 * (pitch_std[:L] + pitch_std[1:L + 1])
    # pitch reset: relative change in mean pitch across gap
    prev_mp = mean_pitch[:L]
    next_mp = mean_pitch[1:L + 1]
    denom = np.where(prev_mp > 1e-3, prev_mp, 1.0)
    preset_g = np.abs(next_mp - prev_mp) / denom

    def _n01(x: np.ndarray) -> np.ndarray:
        rng = float(x.max() - x.min())
        if rng <= 0:
            return np.zeros_like(x, dtype=np.float32)
        return ((x - x.min()) / rng).astype(np.float32)

    fused = 0.5 * _n01(pause_g) + 0.3 * _n01(pstd_g) + 0.2 * _n01(preset_g)
    gap = fused.astype(np.float32)

    if L < n_sentences - 1:
        pad = np.zeros(n_sentences - 1 - L, dtype=np.float32)
        gap = np.concatenate([gap, pad])
    return gap


def _load_shot_gap_scores(vid: str, n_sentences: int, sentences: list[dict]) -> np.ndarray | None:
    """Return per-gap shot-boundary score array of length n_sentences-1, or None.

    Loads data/shots/<vid>_shots.json with entries {timestamp_s, probability}.
    Maps shot timestamps to sentence-gap indices, places a spike per shot, and
    smooths with a small Gaussian (sigma=1) to give near-miss credit.
    """
    p = SHOTS_DIR / f"{vid}_shots.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, list) or len(data) == 0:
        return None

    n_gaps = n_sentences - 1
    if n_gaps <= 0:
        return None
    sent_starts = np.array([float(s.get("start", 0.0)) for s in sentences], dtype=np.float32)

    spikes = np.zeros(n_gaps, dtype=np.float32)
    for shot in data:
        try:
            t = float(shot.get("timestamp_s", shot.get("timestamp", 0.0)))
        except (TypeError, ValueError):
            continue
        prob = float(shot.get("probability", 1.0) or 1.0)
        if t <= 0:
            continue
        # gap i is between sent[i] and sent[i+1]; find first sentence starting >= t
        idx = int(np.searchsorted(sent_starts, t, side="left"))
        gap_idx = max(0, min(n_gaps - 1, idx - 1))
        if prob > spikes[gap_idx]:
            spikes[gap_idx] = prob

    if spikes.max() <= 0:
        return None

    # Gaussian smoothing (sigma=1) for near-miss credit
    kernel = np.array([0.054, 0.242, 0.399, 0.242, 0.054], dtype=np.float32)
    smoothed = np.convolve(spikes, kernel, mode="same")
    rng = float(smoothed.max() - smoothed.min())
    if rng > 0:
        smoothed = (smoothed - smoothed.min()) / rng
    return smoothed.astype(np.float32)


def _normalise01(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    rng = float(x.max() - x.min())
    if rng <= 0:
        return np.zeros_like(x)
    return (x - x.min()) / rng


def _divisive_prosody(
    vecs: np.ndarray,
    n_segments: int,
    prosody_gap: np.ndarray | None,
    cosine_weight: float = 0.7,
) -> list[int]:
    """Divisive seg with prosody re-ranking of candidate splits.

    Strategy: oversample candidate splits with divisive_seg (3x target),
    score each as 0.7*cosine_dissim + 0.3*prosody, keep top n_segments-1.
    """
    target = max(1, n_segments - 1)
    over = min(max(target * 3, target + 2), max(2, len(vecs) - 1))
    cand_b, cand_scores = divisive_seg(vecs, n_segments=over + 1, return_scores=True)
    if not cand_b:
        return []
    cs = np.array([cand_scores.get(b, 0.0) for b in cand_b], dtype=np.float32)
    cs_n = _normalise01(cs)
    if prosody_gap is not None and len(prosody_gap) >= max(cand_b):
        pros = np.array([float(prosody_gap[b - 1]) for b in cand_b], dtype=np.float32)
        pros_n = _normalise01(pros)
        fused = cosine_weight * cs_n + (1.0 - cosine_weight) * pros_n
    else:
        fused = cs_n
    order = np.argsort(-fused)
    picked = sorted(int(cand_b[i]) for i in order[:target])
    return picked


def _divisive_multi(
    vecs: np.ndarray,
    n_segments: int,
    prosody_gap: np.ndarray | None,
    shot_gap: np.ndarray | None,
    w_cos: float = 0.6,
    w_pros: float = 0.2,
    w_shot: float = 0.2,
) -> list[int]:
    """Divisive seg with prosody+shot re-ranking of oversampled candidates.

    Oversample 3x candidate splits, score each as a weighted blend of cosine
    dissimilarity, prosody, and shot-boundary signal, then keep top n_segments-1.
    """
    target = max(1, n_segments - 1)
    over = min(max(target * 3, target + 2), max(2, len(vecs) - 1))
    cand_b, cand_scores = divisive_seg(vecs, n_segments=over + 1, return_scores=True)
    if not cand_b:
        return []
    cs = np.array([cand_scores.get(b, 0.0) for b in cand_b], dtype=np.float32)
    cs_n = _normalise01(cs)

    have_pros = prosody_gap is not None and len(prosody_gap) >= max(cand_b)
    have_shot = shot_gap is not None and len(shot_gap) >= max(cand_b)

    if have_pros:
        pros = np.array([float(prosody_gap[b - 1]) for b in cand_b], dtype=np.float32)
        pros_n = _normalise01(pros)
    else:
        pros_n = np.zeros_like(cs_n)
    if have_shot:
        sh = np.array([float(shot_gap[b - 1]) for b in cand_b], dtype=np.float32)
        sh_n = _normalise01(sh)
    else:
        sh_n = np.zeros_like(cs_n)

    # Renormalise weights based on which modalities are available
    weights = {"cos": w_cos}
    if have_pros:
        weights["pros"] = w_pros
    if have_shot:
        weights["shot"] = w_shot
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    fused = weights["cos"] * cs_n
    if "pros" in weights:
        fused = fused + weights["pros"] * pros_n
    if "shot" in weights:
        fused = fused + weights["shot"] * sh_n

    order = np.argsort(-fused)
    picked = sorted(int(cand_b[i]) for i in order[:target])
    return picked


def depth_seg(vecs: np.ndarray, n_segments: int, window: int = 5) -> list[int]:
    """TextTiling-style depth score on BERT embeddings.

    For each gap i, compare mean of w sentences before vs w sentences after
    using cosine similarity. Smooth the curve, then compute depth score
    (how deep each valley is relative to local peaks). Return top-k gaps.
    """
    N = len(vecs)
    if N < 4 or n_segments < 2:
        return []
    # Cumsum for fast window means
    cumsum = np.zeros((N + 1, vecs.shape[1]), dtype=np.float64)
    cumsum[1:] = np.cumsum(vecs.astype(np.float64), axis=0)

    sims = np.zeros(N - 1)
    for i in range(N - 1):
        lo_l = max(0, i - window + 1)
        left = (cumsum[i + 1] - cumsum[lo_l]) / (i + 1 - lo_l)
        hi_r = min(N, i + 1 + window)
        right = (cumsum[hi_r] - cumsum[i + 1]) / (hi_r - i - 1)
        nl, nr = np.linalg.norm(left), np.linalg.norm(right)
        if nl > 0 and nr > 0:
            sims[i] = float(left @ right) / (nl * nr)

    # Gaussian smooth
    from scipy.ndimage import gaussian_filter1d
    smoothed = gaussian_filter1d(sims, sigma=1.5)

    # Depth score: how far each valley dips below its surrounding peaks
    depth = np.zeros(N - 1)
    for i in range(N - 1):
        # Find nearest peak to left
        lp = smoothed[i]
        for j in range(i - 1, -1, -1):
            if smoothed[j] > lp:
                lp = smoothed[j]
            if j > 0 and smoothed[j] > smoothed[j - 1] and smoothed[j] > smoothed[j + 1]:
                lp = smoothed[j]
                break
        # Find nearest peak to right
        rp = smoothed[i]
        for j in range(i + 1, N - 1):
            if smoothed[j] > rp:
                rp = smoothed[j]
            if j < N - 2 and smoothed[j] > smoothed[j - 1] and smoothed[j] > smoothed[j + 1]:
                rp = smoothed[j]
                break
        depth[i] = 0.5 * (lp - smoothed[i]) + 0.5 * (rp - smoothed[i])

    k = max(1, n_segments - 1)
    top_k = np.argsort(-depth)[:k]
    return sorted(int(i) + 1 for i in top_k)


def depth_seg_smooth(vecs: np.ndarray, n_segments: int, window: int = 5, smooth_w: int = 7) -> list[int]:
    """Depth score on pre-smoothed embeddings."""
    return depth_seg(smooth_embeddings(vecs, window=smooth_w), n_segments, window=window)


_crossenc_model = None

def crossencoder_seg(texts: list[str], n_segments: int) -> list[int]:
    """Use our finetuned MiniLM cross-encoder to score each adjacent pair.
    Take top-(n_segments-1) gaps by boundary score."""
    global _crossenc_model
    CE_PATH = ROOT / "models" / "crossencoder"
    if not CE_PATH.exists():
        raise FileNotFoundError(f"Cross-encoder model not found at {CE_PATH}")
    if _crossenc_model is None:
        import torch
        from sentence_transformers.cross_encoder import CrossEncoder
        _crossenc_model = CrossEncoder(
            str(CE_PATH), num_labels=1,
            default_activation_function=torch.nn.Sigmoid()
        )
    N = len(texts)
    if N < 2:
        return []
    pairs = [[texts[i], texts[i + 1]] for i in range(N - 1)]
    scores = _crossenc_model.predict(pairs, batch_size=64, show_progress_bar=False)
    scores = np.array(scores)
    k = max(1, n_segments - 1)
    top_k = np.argsort(-scores)[:k]
    return sorted(int(i) + 1 for i in top_k)


_bert_wiki_model = None
_bert_wiki_tok = None

def _bert_wiki_seg(texts: list[str], n_segments: int) -> list[int]:
    """Score every adjacent sentence pair with dennlinger/bert-wiki-paragraphs.
    Label 0 = topic break. Take top-(n_segments-1) gaps by break probability."""
    global _bert_wiki_model, _bert_wiki_tok
    if _bert_wiki_model is None:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        _bert_wiki_tok = AutoTokenizer.from_pretrained("dennlinger/bert-wiki-paragraphs")
        _bert_wiki_model = AutoModelForSequenceClassification.from_pretrained(
            "dennlinger/bert-wiki-paragraphs", ignore_mismatched_sizes=True)
        _bert_wiki_model.eval()
    import torch
    N = len(texts)
    if N < 2:
        return []
    scores = []
    batch_size = 32
    pairs_a = [texts[i] for i in range(N - 1)]
    pairs_b = [texts[i + 1] for i in range(N - 1)]
    with torch.no_grad():
        for i in range(0, N - 1, batch_size):
            enc = _bert_wiki_tok(
                pairs_a[i:i+batch_size], pairs_b[i:i+batch_size],
                padding=True, truncation=True, max_length=512,
                return_tensors="pt"
            )
            logits = _bert_wiki_model(**enc).logits
            probs = torch.softmax(logits, dim=-1)
            # index 0 = same_topic, index 1 = topic_break
            scores.extend(probs[:, 1].tolist())
    scores = np.array(scores)
    k = max(1, n_segments - 1)
    top_k = np.argsort(-scores)[:k]
    return sorted(int(i) + 1 for i in top_k)


def _divisive_llm(
    vecs: np.ndarray,
    n_segments: int,
    sentences: list[dict],
) -> list[int]:
    """Divisive seg with LLM binary-classification of candidate boundaries.

    Oversample 2x candidates from divisive, ask Ollama (llama3.1:8b) if topic
    changes across each candidate, keep YES boundaries (top-N by cosine score).
    Falls back to plain divisive if Ollama unavailable.
    """
    target = max(1, n_segments - 1)
    over = min(max(target * 2 + 1, target + 2), max(2, len(vecs) - 1))
    cands, scores = divisive_seg(vecs, n_segments=over + 1, return_scores=True)
    if not cands:
        return divisive_seg(vecs, n_segments=n_segments)
    if not _HAS_LLM:
        return divisive_seg(vecs, n_segments=n_segments)

    try:
        from lecseg.refine.llm_refine import LLMRefiner
        refiner = LLMRefiner()
        if not refiner._is_available():
            return divisive_seg(vecs, n_segments=n_segments)
    except Exception:
        return divisive_seg(vecs, n_segments=n_segments)

    import urllib.request, json as _json
    sent_texts = [s["text"] for s in sentences]
    confirmed: list[int] = []

    def _ollama_yn(prompt_text: str) -> bool:
        """Call Ollama REST API, return True if response contains YES."""
        payload = _json.dumps({
            "model": "llama3.1:8b",
            "prompt": prompt_text,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 5},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = _json.loads(resp.read())
                return "YES" in data.get("response", "").upper()
        except Exception:
            return False

    for b in cands:
        lo = max(0, b - 4)
        hi = min(len(sent_texts), b + 4)
        passage_a = " ".join(sent_texts[lo:b])
        passage_b = " ".join(sent_texts[b:hi])
        prompt = (
            f"Lecture passage A: {passage_a[:400]}\n"
            f"Lecture passage B: {passage_b[:400]}\n"
            "Does the lecture topic change significantly between A and B? "
            "Answer YES or NO only."
        )
        if _ollama_yn(prompt):
            confirmed.append(b)

    if len(confirmed) >= target:
        score_map = {b: scores.get(b, 0.0) for b in confirmed}
        return sorted(sorted(confirmed, key=lambda x: -score_map[x])[:target])
    elif confirmed:
        return sorted(confirmed)
    return divisive_seg(vecs, n_segments=n_segments)


def divisive_block(texts: list[str], n_segments: int, window: int = 5, model: str = "bge") -> list[int]:
    """TreeSeg-style block embeddings: encode multi-sentence windows, then divisive.

    Each position i is encoded as a single string spanning sentences
    [i-w//2 .. i+w//2]. This jointly encodes context rather than averaging
    individual vectors, which is the key TreeSeg trick for better boundary signals.
    """
    vecs = block_embed_sentences(texts, model=model, window=window)
    return divisive_seg(vecs, n_segments=n_segments)


def bic_k_select(vecs: np.ndarray, max_k: int = 30) -> int:
    """Select k using BIC on cosine similarity drop curve.

    Fits a piecewise model: computes the mean pairwise within-segment
    cosine similarity for each k from 2..max_k, then selects k where
    BIC (penalised likelihood) is minimised. This is more principled
    than the heuristic used in divisive_seg's n_segments.

    Returns: optimal k (number of segments)
    """
    from lecseg.models.divisive import divisive_seg
    N = len(vecs)
    if N < 4:
        return 2
    max_k = min(max_k, N // 4, 50)
    if max_k < 2:
        return 2

    # Precompute cosine similarity matrix (capped at 200 sentences for speed)
    cap = min(N, 200)
    v = vecs[:cap]
    sim_mat = v @ v.T  # already L2-normalised

    best_bic = float("inf")
    best_k = 2
    prev_bounds = []
    for k in range(2, max_k + 1):
        bounds = divisive_seg(v, n_segments=k)
        segment_starts = [0] + bounds
        segment_ends = bounds + [cap]
        total_ll = 0.0
        n_params = k - 1  # k-1 boundary parameters
        for s, e in zip(segment_starts, segment_ends):
            if e - s < 2:
                continue
            seg_sim = sim_mat[s:e, s:e]
            # Mean within-segment similarity (upper triangle)
            idx = np.triu_indices(e - s, k=1)
            if len(idx[0]) == 0:
                continue
            mean_sim = float(seg_sim[idx].mean())
            # Log-likelihood proxy: sum of similarities (higher = better fit)
            total_ll += mean_sim * len(idx[0])
        # BIC = -2*ll + n_params * log(N)
        bic = -2 * total_ll + n_params * np.log(cap)
        if bic < best_bic:
            best_bic = bic
            best_k = k
    return best_k


def divisive_bic(vecs: np.ndarray) -> list[int]:
    """Divisive segmentation with BIC-selected k (no oracle k needed)."""
    k = bic_k_select(vecs)
    return divisive_seg(vecs, n_segments=k)


def divisive_bic_smooth(vecs: np.ndarray) -> list[int]:
    """Divisive + BIC k-selection on smoothed (w=7) embeddings."""
    svecs = smooth_embeddings(vecs, window=7)
    k = bic_k_select(svecs)
    return divisive_seg(svecs, n_segments=k)


def min_seg_filter(boundaries: list[int], n_sentences: int, min_seg: int = 5) -> list[int]:
    """Remove boundaries that create segments shorter than min_seg sentences.

    Post-processes any predicted boundary list: iteratively removes the boundary
    that creates the smallest segment until all segments are >= min_seg sentences.
    This reduces false-positive micro-boundaries which inflate Pk.
    """
    if not boundaries:
        return boundaries
    bounds = sorted(boundaries)
    while True:
        # Compute segment lengths
        segs = []
        prev = 0
        for b in bounds:
            segs.append(b - prev)
            prev = b
        segs.append(n_sentences - prev)
        min_len = min(segs)
        if min_len >= min_seg:
            break
        # Remove the boundary adjacent to the shortest segment
        min_idx = segs.index(min_len)
        # min_idx is the segment index; boundary to remove is the min of adjacent boundaries
        if min_idx == 0:
            # First segment too short — remove first boundary
            bounds = bounds[1:]
        elif min_idx == len(segs) - 1:
            # Last segment too short — remove last boundary
            bounds = bounds[:-1]
        else:
            # Middle — remove the boundary creating less disruption (smaller score change)
            # Simple: remove left boundary (before the short segment)
            bounds = bounds[:min_idx - 1] + bounds[min_idx:]
        if not bounds:
            break
    return bounds


def score_aware_min_seg(
    boundaries: list[int],
    scores: dict[int, float],
    n_sentences: int,
    min_seg: int = 10,
) -> list[int]:
    """Remove short-segment boundaries, preferring to keep higher-scoring ones.

    When a segment is too short (< min_seg), remove the LOWER-scoring
    of the two boundaries adjacent to that segment (rather than always
    the left boundary). This retains higher-confidence boundaries.
    """
    if not boundaries:
        return boundaries
    bounds = sorted(boundaries)
    while True:
        segs = []
        prev = 0
        for b in bounds:
            segs.append(b - prev)
            prev = b
        segs.append(n_sentences - prev)
        min_len = min(segs)
        if min_len >= min_seg:
            break
        min_idx = segs.index(min_len)
        if min_idx == 0:
            bounds = bounds[1:]
        elif min_idx == len(segs) - 1:
            bounds = bounds[:-1]
        else:
            left_b = bounds[min_idx - 1]
            right_b = bounds[min_idx]
            score_left = scores.get(left_b, 0.0)
            score_right = scores.get(right_b, 0.0)
            if score_left <= score_right:
                bounds = bounds[:min_idx - 1] + bounds[min_idx:]
            else:
                bounds = bounds[:min_idx] + bounds[min_idx + 1:]
        if not bounds:
            break
    return bounds


def cross_model_score_aware_minlen(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5large",
    window: int = 9,
    frac: float = 0.70,
    min_seg: int = 11,
) -> list[int]:
    """Cross-model ensemble with score-aware min segment length filtering.

    Unlike post-hoc min_seg_filter (which ignores scores), this retains
    the boundary with the higher combined score when removing short segments.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)
    k = max(2, round(n_segments * frac))
    over_k = min(N_cap - 1, k * 4 + 2)

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        raw = divisive_seg(v1, n_segments=k)
        return min_seg_filter(raw, len(v1), min_seg=min_seg)

    N = min(N_cap, len(v2_raw))
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    _, s1 = divisive_seg(v1[:N], n_segments=min(over_k, N - 1), return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=min(over_k, N - 1), return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1[:N], n_segments=k)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    combined_scores = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    top_k = sorted(combined_scores, key=lambda x: -combined_scores[x])[:k]
    boundaries = sorted(b for b in top_k if 0 < b < N)
    return score_aware_min_seg(boundaries, combined_scores, N, min_seg=min_seg)


def divisive_minlen(vecs: np.ndarray, n_segments: int, min_seg: int = 8) -> list[int]:
    """Divisive with post-hoc minimum segment length filtering."""
    raw = divisive_seg(vecs, n_segments=n_segments)
    return min_seg_filter(raw, len(vecs), min_seg=min_seg)


def divisive_smooth7_minlen(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Best combo: smooth w=7 + min segment length filter."""
    svecs = smooth_embeddings(vecs, window=7)
    raw = divisive_seg(svecs, n_segments=n_segments)
    return min_seg_filter(raw, len(vecs), min_seg=8)


def gap_elbow_k(vecs: np.ndarray, max_k: int = 30) -> int:
    """Select k using elbow detection on the divisive dissimilarity score curve.

    Run divisive greedily up to max_k boundaries, track the dissimilarity score
    at each split. The 'elbow' is where the marginal gain drops sharply — adding
    more boundaries gives diminishing returns. Use the second derivative to find
    this point.
    """
    from lecseg.models.divisive import divisive_seg
    N = len(vecs)
    max_k = min(max_k, N // 3, 40)
    if max_k < 2:
        return 2

    # Get boundaries + scores from full divisive run
    bounds, scores_dict = divisive_seg(vecs, n_segments=max_k + 1, return_scores=True)
    if not scores_dict:
        return max(2, min(max_k // 3, 8))

    # Sort boundaries by insertion order (score order = greedy order)
    ordered_scores = sorted(scores_dict.values(), reverse=True)
    if len(ordered_scores) < 2:
        return 2

    # Second derivative of the score curve: find where it's most negative (elbow)
    arr = np.array(ordered_scores)
    if len(arr) < 3:
        return len(arr) + 1
    d2 = np.diff(arr, n=2)
    # Most negative second derivative = steepest drop in score improvement
    elbow_k = int(np.argmin(d2)) + 2  # +2 because diff(n=2) loses 2 elements
    return max(2, min(elbow_k + 1, max_k))  # +1 for segments


def divisive_elbow(vecs: np.ndarray) -> list[int]:
    """Divisive with elbow-detected k (no oracle needed)."""
    k = gap_elbow_k(vecs)
    return divisive_seg(vecs, n_segments=k)


def divisive_elbow_smooth(vecs: np.ndarray) -> list[int]:
    """Divisive + elbow k on smoothed (w=7) embeddings."""
    svecs = smooth_embeddings(vecs, window=7)
    k = gap_elbow_k(svecs)
    return divisive_seg(svecs, n_segments=k)


def dp_seg(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Optimal dynamic programming segmentation.

    Finds the globally optimal k-way partition maximising sum of within-segment
    mean cosine similarity. Greedy divisive is approximate; DP finds the true
    optimum for a fixed k. Uses the identity:
        coherence(a,b) = ||mean(vecs[a:b])||² * (b-a)
    which avoids computing all pairwise cosines.

    Complexity: O(N² + N·k) — feasible for N≤800, k≤50.
    """
    N = len(vecs)
    if N < 2 or n_segments < 2:
        return []
    k = min(n_segments, N)

    # Precompute segment coherence: coh[i][j] = coherence of segment [i, j)
    # coherence = ||mean(vecs[i:j])||² * (j-i)  = (sum_vecs · sum_vecs) / (j-i)
    # Use cumulative sum for O(1) segment sums
    cumsum = np.cumsum(vecs.astype(np.float64), axis=0)  # (N, D)
    # coh(i, j) = ||sum(i:j)||² / (j-i) where sum(i:j) = cumsum[j-1] - (cumsum[i-1] if i>0 else 0)

    def seg_coh(i: int, j: int) -> float:
        length = j - i
        if length <= 0:
            return 0.0
        s = cumsum[j - 1] - (cumsum[i - 1] if i > 0 else np.zeros(vecs.shape[1]))
        return float(s @ s) / length

    # DP: dp[i][m] = max total coherence for first i sentences in m segments
    NEG_INF = -1e18
    dp = np.full((N + 1, k + 1), NEG_INF)
    parent = np.full((N + 1, k + 1), -1, dtype=np.int32)
    dp[0][0] = 0.0

    for m in range(1, k + 1):
        for j in range(m, N - (k - m) + 1):  # j = end of m-th segment
            best_val = NEG_INF
            best_i = -1
            min_i = m - 1
            max_i = j - 1
            for i in range(min_i, max_i + 1):
                if dp[i][m - 1] < NEG_INF / 2:
                    continue
                val = dp[i][m - 1] + seg_coh(i, j)
                if val > best_val:
                    best_val = val
                    best_i = i
            dp[j][m] = best_val
            parent[j][m] = best_i

    # Backtrack to find boundary positions
    boundaries = []
    j = N
    m = k
    while m > 1:
        i = int(parent[j][m])
        if i < 0:
            break
        if i > 0:
            boundaries.append(i)
        j = i
        m -= 1

    return sorted(boundaries)


def dp_seg_smooth(vecs: np.ndarray, n_segments: int) -> list[int]:
    """DP segmentation on smoothed (w=7) embeddings."""
    return dp_seg(smooth_embeddings(vecs, window=7), n_segments)


def cosine_drop_seg(vecs: np.ndarray, n_segments: int, window: int = 3) -> list[int]:
    """Gap scoring via mean cross-boundary cosine similarity drop.

    For each gap i, compute mean similarity between sentences in [i-w, i]
    and sentences in [i+1, i+1+w]. Gaps with lowest similarity (biggest drop)
    are boundaries. Unlike TextTiling which uses a single adjacent-pair score,
    this uses a window for robustness.

    This is similar to BertSeg but uses precomputed embeddings.
    """
    N = len(vecs)
    if N < 4 or n_segments < 2:
        return []
    gap_scores = np.zeros(N - 1)
    for i in range(N - 1):
        lo_l = max(0, i - window + 1)
        hi_r = min(N, i + 1 + window)
        left = vecs[lo_l:i + 1]   # up to and including sentence i
        right = vecs[i + 1:hi_r]  # from sentence i+1
        # Cross similarity: mean of all left-right dot products (already L2-norm)
        cross_sim = float((left @ right.T).mean())
        gap_scores[i] = cross_sim  # low cross-sim = likely boundary

    k = max(1, n_segments - 1)
    # Boundaries where similarity is LOWEST
    top_k = np.argsort(gap_scores)[:k]
    return sorted(int(i) + 1 for i in top_k)


def cosine_drop_smooth_seg(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Cosine-drop gap scoring on smooth w=7 embeddings."""
    return cosine_drop_seg(smooth_embeddings(vecs, window=7), n_segments, window=3)


def ensemble_seg(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Ensemble: average scores from divisive, depth, and cosine-drop, then pick top-k.

    Combines three complementary boundary signals:
    1. Divisive cosine dissimilarity (top-down structural)
    2. Depth score (TextTiling valley depth)
    3. Cross-boundary cosine drop (local gap signal)

    Each method's scores are rank-normalised to [0,1] before averaging.
    """
    N = len(vecs)
    if N < 4 or n_segments < 2:
        return []
    k = max(1, n_segments - 1)

    # Signal 1: divisive scores
    bounds, score_dict = divisive_seg(vecs, n_segments=min(N - 1, k * 3 + 2), return_scores=True)
    div_scores = np.zeros(N - 1)
    for b, s in score_dict.items():
        if 0 < b < N:
            div_scores[b - 1] = s  # b is 1-based boundary -> 0-based gap index b-1

    # Signal 2: cosine drop scores (inverted: low sim = high boundary score)
    drop_scores = np.zeros(N - 1)
    window = 3
    for i in range(N - 1):
        lo_l = max(0, i - window + 1)
        hi_r = min(N, i + 1 + window)
        left = vecs[lo_l:i + 1]
        right = vecs[i + 1:hi_r]
        drop_scores[i] = 1.0 - float((left @ right.T).mean())  # invert: low sim = high score

    # Rank-normalise each signal to [0,1]
    def rank_norm(s: np.ndarray) -> np.ndarray:
        if s.max() == s.min():
            return np.zeros_like(s)
        return (s - s.min()) / (s.max() - s.min())

    combined = (rank_norm(div_scores) + rank_norm(drop_scores)) / 2.0
    top_k = np.argsort(-combined)[:k]
    return sorted(int(i) + 1 for i in top_k)


def ensemble_smooth_seg(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Ensemble on smooth w=7 embeddings."""
    return ensemble_seg(smooth_embeddings(vecs, window=7), n_segments)


def recency_gap_scores(vecs: np.ndarray, window: int = 7) -> np.ndarray:
    """Compute gap boundary scores using recency-weighted window comparison.

    For each gap i, weight sentences closer to the gap more heavily
    (exponential decay away from gap). This sharpens boundary signals
    compared to uniform window averaging.

    Returns: array of length N-1, higher = more likely boundary.
    """
    N = len(vecs)
    if N < 2:
        return np.zeros(N - 1)
    half = window // 2
    # Exponential weights: sentences closest to gap have weight 1.0
    weights = np.exp(-np.arange(half + 1) * 0.5)  # [1.0, 0.61, 0.37, 0.22, ...]
    weights = weights / weights.sum()

    gap_scores = np.zeros(N - 1)
    for i in range(N - 1):
        # Left side: sentences [i, i-1, i-2, ...] weighted by recency
        left_w = np.zeros(vecs.shape[1], dtype=np.float64)
        for d in range(min(half + 1, i + 1)):
            left_w += weights[d] * vecs[i - d]
        nl = float(np.linalg.norm(left_w))
        if nl > 0:
            left_w /= nl

        # Right side: sentences [i+1, i+2, ...] weighted by recency
        right_w = np.zeros(vecs.shape[1], dtype=np.float64)
        for d in range(min(half + 1, N - i - 1)):
            right_w += weights[d] * vecs[i + 1 + d]
        nr = float(np.linalg.norm(right_w))
        if nr > 0:
            right_w /= nr

        # Boundary score = cosine dissimilarity
        if nl > 0 and nr > 0:
            gap_scores[i] = 1.0 - float(left_w @ right_w)

    return gap_scores


def recency_seg(vecs: np.ndarray, n_segments: int, window: int = 7) -> list[int]:
    """Segmentation using recency-weighted gap scoring."""
    N = len(vecs)
    if N < 4 or n_segments < 2:
        return []
    scores = recency_gap_scores(vecs, window=window)
    k = max(1, n_segments - 1)
    top_k = np.argsort(-scores)[:k]
    return sorted(int(i) + 1 for i in top_k)


def recency_seg_smooth(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Recency gap scoring on smooth w=7 embeddings."""
    return recency_seg(smooth_embeddings(vecs, window=7), n_segments, window=7)


def divisive_recency(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Ensemble: divisive scores + recency-weighted gap scores, rank-averaged."""
    N = len(vecs)
    if N < 4 or n_segments < 2:
        return []
    k = max(1, n_segments - 1)

    # Divisive scores
    _, score_dict = divisive_seg(vecs, n_segments=min(N - 1, k * 3 + 2), return_scores=True)
    div_scores = np.zeros(N - 1)
    for b, s in score_dict.items():
        if 0 < b < N:
            div_scores[b - 1] = s

    # Recency scores
    rec_scores = recency_gap_scores(vecs, window=7)

    # Rank-normalise and combine
    def rank_norm(s: np.ndarray) -> np.ndarray:
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else np.zeros_like(s)

    combined = (rank_norm(div_scores) + rank_norm(rec_scores)) / 2.0
    top_k = np.argsort(-combined)[:k]
    return sorted(int(i) + 1 for i in top_k)


def divisive_recency_smooth(vecs: np.ndarray, n_segments: int) -> list[int]:
    """divisive_recency on smooth w=7 embeddings."""
    return divisive_recency(smooth_embeddings(vecs, window=7), n_segments)


def divisive_smooth(vecs: np.ndarray, n_segments: int, window: int = 7) -> list[int]:
    """Convenience: smooth then divisive."""
    return divisive_seg(smooth_embeddings(vecs, window=window), n_segments)


def divisive_smooth13(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth window=13 + divisive."""
    return divisive_smooth(vecs, n_segments, window=13)


def divisive_smooth15(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth window=15 + divisive."""
    return divisive_smooth(vecs, n_segments, window=15)


def divisive_smooth19(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth window=19 + divisive."""
    return divisive_smooth(vecs, n_segments, window=19)


def divisive_smooth25(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth window=25 + divisive."""
    return divisive_smooth(vecs, n_segments, window=25)


def divisive_smooth_dp(vecs: np.ndarray, n_segments: int, window: int = 9) -> list[int]:
    """Smooth then DP (optimal) segmentation."""
    return dp_seg(smooth_embeddings(vecs, window=window), n_segments)


def divisive_conservative(vecs: np.ndarray, n_segments: int, reduce: int = 2) -> list[int]:
    """Conservative divisive: predict fewer boundaries than expected.

    Under-prediction reduces false positives. For Pk, missing a true
    boundary is often less costly than adding a false one (window-error
    counting is asymmetric when FP-rate > FN-rate).
    """
    k = max(2, n_segments - reduce)
    return divisive_seg(vecs, n_segments=k)


def divisive_smooth7_conservative(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=7 + conservative k (predict k-2)."""
    svecs = smooth_embeddings(vecs, window=7)
    k = max(2, n_segments - 2)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth9_conservative(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=9 + conservative k (predict k-2)."""
    svecs = smooth_embeddings(vecs, window=9)
    k = max(2, n_segments - 2)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth11_conservative(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=11 + conservative k (predict k-2)."""
    svecs = smooth_embeddings(vecs, window=11)
    k = max(2, n_segments - 2)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth13_conservative(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=13 + conservative k (predict k-2)."""
    svecs = smooth_embeddings(vecs, window=13)
    k = max(2, n_segments - 2)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth9_consv3(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=9 + very conservative k (predict k-3)."""
    svecs = smooth_embeddings(vecs, window=9)
    k = max(2, n_segments - 3)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth11_consv3(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=11 + very conservative k (predict k-3)."""
    svecs = smooth_embeddings(vecs, window=11)
    k = max(2, n_segments - 3)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth15_conservative(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=15 + conservative k (predict k-2)."""
    svecs = smooth_embeddings(vecs, window=15)
    k = max(2, n_segments - 2)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth_frac(vecs: np.ndarray, n_segments: int, window: int = 9, frac: float = 0.75) -> list[int]:
    """Smooth + predict frac*k boundaries (fractional conservative)."""
    svecs = smooth_embeddings(vecs, window=window)
    k = max(2, round(n_segments * frac))
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth9_frac80(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=9 + 80% of k boundaries."""
    return divisive_smooth_frac(vecs, n_segments, window=9, frac=0.80)


def divisive_smooth9_frac70(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=9 + 70% of k boundaries."""
    return divisive_smooth_frac(vecs, n_segments, window=9, frac=0.70)


def divisive_smooth11_frac80(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=11 + 80% of k boundaries."""
    return divisive_smooth_frac(vecs, n_segments, window=11, frac=0.80)


def divisive_smooth11_frac70(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=11 + 70% of k boundaries."""
    return divisive_smooth_frac(vecs, n_segments, window=11, frac=0.70)


def divisive_smooth9_frac75(vecs: np.ndarray, n_segments: int) -> list[int]:
    return divisive_smooth_frac(vecs, n_segments, window=9, frac=0.75)


def divisive_smooth9_frac85(vecs: np.ndarray, n_segments: int) -> list[int]:
    return divisive_smooth_frac(vecs, n_segments, window=9, frac=0.85)


def divisive_smooth10_frac80(vecs: np.ndarray, n_segments: int) -> list[int]:
    return divisive_smooth_frac(vecs, n_segments, window=10, frac=0.80)


def divisive_smooth11_frac75(vecs: np.ndarray, n_segments: int) -> list[int]:
    return divisive_smooth_frac(vecs, n_segments, window=11, frac=0.75)


def divisive_smooth11_frac85(vecs: np.ndarray, n_segments: int) -> list[int]:
    return divisive_smooth_frac(vecs, n_segments, window=11, frac=0.85)


def divisive_smooth9_consv4(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=9 + very conservative k (predict k-4)."""
    svecs = smooth_embeddings(vecs, window=9)
    k = max(2, n_segments - 4)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth11_consv4(vecs: np.ndarray, n_segments: int) -> list[int]:
    """Smooth w=11 + very conservative k (predict k-4)."""
    svecs = smooth_embeddings(vecs, window=11)
    k = max(2, n_segments - 4)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth9_consv5(vecs: np.ndarray, n_segments: int) -> list[int]:
    svecs = smooth_embeddings(vecs, window=9)
    k = max(2, n_segments - 5)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth9_consv6(vecs: np.ndarray, n_segments: int) -> list[int]:
    svecs = smooth_embeddings(vecs, window=9)
    k = max(2, n_segments - 6)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth9_frac65(vecs: np.ndarray, n_segments: int) -> list[int]:
    return divisive_smooth_frac(vecs, n_segments, window=9, frac=0.65)


def divisive_smooth11_consv5(vecs: np.ndarray, n_segments: int) -> list[int]:
    svecs = smooth_embeddings(vecs, window=11)
    k = max(2, n_segments - 5)
    return divisive_seg(svecs, n_segments=k)


def divisive_smooth11_frac65(vecs: np.ndarray, n_segments: int) -> list[int]:
    return divisive_smooth_frac(vecs, n_segments, window=11, frac=0.65)


def load_embeddings_model(vid: str, model: str) -> np.ndarray | None:
    """Helper to load precomputed embeddings for a given model."""
    p = EMBEDDINGS_DIR / model / vid / "embeddings.npy"
    if not p.exists():
        return None
    return np.load(str(p)).astype(np.float32)


def dual_model_divisive(
    vecs_bge: np.ndarray,
    vid: str,
    n_segments: int,
    window: int = 9,
    frac: float = 0.80,
) -> list[int]:
    """Ensemble: combine BGE and E5-large embedding gap scores, then divisive.

    Loads E5-large embeddings and averages the boundary score from both models
    before selecting top-k boundaries. Better than either alone if the models
    are complementary.
    """
    vecs_e5 = load_embeddings_model(vid, "e5large")
    if vecs_e5 is None:
        # Fallback to single model
        svecs = smooth_embeddings(vecs_bge, window=window)
        k = max(2, round(n_segments * frac))
        return divisive_seg(svecs, n_segments=k)

    N = min(len(vecs_bge), len(vecs_e5), 800)
    v_bge = smooth_embeddings(vecs_bge[:N], window=window)
    v_e5 = smooth_embeddings(vecs_e5[:N], window=window)

    # Get boundary scores from each model using divisive
    k = max(2, round(n_segments * frac))
    over_k = min(N - 1, k * 3 + 2)

    _, scores_bge = divisive_seg(v_bge, n_segments=over_k, return_scores=True)
    _, scores_e5 = divisive_seg(v_e5, n_segments=over_k, return_scores=True)

    # Combine scores: average rank-normalised scores
    all_positions = sorted(set(scores_bge) | set(scores_e5))
    combined_scores = {}
    max_bge = max(scores_bge.values(), default=1.0) or 1.0
    max_e5 = max(scores_e5.values(), default=1.0) or 1.0
    for pos in all_positions:
        s_bge = scores_bge.get(pos, 0.0) / max_bge
        s_e5 = scores_e5.get(pos, 0.0) / max_e5
        combined_scores[pos] = (s_bge + s_e5) / 2.0

    if not combined_scores:
        return divisive_seg(v_bge, n_segments=k)

    top_k = sorted(combined_scores, key=lambda x: -combined_scores[x])[:k]
    return sorted(b for b in top_k if 0 < b < N)


def cross_model_ensemble_seg(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5large",
    window: int = 9,
    frac: float = 0.80,
) -> list[int]:
    """Ensemble boundary scores from two embedding models.

    Loads secondary model embeddings for the video, smooths both, then
    averages rank-normalized divisive scores to pick top-k boundaries.
    More robust than either model alone.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    # Load secondary
    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        k = max(2, round(n_segments * frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    k = max(2, round(n_segments * frac))
    over_k = min(N - 1, k * 4 + 2)

    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    combined = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}
    top_k = sorted(combined, key=lambda x: -combined[x])[:k]
    return sorted(b for b in top_k if 0 < b < N)


def cross_model_rank_vote(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5large",
    window: int = 9,
    frac: float = 0.80,
) -> list[int]:
    """Cross-model ensemble using rank aggregation (Borda count).

    Each model ranks all gap positions by score. The final ranking
    is the sum of ranks (Borda count). Selects top-k by combined rank.
    More robust to outlier scores than simple score averaging.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)
    k = max(2, round(n_segments * frac))
    over_k = min(N_cap - 1, k * 4 + 2)

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    _, s1 = divisive_seg(v1[:N], n_segments=min(over_k, N - 1), return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=min(over_k, N - 1), return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1[:N], n_segments=k)

    # Rank positions by score in each model (descending: best=rank 1)
    sorted_s1 = sorted(s1, key=lambda x: -s1[x])
    sorted_s2 = sorted(s2, key=lambda x: -s2[x])
    rank_s1 = {p: i + 1 for i, p in enumerate(sorted_s1)}
    rank_s2 = {p: i + 1 for i, p in enumerate(sorted_s2)}
    default_rank = max(len(s1), len(s2)) + 1

    # Borda score: lower is better (lower rank = higher priority)
    borda = {p: rank_s1.get(p, default_rank) + rank_s2.get(p, default_rank)
             for p in all_pos}
    top_k = sorted(borda, key=lambda x: borda[x])[:k]
    return sorted(b for b in top_k if 0 < b < N)


def gap_variance_k_select(vecs: np.ndarray, max_k: int = 40) -> int:
    """Select k using variance drop in gap similarity curve.

    Compute the cosine similarity between adjacent sentences (smoothed w=7).
    The optimal k is where the within-segment similarity variance stops
    decreasing significantly as we add more segments.
    """
    N = len(vecs)
    svecs = smooth_embeddings(vecs, window=7)
    if N < 4:
        return 2

    # Compute adjacent cosine similarities
    gap_sims = np.array([float(svecs[i] @ svecs[i + 1]) for i in range(N - 1)])
    # Sort ascending — valley positions
    max_k = min(max_k, N // 4, 40)

    # Try k from 2..max_k, measure residual variance at each k
    variances = []
    for k in range(2, max_k + 1):
        bounds = divisive_seg(svecs, n_segments=k)
        # Compute within-segment variance of gap_sims
        segs = []
        prev = 0
        for b in bounds:
            if b - prev > 0:
                segs.extend(gap_sims[prev:b - 1].tolist())
            prev = b
        if N - prev > 0:
            segs.extend(gap_sims[prev:N - 1].tolist())
        variances.append(float(np.var(segs)) if segs else 0.0)

    if not variances:
        return 2

    # Find elbow: largest drop in variance
    variances = np.array(variances)
    drops = np.diff(variances)
    if len(drops) == 0:
        return 2
    # Largest absolute drop
    elbow = int(np.argmin(drops)) + 2  # +2 since k starts at 2
    return max(2, min(elbow, max_k))


def cross_model_threshold(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5large",
    window: int = 9,
    threshold: float = 0.60,
    min_k: int = 2,
    max_k_frac: float = 1.5,
) -> list[int]:
    """Cross-model ensemble with score threshold instead of fixed-k.

    Select boundaries where the combined (normalized) score exceeds threshold.
    Falls back to top-max_k if too many pass threshold.
    This adapts k based on evidence strength rather than GT chapter count.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)
    over_k = min(N_cap - 1, max(10, round(n_segments * max_k_frac * 2)))

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        k = max(min_k, round(n_segments * 0.80))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v2 = smooth_embeddings(v2_raw[:N], window=window)
    _, s1 = divisive_seg(v1[:N], n_segments=min(over_k, N - 1), return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=min(over_k, N - 1), return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1[:N], n_segments=min_k)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    combined = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    max_combined = max(combined.values())
    thresh = max_combined * threshold
    candidates = [p for p, s in combined.items() if s >= thresh]

    # Clamp to max_k
    max_k = min(round(n_segments * max_k_frac), N - 1)
    if len(candidates) > max_k:
        candidates = sorted(combined, key=lambda x: -combined[x])[:max_k]
    if len(candidates) < min_k:
        candidates = sorted(combined, key=lambda x: -combined[x])[:min_k]

    return sorted(b for b in candidates if 0 < b < N)


def weighted_cross_model(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5large",
    window: int = 9,
    frac: float = 0.70,
    w1: float = 0.55,  # weight for primary model
) -> list[int]:
    """Cross-model ensemble with asymmetric weights.

    Primary model (BGE base) gets w1 weight, secondary (E5-large) gets 1-w1.
    The optimal weighting depends on each model's individual accuracy.
    BGE has Pk=0.3884 individually, E5-large likely similar — equal weighting
    may not be optimal. We search w1 in (0.5, 0.7) range.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)
    k = max(2, round(n_segments * frac))
    over_k = min(N_cap - 1, k * 4 + 2)

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v2 = smooth_embeddings(v2_raw[:N], window=window)
    _, s1 = divisive_seg(v1[:N], n_segments=min(over_k, N - 1), return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=min(over_k, N - 1), return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1[:N], n_segments=k)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    w2 = 1.0 - w1
    combined = {p: w1 * (s1.get(p, 0) / max1) + w2 * (s2.get(p, 0) / max2)
                for p in all_pos}
    top_k = sorted(combined, key=lambda x: -combined[x])[:k]
    return sorted(b for b in top_k if 0 < b < N)


def concat_embed_seg(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5large",
    window: int = 9,
    frac: float = 0.80,
) -> list[int]:
    """Concatenate two embedding spaces and run divisive on combined vectors.

    Instead of averaging scores from two models, this L2-normalises each
    embedding space, concatenates them, then re-normalises. Divisive then
    operates in the combined space, potentially capturing cross-space
    boundary signals.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        k = max(2, round(n_segments * frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    # Concatenate and re-normalise
    v_cat = np.concatenate([v1[:N], v2], axis=1)
    norms = np.linalg.norm(v_cat, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    v_cat = v_cat / norms

    k = max(2, round(n_segments * frac))
    return divisive_seg(v_cat, n_segments=k)


def cross_model_ce_rerank(
    vecs_primary: np.ndarray,
    texts: list[str],
    vid: str,
    n_segments: int,
    window: int = 9,
    frac: float = 0.80,
) -> list[int]:
    """Cross-model ensemble followed by cross-encoder re-ranking.

    Step 1: Get top-2k candidate boundaries from BGE+E5large ensemble.
    Step 2: Re-rank candidates using finetuned cross-encoder (MiniLM).
    Step 3: Return top-k by cross-encoder score.

    This is much faster than cross-encoder-only scoring (scores 2k pairs
    instead of N-1 pairs), while using the cross-encoder's quality signal.
    """
    CE_PATH = ROOT / "models" / "crossencoder"
    if not CE_PATH.exists():
        # Fall back to cross_model without re-ranking
        return cross_model_ensemble_seg(vecs_primary, vid, n_segments,
                                        secondary_model="e5large",
                                        window=window, frac=frac)

    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)
    k = max(2, round(n_segments * frac))
    over_k = min(N_cap - 1, k * 3 + 2)

    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is None:
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v2 = smooth_embeddings(v2_raw[:N], window=window)
    _, s1 = divisive_seg(v1[:N], n_segments=min(over_k, N - 1), return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=min(over_k, N - 1), return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1[:N], n_segments=k)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    combined = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}
    # Get top-2k candidates from ensemble
    top_2k = sorted(combined, key=lambda x: -combined[x])[:min(k * 2 + 2, len(combined))]

    # Re-rank with cross-encoder
    import torch
    from sentence_transformers.cross_encoder import CrossEncoder
    global _crossenc_model
    if _crossenc_model is None:
        _crossenc_model = CrossEncoder(
            str(CE_PATH), num_labels=1,
            default_activation_function=torch.nn.Sigmoid()
        )
    texts_cap = texts[:N_cap]
    pairs = [[texts_cap[b - 1], texts_cap[b]] if b < len(texts_cap) else ["", ""] for b in top_2k]
    ce_scores = _crossenc_model.predict(pairs, batch_size=32, show_progress_bar=False)
    ce_scores = np.array(ce_scores)
    best_k_idx = np.argsort(-ce_scores)[:k]
    return sorted(top_2k[i] for i in best_k_idx if 0 < top_2k[i] < N)


def cross_model_conservative(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5large",
    window: int = 9,
    frac: float = 0.75,
) -> list[int]:
    """Cross-model ensemble + conservative k prediction."""
    return cross_model_ensemble_seg(vecs_primary, vid, n_segments,
                                    secondary_model=secondary_model,
                                    window=window, frac=frac)


def cross_model_nms(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5large",
    window: int = 9,
    frac: float = 0.70,
    min_gap: int = 10,
) -> list[int]:
    """Cross-model ensemble with greedy NMS-style spacing enforcement.

    Instead of post-hoc min_seg_filter, enforces minimum spacing DURING
    boundary selection: after picking the highest-scoring boundary, suppress
    all candidates within min_gap sentences before picking the next.
    This guarantees all selected segments are >= min_gap long, while
    maximizing the score of selected boundaries (unlike post-hoc removal).
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)
    k = max(2, round(n_segments * frac))
    over_k = min(N_cap - 1, k * 6 + 2)  # Larger oversample for NMS

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        raw = divisive_seg(v1, n_segments=k)
        return min_seg_filter(raw, len(v1), min_seg=min_gap)

    N = min(N_cap, len(v2_raw))
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    _, s1 = divisive_seg(v1[:N], n_segments=min(over_k, N - 1), return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=min(over_k, N - 1), return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1[:N], n_segments=k)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    combined = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    # Greedy NMS: pick top-score boundary, suppress within min_gap, repeat
    ranked = sorted(combined, key=lambda x: -combined[x])
    selected = []
    suppressed = set()
    for b in ranked:
        if len(selected) >= k:
            break
        if b in suppressed:
            continue
        selected.append(b)
        # Suppress positions too close to this boundary (before AND after)
        # A gap-i boundary means segment break between sentence i and i+1
        # so segment [prev_b, b] and [b, next_b] must both be >= min_gap
        for d in range(-min_gap + 1, min_gap):
            suppressed.add(b + d)

    return sorted(b for b in selected if 0 < b < N)


def triple_model_ensemble_seg(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    models: list[str] = None,
    window: int = 9,
    frac: float = 0.80,
) -> list[int]:
    """Ensemble boundary scores from three embedding models.

    Loads all available secondary models and averages rank-normalized scores.
    """
    if models is None:
        models = ["bge_large", "e5large", "stella"]
    N_cap = min(len(vecs_primary), 800)
    v_primary = smooth_embeddings(vecs_primary[:N_cap], window=window)
    k = max(2, round(n_segments * frac))
    over_k = min(N_cap - 1, k * 4 + 2)

    all_score_dicts = []
    _, s0 = divisive_seg(v_primary, n_segments=over_k, return_scores=True)
    if s0:
        all_score_dicts.append(s0)

    for model in models:
        v_sec = load_embeddings_model(vid, model)
        if v_sec is None:
            continue
        N = min(N_cap, len(v_sec))
        v_sm = smooth_embeddings(v_sec[:N], window=window)
        _, s = divisive_seg(v_sm[:N_cap], n_segments=min(over_k, N - 1), return_scores=True)
        if s:
            all_score_dicts.append(s)

    if not all_score_dicts:
        return divisive_seg(v_primary, n_segments=k)

    all_pos = sorted(set().union(*[set(sd) for sd in all_score_dicts]))
    combined = {}
    for pos in all_pos:
        scores = []
        for sd in all_score_dicts:
            if pos in sd:
                max_s = max(sd.values()) or 1.0
                scores.append(sd[pos] / max_s)
        combined[pos] = sum(scores) / len(all_score_dicts)

    top_k = sorted(combined, key=lambda x: -combined[x])[:k]
    return sorted(b for b in top_k if 0 < b < N_cap)


def cross_model_prosody_rerank(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    prosody_gap: np.ndarray | None,
    window: int = 9,
    frac: float = 0.70,
) -> list[int]:
    """Cross-model ensemble (BGE+E5) candidates re-ranked with prosody signal.

    Oversample 3x by cross-model ensemble, then re-score each candidate as
    0.7*cross_score + 0.3*prosody_score if prosody is available.
    Falls back to plain cross-model if no prosody.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)
    k = max(2, round(n_segments * frac))

    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is None:
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    over_k = min(N - 1, k * 3 + 2)
    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    cross_scores = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    if prosody_gap is not None and len(prosody_gap) >= max(all_pos, default=0):
        pros_arr = np.array([float(prosody_gap[p - 1]) if 0 < p <= len(prosody_gap) else 0.0
                             for p in all_pos], dtype=np.float32)
        max_pros = pros_arr.max() if pros_arr.max() > 0 else 1.0
        pros_scores = {p: float(pros_arr[i]) / max_pros for i, p in enumerate(all_pos)}
        combined = {p: 0.7 * cross_scores[p] + 0.3 * pros_scores[p] for p in all_pos}
    else:
        combined = cross_scores

    top_k = sorted(combined, key=lambda x: -combined[x])[:k]
    return sorted(b for b in top_k if 0 < b < N)


def multi_resolution_cross_e5(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    frac: float = 0.70,
    windows: tuple[int, ...] = (7, 9, 11),
) -> list[int]:
    """Cross-model (BGE+E5) ensemble over multiple smoothing windows.

    For each window size, compute rank-normalized divisive scores from both models.
    Average all scores: positions that rank highly at multiple scales are more
    likely true boundaries.
    """
    N_cap = min(len(vecs_primary), 800)
    k = max(2, round(n_segments * frac))

    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is None:
        v1 = smooth_embeddings(vecs_primary[:N_cap], window=9)
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1_raw = vecs_primary[:N]
    v2_raw = v2_raw[:N]
    over_k = min(N - 1, k * 4 + 2)

    all_score_dicts = []
    for w in windows:
        sv1 = smooth_embeddings(v1_raw, window=w)
        sv2 = smooth_embeddings(v2_raw, window=w)
        _, s1 = divisive_seg(sv1, n_segments=over_k, return_scores=True)
        _, s2 = divisive_seg(sv2, n_segments=over_k, return_scores=True)
        if s1:
            all_score_dicts.append(s1)
        if s2:
            all_score_dicts.append(s2)

    if not all_score_dicts:
        return divisive_seg(smooth_embeddings(v1_raw, window=9), n_segments=k)

    all_pos = sorted(set().union(*[set(sd) for sd in all_score_dicts]))
    combined = {}
    for p in all_pos:
        scores = []
        for sd in all_score_dicts:
            if p in sd:
                mx = max(sd.values()) or 1.0
                scores.append(sd[p] / mx)
        combined[p] = sum(scores) / len(all_score_dicts)

    top_k = sorted(combined, key=lambda x: -combined[x])[:k]
    return sorted(b for b in top_k if 0 < b < N)


def boundary_local_shift(
    boundaries: list[int],
    vecs_primary: np.ndarray,
    vid: str,
    window: int = 2,
) -> list[int]:
    """Post-hoc local shift: move each predicted boundary to the nearest cosine minimum.

    For each predicted boundary b, search in [b-window, b+window] for the position
    with the lowest cosine similarity between adjacent (smoothed) sentences.
    This corrects small off-by-one errors in boundary placement.
    """
    if not boundaries:
        return boundaries
    N_cap = min(len(vecs_primary), 800)
    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is not None:
        N = min(N_cap, len(v2_raw))
        # Use BGE (primary) smoothed for local shift — both models agree on same positions
        sv = smooth_embeddings(vecs_primary[:N], window=9)
    else:
        sv = smooth_embeddings(vecs_primary[:N_cap], window=9)
        N = len(sv)

    # Precompute adjacent cosine similarities
    adj_sim = np.array([float(sv[i] @ sv[i + 1]) for i in range(N - 1)], dtype=np.float32)

    shifted = []
    used = set()
    for b in sorted(boundaries):
        lo = max(1, b - window)
        hi = min(N - 1, b + window + 1)
        region = range(lo, hi)
        best = min(region, key=lambda x: adj_sim[x - 1])
        if best not in used:
            shifted.append(best)
            used.add(best)
        elif b not in used:
            shifted.append(b)
            used.add(b)
    return sorted(shifted)


def cross_e5_combined_depth(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    frac: float = 0.70,
    window: int = 9,
    depth_w: int = 7,
) -> list[int]:
    """Cross-model depth score: combine BGE+E5 embeddings then use TextTiling depth.

    1. Average the smoothed BGE and E5-large embeddings (combined representation).
    2. L2-normalize the combined vectors.
    3. For each gap, compute the dissimilarity between mean of depth_w sentences
       before vs after (local topic-shift score).
    4. Select top-k by topic-shift score.

    Different from iterative_cross_e5: uses a fixed window instead of segment means.
    More like TextTiling but applied to a richer combined embedding space.
    """
    N_cap = min(len(vecs_primary), 800)

    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is None:
        sv = smooth_embeddings(vecs_primary[:N_cap], window=window)
        N = N_cap
    else:
        N = min(N_cap, len(v2_raw))
        sv1 = smooth_embeddings(vecs_primary[:N], window=window)
        sv2 = smooth_embeddings(v2_raw[:N], window=window)

    k = max(2, round(n_segments * frac))

    def _depth_scores(sv: np.ndarray) -> np.ndarray:
        M = len(sv)
        csums = np.zeros((M + 1, sv.shape[1]), dtype=np.float64)
        csums[1:] = np.cumsum(sv.astype(np.float64), axis=0)
        ts = np.zeros(M - 1, dtype=np.float32)
        for i in range(M - 1):
            lo_l = max(0, i - depth_w + 1)
            left = csums[i + 1] - csums[lo_l]
            n_left = i + 1 - lo_l
            hi_r = min(M, i + 1 + depth_w)
            right = csums[hi_r] - csums[i + 1]
            n_right = hi_r - i - 1
            if n_left > 0 and n_right > 0:
                lm, rm = left / n_left, right / n_right
                nl, nr = np.linalg.norm(lm), np.linalg.norm(rm)
                if nl > 0 and nr > 0:
                    ts[i] = 1.0 - float(lm @ rm) / (nl * nr)
        return ts

    if v2_raw is None:
        topic_shift = _depth_scores(sv)
    else:
        ts1 = _depth_scores(sv1)
        ts2 = _depth_scores(sv2)
        max_ts1 = ts1.max() if ts1.max() > 0 else 1.0
        max_ts2 = ts2.max() if ts2.max() > 0 else 1.0
        topic_shift = (ts1 / max_ts1 + ts2 / max_ts2) / 2

    top_k = np.argsort(-topic_shift)[:k]
    return sorted(int(i) + 1 for i in top_k)


def cross_e5_adaptive_k(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    window: int = 9,
    base_frac: float = 0.70,
    high_frac: float = 0.80,
    low_frac: float = 0.60,
) -> list[int]:
    """Cross-model ensemble with confidence-adaptive k prediction.

    If the boundary score curve has high normalized variance (clear peaks),
    use higher frac (predictions are more reliable). If low variance (flat),
    use lower frac (fewer, more certain boundaries).
    Variance is computed on the combined scores relative to the mean.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is None:
        k = max(2, round(n_segments * base_frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    k_base = max(2, round(n_segments * base_frac))
    over_k = min(N - 1, k_base * 5 + 2)

    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k_base)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    combined = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    # Compute coefficient of variation of combined scores
    scores_arr = np.array(list(combined.values()), dtype=np.float32)
    mean_score = scores_arr.mean()
    std_score = scores_arr.std()
    cv = std_score / (mean_score + 1e-8)

    # Calibrate frac by confidence: high CV = clear boundaries = use higher frac
    # Typical CV range observed empirically: 0.3 (flat) to 0.9 (clear peaks)
    if cv > 0.65:
        frac = high_frac
    elif cv < 0.40:
        frac = low_frac
    else:
        frac = base_frac

    k = max(2, round(n_segments * frac))
    top_k = sorted(combined, key=lambda x: -combined[x])[:k]
    return sorted(b for b in top_k if 0 < b < N)


def _seg_dissim_per_model(vecs: np.ndarray, bounds_arr: list[int], cands: list[int]) -> dict[int, float]:
    """Compute segment dissimilarity for each candidate boundary using its neighbor segments."""
    result = {}
    for idx, b in enumerate(cands):
        l_s, l_e = bounds_arr[idx], b
        r_s, r_e = b, bounds_arr[idx + 2]
        if l_e <= l_s or r_e <= r_s:
            result[b] = 0.0
            continue
        lm = vecs[l_s:l_e].mean(axis=0)
        rm = vecs[r_s:r_e].mean(axis=0)
        nl, nr = np.linalg.norm(lm), np.linalg.norm(rm)
        result[b] = float(1.0 - lm @ rm / (nl * nr)) if nl > 0 and nr > 0 else 0.0
    return result


def iterative_cross_e5_with_prosody(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    prosody_gap: np.ndarray | None,
    frac: float = 0.75,
    window: int = 9,
    w_cross: float = 0.4,
    w_seg: float = 0.4,
    w_pros: float = 0.2,
) -> list[int]:
    """Iterative cross-model + prosody: per-model segment dissimilarity + prosody fusion.

    Computes segment dissimilarity separately per model (handles dim mismatch).
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is None:
        k = max(2, round(n_segments * frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    k_final = max(2, round(n_segments * frac))
    k_rough = min(n_segments, N - 1)
    over_k = min(N - 1, k_rough * 3 + 2)

    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k_final)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    cross_scores = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    top_cands = sorted(cross_scores, key=lambda x: -cross_scores[x])[:min(k_final * 2, len(all_pos))]
    top_cands = sorted(top_cands)
    bounds_arr = [0] + top_cands + [N]

    seg1 = _seg_dissim_per_model(v1, bounds_arr, top_cands)
    seg2 = _seg_dissim_per_model(v2, bounds_arr, top_cands)
    max_s1 = max(seg1.values(), default=1.0) or 1.0
    max_s2 = max(seg2.values(), default=1.0) or 1.0
    seg_scores_n = {b: (seg1[b] / max_s1 + seg2[b] / max_s2) / 2 for b in top_cands}

    if prosody_gap is not None and len(prosody_gap) > 0:
        pros_vals = [float(prosody_gap[b - 1]) if 0 < b <= len(prosody_gap) else 0.0
                     for b in top_cands]
        max_pros = max(pros_vals) if pros_vals and max(pros_vals) > 0 else 1.0
        pros_scores = {b: v / max_pros for b, v in zip(top_cands, pros_vals)}
        combined = {b: w_cross * cross_scores[b] + w_seg * seg_scores_n[b] + w_pros * pros_scores.get(b, 0.0)
                    for b in top_cands}
    else:
        combined = {b: 0.5 * cross_scores[b] + 0.5 * seg_scores_n[b] for b in top_cands}

    top_k = sorted(combined, key=lambda x: -combined[x])[:k_final]
    return sorted(b for b in top_k if 0 < b < N)


def iterative_cross_e5_v2(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    frac: float = 0.75,
    window: int = 9,
    cand_mult: int = 3,
    w_cross: float = 0.3,
    w_seg: float = 0.7,
) -> list[int]:
    """Iterative cross-model v2: larger candidate pool, tunable blend weights.

    Uses cand_mult*k candidates for rescoring (vs 2k in v1).
    Blend weights w_cross and w_seg control cross-model vs segment-dissimilarity.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is None:
        k = max(2, round(n_segments * frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    k_final = max(2, round(n_segments * frac))
    k_rough = min(n_segments, N - 1)
    over_k = min(N - 1, k_rough * 4 + 2)

    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k_final)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    cross_scores = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    # Use larger candidate pool
    top_cands = sorted(cross_scores, key=lambda x: -cross_scores[x])[:min(k_final * cand_mult, len(all_pos))]
    top_cands = sorted(top_cands)
    bounds_arr = [0] + top_cands + [N]

    # Per-model segment dissimilarity (handles dimension mismatch between models)
    seg1 = _seg_dissim_per_model(v1, bounds_arr, top_cands)
    seg2 = _seg_dissim_per_model(v2, bounds_arr, top_cands)
    max_s1 = max(seg1.values(), default=1.0) or 1.0
    max_s2 = max(seg2.values(), default=1.0) or 1.0
    seg_scores_n = {b: (seg1[b] / max_s1 + seg2[b] / max_s2) / 2 for b in top_cands}

    combined = {b: w_cross * cross_scores[b] + w_seg * seg_scores_n[b]
                for b in top_cands}

    top_k = sorted(combined, key=lambda x: -combined[x])[:k_final]
    return sorted(b for b in top_k if 0 < b < N)


def iterative_cross_e5(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    frac: float = 0.70,
    window: int = 9,
) -> list[int]:
    """Two-pass cross-model segmentation: rough segments then segment-level refinement.

    Pass 1: Cross-model ensemble with full k to get rough segment boundaries.
    Pass 2: Compute mean embedding per rough segment, find which rough boundaries
            have the highest inter-segment dissimilarity, keep top-k (frac*GT).

    Segment-level comparison is more noise-robust than sentence-level.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    v2_raw = load_embeddings_model(vid, "e5large")
    if v2_raw is None:
        k = max(2, round(n_segments * frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    # Pass 1: rough segmentation with full k
    k_rough = min(n_segments, N - 1)
    k_final = max(2, round(n_segments * frac))
    over_k = min(N - 1, k_rough * 3 + 2)

    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k_final)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    cross_scores = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    # Pass 2: Per-model segment dissimilarity re-scoring (handles dimension mismatch)
    top_cands = sorted(cross_scores, key=lambda x: -cross_scores[x])[:min(k_final * 2, len(all_pos))]
    top_cands = sorted(top_cands)
    bounds_arr = [0] + top_cands + [N]

    seg1 = _seg_dissim_per_model(v1, bounds_arr, top_cands)
    seg2 = _seg_dissim_per_model(v2, bounds_arr, top_cands)
    max_s1 = max(seg1.values(), default=1.0) or 1.0
    max_s2 = max(seg2.values(), default=1.0) or 1.0

    seg_scores = {b: 0.5 * cross_scores[b] + 0.5 * (seg1[b] / max_s1 + seg2[b] / max_s2) / 2
                  for b in top_cands}

    top_k = sorted(seg_scores, key=lambda x: -seg_scores[x])[:k_final]
    return sorted(b for b in top_k if 0 < b < N)


def iterative_cross_fixed_window(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5",
    frac: float = 0.70,
    window: int = 9,
    seg_window: int = 15,
    w_cross: float = 0.4,
    w_seg: float = 0.6,
    cand_mult: int = 2,
) -> list[int]:
    """Iterative cross-model with fixed-window segment scoring (no circular dependency).

    For each candidate boundary b, compute:
      left_mean = mean(v[max(0,b-seg_window):b])
      right_mean = mean(v[b:min(N,b+seg_window)])
      seg_score = 1 - cosine(left_mean, right_mean)

    This cleanly measures local topic shift without depending on other boundaries.
    Computed per-model to handle dimension mismatch.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        k = max(2, round(n_segments * frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    k_final = max(2, round(n_segments * frac))
    over_k = min(N - 1, max(k_final * cand_mult + 2, k_final + 4))

    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k_final)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    cross_scores = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    top_cands = sorted(cross_scores, key=lambda x: -cross_scores[x])[:min(k_final * cand_mult, len(all_pos))]

    def _fw_seg_score(vecs: np.ndarray, cands: list[int]) -> dict[int, float]:
        scores = {}
        for b in cands:
            lo = max(0, b - seg_window)
            hi = min(len(vecs), b + seg_window)
            lm = vecs[lo:b].mean(axis=0) if b > lo else np.zeros(vecs.shape[1])
            rm = vecs[b:hi].mean(axis=0) if hi > b else np.zeros(vecs.shape[1])
            nl, nr = np.linalg.norm(lm), np.linalg.norm(rm)
            scores[b] = float(1.0 - lm @ rm / (nl * nr)) if nl > 0 and nr > 0 else 0.0
        return scores

    fw1 = _fw_seg_score(v1, top_cands)
    fw2 = _fw_seg_score(v2, top_cands)
    max_fw1 = max(fw1.values(), default=1.0) or 1.0
    max_fw2 = max(fw2.values(), default=1.0) or 1.0
    seg_scores_n = {b: (fw1[b] / max_fw1 + fw2[b] / max_fw2) / 2 for b in top_cands}

    combined = {b: w_cross * cross_scores[b] + w_seg * seg_scores_n[b] for b in top_cands}
    top_k = sorted(combined, key=lambda x: -combined[x])[:k_final]
    return sorted(b for b in top_k if 0 < b < N)


def contrastive_boundary_score(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5",
    frac: float = 0.70,
    window: int = 9,
    ctx_w: int = 10,
    w_cross: float = 0.4,
    w_contrast: float = 0.6,
    cand_mult: int = 2,
) -> list[int]:
    """Contrastive membership boundary scoring + cross-model ensemble.

    For each candidate boundary b, compute a 'contrastive score':
      right_fit = sim(v[b], mean(v[b:b+ctx_w]))  -- fits in right context?
      left_fit  = sim(v[b], mean(v[b-ctx_w:b]))  -- fits in left context?
      contrast  = right_fit - left_fit

    If v[b] fits better in right context (contrast > 0), this is likely a topic boundary.
    Combined with cross-model score for final selection.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        k = max(2, round(n_segments * frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    k_final = max(2, round(n_segments * frac))
    over_k = min(N - 1, k_final * (cand_mult + 2) + 2)

    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k_final)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    cross_scores = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    top_cands = sorted(cross_scores, key=lambda x: -cross_scores[x])[:min(k_final * cand_mult, len(all_pos))]

    def _contrast(vecs: np.ndarray, cands: list[int]) -> dict[int, float]:
        scores = {}
        for b in cands:
            if b <= 0 or b >= len(vecs):
                scores[b] = 0.0
                continue
            sv = vecs[b]
            nl_sv = np.linalg.norm(sv)
            if nl_sv < 1e-8:
                scores[b] = 0.0
                continue
            # Right context mean
            r_end = min(len(vecs), b + ctx_w)
            rm = vecs[b:r_end].mean(axis=0)
            # Left context mean (excluding b itself)
            l_start = max(0, b - ctx_w)
            lm = vecs[l_start:b].mean(axis=0)
            nr, nl = np.linalg.norm(rm), np.linalg.norm(lm)
            right_fit = float(sv @ rm) / (nl_sv * nr) if nr > 0 else 0.0
            left_fit = float(sv @ lm) / (nl_sv * nl) if nl > 0 else 0.0
            scores[b] = right_fit - left_fit  # positive = fits right context better
        return scores

    c1 = _contrast(v1, top_cands)
    c2 = _contrast(v2, top_cands)

    # Normalize contrast scores: shift so 0 is median, scale to [0,1]
    def _normalize_contrast(c: dict[int, float]) -> dict[int, float]:
        vals = list(c.values())
        if not vals:
            return c
        med = float(np.median(vals))
        arr = np.array(vals)
        rng = max(arr.max() - arr.min(), 1e-8)
        return {b: (c[b] - med) / rng + 0.5 for b in c}

    c1n = _normalize_contrast(c1)
    c2n = _normalize_contrast(c2)
    contrast_scores = {b: (c1n[b] + c2n[b]) / 2 for b in top_cands}

    combined = {b: w_cross * cross_scores[b] + w_contrast * contrast_scores.get(b, 0.5)
                for b in top_cands}
    top_k = sorted(combined, key=lambda x: -combined[x])[:k_final]
    return sorted(b for b in top_k if 0 < b < N)


def iterative_cross_e5_generic(
    vecs_primary: np.ndarray,
    vid: str,
    n_segments: int,
    secondary_model: str = "e5",
    frac: float = 0.70,
    window: int = 9,
    w_cross: float = 0.5,
    w_seg: float = 0.5,
    cand_mult: int = 2,
) -> list[int]:
    """Iterative two-pass segmentation with any secondary model.

    Generic version: works with any (primary, secondary) model pair regardless
    of embedding dimensionality. Uses per-model segment dissimilarity scoring.
    """
    N_cap = min(len(vecs_primary), 800)
    v1 = smooth_embeddings(vecs_primary[:N_cap], window=window)

    v2_raw = load_embeddings_model(vid, secondary_model)
    if v2_raw is None:
        k = max(2, round(n_segments * frac))
        return divisive_seg(v1, n_segments=k)

    N = min(N_cap, len(v2_raw))
    v1 = v1[:N]
    v2 = smooth_embeddings(v2_raw[:N], window=window)

    k_final = max(2, round(n_segments * frac))
    k_rough = min(n_segments, N - 1)
    over_k = min(N - 1, k_rough * 3 + 2)

    _, s1 = divisive_seg(v1, n_segments=over_k, return_scores=True)
    _, s2 = divisive_seg(v2, n_segments=over_k, return_scores=True)

    all_pos = sorted(set(s1) | set(s2))
    if not all_pos:
        return divisive_seg(v1, n_segments=k_final)

    max1 = max(s1.values(), default=1.0) or 1.0
    max2 = max(s2.values(), default=1.0) or 1.0
    cross_scores = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}

    top_cands = sorted(cross_scores, key=lambda x: -cross_scores[x])[:min(k_final * cand_mult, len(all_pos))]
    top_cands = sorted(top_cands)
    bounds_arr = [0] + top_cands + [N]

    seg1 = _seg_dissim_per_model(v1, bounds_arr, top_cands)
    seg2 = _seg_dissim_per_model(v2, bounds_arr, top_cands)
    max_s1 = max(seg1.values(), default=1.0) or 1.0
    max_s2 = max(seg2.values(), default=1.0) or 1.0
    seg_scores_n = {b: (seg1[b] / max_s1 + seg2[b] / max_s2) / 2 for b in top_cands}

    combined = {b: w_cross * cross_scores[b] + w_seg * seg_scores_n[b] for b in top_cands}
    top_k = sorted(combined, key=lambda x: -combined[x])[:k_final]
    return sorted(b for b in top_k if 0 < b < N)


def _two_stage_prosody(
    vecs: np.ndarray,
    n_segments: int,
    prosody_gap: np.ndarray | None,
) -> list[int]:
    p = TwoStageBoundaryPredictor()
    modality = {}
    if prosody_gap is not None:
        modality["prosody"] = prosody_gap
    return p.predict(text_vecs=vecs, modality_scores=modality or None, n_segments=n_segments)


def _hierarchical_prosody(
    vecs: np.ndarray,
    n_segments: int,
    prosody_gap: np.ndarray | None,
) -> list[int]:
    seg = HierarchicalSegmenter()
    modality = {}
    if prosody_gap is not None:
        modality["prosody"] = prosody_gap
    try:
        tree = seg.segment(vecs, n_subtopics=n_segments, modality_scores=modality or None)
    except TypeError:
        tree = seg.segment(vecs, n_subtopics=n_segments)
    return tree.chapters


def _load_ground_truth(vid: str, use_youtube: bool = False, draft_ok: bool = False) -> dict | None:
    if use_youtube:
        p = GT_YOUTUBE / f"{vid}.json"
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        # Convert YouTube GT format to gt_hier chapters format
        titles = d.get("titles", [])
        boundaries = [0.0] + list(d.get("boundaries_sec", []))
        chapters = [{"start_sec": s, "title": t} for s, t in zip(boundaries, titles)]
        return {"chapters": chapters, "status": "youtube_gt", "video_id": vid}
    p = GT_HIER / f"{vid}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    allowed = ("reviewed", "done") + (("draft",) if draft_ok else ())
    if d.get("status") not in allowed:
        return None
    return d


def _load_sentences(vid: str) -> list[dict] | None:
    p = SENTENCES_DIR / vid / "sentences.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("sentences", [])


def _load_embeddings(vid: str, model: str = "mpnet") -> np.ndarray | None:
    p = EMBEDDINGS_DIR / model / vid / "embeddings.npy"
    if not p.exists():
        return None
    return np.load(str(p)).astype(np.float32)


def _run_method(
    method: str,
    sentences: list[dict],
    vecs: np.ndarray,
    n_segments: int,
    prosody_gap: np.ndarray | None = None,
    shot_gap: np.ndarray | None = None,
    chunk_size: int = 4,
    vid: str = "",
) -> list[int]:
    """Run a named segmentation method and return boundary indices."""
    texts = [s["text"] for s in sentences]
    N = len(sentences)

    if method == "texttiling":
        return texttiling(texts)
    elif method == "c99":
        return c99(texts, n_segments=n_segments)
    elif method == "cosine":
        return cosine_seg(vecs, n_segments=n_segments)
    elif method == "kmeans":
        return kmeans_seg(vecs, n_segments=n_segments)
    elif method == "bert_seg":
        return bert_seg(vecs, n_segments=n_segments)
    elif method == "two_stage":
        p = TwoStageBoundaryPredictor()
        return p.predict(text_vecs=vecs, n_segments=n_segments)
    elif method == "two_stage_prosody":
        return _two_stage_prosody(vecs, n_segments, prosody_gap)
    elif method == "two_stage_chunked":
        cvecs = chunk_vecs(vecs, chunk_size=chunk_size)
        if len(cvecs) < 2:
            return cosine_seg(vecs, n_segments=n_segments)
        p = TwoStageBoundaryPredictor()
        cb = p.predict(text_vecs=cvecs, n_segments=n_segments)
        return chunk_boundaries_to_sentences(cb, chunk_size, N)
    elif method == "hierarchical":
        seg = HierarchicalSegmenter()
        tree = seg.segment(vecs, n_subtopics=n_segments)
        return tree.chapters
    elif method == "hierarchical_prosody":
        return _hierarchical_prosody(vecs, n_segments, prosody_gap)
    elif method == "divisive":
        return divisive_seg(vecs, n_segments=n_segments)
    elif method == "divisive_chunked":
        cvecs = chunk_vecs(vecs, chunk_size=chunk_size)
        if len(cvecs) < 2:
            return divisive_seg(vecs, n_segments=n_segments)
        cb = divisive_seg(cvecs, n_segments=n_segments)
        return chunk_boundaries_to_sentences(cb, chunk_size, N)
    elif method == "divisive_chunked3":
        cs = 3
        cvecs = chunk_vecs(vecs, chunk_size=cs)
        if len(cvecs) < 2:
            return divisive_seg(vecs, n_segments=n_segments)
        cb = divisive_seg(cvecs, n_segments=n_segments)
        return chunk_boundaries_to_sentences(cb, cs, N)
    elif method == "divisive_prosody":
        return _divisive_prosody(vecs, n_segments, prosody_gap)
    elif method == "divisive_shots":
        return _divisive_multi(vecs, n_segments, None, shot_gap,
                               w_cos=0.7, w_pros=0.0, w_shot=0.3)
    elif method == "divisive_prosody_shots":
        return _divisive_multi(vecs, n_segments, prosody_gap, shot_gap,
                               w_cos=0.6, w_pros=0.2, w_shot=0.2)
    elif method == "divisive_llm":
        return _divisive_llm(vecs, n_segments, sentences)
    elif method == "bert_wiki":
        return _bert_wiki_seg(texts, n_segments)
    elif method == "depth":
        return depth_seg(vecs, n_segments, window=5)
    elif method == "depth_w3":
        return depth_seg(vecs, n_segments, window=3)
    elif method == "depth_w9":
        return depth_seg(vecs, n_segments, window=9)
    elif method == "depth_smooth":
        return depth_seg_smooth(vecs, n_segments, window=5, smooth_w=7)
    elif method == "depth_smooth_prosody":
        svecs = smooth_embeddings(vecs, window=7)
        base = depth_seg(svecs, n_segments, window=5)
        return _divisive_prosody(svecs, n_segments, prosody_gap) if prosody_gap is not None else base
    elif method == "crossencoder":
        return crossencoder_seg(texts, n_segments)
    elif method == "divisive_smooth9":
        return divisive_seg(smooth_embeddings(vecs, window=9), n_segments=n_segments)
    elif method == "divisive_smooth11":
        return divisive_seg(smooth_embeddings(vecs, window=11), n_segments=n_segments)
    elif method == "divisive_block5":
        return divisive_block(texts, n_segments, window=5)
    elif method == "divisive_block7":
        return divisive_block(texts, n_segments, window=7)
    elif method == "divisive_block9":
        return divisive_block(texts, n_segments, window=9)
    elif method == "divisive_bic":
        return divisive_bic(vecs)
    elif method == "divisive_bic_smooth":
        return divisive_bic_smooth(vecs)
    elif method == "divisive_minlen":
        return divisive_minlen(vecs, n_segments)
    elif method == "divisive_smooth7_minlen":
        return divisive_smooth7_minlen(vecs, n_segments)
    elif method == "divisive_elbow":
        return divisive_elbow(vecs)
    elif method == "divisive_elbow_smooth":
        return divisive_elbow_smooth(vecs)
    elif method == "dp":
        return dp_seg(vecs, n_segments)
    elif method == "dp_smooth":
        return dp_seg_smooth(vecs, n_segments)
    elif method == "cosine_drop":
        return cosine_drop_seg(vecs, n_segments)
    elif method == "cosine_drop_smooth":
        return cosine_drop_smooth_seg(vecs, n_segments)
    elif method == "ensemble":
        return ensemble_seg(vecs, n_segments)
    elif method == "ensemble_smooth":
        return ensemble_smooth_seg(vecs, n_segments)
    elif method == "recency":
        return recency_seg(vecs, n_segments)
    elif method == "recency_smooth":
        return recency_seg_smooth(vecs, n_segments)
    elif method == "divisive_recency":
        return divisive_recency(vecs, n_segments)
    elif method == "divisive_recency_smooth":
        return divisive_recency_smooth(vecs, n_segments)
    elif method == "divisive_smooth13":
        return divisive_smooth13(vecs, n_segments)
    elif method == "divisive_smooth15":
        return divisive_smooth15(vecs, n_segments)
    elif method == "divisive_smooth19":
        return divisive_smooth19(vecs, n_segments)
    elif method == "divisive_smooth25":
        return divisive_smooth25(vecs, n_segments)
    elif method == "divisive_smooth_dp":
        return divisive_smooth_dp(vecs, n_segments)
    elif method == "divisive_conservative":
        return divisive_conservative(vecs, n_segments)
    elif method == "divisive_smooth7_conservative":
        return divisive_smooth7_conservative(vecs, n_segments)
    elif method == "divisive_smooth9_conservative":
        return divisive_smooth9_conservative(vecs, n_segments)
    elif method == "divisive_smooth11_conservative":
        return divisive_smooth11_conservative(vecs, n_segments)
    elif method == "divisive_smooth13":
        return divisive_smooth(vecs, n_segments, window=13)
    elif method == "divisive_smooth15":
        return divisive_smooth(vecs, n_segments, window=15)
    elif method == "divisive_smooth19":
        return divisive_smooth(vecs, n_segments, window=19)
    elif method == "divisive_smooth25":
        return divisive_smooth(vecs, n_segments, window=25)
    elif method == "divisive_smooth13_conservative":
        return divisive_smooth13_conservative(vecs, n_segments)
    elif method == "divisive_smooth9_consv3":
        return divisive_smooth9_consv3(vecs, n_segments)
    elif method == "divisive_smooth11_consv3":
        return divisive_smooth11_consv3(vecs, n_segments)
    elif method == "divisive_smooth15_conservative":
        return divisive_smooth15_conservative(vecs, n_segments)
    elif method == "divisive_smooth9_frac80":
        return divisive_smooth9_frac80(vecs, n_segments)
    elif method == "divisive_smooth9_frac70":
        return divisive_smooth9_frac70(vecs, n_segments)
    elif method == "divisive_smooth11_frac80":
        return divisive_smooth11_frac80(vecs, n_segments)
    elif method == "divisive_smooth11_frac70":
        return divisive_smooth11_frac70(vecs, n_segments)
    elif method == "divisive_smooth9_frac75":
        return divisive_smooth9_frac75(vecs, n_segments)
    elif method == "divisive_smooth9_frac85":
        return divisive_smooth9_frac85(vecs, n_segments)
    elif method == "divisive_smooth10_frac80":
        return divisive_smooth10_frac80(vecs, n_segments)
    elif method == "divisive_smooth11_frac75":
        return divisive_smooth11_frac75(vecs, n_segments)
    elif method == "divisive_smooth11_frac85":
        return divisive_smooth11_frac85(vecs, n_segments)
    elif method == "divisive_smooth9_consv4":
        return divisive_smooth9_consv4(vecs, n_segments)
    elif method == "divisive_smooth11_consv4":
        return divisive_smooth11_consv4(vecs, n_segments)
    elif method == "divisive_smooth9_consv5":
        return divisive_smooth9_consv5(vecs, n_segments)
    elif method == "divisive_smooth9_consv6":
        return divisive_smooth9_consv6(vecs, n_segments)
    elif method == "divisive_smooth9_frac65":
        return divisive_smooth9_frac65(vecs, n_segments)
    elif method == "divisive_smooth11_consv5":
        return divisive_smooth11_consv5(vecs, n_segments)
    elif method == "divisive_smooth11_frac65":
        return divisive_smooth11_frac65(vecs, n_segments)
    elif method == "cross_model_e5large":
        return cross_model_ensemble_seg(vecs, vid, n_segments, secondary_model="e5large")
    elif method == "cross_model_bge_large":
        return cross_model_ensemble_seg(vecs, vid, n_segments, secondary_model="bge_large")
    elif method == "cross_model_stella":
        return cross_model_ensemble_seg(vecs, vid, n_segments, secondary_model="stella")
    elif method == "cross_model_bge":
        return cross_model_ensemble_seg(vecs, vid, n_segments, secondary_model="bge")
    elif method == "cross_bge_frac70":
        return cross_model_conservative(vecs, vid, n_segments, "bge", window=9, frac=0.70)
    elif method == "cross_bge_frac75":
        return cross_model_conservative(vecs, vid, n_segments, "bge", window=9, frac=0.75)
    elif method == "cross_rank_e5large":
        return cross_model_rank_vote(vecs, vid, n_segments, secondary_model="e5large")
    elif method == "cross_rank_e5large_frac75":
        return cross_model_rank_vote(vecs, vid, n_segments, secondary_model="e5large", frac=0.75)
    elif method == "triple_model":
        return triple_model_ensemble_seg(vecs, vid, n_segments)
    elif method == "cross_e5_frac75":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.75)
    elif method == "cross_e5_frac70":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
    elif method == "cross_e5_frac80":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.80)
    elif method == "cross_e5_w11_frac80":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=11, frac=0.80)
    elif method == "cross_e5_w11_frac75":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=11, frac=0.75)
    elif method == "cross_e5_w7_frac80":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=7, frac=0.80)
    elif method == "cross_e5_w13_frac80":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=13, frac=0.80)
    elif method == "cross_e5_w9_frac90":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.90)
    elif method == "cross_e5_frac65":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.65)
    elif method == "cross_e5_frac60":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.60)
    elif method == "cross_e5_frac55":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.55)
    elif method == "cross_e5_w11_frac70":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=11, frac=0.70)
    elif method == "cross_e5_w11_frac65":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=11, frac=0.65)
    elif method == "cross_e5_w7_frac70":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=7, frac=0.70)
    elif method == "cross_e5_ce_rerank":
        return cross_model_ce_rerank(vecs, texts, vid, n_segments, window=9, frac=0.75)
    elif method == "concat_e5_frac80":
        return concat_embed_seg(vecs, vid, n_segments, "e5large", window=9, frac=0.80)
    elif method == "concat_e5_frac70":
        return concat_embed_seg(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
    elif method == "cross_e5_frac70_minlen":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=8)
    elif method == "cross_e5_frac70_minlen5":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=5)
    elif method == "weighted_cross_w55":
        return weighted_cross_model(vecs, vid, n_segments, w1=0.55, frac=0.70)
    elif method == "weighted_cross_w60":
        return weighted_cross_model(vecs, vid, n_segments, w1=0.60, frac=0.70)
    elif method == "weighted_cross_w65":
        return weighted_cross_model(vecs, vid, n_segments, w1=0.65, frac=0.70)
    elif method == "weighted_cross_w40":
        return weighted_cross_model(vecs, vid, n_segments, w1=0.40, frac=0.70)
    elif method == "cross_e5_thresh60":
        return cross_model_threshold(vecs, vid, n_segments, threshold=0.60)
    elif method == "cross_e5_thresh70":
        return cross_model_threshold(vecs, vid, n_segments, threshold=0.70)
    elif method == "cross_e5_thresh50":
        return cross_model_threshold(vecs, vid, n_segments, threshold=0.50)
    elif method == "cross_e5_gapvar":
        k = gap_variance_k_select(vecs)
        v2_raw = load_embeddings_model(vid, "e5large")
        if v2_raw is None:
            return divisive_seg(smooth_embeddings(vecs, window=9), n_segments=k)
        N = min(len(vecs), len(v2_raw), 800)
        v1 = smooth_embeddings(vecs[:N], window=9)
        v2 = smooth_embeddings(v2_raw[:N], window=9)
        _, s1 = divisive_seg(v1, n_segments=min(k * 3, N - 1), return_scores=True)
        _, s2 = divisive_seg(v2, n_segments=min(k * 3, N - 1), return_scores=True)
        all_pos = sorted(set(s1) | set(s2))
        if not all_pos:
            return divisive_seg(v1, n_segments=k)
        max1 = max(s1.values(), default=1.0) or 1.0
        max2 = max(s2.values(), default=1.0) or 1.0
        combined = {p: (s1.get(p, 0) / max1 + s2.get(p, 0) / max2) / 2 for p in all_pos}
        top_k = sorted(combined, key=lambda x: -combined[x])[:k]
        return sorted(b for b in top_k if 0 < b < N)
    elif method == "triple_frac80":
        return triple_model_ensemble_seg(vecs, vid, n_segments, frac=0.80)
    elif method == "triple_frac75":
        return triple_model_ensemble_seg(vecs, vid, n_segments, frac=0.75)
    elif method == "triple_frac70":
        return triple_model_ensemble_seg(vecs, vid, n_segments, frac=0.70)
    elif method == "divisive_smooth3":
        return divisive_seg(smooth_embeddings(vecs, window=3), n_segments=n_segments)
    elif method == "divisive_smooth5":
        return divisive_seg(smooth_embeddings(vecs, window=5), n_segments=n_segments)
    elif method == "divisive_smooth7":
        return divisive_seg(smooth_embeddings(vecs, window=7), n_segments=n_segments)
    elif method == "divisive_smooth3_prosody":
        return _divisive_prosody(smooth_embeddings(vecs, window=3), n_segments, prosody_gap)
    elif method == "divisive_chunked_prosody":
        cvecs = chunk_vecs(vecs, chunk_size=chunk_size)
        if len(cvecs) < 2:
            return _divisive_prosody(vecs, n_segments, prosody_gap)
        # downsample prosody to chunk gaps: average pause within each chunk-gap region
        cpros = None
        if prosody_gap is not None and len(prosody_gap) >= chunk_size:
            n_cg = len(cvecs) - 1
            cpros = np.zeros(n_cg, dtype=np.float32)
            for i in range(n_cg):
                # chunk gap i is between chunk i and chunk i+1; corresponds to
                # sentence-gap index ~ (i+1)*chunk_size - 1 in original space
                center = (i + 1) * chunk_size - 1
                lo = max(0, center - 1)
                hi = min(len(prosody_gap), center + 2)
                cpros[i] = prosody_gap[lo:hi].mean()
        cb = _divisive_prosody(cvecs, n_segments, cpros)
        return chunk_boundaries_to_sentences(cb, chunk_size, N)
    elif method == "cross_e5_prosody":
        return cross_model_prosody_rerank(vecs, vid, n_segments, prosody_gap,
                                          window=9, frac=0.70)
    elif method == "cross_e5_prosody_frac75":
        return cross_model_prosody_rerank(vecs, vid, n_segments, prosody_gap,
                                          window=9, frac=0.75)
    elif method == "cross_stella_frac70":
        return cross_model_ensemble_seg(vecs, vid, n_segments,
                                        secondary_model="stella", window=9, frac=0.70)
    elif method == "cross_stella_frac75":
        return cross_model_ensemble_seg(vecs, vid, n_segments,
                                        secondary_model="stella", window=9, frac=0.75)
    elif method == "multi_res_cross_e5":
        return multi_resolution_cross_e5(vecs, vid, n_segments, frac=0.70)
    elif method == "multi_res_cross_e5_frac75":
        return multi_resolution_cross_e5(vecs, vid, n_segments, frac=0.75)
    elif method == "cross_e5_frac70_shift":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return boundary_local_shift(raw, vecs, vid, window=2)
    elif method == "cross_e5_bgelarge_frac70":
        return cross_model_ensemble_seg(vecs, vid, n_segments,
                                        secondary_model="bge_large", window=9, frac=0.70)
    elif method == "iterative_cross_e5":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.70)
    elif method == "iterative_cross_e5_frac75":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.75)
    elif method == "iterative_cross_e5_frac80":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.80)
    elif method == "iterative_cross_e5_frac65":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.65)
    elif method == "iterative_cross_e5_w7":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.70, window=7)
    elif method == "iterative_cross_e5_w11":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.70, window=11)
    elif method == "iterative_cross_e5_w7_frac75":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.75, window=7)
    elif method == "iterative_cross_e5_w11_frac75":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.75, window=11)
    elif method == "cross_e5_adaptive_k":
        return cross_e5_adaptive_k(vecs, vid, n_segments)
    elif method == "cross_e5_combined_depth":
        return cross_e5_combined_depth(vecs, vid, n_segments, frac=0.70)
    elif method == "cross_e5_combined_depth_frac75":
        return cross_e5_combined_depth(vecs, vid, n_segments, frac=0.75)
    elif method == "cross_e5_combined_depth_w5":
        return cross_e5_combined_depth(vecs, vid, n_segments, frac=0.70, depth_w=5)
    elif method == "cross_e5_combined_depth_w9":
        return cross_e5_combined_depth(vecs, vid, n_segments, frac=0.70, depth_w=9)
    elif method == "iterative_cross_e5_prosody":
        return iterative_cross_e5_with_prosody(vecs, vid, n_segments, prosody_gap, frac=0.75)
    elif method == "iterative_cross_e5_prosody_frac70":
        return iterative_cross_e5_with_prosody(vecs, vid, n_segments, prosody_gap, frac=0.70)
    elif method == "iterative_cross_e5_shift":
        raw = iterative_cross_e5(vecs, vid, n_segments, frac=0.75)
        return boundary_local_shift(raw, vecs, vid, window=2)
    elif method == "iterative_cross_e5_shift70":
        raw = iterative_cross_e5(vecs, vid, n_segments, frac=0.70)
        return boundary_local_shift(raw, vecs, vid, window=2)
    elif method == "iterative_v2_frac75":
        return iterative_cross_e5_v2(vecs, vid, n_segments, frac=0.75, w_cross=0.3, w_seg=0.7)
    elif method == "iterative_v2_frac70":
        return iterative_cross_e5_v2(vecs, vid, n_segments, frac=0.70, w_cross=0.3, w_seg=0.7)
    elif method == "iterative_v2_w04":
        return iterative_cross_e5_v2(vecs, vid, n_segments, frac=0.75, w_cross=0.4, w_seg=0.6)
    elif method == "iterative_v2_w02":
        return iterative_cross_e5_v2(vecs, vid, n_segments, frac=0.75, w_cross=0.2, w_seg=0.8)
    elif method == "iterative_v2_segs4":
        return iterative_cross_e5_v2(vecs, vid, n_segments, frac=0.75, cand_mult=4, w_cross=0.3, w_seg=0.7)
    elif method == "cross_e5base_frac70":
        return cross_model_ensemble_seg(vecs, vid, n_segments, secondary_model="e5", window=9, frac=0.70)
    elif method == "cross_e5base_frac75":
        return cross_model_ensemble_seg(vecs, vid, n_segments, secondary_model="e5", window=9, frac=0.75)
    elif method == "iterative_cross_e5base":
        return iterative_cross_e5_generic(vecs, vid, n_segments, secondary_model="e5", frac=0.70)
    elif method == "iterative_cross_e5base_frac75":
        return iterative_cross_e5_generic(vecs, vid, n_segments, secondary_model="e5", frac=0.75)
    elif method == "iterative_cross_bgelarge":
        return iterative_cross_e5_generic(vecs, vid, n_segments, secondary_model="bge_large", frac=0.70)
    elif method == "iterative_cross_bgelarge_frac75":
        return iterative_cross_e5_generic(vecs, vid, n_segments, secondary_model="bge_large", frac=0.75)
    elif method == "iterative_cross_stella":
        return iterative_cross_e5_generic(vecs, vid, n_segments, secondary_model="stella", frac=0.70)
    elif method == "iterative_cross_stella_frac75":
        return iterative_cross_e5_generic(vecs, vid, n_segments, secondary_model="stella", frac=0.75)
    elif method == "iterative_fw_e5base":
        return iterative_cross_fixed_window(vecs, vid, n_segments, secondary_model="e5", frac=0.70)
    elif method == "iterative_fw_e5base_frac75":
        return iterative_cross_fixed_window(vecs, vid, n_segments, secondary_model="e5", frac=0.75)
    elif method == "iterative_fw_stella":
        return iterative_cross_fixed_window(vecs, vid, n_segments, secondary_model="stella", frac=0.70)
    elif method == "iterative_fw_bgelarge":
        return iterative_cross_fixed_window(vecs, vid, n_segments, secondary_model="bge_large", frac=0.70)
    elif method == "contrastive_e5base":
        return contrastive_boundary_score(vecs, vid, n_segments, secondary_model="e5", frac=0.70)
    elif method == "contrastive_e5base_frac75":
        return contrastive_boundary_score(vecs, vid, n_segments, secondary_model="e5", frac=0.75)
    elif method == "contrastive_stella":
        return contrastive_boundary_score(vecs, vid, n_segments, secondary_model="stella", frac=0.70)
    elif method == "iterative_cross_e5_frac75_minlen":
        raw = iterative_cross_e5(vecs, vid, n_segments, frac=0.75)
        return min_seg_filter(raw, len(vecs), min_seg=8)
    elif method == "iterative_cross_e5_frac65_minlen":
        raw = iterative_cross_e5(vecs, vid, n_segments, frac=0.65)
        return min_seg_filter(raw, len(vecs), min_seg=8)
    elif method == "iterative_cross_e5_frac70_minlen":
        raw = iterative_cross_e5(vecs, vid, n_segments, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=8)
    elif method == "iterative_cross_e5_frac60":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.60)
    elif method == "iterative_cross_e5_frac55":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.55)
    elif method == "iterative_cross_e5_frac50":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.50)
    elif method == "iterative_v2_frac65":
        return iterative_cross_e5_v2(vecs, vid, n_segments, frac=0.65, w_cross=0.3, w_seg=0.7)
    elif method == "iterative_v2_frac60":
        return iterative_cross_e5_v2(vecs, vid, n_segments, frac=0.60, w_cross=0.3, w_seg=0.7)
    elif method == "iterative_v2_frac75_minlen":
        raw = iterative_cross_e5_v2(vecs, vid, n_segments, frac=0.75, w_cross=0.3, w_seg=0.7)
        return min_seg_filter(raw, len(vecs), min_seg=8)
    elif method == "cross_e5_frac65_minlen":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.65)
        return min_seg_filter(raw, len(vecs), min_seg=8)
    elif method == "iterative_cross_e5_frac75_minlen5":
        raw = iterative_cross_e5(vecs, vid, n_segments, frac=0.75)
        return min_seg_filter(raw, len(vecs), min_seg=5)
    elif method == "iterative_cross_e5_frac70":
        return iterative_cross_e5(vecs, vid, n_segments, frac=0.70)
    elif method == "cross_e5_frac65":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.65)
    elif method == "cross_e5_frac60":
        return cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.60)
    elif method == "cross_e5_frac65_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.65)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac65_minlen12":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.65)
        return min_seg_filter(raw, len(vecs), min_seg=12)
    elif method == "cross_e5_frac70_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac60_minlen8":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.60)
        return min_seg_filter(raw, len(vecs), min_seg=8)
    elif method == "cross_e5_frac60_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.60)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "iterative_cross_e5_frac70_minlen10":
        raw = iterative_cross_e5(vecs, vid, n_segments, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "iterative_cross_e5_frac65_minlen10":
        raw = iterative_cross_e5(vecs, vid, n_segments, frac=0.65)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac70_minlen12":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=12)
    elif method == "cross_e5_frac70_minlen15":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=15)
    elif method == "cross_e5_frac70_minlen20":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=20)
    elif method == "cross_e5_frac75_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.75)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac75_minlen12":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.75)
        return min_seg_filter(raw, len(vecs), min_seg=12)
    elif method == "cross_e5_frac80_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.80)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac65_minlen15":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.65)
        return min_seg_filter(raw, len(vecs), min_seg=15)
    elif method == "cross_e5_w11_frac70_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=11, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_w11_frac70_minlen12":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=11, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=12)
    elif method == "cross_e5_frac85_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.85)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_w7_frac70_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=7, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac70_adaptive_minlen":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        min_seg_adaptive = max(5, len(vecs) // max(1, n_segments * 2))
        return min_seg_filter(raw, len(vecs), min_seg=min_seg_adaptive)
    elif method == "multi_res_cross_e5_minlen10":
        raw = multi_resolution_cross_e5(vecs, vid, n_segments, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_nms10":
        return cross_model_nms(vecs, vid, n_segments, min_gap=10)
    elif method == "cross_e5_nms12":
        return cross_model_nms(vecs, vid, n_segments, min_gap=12)
    elif method == "cross_e5_nms8":
        return cross_model_nms(vecs, vid, n_segments, min_gap=8)
    elif method == "cross_e5_nms10_frac75":
        return cross_model_nms(vecs, vid, n_segments, frac=0.75, min_gap=10)
    elif method == "cross_e5_nms10_frac65":
        return cross_model_nms(vecs, vid, n_segments, frac=0.65, min_gap=10)
    elif method == "cross_e5_nms10_w11":
        return cross_model_nms(vecs, vid, n_segments, window=11, min_gap=10)
    elif method == "triple_frac70_minlen10":
        raw = triple_model_ensemble_seg(vecs, vid, n_segments, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "triple_frac65_minlen10":
        raw = triple_model_ensemble_seg(vecs, vid, n_segments, frac=0.65)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_model_bge_e5_frac70_minlen10":
        raw = cross_model_ensemble_seg(vecs, vid, n_segments, secondary_model="bge", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac68_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.68)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac72_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.72)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac74_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.74)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_frac70_minlen9":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=9)
    elif method == "cross_e5_frac70_minlen11":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_frac68_minlen11":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.68)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_frac72_minlen11":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.72)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_frac75_minlen11":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.75)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_frac65_minlen11":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.65)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "concat_e5_frac70_minlen10":
        raw = concat_embed_seg(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "concat_e5_frac70_minlen11":
        raw = concat_embed_seg(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_w13_frac70_minlen11":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=13, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_w13_frac70_minlen10":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=13, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_w15_frac70_minlen11":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=15, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_rank_e5_frac70_minlen11":
        raw = cross_model_rank_vote(vecs, vid, n_segments, secondary_model="e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_rank_e5_frac70_minlen10":
        raw = cross_model_rank_vote(vecs, vid, n_segments, secondary_model="e5large", window=9, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "multi_res_e5_frac70_minlen11":
        raw = multi_resolution_cross_e5(vecs, vid, n_segments, frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_score_minlen11":
        return cross_model_score_aware_minlen(vecs, vid, n_segments, "e5large",
                                              window=9, frac=0.70, min_seg=11)
    elif method == "cross_e5_score_minlen10":
        return cross_model_score_aware_minlen(vecs, vid, n_segments, "e5large",
                                              window=9, frac=0.70, min_seg=10)
    elif method == "cross_e5_score_minlen12":
        return cross_model_score_aware_minlen(vecs, vid, n_segments, "e5large",
                                              window=9, frac=0.70, min_seg=12)
    elif method == "triple_bgelarge_e5_mpnet_frac70_minlen11":
        raw = triple_model_ensemble_seg(vecs, vid, n_segments,
                                        models=["e5large", "mpnet"], frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "triple_bgelarge_e5_mpnet_frac70_minlen10":
        raw = triple_model_ensemble_seg(vecs, vid, n_segments,
                                        models=["e5large", "mpnet"], frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "triple_bgelarge_e5large_bge_frac70_minlen11":
        raw = triple_model_ensemble_seg(vecs, vid, n_segments,
                                        models=["e5large", "bge"], frac=0.70)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "dp_frac70_minlen11":
        svecs = smooth_embeddings(vecs, window=9)
        k = max(2, round(n_segments * 0.70))
        raw = dp_seg(svecs, n_segments=k)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "dp_frac70_minlen10":
        svecs = smooth_embeddings(vecs, window=9)
        k = max(2, round(n_segments * 0.70))
        raw = dp_seg(svecs, n_segments=k)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "depth_frac70_minlen11":
        svecs = smooth_embeddings(vecs, window=9)
        k = max(2, round(n_segments * 0.70))
        raw = depth_seg(svecs, n_segments=k, window=5)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_frac70_adaptive_minlen2":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        # Adaptive min_seg: 30% of expected segment length, floored at 8
        expected_seg_len = max(1, len(vecs) // max(1, n_segments))
        min_seg_adaptive = max(8, min(15, round(expected_seg_len * 0.30)))
        return min_seg_filter(raw, len(vecs), min_seg=min_seg_adaptive)
    elif method == "cross_e5_frac70_adaptive_minlen3":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        # Adaptive min_seg: 40% of expected segment length, floored at 8
        expected_seg_len = max(1, len(vecs) // max(1, n_segments))
        min_seg_adaptive = max(8, min(15, round(expected_seg_len * 0.40)))
        return min_seg_filter(raw, len(vecs), min_seg=min_seg_adaptive)
    elif method == "cross_e5_gauss_frac70_minlen11":
        N_cap = min(len(vecs), 800)
        v1 = smooth_embeddings_gaussian(vecs[:N_cap], window=9, sigma=2.0)
        k = max(2, round(n_segments * 0.70))
        over_k = min(N_cap - 1, k * 4 + 2)
        v2_raw = load_embeddings_model(vid, "e5large")
        if v2_raw is None:
            raw = divisive_seg(v1, n_segments=k)
        else:
            N = min(N_cap, len(v2_raw))
            v2 = smooth_embeddings_gaussian(v2_raw[:N], window=9, sigma=2.0)
            _, s1 = divisive_seg(v1[:N], n_segments=min(over_k, N-1), return_scores=True)
            _, s2 = divisive_seg(v2, n_segments=min(over_k, N-1), return_scores=True)
            all_pos = sorted(set(s1) | set(s2))
            max1 = max(s1.values(), default=1.0) or 1.0
            max2 = max(s2.values(), default=1.0) or 1.0
            combined = {p: (s1.get(p,0)/max1 + s2.get(p,0)/max2)/2 for p in all_pos}
            top_k = sorted(combined, key=lambda x: -combined[x])[:k]
            raw = sorted(b for b in top_k if 0 < b < N)
        return min_seg_filter(raw, len(vecs), min_seg=11)
    elif method == "cross_e5_gauss_frac70_minlen10":
        N_cap = min(len(vecs), 800)
        v1 = smooth_embeddings_gaussian(vecs[:N_cap], window=9, sigma=2.0)
        k = max(2, round(n_segments * 0.70))
        over_k = min(N_cap - 1, k * 4 + 2)
        v2_raw = load_embeddings_model(vid, "e5large")
        if v2_raw is None:
            raw = divisive_seg(v1, n_segments=k)
        else:
            N = min(N_cap, len(v2_raw))
            v2 = smooth_embeddings_gaussian(v2_raw[:N], window=9, sigma=2.0)
            _, s1 = divisive_seg(v1[:N], n_segments=min(over_k, N-1), return_scores=True)
            _, s2 = divisive_seg(v2, n_segments=min(over_k, N-1), return_scores=True)
            all_pos = sorted(set(s1) | set(s2))
            max1 = max(s1.values(), default=1.0) or 1.0
            max2 = max(s2.values(), default=1.0) or 1.0
            combined = {p: (s1.get(p,0)/max1 + s2.get(p,0)/max2)/2 for p in all_pos}
            top_k = sorted(combined, key=lambda x: -combined[x])[:k]
            raw = sorted(b for b in top_k if 0 < b < N)
        return min_seg_filter(raw, len(vecs), min_seg=10)
    elif method == "cross_e5_constrained_minlen11":
        N_cap = min(len(vecs), 800)
        v1 = smooth_embeddings(vecs[:N_cap], window=9)
        k = max(2, round(n_segments * 0.70))
        v2_raw = load_embeddings_model(vid, "e5large")
        if v2_raw is None:
            return divisive_seg_constrained(v1, n_segments=k, min_seg=11)
        N = min(N_cap, len(v2_raw))
        v2 = smooth_embeddings(v2_raw[:N], window=9)
        # Run constrained divisive on each model, then combine
        b1 = divisive_seg_constrained(v1[:N], n_segments=k, min_seg=11)
        b2 = divisive_seg_constrained(v2, n_segments=k, min_seg=11)
        # Borda vote: positions appearing in both get priority
        votes = {}
        for b in b1:
            votes[b] = votes.get(b, 0) + 2
        for b in b2:
            votes[b] = votes.get(b, 0) + 1
        # Sort by vote count (ties = position in b1 first)
        sorted_cands = sorted(votes, key=lambda x: -votes[x])
        # Keep top-k, ensuring no too-close pairs (re-apply min_seg)
        return min_seg_filter(sorted(sorted_cands[:k*2]), N, min_seg=11)[:k]
    elif method == "cross_e5_constrained_minlen10":
        N_cap = min(len(vecs), 800)
        v1 = smooth_embeddings(vecs[:N_cap], window=9)
        k = max(2, round(n_segments * 0.70))
        v2_raw = load_embeddings_model(vid, "e5large")
        if v2_raw is None:
            return divisive_seg_constrained(v1, n_segments=k, min_seg=10)
        N = min(N_cap, len(v2_raw))
        v2 = smooth_embeddings(v2_raw[:N], window=9)
        b1 = divisive_seg_constrained(v1[:N], n_segments=k, min_seg=10)
        b2 = divisive_seg_constrained(v2, n_segments=k, min_seg=10)
        votes = {}
        for b in b1:
            votes[b] = votes.get(b, 0) + 2
        for b in b2:
            votes[b] = votes.get(b, 0) + 1
        sorted_cands = sorted(votes, key=lambda x: -votes[x])
        return min_seg_filter(sorted(sorted_cands[:k*2]), N, min_seg=10)[:k]
    elif method == "cross_e5_frac70_minlen10_llm":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        filtered = min_seg_filter(raw, len(vecs), min_seg=10)
        if _HAS_LLM:
            try:
                from lecseg.refine.llm_refine import LLMRefiner
                refiner = LLMRefiner()
                if refiner._is_available():
                    filtered = refiner.filter_boundaries(texts, filtered, context=5)
            except Exception:
                pass
        return filtered
    elif method == "cross_e5_frac70_llm_filter":
        raw = cross_model_conservative(vecs, vid, n_segments, "e5large", window=9, frac=0.70)
        if _HAS_LLM:
            try:
                from lecseg.refine.llm_refine import LLMRefiner
                refiner = LLMRefiner()
                if refiner._is_available():
                    raw = refiner.filter_boundaries(texts, raw, context=5)
            except Exception:
                pass
        return raw
    else:
        raise ValueError(f"Unknown method: {method}")


ALL_METHODS = [
    "texttiling", "c99", "cosine", "kmeans", "bert_seg",
    "two_stage", "two_stage_prosody", "two_stage_chunked",
    "hierarchical", "hierarchical_prosody",
    "divisive", "divisive_chunked", "divisive_chunked3",
    "divisive_prosody", "divisive_chunked_prosody",
    "divisive_shots", "divisive_prosody_shots",
    "divisive_llm",
    "divisive_smooth3", "divisive_smooth5", "divisive_smooth7",
    "divisive_smooth9", "divisive_smooth11",
    "divisive_smooth3_prosody",
    "depth", "depth_w3", "depth_w9", "depth_smooth",
    "crossencoder",
    "bert_wiki",
    "divisive_block5", "divisive_block7", "divisive_block9",
    "divisive_bic", "divisive_bic_smooth",
    "divisive_minlen", "divisive_smooth7_minlen",
    "divisive_elbow", "divisive_elbow_smooth",
    "dp", "dp_smooth",
    "cosine_drop", "cosine_drop_smooth",
    "ensemble", "ensemble_smooth",
    "recency", "recency_smooth",
    "divisive_recency", "divisive_recency_smooth",
    "divisive_smooth13", "divisive_smooth15", "divisive_smooth19", "divisive_smooth25",
    "divisive_smooth_dp",
    "divisive_conservative", "divisive_smooth7_conservative", "divisive_smooth9_conservative",
    "divisive_smooth11_conservative", "divisive_smooth13_conservative",
    "divisive_smooth9_consv3", "divisive_smooth11_consv3",
    "divisive_smooth15_conservative",
    "divisive_smooth9_frac80", "divisive_smooth9_frac70",
    "divisive_smooth11_frac80", "divisive_smooth11_frac70",
    "divisive_smooth9_consv5", "divisive_smooth9_consv6",
    "divisive_smooth9_frac65",
    "divisive_smooth11_consv5", "divisive_smooth11_frac65",
    "cross_model_e5large", "cross_model_bge_large",
]


def run_eval(
    methods: list[str] = ALL_METHODS,
    embedding_model: str = "mpnet",
    verbose: bool = False,
    output: Path | None = None,
    use_youtube: bool = False,
    draft_ok: bool = False,
) -> dict:
    """
    Run evaluation for all videos and methods.

    Returns nested dict: {method: {video_id: scores_dict}}
    """
    results: dict[str, dict[str, dict]] = {m: {} for m in methods}
    aggregates: dict[str, list] = {m: [] for m in methods}

    # Find all videos with both ground truth and sentences
    gt_source = GT_YOUTUBE if use_youtube else GT_HIER
    gt_files = sorted(gt_source.glob("*.json"))
    gt_files = [f for f in gt_files if not f.name.startswith("_") and f.suffix == ".json"
                and f.name not in ("flags_decisions.md", "gt_summary.csv")]
    if not gt_files:
        print("No ground truth annotations found.")
        return {}

    if use_youtube:
        print(f"Using YouTube chapter GT ({len(gt_files)} videos)")
    elif draft_ok:
        print(f"Using gt_hier annotations (draft+reviewed, {len(gt_files)} videos)")

    for gt_file in gt_files:
        vid = gt_file.stem
        if vid.startswith("_"):
            continue

        gt = _load_ground_truth(vid, use_youtube=use_youtube, draft_ok=draft_ok)
        if gt is None:
            continue

        sents = _load_sentences(vid)
        if sents is None:
            if verbose:
                print(f"  SKIP {vid}: no sentence file")
            continue

        N = len(sents)
        # O(n²) methods need a sentence cap; divisive-family methods do not (O(N·K))
        O2_METHODS = {"texttiling", "c99", "cosine", "kmeans", "bert_seg",
                      "two_stage", "two_stage_prosody", "two_stage_chunked",
                      "hierarchical", "hierarchical_prosody"}
        MAX_SENTS_O2 = 800

        ref_ch_dicts = gt.get("chapters", [])
        n_segments_ch = max(2, len(ref_ch_dicts))

        # Load or compute embeddings (full length)
        vecs = _load_embeddings(vid, embedding_model)
        if vecs is None:
            if verbose:
                print(f"  Computing embeddings for {vid}...")
            texts = [s["text"] for s in sents]
            vecs = embed_sentences(texts, model=embedding_model)

        # Capped versions for O(n²) methods
        N_capped = min(N, MAX_SENTS_O2)
        sents_capped = sents[:N_capped]
        vecs_capped = vecs[:N_capped]

        def _ref_boundaries_for(n_use: int, sents_use: list) -> list[int]:
            starts = np.array([s["start"] for s in sents_use])
            bounds = []
            for ch in ref_ch_dicts[1:]:
                t = ch["start_sec"]
                idx = int(np.searchsorted(starts, t, side="left"))
                idx = max(1, min(idx, n_use - 1))
                bounds.append(idx)
            return sorted(set(bounds))

        ref_boundaries_full   = _ref_boundaries_for(N, sents)
        ref_boundaries_capped = _ref_boundaries_for(N_capped, sents_capped)

        prosody_gap_full   = _load_prosody(vid, N)
        shot_gap_full      = _load_shot_gap_scores(vid, N, sents)
        prosody_gap_capped = _load_prosody(vid, N_capped)
        shot_gap_capped    = _load_shot_gap_scores(vid, N_capped, sents_capped)

        if verbose:
            capped_note = f" [capped {N}->{N_capped}]" if N > MAX_SENTS_O2 else ""
            pros_note = " +prosody" if prosody_gap_full is not None else ""
            shot_note = " +shots" if shot_gap_full is not None else ""
            print(f"  {vid}: N={N}{capped_note}  n_seg={n_segments_ch}  ref_boundaries={len(ref_boundaries_full)}{pros_note}{shot_note}")

        for method in methods:
            # All methods use capped window; divisive-family is fast enough but
            # empirically degrades on 2000+ sentence sequences due to global noise.
            sents_use  = sents_capped
            vecs_use   = vecs_capped
            n_use      = N_capped
            pros_use   = prosody_gap_capped
            shot_use   = shot_gap_capped
            ref_use    = ref_boundaries_capped
            n_seg_use  = n_segments_ch  # full chapter count (consistent with prior evals)

            try:
                # Longer timeout for LLM method (~10-15s per candidate)
                t_out = 600 if method == "divisive_llm" else 120
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_run_method, method, sents_use, vecs_use, n_seg_use, pros_use, shot_use, 4, vid)
                    hyp = fut.result(timeout=t_out)
                scores = evaluate(hyp, ref_use, n_units=n_use)
                scores_dict = scores.as_dict()
                # Multi-tolerance F1
                for t in (1, 2, 3, 5):
                    _, _, f1t = tolerance_f1(hyp, ref_use, n_use, tolerance=t)
                    scores_dict[f"f1_t{t}"] = round(float(f1t), 4)
                results[method][vid] = scores_dict
                aggregates[method].append(scores_dict)
            except FuturesTimeout:
                if verbose:
                    print(f"    {method} TIMEOUT (>45s) — skipped")
                results[method][vid] = {"error": "timeout"}
            except Exception as e:
                if verbose:
                    print(f"    {method} FAILED: {e}")
                results[method][vid] = {"error": str(e)}

    # Compute per-method aggregate stats
    summary: dict[str, dict] = {}
    for method in methods:
        agg_list = aggregates[method]
        if not agg_list:
            summary[method] = {}
            continue

        keys = [k for k in agg_list[0] if isinstance(agg_list[0][k], (int, float))]
        summary[method] = {
            k: round(sum(d.get(k, 0) for d in agg_list) / len(agg_list), 4)
            for k in keys
        }

    gt_mode = "youtube_gt" if use_youtube else ("draft_ok" if draft_ok else "reviewed_only")
    report = {"results": results, "summary": summary, "n_videos": len(gt_files), "gt_mode": gt_mode}

    if output is None:
        output = RESULTS_DIR / "eval.json"
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output}")

    # Print summary table — Pk/WD only (field standard); plus tolerance-Pk via F1@t2 proxy
    print("\n=== EVALUATION SUMMARY (Pk/WD — field standard) ===")
    print(f"{'Method':<30} {'Pk':>8} {'WD':>8} {'F1@t2':>8}")
    print("-" * 58)
    ordered = sorted(summary.items(), key=lambda kv: kv[1].get("pk", 1.0) if kv[1] else 1.0)
    for method, stats in ordered:
        if not stats:
            print(f"{method:<30} (no results)")
            continue
        print(f"{method:<30} "
              f"{stats.get('pk', 0):>8.4f} "
              f"{stats.get('wd', 0):>8.4f} "
              f"{stats.get('f1_t2', 0):>8.4f}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Run full ablation evaluation")
    parser.add_argument("--method", nargs="+", default=ALL_METHODS,
                        help="Methods to evaluate (default: all)")
    parser.add_argument("--model", default="mpnet",
                        help="Embedding model (sbert/mpnet/e5/bge)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--youtube-gt", action="store_true",
                        help="Use YouTube chapter GT instead of gt_hier")
    parser.add_argument("--draft-ok", action="store_true",
                        help="Accept draft annotations (not just reviewed)")
    args = parser.parse_args()

    methods = ALL_METHODS if "all" in args.method else args.method
    out = Path(args.output) if args.output else None
    run_eval(methods=methods, embedding_model=args.model, verbose=args.verbose,
             output=out, use_youtube=args.youtube_gt, draft_ok=args.draft_ok)


if __name__ == "__main__":
    main()
