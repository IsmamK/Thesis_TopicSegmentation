# NOVELTY_TRACKER — Locked Research Gap and Novelty Claims

This document locks the seven LECSEG novelty claims. Each claim is tied to a prior-work gap, an implementing module, an experiment config, and a thesis proof artifact.

| ID | Name | Gap it closes (with citations from matrix) | Implementing module (file path) | Experiment config | Proof artifact (table/figure) |
|---|---|---|---|---|---|
| N1 | Multimodal lecture boundary pipeline | Text-only segmentation work such as Hearst/TextTiling, Choi/C99, Reimers/Sentence-BERT, and Sun/contrastive transformer focuses on text, while Radford/Whisper provides ASR but not topic boundaries. LECSEG closes the gap by combining transcript, embeddings, and lecture-specific signals. | `src/lecseg/models/boundary_predictor.py`, `src/lecseg/features/emb_text.py`, `src/lecseg/preprocess/transcribe.py` | `configs/experiments/n1_multimodal_boundary.yaml` | Table 4.2, Figure 4.1 |
| N2 | Reliability-weighted multimodal fusion | Visual/audio/video papers such as Gandhi/visually salient words, Karim/MED-VT++, and Yu/multimodal coherence use multimodal evidence, but do not explicitly weight lecture modalities by reliability for boundary prediction. | `src/lecseg/models/rw_fusion.py`, `src/lecseg/features/emb_visual.py`, `src/lecseg/features/prosody.py` | `configs/experiments/n2_rw_fusion.yaml` | Table 4.3, Figure 4.4 |
| N3 | Two-level hierarchical lecture segmentation | Prior lecture segmentation systems such as Tuna/classroom videos, Zhang/MOOC segmentation, Chand & Ogul/lecture video segmentation, and Che & Yang/slide synchronization mainly target flat boundaries or alignment, not chapter plus subtopic hierarchy. | `src/lecseg/models/hier_output.py`, `src/lecseg/report/export_segments.py` | `configs/experiments/n3_hierarchical_output.yaml` | Table 4.2, Figure 4.2 |
| N4 | Local LLM boundary refinement and auto-titling | Fan/topic segmentation via LLMs and related LLM-based segmentation work show LLM usefulness, but often depend on closed or non-local models. LECSEG uses local Ollama Llama 3.1/Mistral refinement for reproducible boundary cleanup and title generation. | `src/lecseg/refine/llm_refine.py`, `src/lecseg/refine/title_generator.py` | `configs/experiments/n4_local_llm_refine.yaml` | Table 4.5, Figure 4.5 |
| N5 | LECSEG-30 seed dataset across five domains | Existing lecture resources such as AVLectures, Tuna/classroom videos, and Zhang/MOOC segmentation are limited by source, setting, annotation structure, or availability. LECSEG-30 creates a curated 30-video, five-domain seed dataset using creator chapter boundaries. | `data/video_list.csv`, `scripts/validate_video_list.py`, `data/release/LECSEG-30/` | `configs/experiments/n5_dataset_validation.yaml` | Table 3.1, Figure 3.2 |
| N6 | Unified evaluation with multiple segmentation metrics | Beeferman/Pk, Pevzner & Hearst/WindowDiff, and Fournier/Boundary Similarity each contribute evaluation ideas, but prior work often reports only one or two metrics without unified comparison, confidence intervals, or significance testing. | `src/lecseg/eval/metrics.py`, `src/lecseg/eval/stats.py` | `configs/experiments/n6_eval_suite.yaml` | Table 4.4, Figure 4.6 |
| N7 | Reproducible end-to-end artifact release | Many prior systems release partial code, closed data, or non-reproducible experiments. LECSEG closes this gap by tying Makefile commands, configs, dataset manifest, results, and thesis tables into one reproducible pipeline. | `Makefile`, `configs/`, `scripts/reproduce.py`, `results/` | `configs/experiments/n7_reproducibility.yaml` | Appendix A, Table A.1 |

## Sanity Check

Each claim follows this chain:

1. Prior work leaves a specific gap.
2. LECSEG implements a module that targets that gap.
3. A named experiment config will test the module.
4. A thesis table or figure will report the proof.

## Prior Work Anchors Used

Hearst/TextTiling, Choi/C99, Beeferman/Pk, Pevzner & Hearst/WindowDiff, Fournier/Boundary Similarity, Tuna/classroom videos, Zhang/MOOC segmentation, Gandhi/visually salient words, Chand & Ogul/lecture video segmentation, Freisinger/multilingual topic segmentation, D.S.S./AVLectures, Sun/contrastive transformer, Karim/MED-VT++, Yu/multimodal coherence, Fan/LLM topic segmentation, Sener/activity segmentation, Che & Yang/slide synchronization, Reimers/Sentence-BERT, Radford/Whisper.

## Backup Novelty Pool

- B1 — Multilingual capability for Bangla-English mixed lectures.
- B2 — CPU-only real-time inference benchmark.
- B3 — Slide-aware OCR-conditioned boundary scoring.
- B4 — Calibrated boundary confidence scores.
- B5 — Active-learning-friendly annotation tool with disagreement highlighting.
