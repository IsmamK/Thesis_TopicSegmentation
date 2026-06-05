"""Pause-burst topic transition detector.

Uses prosody features (pause_after, pitch_reset) as primary boundary signals.
In academic lectures, significant topic transitions often coincide with:
  - Long pauses (lecturer pausing to mark a conceptual shift)
  - Pitch resets (returning to a neutral/lower pitch for a new topic start)
  - Combination of both (strongest signal)

This complements the text-embedding approach with a purely acoustic signal.
Results inform whether acoustic transitions align with YouTube chapter boundaries.

Usage:
    python scripts/pause_transition_eval.py [--verbose]
"""

import argparse
import json
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from lecseg.metrics import evaluate

PROSODY_DIR = Path("data/prosody")
SENT_DIR = Path("data/sentences")
GT_PATH = Path("data/gt")


def load_prosody_gap_scores(vid_id: str, n: int) -> dict[str, np.ndarray] | None:
    """Return multiple prosody-based gap scores."""
    p = PROSODY_DIR / f"{vid_id}.json"
    if not p.exists():
        return None
    data = json.load(open(p, encoding="utf-8"))
    if not data:
        return None

    pauses = np.array([float(d.get("pause_after", 0.0) or 0.0) for d in data])
    pitch = np.array([float(d.get("mean_pitch", 0.0) or 0.0) for d in data])
    pitch_std = np.array([float(d.get("pitch_std", 0.0) or 0.0) for d in data])

    L = min(len(pauses) - 1, n - 1)
    if L <= 0:
        return None

    # Signal 1: raw pause after sentence i (gap i = between sent i and i+1)
    pause_gap = pauses[:L].copy()

    # Signal 2: pitch reset across gap — large change in pitch
    prev_p = pitch[:L]
    next_p = pitch[1:L + 1]
    denom = np.where(prev_p > 1e-3, prev_p, 1.0)
    pitch_reset = np.abs(next_p - prev_p) / denom

    # Signal 3: pitch_std near gap (high variance = lecturer is uncertain/preparing)
    pstd_gap = 0.5 * (pitch_std[:L] + pitch_std[1:L + 1])

    def n01(x):
        r = float(x.max() - x.min())
        return np.zeros_like(x) if r <= 0 else (x - x.min()) / r

    return {
        "pause": n01(pause_gap),
        "pitch_reset": n01(pitch_reset),
        "pitch_std": n01(pstd_gap),
        "fused_0.6_0.2_0.2": 0.6 * n01(pause_gap) + 0.2 * n01(pitch_reset) + 0.2 * n01(pstd_gap),
        "fused_0.5_0.3_0.2": 0.5 * n01(pause_gap) + 0.3 * n01(pitch_reset) + 0.2 * n01(pstd_gap),
        "fused_0.7_0.2_0.1": 0.7 * n01(pause_gap) + 0.2 * n01(pitch_reset) + 0.1 * n01(pstd_gap),
    }


def pick_boundaries(scores: np.ndarray, n_targets: int, min_len: int = 5) -> list[int]:
    n = len(scores)
    s = scores.copy()
    s[:min_len] = 0.0
    s[n - min_len:] = 0.0
    selected = []
    s_work = s.copy()
    for _ in range(n_targets):
        idx = int(np.argmax(s_work))
        if s_work[idx] <= 0:
            break
        selected.append(idx + 1)  # boundary after sentence idx
        for d in range(-min_len, min_len + 1):
            j = idx + d
            if 0 <= j < n:
                s_work[j] = 0.0
    return sorted(selected)


def run_video(vid_id: str, verbose: bool = False) -> dict | None:
    sent_path = SENT_DIR / vid_id / "sentences.json"
    if not sent_path.exists():
        return None
    sents = json.load(open(sent_path, encoding="utf-8"))["sentences"]
    n = len(sents)

    gt_file = GT_PATH / f"{vid_id}.json"
    if not gt_file.exists():
        return None
    gt_data = json.load(open(gt_file, encoding="utf-8"))
    boundaries_sec = gt_data.get("boundaries_sec", [])
    if not boundaries_sec:
        return None

    starts = np.array([s["start"] for s in sents])
    ref_boundaries = sorted(set(
        max(1, min(int(np.searchsorted(starts, float(t), side="left")), n - 1))
        for t in boundaries_sec
    ))

    cap = min(n, 800)
    ref_cap = [b for b in ref_boundaries if b < cap]
    if not ref_cap:
        return None

    n_targets = len(ref_cap)
    gap_scores = load_prosody_gap_scores(vid_id, cap)
    if gap_scores is None:
        return None

    results = {}
    for signal_name, scores in gap_scores.items():
        boundaries = pick_boundaries(scores, n_targets)
        boundaries = [b for b in boundaries if 0 < b < cap]
        if not boundaries:
            continue
        ev = evaluate(boundaries, ref_cap, n_units=cap)
        results[signal_name] = {"pk": ev.pk, "wd": ev.wd,
                                 "bs": ev.boundary_similarity, "f1": ev.f1}

    if verbose and results:
        best = min(results.items(), key=lambda x: x[1]["pk"])
        print(f"  {vid_id}: best={best[0]} Pk={best[1]['pk']:.4f}")

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    manifest = [json.loads(l) for l in open("data/manifest.jsonl", encoding="utf-8")]
    vids = [v["id"] for v in manifest]
    print(f"Pause transition eval on {len(vids)} videos...")

    signal_pks: dict[str, list] = {}
    signal_wds: dict[str, list] = {}
    n_ok = 0

    for i, vid_id in enumerate(vids):
        r = run_video(vid_id, args.verbose)
        if r:
            n_ok += 1
            for sig, metrics in r.items():
                signal_pks.setdefault(sig, []).append(metrics["pk"])
                signal_wds.setdefault(sig, []).append(metrics["wd"])
        else:
            if args.verbose:
                print(f"  {vid_id}: SKIP")

    print(f"\n== Pause Transition Segmenter ({n_ok}/{len(vids)} videos) ==")
    print(f"{'Signal':<30} {'Mean Pk':>10} {'Mean WD':>10}")
    print("-" * 54)
    rows = [(sig, np.mean(pks), np.mean(signal_wds[sig]))
            for sig, pks in signal_pks.items()]
    rows.sort(key=lambda x: x[1])
    for sig, mpk, mwd in rows:
        marker = " <-- BEST" if sig == rows[0][0] else ""
        print(f"{sig:<30} {mpk:>10.4f} {mwd:>10.4f}{marker}")

    print(f"\nComparison:")
    print(f"  BGE-divisive baseline:  Pk=0.3884")
    print(f"  Cross-model best:       Pk=0.3715")
    print(f"  Balanced selector:      Pk=0.3588")

    best_sig, best_pk, best_wd = rows[0]
    if best_pk < 0.3715:
        print(f"\nPause signal BEATS cross-model! Pk={best_pk:.4f} ({best_sig})")
    elif best_pk < 0.3884:
        print(f"\nPause signal beats BGE-divisive. Pk={best_pk:.4f} ({best_sig})")
    else:
        print(f"\nPause signal does not beat baseline. Best Pk={best_pk:.4f}")
        print(f"  --> Prosody alone is insufficient for chapter-level segmentation")
        print(f"  --> But useful as an additional feature in the method selector")

    out = {
        "method": "pause_transition_segmenter",
        "n_videos": n_ok,
        "summary": {sig: {"mean_pk": round(float(np.mean(pks)), 4),
                           "mean_wd": round(float(np.mean(signal_wds[sig])), 4)}
                    for sig, pks in signal_pks.items()},
    }
    out_path = Path("results/eval_pause_transition.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
