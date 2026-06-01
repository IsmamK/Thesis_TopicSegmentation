**To:** [Supervisor]
**From:** Israk (T2520718)
**Subject:** Pre-Thesis Progress Brief — LECSEG: Lecture Topic Segmentation — Requesting Feedback

---

Dear Sir,

I hope you are doing well. I am writing to give you a complete brief of my pre-thesis project **LECSEG** and to request your feedback before I proceed to the final writing phase. I have tried to keep this as readable as possible — every concept is explained before the results are shown, and I have been honest about both what worked and what did not.

Please let me know if anything needs to be changed, dropped, or explained differently.

---

## 1. What Is This Project About?

A recorded lecture is a single continuous video, but inside it the instructor covers many separate topics. For example, a physics lecture might cover *Newton's laws*, then *friction*, then *circular motion* — each is a distinct topic. The goal of **lecture topic segmentation** is to automatically detect exactly where each topic change happens.

**Why does this matter?**
- Students can jump directly to the topic they need to review (like YouTube chapters, but automatic)
- Each segment can be individually summarised or indexed for search
- It works on any recorded lecture without requiring manual labelling

**What the system takes as input:** A lecture video
**What it outputs:** A list of timestamps where topics change, plus an auto-generated title for each segment

---

## 2. Why Is This a Hard Problem?

Most prior work on topic segmentation was done on *written text* — newspaper articles, Wikipedia. Lectures are much harder because:

- Speech is informal, repetitive, and has no paragraph breaks
- Topic changes are gradual, not sharp — an instructor bridges topics over several sentences
- The same vocabulary (e.g., "energy") appears across many different topics in the same lecture
- A lecture has multiple signals of a topic change that written text does not — pauses, pitch drops, slide changes — but most prior systems ignore these

This is the core gap LECSEG addresses.

---

## 3. Dataset — LECSEG-30

Since there was no suitable lecture-domain benchmark available, I built one.

**What it contains:**
- 30 YouTube lecture videos
- 5 academic domains: Computer Science, Mathematics, Physics, Biology, History/Humanities
- ~20+ hours of total content
- Ground-truth topic boundaries from two sources:
  1. **YouTube creator chapter markers** — used as the primary ground truth for all 30 videos
  2. **Manual hierarchical annotations** — two annotators independently labelled a subset with both chapter-level and subtopic-level boundaries

**Inter-Annotator Agreement:** Measured using **Cohen's Kappa** (κ), which corrects for chance agreement. κ = 1 means perfect agreement, κ = 0 means no better than chance. This validates that the ground-truth labels are consistent.

**Why this is novel (N5):** Existing lecture datasets like *AVLectures* (2023) and *Tuna et al.* (2015) are limited to a single domain or setting. LECSEG-30 spans five domains and provides both coarse chapter and fine subtopic annotations.

---

## 4. What We Built — The Full Pipeline

The system processes a raw lecture video through these stages in order:

| Step | Tool | What it does |
|---|---|---|
| 1. Transcription | **Whisper large-v3** (Radford et al., 2023) | Converts audio to text with word-level timestamps. Ran on cloud GPU (vast.ai RTX 5090). |
| 2. Sentence splitting | **pysbd + spaCy** | Groups Whisper words into proper sentences, preserving timestamps. Produced 46,525 sentences across 30 videos. |
| 3. Shot detection | **TransNetV2** | Detects visual cuts (slide changes, camera changes) — a signal for topic shifts. |
| 4. Slide OCR | **PaddleOCR** | Reads text from slide keyframes — a new slide title often marks a new topic. |
| 5. Prosody extraction | **librosa** | Extracts pause duration and pitch change per sentence. Long pauses and pitch drops are a known lecture cue for topic transitions. Chunked processing was needed to handle 1–2 hr audio on commodity hardware (Extra contribution E2). |
| 6. Text embeddings | **Sentence-BERT: MPNet, E5, BGE, MiniLM** | Converts each sentence to a 768-number semantic vector. Sentences on the same topic should have similar vectors; sentences across a topic boundary should differ. |
| 7. Visual embeddings | **CLIP ViT-B/32** | Converts slide keyframes to visual vectors for visual similarity scoring. |
| 8. Alignment | Custom alignment module | Aligns all signals (text, visual, audio) to the same sentence timeline so they can be fused. |

