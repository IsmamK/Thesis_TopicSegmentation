# LecSeg-30 Defense Presentation Scripts
### 5 People · 15 Minutes · ~3 Minutes Each
### BRAC University · CSE400 · June 2026

---

> **General instructions:**
> - Speak slowly and clearly. Do not rush.
> - Look at the panel, not the screen.
> - Point to things on the slide when you mention them.
> - You do not need to say every word exactly — know the meaning, speak naturally.

---

## SLIDE ORDER (23 slides)

| # | Title | Person |
|---|-------|--------|
| 1 | Title | 1 — Sadia |
| 2 | The Problem | 1 — Sadia |
| 3 | Three Types of Topic Boundary | 1 — Sadia |
| 4 | Dataset — LecSeg-30 | 2 — Fahmida |
| 5 | Annotation Tool | 2 — Fahmida |
| 6 | The LecSeg Pipeline | 2 — Fahmida |
| 7 | How Segmentation Works | 2 — Fahmida |
| 8 | Our Novel Methods N1–N4 | 3 — Alimool |
| 9 | How We Measure: Pk and WD | 3 — Alimool |
| 10 | All Methods Compared | 3 — Alimool |
| 11 | Official Results | 3 — Alimool |
| 12 | The Method Selector | 4 — Ismam |
| 13 | The Oracle Experiment | 4 — Ismam |
| 14 | Two Central Findings | 4 — Ismam |
| 15 | Granularity Mismatch | 4 — Ismam |
| 16 | Web App Demo | 5 — Rafi |
| 17 | Web App Output | 5 — Rafi |
| 18 | Where It Works / Errors | 5 — Rafi |
| 19 | Related Work Comparison | 5 — Rafi |
| 20 | What We Contributed | 5 — Rafi |
| 21 | Honest Assessment | 5 — Rafi |
| 22 | Final Verdict | 5 — Rafi |
| 23 | Questions | — |

---

## PERSON 1 — Sadia Alam
### Slides: 1, 2, 3
### Time: ~3 minutes

---

*[Title slide showing. Speak confidently.]*

Good morning, everyone.

Our thesis is called **LecSeg-30** — a Reproducible, Low-Resource Benchmark and Diagnostic Study for Lecture-Video Topic Segmentation.

Let me begin with a simple question. You are studying for your exam. You find a 3-hour Linear Algebra lecture on YouTube. You need only the part about eigenvalues. What do you do? Watch from the beginning? Guess a timestamp? Most students just give up.

This is the problem. YouTube has millions of academic lectures. Most have no chapter structure. Students waste enormous time just scrubbing through videos. Manual chapter creation is too expensive for universities to do at scale.

Our solution: automatically divide a lecture video into meaningful topic sections — producing chapter timestamps a student can click directly.

*[Move to slide 3 — Three Types of Topic Boundary.]*

Now, this sounds straightforward. But before we could build anything, we had to understand a key complexity. The phrase "topic boundary" actually means three completely different things.

**First: Discourse Transition.** This is a fine-grained rhetorical shift — moving from a definition to an example, or from a theorem to a proof. These happen dozens of times per chapter. Signals like pauses and pitch changes can detect them. But they fire far too often for our purpose.

**Second: Semantic Shift.** A drop in meaning similarity between adjacent groups of sentences. Sentence embedding models detect this at roughly the paragraph level.

**Third: Editorial Chapter Boundary.** The actual timestamp a video creator places on YouTube — deliberately dividing the recording into labeled, navigational sections. This is coarse: typically 5 to 20 minutes per chapter. **This is what LecSeg-30 measures.**

The critical insight: if you use signals that detect discourse transitions to predict editorial chapters, you will generate many more boundaries than the creator intended. The signal is not wrong — it is operating at the wrong level of detail. We call this the **Granularity Mismatch**, and it is one of our two central research findings.

*[Hand over to Person 2.]*

"With that, I'll hand it over to Fahmida who will explain what we built and exactly how the system works."

