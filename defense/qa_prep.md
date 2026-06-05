# LECSEG Defense Q&A Preparation
**T45 — Defense Q&A preparation document**

Anticipated committee questions and model answers. Study this document before the 2× dress rehearsal (T46).

---

## 1. Motivation & Scope

**Q: Why YouTube chapter metadata as ground truth? Isn't that noisy?**
Creator-provided chapters are noisy, but: (1) they reflect actual human topicisation of the content; (2) they exist at scale for 30 diverse lectures; (3) our inter-annotator study (§T13) shows Cohen's κ = 0.535 at chapter level and κ = 0.426 at subtopic level when compared with our manual double-annotation — moderate agreement, consistent with prior annotation studies on educational content. We treat YouTube chapters as the primary reference and human annotations as validation.

**Q: Why 30 videos? Is that enough for evaluation?**
30 is standard in topic-segmentation benchmarks (e.g., Choi 2000 used synthetic data; QMSUM uses 35 meetings). Our videos total 32.52 hours across 5 academic domains. Given the cost of manual annotation, 30 is a principled choice. We report 95% bootstrap CIs to quantify uncertainty.

**Q: What are the 5 academic domains?**
Computer Science, Mathematics, Physics, Biology, and the Humanities/Social Sciences. Domain balance prevents metric inflation from one easy domain.

---

## 2. Methodology

**Q: Why not fine-tune a transformer end-to-end for segmentation?**
Three reasons: (1) Our dataset (30 videos) is too small for fine-tuning a large model without severe overfitting; (2) our novel contribution is the *fusion* and *hierarchy* architecture, not the encoder; (3) using frozen pre-trained encoders (Whisper, CLIP, SBERT) is reproducible on commodity hardware. An end-to-end approach is a valid future direction (§6).

**Q: How does Reliability-Weighted Fusion (N2) differ from simple concatenation?**
Concatenation treats all modalities equally. RWF weights each modality by `exp(-H(scores))` where H is the normalised Shannon entropy of that modality's gap-score distribution. A modality with a sharply-peaked gap distribution (clear boundaries) gets a high weight; a flat distribution (noisy/uninformative) gets downweighted automatically. This is data-driven and requires no manual tuning.

**Q: Why Silero VAD + faster-whisper rather than the standard OpenAI Whisper?**
Speed. faster-whisper is 4× faster with identical accuracy (ctranslate2 backend). VAD preprocessing removes silence, which further reduces computation on long lectures. We verified transcription quality on 5 manually-checked videos; WER ≈ 8% for native-English speakers and ≈ 14% for accented speech.

**Q: What is the "two-stage" in the Two-Stage Boundary Predictor (N1)?**
Stage 1 (broad pass): cosine depth-score valleys below a low threshold (μ - 0.5σ) produce candidate boundaries. This ensures high recall at low precision.
Stage 2 (refine): the RWF-fused multimodal signal re-scores only the candidate set, keeping boundaries that exceed μ - 1.2σ on the fused signal. This improves precision without missing real boundaries.

**Q: How do you ensure chapters are a strict superset of subtopics in N3?**
After predicting subtopic boundaries independently, we force any chapter boundary to also be a subtopic boundary: `subtopic_set.update(chapters)`. This preserves the nested structure by construction, not by post-hoc filtering.

**Q: Why Ollama / local LLM rather than GPT-4?**
Reproducibility: GPT-4 responses are non-deterministic and the API changes over time. Ollama runs llama3.1:8b locally, making our results fully reproducible. Our LLM component (N4) generates titles and can refine boundaries; a small local model is sufficient for this task and supports the reproducibility claim (N7). We ablate N4 separately and report its contribution honestly.

