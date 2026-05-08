# MED-VT++: Unifying Multimodal Learning with Multi-Scale Encoder-Decoder Video Transformer

**Authors:** Rezaul Karim, He Zhao, Richard P. Wildes, Mennatullah Siam
**Year:** 2024
**Venue:** arXiv preprint 2304.05930 (extended version of CVPR 2023 paper)
**Citation key:** `karim2024_medvt`
**Link:** https://arxiv.org/abs/2304.05930

## BibTeX
```bibtex
@misc{karim2024_medvt,
  author        = {Karim, Rezaul and Zhao, He and Wildes, Richard P. and Siam, Mennatullah},
  title         = {{MED-VT++}: Unifying multimodal learning with multi-scale encoder-decoder video transformer},
  year          = {2024},
  eprint        = {2304.05930},
  archivePrefix = {arXiv}
}
```

## Problem (2 sentences)
Temporal video understanding tasks such as video object segmentation and actor-action segmentation require models that jointly capture spatial appearance, temporal dynamics, and (optionally) audio cues across multiple scales. MED-VT++ proposes a unified multi-scale encoder-decoder transformer that handles these tasks in a single architecture without optical flow or per-task specialised modules.

## Method (5 bullets)
- Designs a multi-scale video transformer encoder that processes spatiotemporal features at multiple resolutions, enabling the model to capture both fine-grained spatial details and coarse temporal structure.
- Introduces a transductive many-to-many label propagation mechanism that enforces temporal consistency across frames without requiring optical flow as a separate input.
- Optionally fuses audio features into the visual encoder via cross-modal attention (the "++" extension over the CVPR 2023 base model), enabling audio-visual video object segmentation.
- Applies a shared decoder with task-specific output heads across multiple dense video prediction tasks: automatic video object segmentation (AVOS), actor-action segmentation, video scene segmentation, and audio-visual segmentation (AVS).
- Evaluates on standard benchmarks for each task, demonstrating state-of-the-art performance without optical flow.

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| YouTube-VOS | 4,453 videos | General video (object segmentation) |
| DAVIS 2016/2017 | 50/90 videos | Object segmentation |
| A2D-Sentences | 3,782 videos | Actor-action segmentation |
| AVSBench | 4,932 clips | Audio-visual segmentation |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| J&F mean | not reported in abstract | YouTube-VOS |
| mIoU | not reported in abstract | A2D-Sentences |

## Limitations (3 bullets, from the paper itself)
- MED-VT++ is designed for dense per-frame prediction tasks; it is not directly designed for the coarser task of topic boundary detection in lecture videos, which requires reasoning over minutes-long temporal windows.
- The model requires significant compute for multi-scale spatiotemporal attention over video sequences.
- Audio-visual fusion is limited to paired audio-visual data; it does not address scenarios with unreliable or missing audio modalities.

## How it relates to our work (1 paragraph)
MED-VT++ is cited in LECSEG Chapter 2 as a representative state-of-the-art video transformer for dense video segmentation, contrasting with LECSEG's approach. The NOVELTY_TRACKER identifies `karim2024_medvt` as gap evidence for N2: MED-VT++ fuses audio and visual modalities but does not gate them by estimated reliability—all modalities are treated equally regardless of signal quality. LECSEG's reliability-weighted fusion directly addresses this limitation in the context of lecture video segmentation.

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): MED-VT++ performs dense frame-level segmentation (object masks); LECSEG performs sentence-level topic boundary detection with a hierarchical two-level output.
- **N2** (reliability-weighted fusion): MED-VT++ fuses audio and visual without reliability gating; LECSEG learns per-modality reliability weights adaptively.
- **N3** (two-level output): MED-VT++ does not model hierarchical topic structure; LECSEG jointly predicts chapter and subtopic boundaries.
- **N4** (local-LLM refinement): No LLM step in MED-VT++; LECSEG adds local-LLM boundary verification and titling.
- **N5** (LECSEG-30 dataset): Evaluated on general video benchmarks; LECSEG uses a lecture-specific κ-validated dataset.
- **N6** (5-metric eval + CIs): Segmentation IoU metrics; LECSEG uses five boundary-specific metrics with bootstrap CIs.
- **N7** (reproducibility): Code released; LECSEG adds pinned seeds, configs, and `make reproduce`.


