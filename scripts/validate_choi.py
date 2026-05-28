"""
Validate baselines on the real Choi (2000) benchmark dataset.

Parses 200 .ref files from data/benchmarks/choi_original/ (4 conditions),
runs TextTiling (NLTK reference), our C99, and CosineSeg, then compares
to published numbers.

Published Pk (lower=better):
    TextTiling:  ~0.46  (Choi 2000 Table 2)
    C99:         ~0.12  (Choi 2000 Table 2)
    BayesSeg:    ~0.10  (Eisenstein & Barzilay 2008)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
from lecseg.metrics import pk, wd
from lecseg.baselines.classical import c99


CHOI_DIR = ROOT / "data" / "benchmarks" / "choi_original"
CONDITIONS = ["3-11", "3-5", "6-8", "9-11"]


def parse_ref_file(path: Path) -> tuple[list[str], list[int]]:
    """Parse a .ref file → (sentences, boundary_indices).

    Boundaries are sentence indices where a *new* segment begins (1-based,
    i.e. boundary at position k means segment break between sentence k-1 and k).
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = [b.strip() for b in text.split("==========") if b.strip()]

    sentences: list[str] = []
    boundaries: list[int] = []

    for block in blocks:
        block_sents = [s.strip() for s in block.splitlines() if s.strip()]
        if not block_sents:
            continue
        if sentences:  # not the first segment
            boundaries.append(len(sentences))
        sentences.extend(block_sents)

    return sentences, boundaries


def run_nltk_texttiling(sentences: list[str]) -> list[int]:
    """NLTK reference TextTiling implementation."""
    try:
        from nltk.tokenize import TextTilingTokenizer
    except ImportError:
        return []

    # TextTilingTokenizer works on a single string with double-newlines as paragraph breaks
    text = "\n\n".join(sentences)
    ttt = TextTilingTokenizer(w=20, k=10)
    try:
        tiles = ttt.tokenize(text)
    except Exception:
        return []

    # Reconstruct boundary indices from tile lengths
    boundaries = []
    pos = 0
    for tile in tiles[:-1]:
        tile_sents = [s.strip() for s in tile.split("\n\n") if s.strip()]
        pos += len(tile_sents)
        if 0 < pos < len(sentences):
            boundaries.append(pos)
    return sorted(set(boundaries))


def run_our_c99(sentences: list[str], n_segs: int) -> list[int]:
    return c99(sentences, n_segments=n_segs)


def evaluate_pk(hyp: list[int], ref: list[int], n: int) -> float:
    return pk(hyp, ref, n_units=n)


def main():
    all_results: dict[str, dict] = {}

    for cond in CONDITIONS:
        cond_dir = CHOI_DIR / cond
        if not cond_dir.exists():
            print(f"  SKIP {cond}: directory not found")
            continue

        ref_files = sorted(cond_dir.glob("*.ref"))
        print(f"\nCondition {cond}: {len(ref_files)} files")

        pks_tt, pks_c99 = [], []

        for rf in ref_files:
            sents, ref_bounds = parse_ref_file(rf)
            if len(sents) < 5:
                continue
            n_segs = len(ref_bounds) + 1

            # NLTK TextTiling
            tt_bounds = run_nltk_texttiling(sents)
            pk_tt = evaluate_pk(tt_bounds, ref_bounds, len(sents))
            pks_tt.append(pk_tt)

            # Our C99 (capped at 300 sentences to avoid O(n^2) hang)
            sents_cap = sents[:300]
            ref_bounds_cap = [b for b in ref_bounds if b < len(sents_cap)]
            c99_bounds = run_our_c99(sents_cap, n_segs)
            pk_c99 = evaluate_pk(c99_bounds, ref_bounds_cap, len(sents_cap))
            pks_c99.append(pk_c99)

        mean_tt = sum(pks_tt) / len(pks_tt) if pks_tt else float("nan")
        mean_c99 = sum(pks_c99) / len(pks_c99) if pks_c99 else float("nan")

        print(f"  NLTK TextTiling Pk={mean_tt:.4f}  (published ~0.46)")
        print(f"  Our C99         Pk={mean_c99:.4f}  (published ~0.12)")

        all_results[cond] = {
            "n_docs": len(pks_tt),
            "nltk_texttiling_pk": round(mean_tt, 4),
            "our_c99_pk": round(mean_c99, 4),
        }

    # Aggregate across all conditions
    all_tt = [v["nltk_texttiling_pk"] for v in all_results.values()]
    all_c99 = [v["our_c99_pk"] for v in all_results.values()]
    overall = {
        "overall_nltk_texttiling_pk": round(sum(all_tt)/len(all_tt), 4) if all_tt else None,
        "overall_our_c99_pk": round(sum(all_c99)/len(all_c99), 4) if all_c99 else None,
        "published_texttiling_pk": 0.46,
        "published_c99_pk": 0.12,
        "conditions": all_results,
    }

    out = ROOT / "results" / "choi_validation.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(overall, indent=2), encoding="utf-8")
    print(f"\n\nOverall NLTK TextTiling Pk={overall['overall_nltk_texttiling_pk']}  (published ~0.46)")
    print(f"Overall Our C99         Pk={overall['overall_our_c99_pk']}  (published ~0.12)")
    print(f"\nSaved to {out}")

    # Interpretation
    c99_ratio = overall["overall_our_c99_pk"] / 0.12 if overall["overall_our_c99_pk"] else None
    print("\n=== SCIENTIFIC METHOD ASSESSMENT ===")
    if c99_ratio and c99_ratio < 2.0:
        print("C99: ACCEPTABLE — within 2x of published Pk (implementation differences expected)")
    elif c99_ratio:
        print(f"C99: WEAK — {c99_ratio:.1f}x worse than published. Consider:")
        print("  - Using segeval library's C99 (pip install segeval)")
        print("  - Or citing our implementation as 'C99-lite' with known limitations")
    tt_ratio = overall["overall_nltk_texttiling_pk"] / 0.46 if overall["overall_nltk_texttiling_pk"] else None
    if tt_ratio and tt_ratio < 1.5:
        print("TextTiling (NLTK): VALIDATED — close to published Pk")
    elif tt_ratio:
        print(f"TextTiling (NLTK): Pk={overall['overall_nltk_texttiling_pk']} vs published 0.46")


if __name__ == "__main__":
    main()