**Q: Does prosody actually help?**
No — and we report this honestly as a negative result. Prosody features (pause duration, pitch) were extracted for all 30 videos and integrated into the reliability-weighted fusion (N2). Ablations showed prosody fusion consistently worsened Pk/WD versus text-only methods. This is itself a finding: audio-prosodic signals are not reliable boundary indicators for YouTube lecture transcripts, likely because lectures are edited and pauses do not align with topic shifts. We include prosody in the pipeline for completeness and reproducibility but do not claim it improves the final result.

---

## 3. Evaluation

**Q: What is Pk and why use it?**
Pk (Beeferman 1999) is a probabilistic error metric: for a random window of k sentences, it measures the probability that two sentences inside the window are mis-classified (one is in a different segment when the reference says same, or vice versa). It penalises near-miss errors less than exact-match metrics. Lower Pk = better.

**Q: Why report both Pk and WD? They look similar.**
WindowDiff (Pevzner & Hearst 2002) is asymmetric: it counts *boundary count differences* per window, penalising over-segmentation more than Pk does. Reporting both reveals whether a method is over- or under-segmenting. Pk and WD can give different rankings; showing both is standard in the literature.

**Q: How do you set n_segments? Ground-truth cheating?**
For methods that need n_segments (KMeans, TwoStage), we use the *ground-truth* count at inference time. This is standard in the evaluation literature (Choi 2000, Riedl & Biemann 2012) and favours all methods equally. In practice, we also run an unsupervised mode using our automatic n-segment estimator and report those numbers separately in Appendix C.

**Q: What is H-WD?**
Hierarchical WindowDiff: an extension of WD to a two-level segmentation. A window of k sentences counts boundary errors at both chapter and subtopic levels, with the chapter-level error weighted more (×2). It is the primary metric for our hierarchical output (N3).

---

## 4. Results

**Q: Is the improvement over BertSeg statistically significant?**
Yes. Paired Wilcoxon signed-rank test (30 videos, α = 0.05): TwoStage vs. BertSeg achieves p < 0.05 on Pk and WD. Bootstrap 95% CIs are non-overlapping. See Table 2 for exact p-values.

**Q: Where does the method fail? (Error analysis)**
Three common failure modes (T31): (1) *Dense lecture segments* — when a speaker presents ≥6 subtopics in a single chapter, boundaries are missed; (2) *Accented/fast speech* — higher ASR WER degrades text embeddings; (3) *No slide changes* — when visual modality is flat (whiteboard or no slides), N2 down-weights visual but the transition is still harder to detect. These are discussed in §4.4.

---

## 5. Broader Questions

**Q: How would this scale to a full university MOOC platform?**
The pipeline processes a 60-min lecture in ~4 minutes on an A4000 GPU. For a platform with 10,000 lectures: batch processing overnight. The bottleneck is ASR (Whisper), not our model. We include a Streamlit demo (T39) and plan Hugging Face model release (T43).

**Q: How does this compare to VideoLLaMA / GPT-4V approaches?**
VideoLLaMA processes video end-to-end but is extremely expensive (100× our compute budget per video) and not reproducible on academic hardware. GPT-4V-based approaches exist (e.g., VideoAgent) but are closed-source and not designed for hour-long lectures. Our approach is the only one that produces *hierarchical* (chapter + subtopic) output with *open-source* tools on commodity GPUs.

**Q: What are the limitations?**
(1) English-only (Whisper can do multilingual but embeddings are English-optimised); (2) ground-truth from YouTube chapters may not perfectly align with pedagogical structure; (3) prosody, shot, and OCR signals were extracted but did not improve final Pk/WD in ablations — multimodal fusion remains an open problem; (4) evaluation on 30 videos only — larger study needed for publication; (5) the method selector fails on the Mathematics domain and is not domain-general.

---

## 6. Hard Questions (Likely From a Critical Examiner)

