"""Tests for scripts/tables.py LaTeX table generation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from tables import make_main_table, make_ablation_table


def _fake_results():
    """Minimal fake results dict: method -> {video_id -> {metric -> float}}."""
    methods = {
        "texttiling":    {"pk": 0.35, "wd": 0.40, "f1": 0.55, "bs": 0.60},
        "c99":           {"pk": 0.33, "wd": 0.38, "f1": 0.57, "bs": 0.62},
        "cosine":        {"pk": 0.30, "wd": 0.35, "f1": 0.60, "bs": 0.65},
        "kmeans":        {"pk": 0.31, "wd": 0.36, "f1": 0.59, "bs": 0.64},
        "bert_seg":      {"pk": 0.28, "wd": 0.33, "f1": 0.63, "bs": 0.68},
        "two_stage":     {"pk": 0.22, "wd": 0.27, "f1": 0.72, "bs": 0.75},
        "two_stage_llm": {"pk": 0.21, "wd": 0.26, "f1": 0.74, "bs": 0.77},
        "hierarchical":  {"pk": 0.20, "wd": 0.24, "f1": 0.76, "bs": 0.79},
    }
    # Wrap in video-level dict
    return {m: {"vid001": scores} for m, scores in methods.items()}


def test_make_main_table_returns_string():
    results = _fake_results()
    table = make_main_table(results)
    assert isinstance(table, str)
    assert r"\begin{table}" in table
    assert r"\end{table}" in table


def test_make_main_table_contains_methods():
    results = _fake_results()
    table = make_main_table(results)
    assert "TextTiling" in table or r"\textsc{TextTiling}" in table
    assert r"\textbf" in table  # best values bolded


def test_make_main_table_has_midrule():
    results = _fake_results()
    table = make_main_table(results)
    # Should have a midrule separating baselines from novel
    assert table.count(r"\midrule") >= 2


def test_make_ablation_table_returns_string():
    results = _fake_results()
    table = make_ablation_table(results)
    assert isinstance(table, str)
    assert r"\begin{table}" in table
    assert r"\checkmark" in table


def test_make_main_table_empty_results():
    table = make_main_table({})
    assert r"\begin{table}" in table
    # Should not crash, just produce table with no rows
