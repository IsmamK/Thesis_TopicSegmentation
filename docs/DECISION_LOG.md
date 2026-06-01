# DECISION LOG

This file records significant design and scope decisions. Dates reflect when the
current project state made each decision operational.

## Architecture Decisions

| Date | Decision | Alternatives | Reason | Owner |
|---|---|---|---|---|
| 2026-05-26 | Use Whisper/faster-whisper style ASR for transcripts | Manual transcripts, API ASR | Local, reproducible, strong lecture transcription quality | Team |
| 2026-05-26 | Use local Ollama Llama-3.1 8B for optional refinement/titling | GPT-4 API, no LLM | Avoid closed API dependency and data egress | Team |
| 2026-05-31 | Treat BGE/E5 cross-model scores as the current best chapter-level direction | MPNet-only, visual-first fusion | Best verified 30-video Pk/WD is from cross-model conservative selection | Team |
| 2026-05-27 | Keep two-level hierarchy: chapters and subtopics | Flat only, three levels | Matches available labels and is understandable for defense | Team |
| 2026-05-27 | Extract shot, OCR, and prosody signals but report caveats | Text-only only | Enables multimodal analysis while acknowledging noisy auxiliary signals | Team |

## Dataset Decisions

| Date | Decision | Alternatives | Reason | Owner |
|---|---|---|---|---|
| 2026-05-25 | Use public YouTube lectures with creator chapters | Private lectures, fully manual GT | Public, reproducible, feasible within thesis timeline | Team |
| 2026-05-25 | Release URLs/metadata/annotations rather than raw videos | Redistribute videos | Respects platform terms and reduces release size | Team |
| 2026-05-31 | Report the true domain distribution rather than a balanced claim | Force 5x6 balance | Manifest is Biology 6, CS 7, Math 4, Philosophy 6, Physics 7 | Team |

## Evaluation Decisions

| Date | Decision | Alternatives | Reason | Owner |
|---|---|---|---|---|
| 2026-05-28 | Use 30-video YouTube GT as official chapter benchmark | `reviewed_only` 31-video runs | Official dataset has 30 videos; 31-video runs are not clean enough for final claims | Team |
| 2026-05-28 | Report Pk and WD as primary segmentation metrics | Accuracy only, strict F1 only | Pk/WD are standard and less brittle for near-boundary shifts | Team |
| 2026-05-31 | Discuss strict F1 as a limitation | Hide low F1 | Best Pk/WD method is conservative and has low exact-match recall | Team |
| 2026-05-31 | Use diagnostic negative results in the thesis | Report only wins | Oracle-k and bert-wiki transfer results strengthen the research argument | Team |

## Scope Decisions

| Date | Decision | Alternatives | Reason | Owner |
|---|---|---|---|---|
| 2026-05-31 | Do not claim sub-0.30 Pk/WD | Overstate result | Current verified deployable selector is Pk 0.3588, WD 0.3739; diagnostic oracle is Pk 0.2980, WD 0.3280 but not deployable | Team |
| 2026-05-31 | Keep public-release cleanup separate from research cleanup | Delete files immediately | Avoid accidental loss of user data; release package can exclude internal files | Team |
| 2026-05-31 | Frame candidate ranking as future work | Keep random ablations | Oracle-k shows k-selection is not the bottleneck | Team |
