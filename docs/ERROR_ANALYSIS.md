# 🔍 ERROR ANALYSIS

**Built in T31. This file will be filled with per-error-type analysis from the
experiment results. The template below defines the structure.**

---

## Error taxonomy

We classify boundary prediction errors into four types. For each type we
report: frequency across folds, characteristic input conditions, and the
module responsible.

| ID | Error type | When it occurs | Module |
|---|---|---|---|
| E1 | Boundary merge | Fast-paced lecture, dense slides, short subtopics | Boundary predictor |
| E2 | Over-segmentation | Transition phrases ("So, moving on"), prosody false positives | Fusion + boundary |
| E3 | OCR-failure cascade | Handwritten content, small fonts, non-English math | OCR + fusion |
| E4 | LLM hallucination | Out-of-domain titles (rare disciplines), very short segments | Refinement |

---

## E1 — Boundary merge (under-segmentation)

**Description:** Two or more ground-truth topics are merged into one predicted
segment. The model fails to detect the transition.

**Frequency:** TODO — fill from `results/error_analysis/E1_*.json`

**Representative example:**
```
Gold:    [Intro (0–3 min)] | [Newton's Laws (3–12 min)] | [Friction (12–20 min)]
Pred:    [Intro (0–3 min)] | [Mechanics (3–20 min)]
```

**Root cause:** Text embeddings for "Newton's Laws" and "Friction" are
semantically adjacent (both mechanics sub-topics). The reliability score for
the visual stream is low (chalkboard, poor OCR confidence), so the model
relies mostly on text, which cannot separate the two.

**Mitigation tested:** Increase visual reliability weight for slide-rich
lectures (ablation in Table TODO). Partial improvement.

---

## E2 — Over-segmentation

**Description:** A false boundary is inserted mid-topic.

**Frequency:** TODO

**Representative example:**
```
Gold:    [Sorting algorithms (5–25 min)]
Pred:    [Sorting intro (5–11 min)] | [Sorting details (11–25 min)]
```

**Root cause:** Transition phrase ("So, let's dig deeper") triggers prosody
spike (pause + pitch reset). The model interprets it as a topic change.

**Mitigation tested:** LLM refinement snaps the boundary away. Partially
effective — LLM occasionally disagreed with human annotation.

---

## E3 — OCR-failure cascade

**Description:** PaddleOCR returns low-confidence or empty output on a
handwritten chalkboard frame. The fusion module sets visual weight ≈ 0, but
the reliability module still counts the video as "has visual stream",
causing a misleading fusion vector.

**Frequency:** TODO

**Mitigation tested:** Hard-threshold: if OCR confidence < 0.3 for >60% of
frames in a window, set visual weight = 0 explicitly. Reduces E3 by TODO%.

---

## E4 — LLM hallucination

**Description:** The local LLM generates a chapter title that is incorrect or
generic ("Introduction", "Overview") for a segment whose topic requires domain
knowledge the 8B model lacks.

**Frequency:** TODO (low — affects titles, not boundaries)

**Mitigation:** Title quality is evaluated separately as human preference
score. It is not included in the five boundary metrics.

---

## How to reproduce

```
python -m lecseg reproduce-all --error-analysis
# Writes to results/error_analysis/
python scripts/interpret.py results/error_analysis/
```

*Fill concrete numbers, examples, and mitigation results in T31.*
