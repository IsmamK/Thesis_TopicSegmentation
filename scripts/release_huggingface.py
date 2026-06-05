"""Release LECSEG-30 dataset to HuggingFace Hub.

Uploads:
- data/gt/ (YouTube chapter ground truth, 30 videos)
- data/gt_hier/ (hierarchical annotations, 30 videos)
- data/manifest.jsonl (video manifest)
- data/sentences/ (sentence splits, 30 videos)

Does NOT upload:
- Raw video files (too large, not redistributable)
- Embeddings (derived, reproducible from sentences)
- Audio features (derived)

Usage:
    python scripts/release_huggingface.py --repo-id USERNAME/lecseg30 [--dry-run]

Requires: huggingface-cli login (or HF_TOKEN env var)
"""

import argparse
import json
import os
from pathlib import Path
from datasets import Dataset, DatasetDict, Features, Value, Sequence


def load_manifest():
    return [json.loads(l) for l in open("data/manifest.jsonl", encoding="utf-8")]


def load_gt(vid_id: str) -> dict:
    p = Path(f"data/gt/{vid_id}.json")
    if p.exists():
        return json.load(open(p, encoding="utf-8"))
    return {}


def load_gt_hier(vid_id: str) -> dict:
    p = Path(f"data/gt_hier/{vid_id}.json")
    if p.exists():
        return json.load(open(p, encoding="utf-8"))
    return {}


def load_sentences(vid_id: str) -> list:
    p = Path(f"data/sentences/{vid_id}/sentences.json")
    if p.exists():
        return json.load(open(p, encoding="utf-8")).get("sentences", [])
    return []


def build_dataset(manifest: list) -> DatasetDict:
    # Main metadata split
    meta_rows = []
    sentences_rows = []
    boundaries_rows = []

    for v in manifest:
        vid_id = v["id"]
        gt = load_gt(vid_id)
        gt_hier = load_gt_hier(vid_id)
        sents = load_sentences(vid_id)

        meta_rows.append({
            "video_id": vid_id,
            "title": v.get("title", ""),
            "domain": v.get("domain", ""),
            "duration_sec": float(gt.get("duration_sec", 0)),
            "n_chapters": int(gt.get("num_chapters", 0)),
            "n_sentences": len(sents),
            "youtube_url": f"https://www.youtube.com/watch?v={vid_id}",
        })

        # Chapter boundaries
        for i, (t, title) in enumerate(zip(
            gt.get("boundaries_sec", []),
            gt.get("titles", [""] * 100)[1:]  # skip first (intro)
        )):
            boundaries_rows.append({
                "video_id": vid_id,
                "boundary_idx": i,
                "start_sec": float(t),
                "title": str(title),
                "level": "chapter",
            })

        # Hierarchical subtopic boundaries
        for subtopic in gt_hier.get("subtopics", []):
            boundaries_rows.append({
                "video_id": vid_id,
                "boundary_idx": subtopic.get("idx", -1),
                "start_sec": float(subtopic.get("start_sec", -1)),
                "title": subtopic.get("title", ""),
                "level": "subtopic",
            })

        # Sentences
        for s in sents:
            sentences_rows.append({
                "video_id": vid_id,
                "sentence_idx": int(s["idx"]),
                "start_sec": float(s["start"]),
                "end_sec": float(s["end"]),
                "text": s["text"],
            })

    return DatasetDict({
        "metadata": Dataset.from_list(meta_rows),
        "boundaries": Dataset.from_list(boundaries_rows),
        "sentences": Dataset.from_list(sentences_rows),
    })


def create_dataset_card(manifest: list) -> str:
    n = len(manifest)
    domains = {}
    for v in manifest:
        d = v.get("domain", "UNKNOWN")
        domains[d] = domains.get(d, 0) + 1
    domain_str = ", ".join(f"{d} ({c})" for d, c in sorted(domains.items()))
    return f"""---
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

**Domains:** {domain_str}

## Splits

| Split | Description | Rows |
|---|---|---|
| `metadata` | Per-video metadata | {n} |
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
@misc{{lecseg30_2026,
  title={{LECSEG-30: A Hierarchical Lecture Topic Segmentation Benchmark}},
  author={{[Author names omitted for review]}},
  year={{2026}},
  note={{Pre-thesis project T2520718}}
}}
```

## License

CC BY 4.0. Raw videos are not redistributed; only transcripts and annotations.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", default="lecseg/lecseg30",
                        help="HuggingFace repo ID (username/dataset-name)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Build dataset locally without pushing")
    args = parser.parse_args()

    manifest = load_manifest()
    print(f"Building LECSEG-30 dataset from {len(manifest)} videos...")

    ds = build_dataset(manifest)
    print(f"Dataset built:")
    for split, d in ds.items():
        print(f"  {split}: {len(d)} rows")

    # Save card
    card = create_dataset_card(manifest)
    Path("data/huggingface_dataset_card.md").write_text(card, encoding="utf-8")
    print("Dataset card saved to data/huggingface_dataset_card.md")

    if args.dry_run:
        print("\n[DRY RUN] Dataset built successfully. Use --repo-id and remove --dry-run to push.")
        # Save locally as parquet for verification
        for split, d in ds.items():
            out = Path(f"data/hf_export/{split}.parquet")
            out.parent.mkdir(parents=True, exist_ok=True)
            d.to_parquet(str(out))
            print(f"  Saved {out}")
        return

    try:
        from huggingface_hub import HfApi
        api = HfApi()
        ds.push_to_hub(args.repo_id, private=False)
        print(f"\nDataset pushed to https://huggingface.co/datasets/{args.repo_id}")

        # Push dataset card
        api.upload_file(
            path_or_fileobj=card.encode("utf-8"),
            path_in_repo="README.md",
            repo_id=args.repo_id,
            repo_type="dataset",
        )
        print("Dataset card uploaded.")
    except Exception as e:
        print(f"Push failed: {e}")
        print("Run: huggingface-cli login")
        print("Or set HF_TOKEN environment variable")


if __name__ == "__main__":
    main()
