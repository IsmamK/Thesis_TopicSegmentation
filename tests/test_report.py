"""Tests for scripts/report.py Markdown report generation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from report import generate_report


def _fake_results():
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
    return {m: {"vid001": scores, "vid002": scores} for m, scores in methods.items()}


def test_report_is_string():
    r = generate_report(_fake_results())
    assert isinstance(r, str)
    assert len(r) > 100


def test_report_has_sections():
    r = generate_report(_fake_results())
    assert "## 1. Main Results" in r
    assert "## 2. Improvement" in r
    assert "## 3. Per-Video" in r


def test_report_bold_best_values():
    r = generate_report(_fake_results())
    assert "**0." in r  # best values bolded


def test_report_empty_results():
    r = generate_report({})
    assert isinstance(r, str)
    assert "LECSEG" in r
