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
- Creator-provided chapter boundaries as ground truth (419 total)
- Human-reviewed hierarchical subtopic annotations (904 labels)
- Pre-computed sentence splits (Whisper ASR + spaCy)
- Inter-annotator agreement: chapter κ=0.535, subtopic κ=0.426

**Domains:** BIOLOGY (6), CS (7), MATH (4), PHILOSOPHY (6), PHYSICS (7)

## Splits

| Split | Description | Rows |
|---|---|---|
| `metadata` | Per-video metadata | 30 |
| `boundaries` | Chapter + subtopic boundaries | varies |
| `sentences` | Sentence-level transcript segments | ~25,000 |

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