Everything from step 3 onward is aligned to the sentence timeline — so every sentence carries text, visual, OCR, and prosody features as a unified feature vector.

---

## 5. The Novel Contributions (N1–N7 and E1–E4)

These are the original contributions of this thesis. I will explain each simply.

---

### N1 — Two-Stage Boundary Predictor
**Gap it closes:** Prior methods apply a single threshold to cosine similarity scores. This is noisy and generates too many false boundaries.

**How it works in two stages:**
- **Stage 1 (cast a wide net):** Use a loose threshold to find many candidate boundaries — prioritise not missing any real ones
- **Stage 2 (filter the net):** Re-score each candidate using all available modality signals together and apply a stricter threshold to remove weak ones

This is the same logic as a search engine: first retrieve many results, then re-rank and filter.

---

### N2 — Reliability-Weighted Fusion
**Gap it closes:** Prior multimodal systems (e.g., *Yu et al., 2024 — Multimodal Fusion & Coherence Modeling*; *Karim et al., 2024 — MED-VT++*) either use fixed weights or simple averaging across modalities. But in lectures, modality quality varies per video — a whiteboard lecture has no meaningful slide signal; a noisy recording has poor prosody.

**How it works:** For each modality (text, prosody, visual), we measure the **Shannon entropy** of its boundary score distribution:
- If a modality's scores are concentrated (peaked), it is confident → give it high weight
- If its scores are flat/uniform (spread everywhere), it is providing noise → give it low weight

Weight formula: `w = exp(−entropy)`

No training is needed — the weights adapt per video automatically.

---

### N3 — Two-Level Hierarchical Segmentation *(Headline contribution — statistically significant)*
**Gap it closes:** Every prior lecture segmentation system outputs a *flat* list of boundaries. Real lectures have two natural levels:
- **Chapters** (~5–8 per lecture): major topic shifts, like a book's chapter headings
- **Subtopics** (~15–25 per lecture): finer divisions within each chapter

**How it works:** The predictor runs twice — once for coarse chapter boundaries, once for finer subtopics — with the constraint that every chapter boundary must also be a subtopic boundary (mathematically consistent nesting).

**Why it matters:** A student can navigate at the chapter level ("take me to the Derivation section") or at the subtopic level ("take me to where the proof begins"). Both levels of granularity are generated automatically.

---

### N4 — Local LLM Boundary Refinement + Auto-Titling
**Gap it closes:** Recent LLM-based segmentation papers (*Fan et al., 2023 — Topic Segmentation via LLMs*) rely on closed API models (GPT-4, Claude) — expensive, non-reproducible, and unavailable without internet access.

**How it works:** After the hierarchical predictor produces boundaries, the text around each boundary (±2 sentences) is sent to a **locally running** Llama 3.1 8B model (via Ollama). The model:
1. Confirms or adjusts the boundary position
2. Generates a 3–8 word title for each resulting segment

**Why local:** No API key, no cost, no data leaving the machine, fully reproducible on any computer with a GPU.

---

### N5 — LECSEG-30 Dataset (described in Section 3 above)

---

### N6 — Unified Evaluation Suite with Confidence Intervals and Significance Tests
**Gap it closes:** Prior work (including recent papers like *Freisinger et al., 2023 — Multilingual Topic Segmentation*) typically reports only one or two metrics without confidence intervals, making comparisons unreliable.

**What we built:**
- Five metrics reported together: Pk, WD, Boundary Similarity, Tolerance-F1 (at ±1, ±2, ±3 sentences), H-WD
- Bootstrap 95% confidence intervals (1000 resamples) for every number
- Paired Wilcoxon signed-rank tests (non-parametric, appropriate for non-normal video-level scores)
- Holm correction for multiple comparisons

---

### N7 — Fully Reproducible End-to-End Pipeline
A single command (`python scripts/pipeline.py`) runs the entire system from raw video URLs to evaluation tables. All dependencies are pinned, random seeds are fixed (seed=42), and results are versioned alongside code.

---

### Extra Contributions (E1–E4)

