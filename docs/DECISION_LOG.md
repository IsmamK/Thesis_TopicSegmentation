# 📋 DECISION LOG

**Every significant design or scope decision goes here. Prevents re-litigating the same questions.**

Format per entry:
- **Date** — when was this decided
- **Decision** — what was decided (one sentence)
- **Alternatives considered** — what else was on the table
- **Reason** — why this option was chosen
- **Owner** — who made the final call

---

## Architecture decisions

| Date | Decision | Alternatives | Reason | Owner |
|---|---|---|---|---|
| TBD | Use faster-whisper for ASR | openai-whisper, AssemblyAI API | 3× faster on CPU, same WER, fully local | Team |
| TBD | Use Llama-3.1 8B via Ollama for refinement | GPT-4 API, Mistral 7B | Reproducible, free, no data leaves local | Team |
| TBD | SBERT/MPNet as primary text backbone | E5, BGE, GTE | Strong on semantic similarity benchmarks, well-documented | Team |
| TBD | 5-fold cross-validation at video level | Random sentence split, 80/20 holdout | Prevents within-video leakage; standard for small corpora | Team |
| TBD | Two-level hierarchy (chapter + subtopic) | Three levels, flat only | Three levels unsupported by creator annotations; flat loses novelty claim N3 | Team |
| TBD | TransNetV2 for shot detection | PySceneDetect, custom CNN | Pre-trained, no fine-tuning needed, fast | Team |
| TBD | PaddleOCR for slide text | Tesseract, EasyOCR | Better accuracy on projected slides, GPU-optional | Team |

---

## Dataset decisions

| Date | Decision | Alternatives | Reason | Owner |
|---|---|---|---|---|
| TBD | Use YouTube creator-provided chapters as silver labels | Manual annotation from scratch | 30 videos × 2 annotators from scratch = 300+ hours; creators know their own content | Team |
| TBD | Release URLs + metadata only, not video files | Full video release | YouTube ToS prohibits redistribution | Team |
| TBD | 5 academic domains (CS, Math, Physics, Biology, History) | All CS, random domains | Stress-test cross-domain generalisation | Team |

---

## Evaluation decisions

| Date | Decision | Alternatives | Reason | Owner |
|---|---|---|---|---|
| TBD | Bootstrap n=1000 for CIs | n=500, analytical CI | 1000 is the community standard; 500 gives noisier CIs | Team |
| TBD | Wilcoxon signed-rank for significance | t-test, permutation test | Non-parametric; video-level scores are not normally distributed | Team |
| TBD | Holm correction for multi-method comparisons | Bonferroni | Holm is more powerful while still controlling FWER | Team |

---

## Scope decisions

| Date | Decision | Alternatives | Reason | Owner |
|---|---|---|---|---|
| TBD | Publish model on HuggingFace | GitHub release only | HuggingFace model hub is the community norm; easier deployment | Team |
| TBD | Publish dataset on Zenodo | GitHub LFS, OSF | Zenodo provides DOI + CC licence + long-term archival | Team |
| TBD | No real-time/streaming support in v1 | Streaming from day 1 | Scope creep; flagged as Future Work | Team |

---

*Add new rows as decisions are made. Don't delete rows — if a decision reverses, add a new row with the updated decision and a "Supersedes [date]" in the Reason column.*
