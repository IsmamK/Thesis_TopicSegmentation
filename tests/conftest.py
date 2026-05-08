"""Shared pytest fixtures for the LECSEG test suite."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_segments_short() -> list[int]:
    """A 20-unit ``[0|1]`` boundary sequence with 3 boundaries."""
    return [0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]


@pytest.fixture
def sample_segments_predicted() -> list[int]:
    """Predicted boundaries close to but not equal to ground-truth."""
    return [0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
