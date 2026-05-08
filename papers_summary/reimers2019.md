# Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks

**Authors:** Nils Reimers, Iryna Gurevych
**Year:** 2019
**Venue:** EMNLP 2019 (Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing)
**Citation key:** `reimers2019_sbert`
**Link:** https://arxiv.org/abs/1908.10084

## BibTeX
```bibtex
@inproceedings{reimers2019_sbert,
  author    = {Reimers, Nils and Gurevych, Iryna},
  title     = {Sentence-{BERT}: Sentence Embeddings using Siamese {BERT}-Networks},
  booktitle = {Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing (EMNLP-IJCNLP)},
  pages     = {3982--3992},
  publisher = {Association for Computational Linguistics},
  year      = {2019},
  doi       = {10.18653/v1/D19-1410},
}
```

## Problem (2 sentences)

Standard BERT requires both sentences to be fed jointly through the network for sentence-pair tasks, making it computationally prohibitive for tasks like semantic similarity search or clustering over large sentence collections (finding the closest pair among 10,000 sentences requires ~50 million inference passes, roughly 65 hours). The paper asks whether BERT can be adapted to produce fixed-size, semantically meaningful sentence embeddings that support efficient cosine-similarity comparison.

## Method (5 bullets)
- Fine-tune pretrained BERT (and RoBERTa) using siamese and triplet network structures, where two sentence branches share weights and produce independent embeddings.
- Apply a pooling operation (mean pooling over token embeddings) on top of BERT's output to derive a fixed-size sentence vector.
- Train with objective functions suited to the downstream task: softmax classification loss on Natural Language Inference (NLI) data for classification tasks, and cosine-similarity regression loss on Semantic Textual Similarity (STS) data for similarity tasks.
- Use triplet networks with a margin-based ranking loss for tasks requiring fine-grained ordering of sentence similarity.
- Evaluate on seven STS benchmarks and multiple SentEval transfer tasks, measuring Spearman rank correlation to confirm that the learned embeddings capture human semantic similarity judgements.

## Datasets used
| Dataset | Size | Domain |
|---|---|---|
| SNLI (Stanford NLI) | 570K sentence pairs | Natural language inference |
| MultiNLI | 433K sentence pairs | Multi-genre NLI |
| STS 2012–2016 benchmarks | ~1K–3K pairs each | Semantic textual similarity |
| STSbenchmark (STSb) | ~8.6K pairs | Semantic textual similarity |
| SICK-Relatedness | ~10K pairs | Semantic relatedness |

## Metrics & headline results
| Metric | Value | Dataset |
|---|---|---|
| Spearman correlation (avg, SBERT-NLI-base) | 74.89 | STS12–STS16 + STSb + SICK-R |
| Spearman correlation (avg, SBERT-NLI-large) | 76.55 | STS12–STS16 + STSb + SICK-R |
| SentEval avg (SBERT-NLI-base) | 87.41 | Transfer tasks |
| SentEval avg (SBERT-NLI-large) | 87.69 | Transfer tasks |
| Inference time (10K sentence similarity) | ~5 seconds | — |
| Inference time (vanilla BERT, same task) | ~65 hours | — |

## Limitations (3 bullets, from the paper itself)
- SBERT "requires fine-tuning on labeled sentence-pair data (NLI or STS), which limits applicability to domains lacking such annotations" (paraphrased from paper context).
- The approach inherits BERT's maximum sequence length of 512 tokens, making it unsuitable for very long document embeddings without truncation.
- Performance improvements over InferSent and Universal Sentence Encoder are task-dependent, and SBERT does not consistently outperform task-specific BERT fine-tuning on classification benchmarks.

## How it relates to our work (1 paragraph)

SBERT is a foundational component for text-based boundary detection in LECSEG's transcript-processing stream. By encoding transcript segments as dense sentence vectors, cosine similarity can be computed between adjacent windows to detect drops in coherence that signal topic boundaries — a common and effective approach. SBERT's efficiency advantage (5 s vs 65 h for 10K sentences) is critical in lecture-scale settings where thousands of utterance windows must be compared. Its publicly available pre-trained models also support LECSEG's reproducibility goals.

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): SBERT is a text-only embedding model; LECSEG uses SBERT-derived features as one signal within a multimodal hierarchical pipeline.
- **N2** (reliability-weighted fusion): SBERT produces embeddings but has no mechanism to weight its contribution relative to other modalities; LECSEG adds learned gating over modalities.
- **N3** (two-level output): SBERT is a feature extractor, not a segmentation system; LECSEG combines SBERT-based coherence signals with others to produce two-level boundaries.
- **N4** (local-LLM refinement): No boundary refinement or titling; LECSEG adds a local-LLM stage for post-processing.
- **N5** (LECSEG-30 dataset): SBERT is evaluated on STS and transfer benchmarks, not lecture-video segmentation; LECSEG-30 provides the missing domain-specific evaluation.
- **N6** (5-metric eval + CIs): SBERT uses Spearman correlation on STS tasks; LECSEG uses segmentation-specific metrics (P_k, WinDiff, F₁, etc.) with bootstrap CIs.
- **N7** (reproducibility): SBERT models and code are publicly available; LECSEG builds on this tradition with a fully reproducible segmentation system release.