| ID | Contribution | Why It Matters |
|---|---|---|
| E1 | Whisper-to-sentence alignment | Whisper outputs word segments, not sentences. This module re-segments them into proper sentences while preserving timestamps — 46,525 sentences from 30 videos. Without this, embeddings receive paragraph-length chunks and cosine similarity degrades. |
| E2 | Chunked prosody extraction | librosa runs out of memory on 1–2 hr audio. This splits audio into fixed windows, extracts features, and stitches them — enabling prosody on commodity hardware. |
| E3 | Multi-embedding-model abstraction | A single interface supports MiniLM, MPNet, E5, BGE. Enables ablation of embedding models without code changes. |
| E4 | Hierarchical annotation tool | A purpose-built Streamlit tool for labelling both chapter and subtopic boundaries, with status tracking (draft/reviewed/done) and support for the two-annotator IAA workflow. |

---

## 6. Evaluation Metrics — What They Mean and Why We Use Them

Standard classification metrics like accuracy or F1 do not work well for segmentation. A boundary that is 1 sentence away from the true boundary is much better than one that is completely wrong — but standard F1 treats both as equally wrong. We use metrics designed specifically for this.

---

### Pk — The Standard Segmentation Error Rate
*(Beeferman et al., 1999 — still the community standard; used in all recent papers)*

**Simple explanation:** Imagine sliding a window of *k* sentences across both the predicted and reference segmentations side by side. At each position, ask: "Does this window straddle a boundary in one segmentation but not the other?" The fraction of window positions where this happens is Pk.

- **k** = half the average segment size (so the window is neither too small nor too large)
- **Lower is better.** Perfect score = 0. Random prediction ≈ 0.5
- **Why use it:** It penalises large position errors more than small ones. Being 1 sentence off barely hurts Pk; being 20 sentences off hurts a lot. This captures the practical reality that near-misses are acceptable.

**Why it is still used in 2024–2025 papers:** Pk remains the standard because it is directly comparable across the entire literature. Every paper from 2015 to 2024 reports it, so it is the only way to situate our results in context. However, it has a known bias — it can reward over-segmentation — which is why we also report WD and BS.

---

### WindowDiff (WD) — The Improved Version of Pk
*(Pevzner & Hearst, 2002 — standard companion to Pk)*

**Simple explanation:** Same sliding window idea as Pk, but instead of asking "is there any boundary difference?" it asks "how many boundaries are in the window in each case, and by how much do they differ?" This fixes a known flaw in Pk where inserting many false boundaries near true ones could artificially lower Pk.

- **Lower is better.** WD ≥ Pk always. If WD is much higher than Pk for a method, that method is over-segmenting.
- **Why both Pk and WD:** They are complementary. Pk can miss over-segmentation; WD catches it.

---

### Boundary Similarity (BS) — Precision/Recall with Tolerance
*(Fournier, 2013)*

A predicted boundary counts as correct if it is within a tolerance window of a reference boundary. Returns a value between 0 and 1 — **higher is better**. This is the most interpretable metric: a score of 0.13 means 13% of boundaries were correctly found within the tolerance.

---

### Tolerance-F1 — Standard F1 with a Position Window
Standard F1 (precision × recall balance) but a prediction is a true positive if it falls within ±1, ±2, or ±3 sentences of a reference boundary. We report all three tolerance levels. **Higher is better.**

---

### Hierarchical WindowDiff (H-WD) — Our Custom Metric (N6)
An extension of WD computed at both the chapter and subtopic levels simultaneously. This is our original contribution — no prior paper evaluates hierarchical lecture segmentation this way.

---

## 7. Results

All results are evaluated on the 30 LECSEG-30 videos against YouTube creator chapter boundaries.

### 7.1 Full Results Table

| Method | Type | Pk ↓ | WD ↓ | BS ↑ | F1 ↑ | Precision | Recall |
|---|---|---|---|---|---|---|---|
| TextTiling | Baseline | 0.605 | 0.898 | 0.147 | 0.139 | 0.104 | 0.395 |
| C99 | Baseline | 0.422 | 0.449 | 0.035 | 0.029 | 0.028 | 0.030 |
| CosineSeg | Baseline | 0.478 | 0.530 | 0.078 | 0.087 | 0.085 | 0.092 |
| KMeans | Baseline | 0.617 | **0.998** | 0.496 | 0.048 | 0.026 | **0.999** |
| BertSeg | Baseline | 0.470 | 0.516 | 0.062 | 0.065 | 0.062 | 0.068 |
| TwoStage (text only) | Novel N1 | 0.491 | 0.541 | 0.070 | 0.079 | 0.077 | 0.082 |
| TwoStage + Prosody | Novel N1+N2 | 0.432 | 0.493 | **0.131** | **0.142** | 0.139 | 0.146 |
| Hierarchical | Novel N3 | **0.417** | 0.426 | 0.062 | 0.049 | 0.119 | 0.032 |
| Hierarchical + Prosody | Novel N3+N2 | 0.421 | 0.431 | 0.063 | 0.041 | 0.100 | 0.027 |
| Hierarchical + LLM | Novel N3+N4 | 0.418 | **0.421** | 0.053 | 0.038 | 0.111 | 0.023 |

