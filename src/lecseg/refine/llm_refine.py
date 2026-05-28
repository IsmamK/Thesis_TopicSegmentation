"""
T28 / N4 — LLM boundary refinement and segment titling.

Uses a local Ollama LLM to:
1. Refine predicted boundaries: given surrounding sentences, confirm or adjust
   a predicted boundary by ±tolerance sentences.
2. Generate segment titles: given all sentences in a segment, produce a short
   descriptive title (3–8 words).

Requires Ollama to be running locally: `ollama serve`
Default model: llama3.1:8b (can be overridden).

Usage:
    from lecseg.refine.llm_refine import LLMRefiner

    refiner = LLMRefiner(model="llama3.1:8b")
    refined = refiner.refine_boundaries(sentences, predicted_boundaries, tolerance=2)
    titles = refiner.title_segments(sentences, boundaries)
"""

from __future__ import annotations

import json
import re
import time
from typing import Sequence

import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"


def _ollama_generate(prompt: str, model: str, temperature: float = 0.1) -> str:
    """Call Ollama generate API and return response text."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 200},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "").strip()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama not reachable at {OLLAMA_URL}: {e}") from e


class LLMRefiner:
    """
    LLM-based boundary refinement and segment titling.

    Args:
        model:       Ollama model name
        temperature: generation temperature
        timeout:     per-call timeout in seconds
    """

    def __init__(self, model: str = "llama3.1:8b", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

    def _is_available(self) -> bool:
        try:
            urllib.request.urlopen("http://localhost:11434", timeout=3)
            return True
        except Exception:
            return False

    def title_segment(self, sentences: list[str], max_words: int = 8) -> str:
        """
        Generate a short title for a segment given its sentences.

        Args:
            sentences: all sentences in the segment
            max_words: maximum words in the title

        Returns:
            Title string (3–8 words).
        """
        excerpt = " ".join(sentences[:5])
        if len(excerpt) > 500:
            excerpt = excerpt[:500] + "..."

        prompt = (
            f"Given this lecture excerpt, write a concise topic title "
            f"(exactly 3 to {max_words} words, no quotes, no punctuation at end):\n\n"
            f"\"{excerpt}\"\n\n"
            f"Title:"
        )
        response = _ollama_generate(prompt, self.model, self.temperature)
        # Clean up: take first line, strip quotes
        title = response.split("\n")[0].strip().strip('"\'')
        # Remove trailing punctuation
        title = re.sub(r"[.!?]+$", "", title).strip()
        return title if title else "Untitled Segment"

    def title_segments(
        self,
        sentences: Sequence[str],
        boundaries: list[int],
    ) -> list[str]:
        """
        Generate titles for all segments defined by the boundary list.

        Args:
            sentences:  all sentences in order
            boundaries: 1-based boundary indices

        Returns:
            List of title strings, one per segment.
        """
        sents = list(sentences)
        N = len(sents)
        bounds = [0] + sorted(boundaries) + [N]
        segments = [sents[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]

        titles = []
        for seg_sents in segments:
            if seg_sents:
                titles.append(self.title_segment(seg_sents))
            else:
                titles.append("Empty Segment")
        return titles

    def refine_boundary(
        self,
        sentences: Sequence[str],
        boundary: int,
        tolerance: int = 2,
    ) -> int:
        """
        Ask LLM to confirm or adjust a single predicted boundary position.

        Args:
            sentences:  all sentences in order
            boundary:   predicted 1-based boundary index
            tolerance:  max adjustment in either direction

        Returns:
            Refined boundary index (may be same as input).
        """
        sents = list(sentences)
        N = len(sents)

        lo = max(0, boundary - tolerance - 2)
        hi = min(N, boundary + tolerance + 2)
        window_sents = sents[lo:hi]

        candidates = list(range(
            max(1, boundary - tolerance),
            min(N, boundary + tolerance + 1)
        ))

        if not candidates:
            return boundary

        numbered = "\n".join(
            f"[{lo + i + 1}] {s}" for i, s in enumerate(window_sents)
        )
        cand_str = ", ".join(str(c) for c in candidates)

        prompt = (
            "You are analyzing a lecture transcript. A topic boundary has been predicted.\n"
            f"Here are sentences around the boundary (sentence numbers shown in brackets):\n\n"
            f"{numbered}\n\n"
            f"The predicted boundary is after sentence [{boundary}]. "
            f"Candidate positions: {cand_str}.\n"
            f"Which sentence number best marks where a new topic starts? "
            f"Reply with just the number."
        )

        response = _ollama_generate(prompt, self.model, self.temperature)
        # Extract first integer from response
        match = re.search(r"\b(\d+)\b", response)
        if match:
            refined = int(match.group(1))
            if refined in candidates:
                return refined
        return boundary

    def refine_boundaries(
        self,
        sentences: Sequence[str],
        boundaries: list[int],
        tolerance: int = 2,
    ) -> list[int]:
        """
        Refine all predicted boundaries using LLM context.

        Args:
            sentences:  all sentences in order
            boundaries: predicted 1-based boundary indices
            tolerance:  max adjustment per boundary

        Returns:
            Refined boundary list (may have fewer boundaries if LLM collapses some).
        """
        if not self._is_available():
            return boundaries  # fall back to original if Ollama not running

        refined = []
        used = set()
        for b in sorted(boundaries):
            r = self.refine_boundary(sentences, b, tolerance)
            if r not in used:
                refined.append(r)
                used.add(r)

        return sorted(refined)