---

## PERSON 2 — Fahmida Afrin Moon
### Slides: 4, 5, 6, 7
### Time: ~3 minutes

---

*[Slide 4 — Dataset.]*

Thank you. Let me tell you what we actually built.

We created a dataset called **LecSeg-30** — 30 public YouTube lectures across 5 subjects: Biology, Computer Science, Mathematics, Philosophy, and Physics. 32.5 hours of content, 419 creator chapter boundaries, 904 reviewed subtopic labels.

This is a **low-resource** benchmark — deliberately small so every single prediction is traceable. A small, fully auditable benchmark tells us more about why methods fail than a large benchmark that just averages everything out.

*[Slide 5 — Annotation Tool. Move quickly.]*

We built a custom Streamlit annotation tool. Yellow dividers are YouTube creator chapters — our reference. Annotators placed green markers for finer subtopic boundaries. Two annotators worked independently so we could measure human agreement.

*[Slide 6 — Pipeline.]*

Here is the full pipeline from start to finish: audio goes into Whisper transcription, then sentence splitting, then embedding, then boundary scoring, and finally chapter titles. We also bring in CLIP visual signals, OCR slide text, and shot detection at the scoring stage.

*[Slide 7 — How Segmentation Works.]*

Let me explain exactly how the segmentation works — this is the core mechanism.

*[Point to figure on slide.]*

After transcription, each sentence is converted to a mathematical vector — an embedding. Sentences with similar meaning are close together in this space. Sentences with different meaning are far apart.

For each sentence position in the transcript, we compare the group of sentences BEFORE that position with the group AFTER it. We measure how different they are. This is cosine dissimilarity. You can see the score curve in the figure — peaks appear where the topic is changing. We find those peaks, apply a minimum segment length, and convert each peak's sentence position back to a Whisper timestamp. That becomes the chapter marker.

*[Hand over to Person 3.]*

"Let me pass it to Alimool who will explain our novel contributions and share our results."

---

## PERSON 3 — Alimool Razi
### Slides: 8, 9, 10, 11
### Time: ~3 minutes

---

*[Slide 8 — Novel Methods.]*

Thank you. We did not just use existing tools. We created four novel components.

**N1** — the Two-Stage Predictor. It separates candidate generation from boundary selection. Stage one uses a low threshold to collect every possible boundary — optimizing for recall. Stage two filters that pool using the full multimodal signal — optimizing for precision. This two-stage decomposition is what the oracle experiment later validates.

**N2** — Entropy-Weighted Fusion. We combine multiple signals — text embeddings, CLIP visual, OCR — by measuring how confident each signal is using entropy. Signals with sharp, peaked score distributions get high weight. Flat, uninformative signals get low weight automatically, per video. No labeled data needed.

**N3** — Hierarchical Nesting. We produce both chapter-level and subtopic-level boundaries at once, with a strict containment constraint: every chapter boundary is also a subtopic boundary.

**N4** — Offline LLM Titling. Chapter titles are generated by Llama 3.1 running completely locally — no internet, no API costs. A university with 1,000 lectures pays essentially nothing.

The Method Selector then picks which combination of these works best for each video.

*[Slide 9 — Metrics.]*

Now let me explain how we measure performance.

We use two metrics: **Pk** and **WindowDiff**. Both slide a window across the transcript and ask at each position: do our predicted boundaries agree with the creator's boundaries within this window?

**Pk is the fraction of window positions where they disagree. Lower is better. Zero is perfect. 0.5 is random guessing.**

**WindowDiff is stricter — instead of just asking "do they agree," it counts how many boundaries fall inside each window for both prediction and reference, and penalizes the difference. It catches over-segmentation more harshly than Pk does.**

Why not exact match? Because for lecture navigation, a boundary two sentences early is still useful — you land in the right section. Pk and WindowDiff are the community standard for segmentation research for exactly this reason.

