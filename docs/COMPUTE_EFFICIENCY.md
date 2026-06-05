# Compute Efficiency

This table supports a narrow efficiency claim: LECSEG is inexpensive and reproducible locally compared with high-resource chaptering systems. It does not prove external performance superiority.

| Method | Training | Main cost | Observed/expected runtime | Notes |
|---|---|---|---|---|
| TextTiling / C99 | None | CPU lexical similarity | <1 min for full benchmark | Classical lightweight baselines. |
| BGE-divisive baseline | None | Cached sentence embeddings + divisive segmentation | embedding cached; segmentation <1 min | Stable local baseline. |
| Cross-model conservative | None | Two cached embedding streams + agreement filter | <1 min once embeddings exist | Best single global method. |
| Balanced LOO selector | Small ExtraTrees meta-selector | Existing result portfolio + video-level features | ~2 min per selector sweep on local CPU | Best deployable mean Pk/WD operating point. |
| TreeSeg same-dataset adapter | None | Local embeddings + TreeSeg split objective | ~49 sec for 30 videos, bge-large | Same-dataset comparator; worse Pk/WD, better F1@2. |
| Local LLM verifier | None | Ollama prompts over candidate shortlist | cacheable; depends on shortlist size/model | Diagnostic baseline/comparison, not promoted unless metrics improve. |
| High-resource chaptering systems | Large supervised/LLM training | Thousands to hundreds of thousands of videos | not locally reproduced | Not directly comparable without same benchmark. |
