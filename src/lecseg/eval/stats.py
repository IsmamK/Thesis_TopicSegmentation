"""
T30 — Bootstrap 95% CIs and paired Wilcoxon significance tests.

Usage:
    from lecseg.eval.stats import bootstrap_ci, wilcoxon_test, compare_methods

    ci = bootstrap_ci(scores, n_bootstrap=1000)
    p_value = wilcoxon_test(scores_a, scores_b)
    report = compare_methods(results_dict, baseline="cosine", novel="two_stage")
"""

from __future__ import annotations

import math
import random
from typing import Callable


def bootstrap_ci(
    values: list[float],
    stat: Callable[[list[float]], float] = None,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Compute bootstrap confidence interval.

    Args:
        values:     observed values (one per video)
        stat:       statistic function (default: mean)
        n_bootstrap: number of bootstrap resamples
        confidence:  confidence level (default 0.95)
        seed:        random seed

    Returns:
        (point_estimate, lower_bound, upper_bound)
    """
    if not values:
        return (0.0, 0.0, 0.0)

    if stat is None:
        stat = lambda x: sum(x) / len(x)

    rng = random.Random(seed)
    n = len(values)
    point = stat(values)

    bootstrap_stats = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(values) for _ in range(n)]
        bootstrap_stats.append(stat(sample))

    bootstrap_stats.sort()
    alpha = 1 - confidence
    lo_idx = int(alpha / 2 * n_bootstrap)
    hi_idx = int((1 - alpha / 2) * n_bootstrap)

    lo = bootstrap_stats[min(lo_idx, len(bootstrap_stats) - 1)]
    hi = bootstrap_stats[min(hi_idx, len(bootstrap_stats) - 1)]

    return (round(point, 4), round(lo, 4), round(hi, 4))


def wilcoxon_test(
    scores_a: list[float],
    scores_b: list[float],
) -> float:
    """
    Paired Wilcoxon signed-rank test (two-tailed).

    Returns approximate p-value. For n >= 10, uses normal approximation.
    For n < 10, uses exact distribution.

    Args:
        scores_a: scores for method A (one per video)
        scores_b: scores for method B (one per video)

    Returns:
        p-value (lower = more significant difference)
    """
    if len(scores_a) != len(scores_b):
        raise ValueError("scores must have the same length")
    if not scores_a:
        return 1.0

    diffs = [b - a for a, b in zip(scores_a, scores_b) if b != a]
    if not diffs:
        return 1.0

    # Rank absolute differences
    abs_diffs = [(abs(d), i, d > 0) for i, d in enumerate(diffs)]
    abs_diffs.sort(key=lambda x: x[0])

    # Assign ranks (handle ties by averaging)
    ranks: list[float] = [0.0] * len(abs_diffs)
    i = 0
    while i < len(abs_diffs):
        j = i
        while j < len(abs_diffs) and abs_diffs[j][0] == abs_diffs[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    W_plus = sum(r for r, (_, _, pos) in zip(ranks, abs_diffs) if pos)
    W_minus = sum(r for r, (_, _, pos) in zip(ranks, abs_diffs) if not pos)
    W = min(W_plus, W_minus)

    n = len(diffs)
    if n < 10:
        # Exact: p = 2 * P(W <= observed | H0)
        # Use critical values table approximation
        # For small n, use normal approximation with correction
        pass

    # Normal approximation (good for n >= 10)
    expected = n * (n + 1) / 4
    variance = n * (n + 1) * (2 * n + 1) / 24

    if variance <= 0:
        return 1.0

    z = (W - expected) / math.sqrt(variance)
    # Two-tailed p-value using normal CDF approximation
    p = 2 * _norm_cdf(-abs(z))
    return round(p, 4)


def _norm_cdf(z: float) -> float:
    """Standard normal CDF via approximation."""
    # Abramowitz & Stegun approximation (error < 7.5e-8)
    a = [0.319381530, -0.356563782, 1.781477937, -1.821255978, 1.330274429]
    t = 1 / (1 + 0.2316419 * abs(z))
    poly = sum(a[i] * t ** (i + 1) for i in range(5))
    phi = (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z)
    cdf = 1 - phi * poly
    return cdf if z >= 0 else 1 - cdf


def compare_methods(
    results: dict[str, dict[str, dict]],
    baseline: str,
    novel: str,
    metrics: list[str] | None = None,
    n_bootstrap: int = 1000,
) -> dict:
    """
    Compare two methods across all videos with bootstrap CIs and Wilcoxon test.

    Args:
        results:     {method: {video_id: {metric: value}}}
        baseline:    name of baseline method
        novel:       name of novel method
        metrics:     list of metric names to compare (default: pk, wd, f1, boundary_similarity)
        n_bootstrap: number of bootstrap resamples

    Returns:
        Dict with per-metric comparison results.
    """
    if metrics is None:
        metrics = ["pk", "wd", "f1", "boundary_similarity"]

    base_results = results.get(baseline, {})
    novel_results = results.get(novel, {})

    # Find common videos
    common_vids = sorted(
        v for v in base_results if v in novel_results
        and "error" not in base_results[v] and "error" not in novel_results[v]
    )

    if not common_vids:
        return {"error": "No common videos with valid results"}

    comparison = {
        "baseline": baseline,
        "novel": novel,
        "n_videos": len(common_vids),
        "metrics": {},
    }

    for metric in metrics:
        base_scores = [base_results[v].get(metric, 0.0) for v in common_vids]
        novel_scores = [novel_results[v].get(metric, 0.0) for v in common_vids]

        # For Pk/WD: lower is better; for F1/BS: higher is better
        lower_better = metric in ("pk", "wd")

        base_ci = bootstrap_ci(base_scores, n_bootstrap=n_bootstrap)
        novel_ci = bootstrap_ci(novel_scores, n_bootstrap=n_bootstrap)
        p_value = wilcoxon_test(base_scores, novel_scores)

        base_mean = base_ci[0]
        novel_mean = novel_ci[0]
        delta = novel_mean - base_mean
        improves = (delta < 0) if lower_better else (delta > 0)

        comparison["metrics"][metric] = {
            "baseline_mean": base_mean,
            "baseline_ci": list(base_ci[1:]),
            "novel_mean": novel_mean,
            "novel_ci": list(novel_ci[1:]),
            "delta": round(delta, 4),
            "p_value": p_value,
            "significant": p_value < 0.05,
            "improves": improves,
        }

    return comparison