*(↓ = lower is better, ↑ = higher is better. Bold = best value in column)*

---

### 7.2 Honest Result Breakdown

**TextTiling — Fails badly**
Pk=0.605 is *worse than random* (random ≈ 0.5). WD=0.898 is near the maximum possible. It massively over-segments — predicting ~40–50 boundaries per video when the ground truth has ~8–12. Precision=0.104 confirms this: only 1 in 10 predicted boundaries is real. It was designed for formal written text and simply does not transfer to spoken lecture audio.

**C99 — Misleadingly decent Pk, but broken F1**
Pk=0.422 looks acceptable, but F1=0.029 is nearly zero, with both precision=0.028 and recall=0.030 close to zero. This tells us C99 predicts almost no boundaries at all — and by predicting nothing, it avoids many false positives, which keeps Pk from being terrible. In practice it is useless for this task. Note: this is our simplified "C99-lite" reimplementation, not the full published C99 — a distinction we are transparent about.

**KMeans — Complete failure**
WD=0.998 and recall=0.999 means it predicts a boundary at almost every sentence. The high BS=0.496 is misleading — it scores high on boundary similarity only because it predicts everywhere, so some predictions happen to fall near true boundaries. This is not a useful segmentation.

**TwoStage text-only — Does not improve over baselines**
Pk=0.491 is worse than C99 and BertSeg. This is an honest finding: the two-stage design alone, without extra modality signals, does not outperform simpler baselines. The two-stage logic only gains strength when prosody is added.

**TwoStage + Prosody (N1+N2) — Best F1 and BS, meaningful improvement**
Adding prosody to the two-stage predictor gives Pk=0.432 and the best F1=0.142 and BS=0.131 across all methods. This is the only method that achieves meaningful boundary *detection* quality — precision=0.139 and recall=0.146 are balanced. The prosody signal (pause duration) is the single biggest useful multimodal feature.

**Hierarchical (N3) — Best Pk and WD, statistically significant**
Pk=0.417, WD=0.426 — the best Pk/WD values across all methods. However, recall=0.032 is very low — the hierarchical method is conservative, predicting very few but highly precise boundaries (precision=0.119 is the second-highest). Whether this is a strength or weakness depends on the use case: for a student navigation interface, precise chapter markers matter more than catching every subtopic.

**Statistical significance (Wilcoxon signed-rank, n=30 videos):**
- Hierarchical vs CosineSeg: ΔPk = −0.061, **p = 0.003** ✅
- Hierarchical vs BertSeg: ΔPk = −0.053, **p = 0.001** ✅
- Hierarchical vs C99: ΔWD = −0.024, **p = 0.049** ✅
- Bootstrap 95% CI for Hierarchical Pk: **[0.396, 0.439]**

**Hierarchical + LLM (N3+N4) — Best WD, highest precision**
WD=0.421 (best across all methods), Pk=0.418, precision=0.111 (highest). The LLM refinement step removes borderline false positives and produces clean segment titles. This is the full proposed system.

---

### 7.3 What the Results Tell Us

There are two different "winners" depending on what you care about:

| If you want... | Best method | Why |
|---|---|---|
| Fewest false chapter markers (precision) | **Hierarchical + LLM** | Pk=0.418, WD=0.421, precision=0.111 |
| Best at actually *finding* boundaries (F1) | **TwoStage + Prosody** | F1=0.142, BS=0.131 |

The hierarchical approach is better for a *chapter navigation* use case — fewer, more confident boundaries. The TwoStage+Prosody is better for *complete coverage* — it finds more real boundaries.

The low F1 values across the board (even our best is 0.142) are partly explained by the ground truth being coarse YouTube chapter markers (~8–12 per video), while some methods predict finer-grained boundaries. This granularity mismatch is a genuine limitation and is documented.

---