**Our best result is Pk = 0.3588 and WD = 0.3739.** This means for a 90-minute lecture with 10 chapters, the system identifies the correct chapter region most of the time. A student may scan 1–2 minutes within a section, but they find the content. Real, usable chapters are generated.

*[Slide 10 — Methods chart.]*

Here is every method we tested. Lower is better. Classical methods like TextTiling and KMeans perform poorly — around 0.6. Our BGE-divisive baseline gets 0.3884. The cross-model method reaches 0.3713. Our selector reaches **0.3588** — our best result. Each step is a real improvement.

*[Slide 11 — Official Results.]*

Here are the exact numbers with statistical significance.

The cross-model method is significantly better than the baseline with **p = 0.006**. Our selector — Pk = 0.3588 and WD = 0.3739 — is significantly better than the baseline with **p = 0.025**. Both improvements are real, not due to chance.

At the bottom you see the oracle result: Pk = 0.0172. Person 4 will explain what this means.

*[Hand over to Person 4.]*

"Let me pass it to Ismam who will explain how the selector works and what the oracle experiment reveals."

---

## PERSON 4 — Ismam Khan
### Slides: 12, 13, 14, 15
### Time: ~3 minutes

---

*[Slide 12 — Method Selector.]*

Thank you. You just saw our best result — Pk = 0.3588 — comes from the selector. Let me explain how it works.

Our experiments show no single method is best for every video. BGE-divisive might be optimal for a dense Math lecture, but cross-model might work better for a narrative Philosophy lecture. So we trained a small machine learning model — an ExtraTrees classifier — that takes features of a new video — its domain, duration, embedding variance — and predicts which of our 80+ method configurations will perform best. It then runs that configuration on the video.

Important: **the selector runs BEFORE segmentation.** It looks at metadata features available without any labeled boundaries — domain, duration, embedding statistics — predicts the best configuration, and that configuration runs. It does not try multiple algorithms and pick the best after the fact.

It is trained leave-one-out: for each test video, trained on the other 29. This gives Pk = 0.3588. However, if a video comes from a domain completely unseen in training, performance degrades to Pk = 0.4012. We report this limitation honestly.

*[Slide 13 — Oracle.]*

Now — the oracle experiment. This is our most important diagnostic result.

First, let me explain the **candidate pool**. The pipeline runs with a low threshold and produces around 40 possible boundary positions for a 60-minute lecture. The creator placed 7 real chapter boundaries. Of those 7, **96.8% are already in our 40 candidates**. The correct timestamps are already there.

Now — what is the **oracle**? It is an imaginary version of our system that cheats on one thing: it looks at the correct answers to perfectly choose which of the 40 candidates are the 7 real boundaries. We do not deploy it. We use it as a **diagnostic tool**.

*[Point to oracle Pk numbers.]*

Oracle result: **Pk = 0.0172** — near perfect. Our actual best: Pk = 0.3588. Gap = 0.34 Pk points.

This entire gap is a **position ranking problem** — deciding which candidates are real chapters versus discourse noise. The correct boundaries are in the pool. The bottleneck is choosing them.

*[Slide 14 — Two Central Findings.]*

Two central findings from our research.

**Finding 1**: the bottleneck is position selection, not detection. Oracle proves this. The data has what is needed.

**Finding 2**: granularity mismatch — let me show the evidence.

*[Slide 15 — Granularity Mismatch.]*

Look at this table. Every signal that detects fine-grained transitions made performance WORSE — discourse markers, BERTopic, GPT-2 perplexity, acoustic prosody. They detect real transitions, but at the wrong scale.

The one exception is CLIP visual embeddings — which improved performance. Why? Because when a lecturer starts a new chapter, they switch to a new slide. Slide scene changes happen at the same scale as creator chapters. CLIP naturally aligns with editorial granularity.

This finding is transferable: any future system targeting editorial chapter segmentation should avoid fine-grained signals and focus on visual and semantic embedding signals.

*[Hand over to Person 5.]*

