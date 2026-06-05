---
license: cc-by-4.0
task_categories:
- text-segmentation
language:
- en
tags:
- lecture
- topic-segmentation
- education
- hierarchical
- benchmark
size_categories:
- 1K<n<10K
---

# LECSEG-30: Lecture Topic Segmentation Benchmark

A 30-video, 32.52-hour hierarchical lecture topic segmentation benchmark from YouTube.

## Dataset Description

**LECSEG-30** provides:
- 30 YouTube lecture videos across 5 academic domains
- Creator-provided chapter boundaries as reproducible reference labels (419 total)
- Human-reviewed, LLM-assisted hierarchical subtopic annotations (904 labels)
- Pre-computed sentence splits (Whisper ASR + spaCy)
- Inter-annotator agreement: chapter κ=0.535, subtopic κ=0.426

**Domains:** BIOLOGY (6), CS (7), MATH (4), PHILOSOPHY (6), PHYSICS (7)

## Splits

| Split | Description | Rows |
|---|---|---|
| `metadata` | Per-video metadata | 30 |
| `boundaries` | Chapter + subtopic boundaries | varies |
| `sentences` | Sentence-level transcript segments | ~25,000 |

## Intended Use

LECSEG-30 is intended for low-resource lecture-video topic segmentation,
chapter-boundary evaluation, subtopic-analysis research, and reproducibility
studies. It is best used for controlled experiments and diagnostic analysis,
not as a universal large-scale video chaptering benchmark.

## Limitations and Biases

- The dataset contains only 30 videos and is intentionally small.
- Domain balance is imperfect; Mathematics has only 4 videos.
- YouTube chapters are creator-provided navigation references, not perfect
  pedagogical ground truth.
- Subtopic labels began as LLM-generated drafts and were then human-reviewed;
  this should be cited as human-reviewed LLM-assisted annotation.
- Raw videos are not redistributed. Users must retrieve videos from the
  original public YouTube URLs if needed.

## Usage

```python
from datasets import load_dataset
ds = load_dataset("lecseg/lecseg30")

# Get all boundaries for a video
video_id = "NNnIGh9g6fA"
bounds = ds["boundaries"].filter(lambda x: x["video_id"] == video_id)
```

## Citation

If you use LECSEG-30, please cite:
```
@misc{lecseg30_2026,
  title={LECSEG-30: A Hierarchical Lecture Topic Segmentation Benchmark},
  author={[Author names omitted for review]},
  year={2026},
  note={Pre-thesis project T2520718}
}
```

## License

CC BY 4.0. Raw videos are not redistributed; only transcripts and annotations.
