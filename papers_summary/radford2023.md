# Robust Speech Recognition via Large-Scale Weak Supervision (Whisper)

**Authors:** Alec Radford, Jong Wook Kim, Tao Xu, Greg Brockman, Christine McLeavey, Ilya Sutskever
**Year:** 2023
**Venue:** ICML 2023 (Proceedings of the 40th International Conference on Machine Learning, pages 28492–28518)
**Citation key:** `radford2023_whisper`
**Link:** https://arxiv.org/abs/2212.04356

## BibTeX
```bibtex
@inproceedings{radford2023_whisper,
  author    = {Radford, Alec and Kim, Jong Wook and Xu, Tao and Brockman, Greg and McLeavey, Christine and Sutskever, Ilya},
  title     = {Robust Speech Recognition via Large-Scale Weak Supervision},
  booktitle = {Proceedings of the 40th International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {202},
  pages     = {28492--28518},
  publisher = {PMLR},
  year      = {2023},
}
```

## Problem (2 sentences)

Supervised automatic speech recognition (ASR) systems trained on carefully curated, high-quality datasets tend to be brittle: they achieve strong in-distribution performance but degrade significantly on out-of-distribution audio, accents, or languages. The paper asks whether training a single multitask, multilingual ASR model on a very large but weakly supervised corpus of internet audio can yield systems that are both accurate and broadly robust without dataset-specific fine-tuning.

## Method (5 bullets)
- Collect 680,000 hours of audio paired with transcripts crawled from the internet, covering 99 languages and multiple tasks (transcription, translation, language identification), using the naturally occurring audio–text alignment as weak supervision.
- Train a sequence-to-sequence Transformer encoder-decoder (multiple model sizes from 39 M to 1.5 B parameters) directly on this data using standard cross-entropy, without any specialised pre-training objectives.
- Frame all tasks (transcription, translation, voice activity detection, language ID) as a single conditional generation problem using a shared vocabulary and task-conditioning tokens prepended to the decoder input.
- Evaluate models in a zero-shot transfer regime: no fine-tuning on any evaluation benchmark, assessing generalisation purely from the large-scale weak supervision.
- Compare against fully supervised baselines and human transcription on standard benchmarks (LibriSpeech, Common Voice, VoxPopuli, etc.) and a diverse set of out-of-distribution test sets.

## Datasets used
| Dataset | Size | Domain |
|---|---|---|
| Internet audio with transcripts (training) | 680,000 hours, 99 languages | Multilingual, multitask web audio |
| LibriSpeech (evaluation) | 960 h train / test-clean & test-other splits | Read English audiobooks |
| Common Voice (evaluation) | not reported in abstract | Crowd-sourced multilingual speech |
| VoxPopuli (evaluation) | not reported in abstract | European Parliament speech |
| Additional out-of-distribution test sets | not reported in abstract | Various domains |

## Metrics & headline results
| Metric | Value | Dataset |
|---|---|---|
| WER (Whisper large-v2, zero-shot) | 2.7% | LibriSpeech test-clean |
| WER (Whisper small, zero-shot) | 6.7% | LibriSpeech test-clean |
| Error reduction vs. supervised baselines | ~55.2% fewer errors on average | Out-of-distribution datasets |

## Limitations (3 bullets, from the paper itself)
- The models are released as a "foundation for further work" rather than a finished product, implying known gaps in coverage and robustness that remain to be addressed.
- Zero-shot performance on lower-resource languages lags behind English and other high-resource languages due to data imbalance in the 680K-hour training set.
- The weak supervision from internet audio contains noise and misalignments that can introduce systematic transcription errors, particularly for disfluencies and non-speech events.

## How it relates to our work (1 paragraph)

Whisper is the ASR backbone used in LECSEG to transcribe lecture audio into text, which then feeds the transcript-based boundary detection stream. Its robustness to diverse speakers, accents, recording conditions, and technical vocabulary makes it well-suited to the heterogeneous lecture videos in LECSEG-30. Whisper's multilingual capability also means the pipeline can in principle extend beyond English lectures without replacing the ASR component. The quality of the Whisper transcript directly affects the reliability weight assigned to the transcript modality in LECSEG's fusion stage.

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): Whisper is a speech recognition system; LECSEG uses its output as one modality alongside slides and audio features in a hierarchical segmentation pipeline.
- **N2** (reliability-weighted fusion): Whisper produces transcripts but has no mechanism to signal segment-level transcription confidence for downstream fusion; LECSEG adds reliability gating over the transcript stream.
- **N3** (two-level output): Whisper outputs a flat token sequence; LECSEG infers two-level topical boundaries from transcript content.
- **N4** (local-LLM refinement): Whisper does not perform topic-boundary refinement or segment titling; LECSEG adds a local-LLM post-processing stage.
- **N5** (LECSEG-30 dataset): Whisper is evaluated on speech recognition benchmarks; LECSEG-30 is the first lecture-video segmentation benchmark with multi-level annotations.
- **N6** (5-metric eval + CIs): Whisper reports WER; LECSEG reports five segmentation metrics (P_k, WinDiff, F₁, etc.) with bootstrap confidence intervals.
- **N7** (reproducibility): Whisper models and code are publicly released; LECSEG builds on this by also releasing its segmentation-specific components, dataset, and training scripts.