**Q: Your TreeSeg-style reimplementation on your own dataset got Pk=0.432, but TreeSeg reports Pk=0.367 on their dataset. Doesn't that mean TreeSeg is actually better than you?**
No — the comparison is between two different datasets, not the same one. TreeSeg's 0.367 is on TinyRec (21 self-recorded lectures with controlled recording conditions). Our reimplementation runs on LECSEG-30 (30 YouTube lectures from diverse domains and presenters). The gap reflects dataset difficulty, not method quality. Critically, our best method on LECSEG-30 achieves Pk=0.3588 — better than the TreeSeg reimplementation's 0.432 on the same dataset. We beat the TreeSeg-style approach on our own benchmark. We cannot claim we beat TreeSeg on their benchmark because we have not run on TinyRec, which would require a separate experiment.

**Q: The gap between your Pk=0.3588 and TreeSeg's Pk=0.367 is only 0.008. Is that even meaningful?**
Two responses: (1) Pk differences in topic segmentation are typically small — published work treats 0.01–0.02 as meaningful (see Riedl & Biemann 2012). Our improvement over our own baseline (0.3884→0.3588, delta=0.03) is statistically significant at p=0.025. (2) More importantly, our comparison to TreeSeg is across different datasets and is indicative only. Our primary contribution is not beating TreeSeg by a large margin — it is providing a new open benchmark with hierarchical annotation and a reproducible low-resource evaluation protocol that others can now use and beat.

**Q: Why didn't you just prompt an LLM like GPT-4 or llama directly for segmentation? Wouldn't that obviously work better?**
This is a valid direction and we acknowledge it as future work. The main reasons we did not make it our primary method: (1) Reproducibility — GPT-4 API responses are non-deterministic and the model changes over time; we cannot guarantee others reproduce our exact numbers. (2) Cost — 30 lectures × avg 800 sentences = 24,000 sentences per full run; GPT-4 costs would make the benchmark impractical for academic replication. (3) Local LLM experiments were run (Ollama llama3.1:8b as a boundary refiner) and did not improve Pk/WD — the small local model was not strong enough. A properly prompted GPT-4 baseline is a clear next step, but publishing unverified API-dependent results in a thesis is risky.

**Q: Your Mathematics domain is the only one where your selector makes results worse. Why include it in the official result?**
We include it because honest evaluation requires all domains, not just the ones where our method works. Excluding Math would inflate our numbers and mislead readers. Instead, we analyse the failure mode explicitly: Mathematics lectures verbalize equations, creating flat embedding landscapes where cosine similarity loses discriminative power. This is an analytical finding, not a flaw we hid. The selector still improves Pk in 4/5 domains, and the Math failure motivates concrete future work (better transcript preprocessing for equation-heavy content, domain-adaptive models).

**Q: Your F1@2 is 0.0893 — that is very low. Are you really finding any boundaries at all?**
This apparent paradox is explained by the mismatch between Pk/WD and F1. Pk/WD measure window-level consistency and are the standard metrics in topic segmentation since Beeferman 1999. F1 measures exact boundary hit at tolerance ±2 sentences. YouTube chapters are long (avg 6–8 minutes, ~80 sentences), so the number of true boundaries is small (avg 14 per video) and a method producing 12 boundaries in roughly the right places can achieve Pk=0.36 but F1=0.09 if those boundaries are each off by 5–10 sentences. The oracle analysis confirms this: with perfect candidate selection from our generated candidates, Pk=0.017 is achievable — the candidates exist, the problem is selection precision. Low F1 is a known property of Pk-optimised unsupervised methods and is discussed in §4.5.

**Q: You have 30 videos. Isn't that too small to draw statistically meaningful conclusions?**
We address this three ways: (1) We use paired Wilcoxon signed-rank tests (non-parametric, appropriate for small n) rather than t-tests. (2) We report 95% bootstrap confidence intervals computed over 1000 resamples, which gives honest uncertainty estimates. (3) Published benchmarks in this area are comparably small: Choi 2000 used ~900 synthetic documents, QMSUM has 35 meetings, TinyRec has 21 lectures. 30 real manually-annotated videos with hierarchical labels is at or above the standard in this field. We are transparent that a larger study would strengthen the conclusions.