"Thank you. I'll hand it over to Rafi for the demo, comparison with other work, and our final summary."

---

## PERSON 5 — Md. Shahriar Islam Rafi
### Slides: 16, 17, 18, 19, 20, 21, 22
### Time: ~3 minutes

---

*[Slide 16 — Web App. Move fast.]*

Thank you. We built a full web application. Paste any YouTube URL — the system downloads audio, transcribes it, selects the best method, and generates chapter titles using a local AI model running completely offline. No API keys, no internet for inference.

We tested it on BRACU's own CSE420 Compiler Design lectures and it correctly identified chapter transitions including Lexical Analysis and Context-Free Grammar.

*[Slide 18 — Errors.]*

We identified five error types. The most common is boundary displacement — correct region, wrong sentence. Over-segmentation happens when fine-grained signals are active. Under-segmentation happens in Math and Biology with dense, consistent vocabulary.

For external validation: we tested the core BGE-divisive signal on 10 videos from 3Blue1Brown, Veritasium, and CrashCourse — not in our benchmark. External Pk = 0.389 vs benchmark Pk = 0.388 — a difference of 0.001. The core signal generalizes.

*[Slide 19 — Related Work.]*

How does our work compare? Large systems like VidChapters-7M use 817,000 videos with supervised fine-tuning. We do not compete at that scale. TreeSeg is the closest comparable: Pk = 0.367 on its own 21-video dataset — a different dataset, so numbers are NOT directly comparable. Our Pk = 0.3588 is in the same range with zero labeled training data.

What we offer specifically: we are the **first publicly reproducible low-resource benchmark** for lecture-video chapter segmentation with Pk/WD metrics, bootstrap confidence intervals, oracle analysis, and hierarchical annotation together. We established this benchmark — future researchers can run any method on our 30 videos and compare directly.

*[Slides 20 and 22.]*

To summarize: we contributed a dataset, a bottleneck finding, a granularity mismatch diagnosis, a two-level annotation protocol, and a fully reproducible pipeline.

**We achieved real, automated lecture segmentation.** Our best result is Pk = 0.3588 and WD = 0.3739 — validated with statistical significance, tested externally, competitive with comparable published work — using zero labeled training data.

The most important sentence from our research: **candidate generation is largely solved — candidate selection and ranking is the bottleneck.** That tells the next researcher exactly where to invest.

Thank you. We welcome your questions.

---

## KEY CONCEPTS — Know These Cold

### Oracle vs Method Selector (most common confusion)

| | Oracle "selection" | Method Selector |
|---|---|---|
| What it selects | Which POSITIONS (timestamps) from the pool are real chapter boundaries | Which ALGORITHM to run on a new video |
| When it runs | Diagnostic experiment only — not deployed | Runs before segmentation for every new video |
| How it decides | Cheats: looks at correct answers | ExtraTrees on video metadata features |
| Result | Oracle Pk=0.0172 (ceiling) | Selector Pk=0.3588 (our best) |

### Candidate Pool (what it is)

The pipeline runs with a very low threshold → produces many candidate timestamp positions (~40 for a 60-min lecture). Most are noise. The correct 7 chapter boundaries are among the 40 at 96.8% recall. The challenge is finding the 7 among the 40.

### Why Pk=0.3588 is a good result

- Random guessing = 0.5. Perfect = 0.0.
- We achieve 0.3588 with ZERO labeled training data.
- Comparable to TreeSeg (Pk=0.367) on its own dataset.
- Statistically significantly better than every classical and neural baseline.
- Real chapters are generated and usable.

### Selector and external videos

The selector takes video metadata features (domain, duration, embedding variance) available for any YouTube video. It runs BEFORE segmentation — it predicts the best algorithm upfront. Leave-domain-out (Pk=0.4012) shows the selector is less reliable on entirely new domains.

---

## TRANSITION PHRASES

- "With that, I'll hand it over to [Name] who will cover..."
- "Let me pass it to [Name] to explain..."