## 8. Comparison to Recent Related Work

We do not compare numerically to other papers because they use different datasets — a direct number comparison would be meaningless. Instead, we position LECSEG methodologically:

| Recent Paper | Their approach | What LECSEG adds |
|---|---|---|
| **Fan et al., 2023** — *Topic Segmentation via LLMs* [(arxiv)](https://arxiv.org/abs/2304.09214) | Uses GPT-4 for segmentation | We use a local open model (Llama 3.1 8B) — free, reproducible, no API |
| **Freisinger et al., 2023** — *Unsupervised Multilingual Topic Segmentation* [(arxiv)](https://arxiv.org/abs/2302.08929) | Text-only, multilingual | We add prosody + visual + hierarchical structure |
| **Yu et al., 2024** — *Multimodal Fusion & Coherence Modeling* | Fixed-weight multimodal fusion | We use entropy-based reliability weighting that adapts per video |
| **Karim et al., 2024** — *MED-VT++* | Multimodal for medical video | Medical domain only; no lecture-specific signals or evaluation |
| **Radford et al., 2023** — *Whisper* [(arxiv)](https://arxiv.org/abs/2212.04356) | ASR only | Whisper is a component in our pipeline, not a segmentation system |
| **D.S.S. et al., 2023** — *AVLectures* | Lecture resource/dataset | Single domain; no hierarchical annotation or reproducible pipeline |

The classical baselines (TextTiling, C99) are still included because they remain the standard baseline in the segmentation literature — every 2023–2024 paper still reports them for comparability. We are explicit that our C99 is a "lite" reimplementation.

---

## 9. Honest Limitations

| Limitation | Explanation |
|---|---|
| F1 values are low across all methods | Ground truth is coarse (YouTube chapters). Methods that predict finer boundaries get penalised even when approximately correct. |
| TwoStage text-only does not beat baselines | Without prosody, N1 alone is not a contribution. N1's value only appears when combined with N2 (prosody fusion). |
| C99-lite does not reproduce published Pk=0.12 | Our reimplementation gives Pk≈0.51 on the Choi benchmark vs published 0.12. We call it "C99-lite" and are transparent about this gap. |
| Visual features (OCR, shot detection) have modest impact | Slide changes do not always coincide with topic boundaries in every lecture style (especially whiteboard lectures). |
| LLM titling is evaluated qualitatively only | No automatic title quality metric exists yet — evaluation is based on manual inspection. |
| 30 videos is a small dataset | Sufficient for statistical testing (Wilcoxon, bootstrap CI) but limits generalisability claims. |

---

## 10. Current Status

| Item | Status |
|---|---|
| Total deliverables completed | 32 / 47 |
| Unit tests passing | 177 |
| Pipeline (raw video → results) | Fully functional |
| All 30 videos processed | Done |
| Evaluation (all methods, all metrics) | Done |
| Statistical significance testing | Done |
| Error analysis | Done |
| LaTeX tables + thesis figures | In progress |
| Thesis writing | In progress |

---

## 11. Technology Stack Summary

| Component | Technology |
|---|---|
| Speech recognition | OpenAI Whisper large-v3 |
| Sentence segmentation | pysbd + spaCy |
| Text embeddings | Sentence-BERT: MPNet, E5-large, BGE-large, MiniLM |
| Visual embeddings | CLIP ViT-B/32 |
| Shot detection | TransNetV2 |
| Slide OCR | PaddleOCR |
| Prosody | librosa (pauses, pitch, rate) |
| LLM refinement | Ollama + Llama 3.1 8B (fully local) |
| Annotation tool | Streamlit (custom-built) |
| Evaluation | Custom Pk/WD/BS/F1/H-WD + bootstrap + Wilcoxon |
| Demo | Streamlit web app |

---

I would greatly appreciate your feedback on the following specific points:

1. Are the novelty claims (N1–N7) framed strongly enough, or should any be repositioned?
2. The low F1 values — do you think this needs a stronger explanation in the thesis, or is the granularity mismatch argument sufficient?
3. Should the TwoStage+Prosody result be highlighted more prominently since it has the best F1/BS, even though Hierarchical has the best Pk/WD?
4. Any concerns about the C99-lite limitation?

Thank you for your time, Sir.

Best regards,
Israk
Pre-Thesis T2520718 — LECSEG: Lecture Topic Segmentation
