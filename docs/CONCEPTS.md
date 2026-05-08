# 📚 CONCEPTS — What We're Doing, Explained Simply

**Audience: a team-mate who has finished 2nd-year CS but has never done ML research.**
Every section is self-contained. Read just the ones relevant to your current task.

Use `Ctrl+F` / `Cmd+F` with the anchor ids to jump around.

---

## <a id="environment"></a> Environment (T01–T05)

**What:** installing Python, Git, FFmpeg, LaTeX, Ollama on your computer so every command we use later works.

**Why:** without a consistent environment, code that works on one laptop crashes on another. The 5 tasks in Phase 1 guarantee everyone's machine is identical.

**Resources:**
- Python installer basics: https://realpython.com/installing-python/
- FFmpeg in 30 seconds: https://ffmpeg.org/ffmpeg.html
- Git crash course: https://www.atlassian.com/git/tutorials

---

## <a id="project-layout"></a> Project layout (T02)

**What:** a fixed set of folders (`src/`, `configs/`, `data/`, `results/`, `thesis/`, `paper/`, `webapp/`, …) everything lives in.

**Why:** research code tends to explode into ad-hoc scripts. A fixed layout makes the project readable 2 months from now.

---

## <a id="python-packages"></a> Python packages & virtual environments (T03)

**What:** a **package** is a folder of `.py` files you can `import`. A **virtual environment** is an isolated Python + library sandbox.

**Why:** different projects need different library versions. The venv keeps them separate.

**Key terms:**
- `pip install -e .` — install our package *in editable mode* so live code edits take effect.
- `pyproject.toml` — modern standard replacing `setup.py` + `requirements.txt`.

**Resources:** https://packaging.python.org/en/latest/tutorials/installing-packages/

---

## <a id="llms"></a> Large Language Models (LLMs) (T04)

**What:** neural networks trained on billions of web pages that predict the next word given previous words. The popular ones: GPT-4 (closed), Claude (closed), Llama 3.1 (open), Mistral (open).

**Why for us:** Novelty **N4** uses a *local* (open) LLM to decide if two pieces of text are about different topics and to propose chapter titles. Local = runs on your machine via Ollama.

**Resources:**
- Visual explainer: https://bbycroft.net/llm
- Ollama guide: https://github.com/ollama/ollama

---

## <a id="smoke-tests"></a> Smoke tests (T05)

**What:** a tiny end-to-end run that touches every component — just enough to prove "the pipes are connected".

**Why:** catches 90% of install problems in minutes instead of hours.

---

## <a id="literature-review"></a> Literature review (T06–T07)

**What:** reading papers in your area and writing down (1) what they did, (2) what they got wrong / missed, (3) how your work differs.

**Why:** a thesis without a strong literature review cannot claim novelty. The panel will ask "why is this new?" and you'd better have a rehearsed answer.

**Resources:**
- Connected Papers (visual paper graph): https://www.connectedpapers.com/
- Semantic Scholar: https://semanticscholar.org/

---

## <a id="novelty"></a> Novelty claims (T08)

**What:** a numbered list of things your thesis does that nobody has done before, each pinned to (a) the paper that admits the gap, (b) the module that implements your fix, (c) the experiment that proves it works.

**Why:** this is what you defend. See `docs/NOVELTY_TRACKER.md`.

---

## <a id="dataset"></a> Dataset (T09–T10)

**What:** the collection of videos + ground-truth labels we train and evaluate on. Ours is LECSEG-30.

**Why:** the quality of your results is bounded by the quality of your dataset. Garbage in → garbage out.

**Key terms:**
- **Domain** — a subject area (physics, biology, CS). Covering multiple domains makes our results generalisable.
- **yt-dlp** — the open downloader we use to fetch YouTube videos.

---

## <a id="ground-truth"></a> Ground truth (T11)

**What:** the "correct answer" your model is scored against. For us: the chapter timestamps the YouTube video creator wrote.

**Why:** every metric compares `pred` against `gt`. Without clean GT, metrics are meaningless.

---

## <a id="annotation"></a> Annotation (T12)

**What:** labelling data by hand. In our case: watching a lecture and writing down where subtopic boundaries go.

**Why:** only humans can judge what "a topic shift" means. The model later learns to imitate the human labels.

**Resources:** https://github.com/doccano/doccano (general open-source annotation tool).

---

## <a id="agreement"></a> Inter-annotator agreement / Cohen's kappa (T13)

**What:** a number (−1 to +1) measuring how much two humans agree on labels, adjusted for the agreement you'd get by random chance.

**Interpretation:**
- κ ≥ 0.8 — almost perfect.
- 0.6–0.79 — substantial (what we target).
- < 0.4 — weak; the task itself is ill-defined.

**Why for us:** a published dataset that reports κ is trustworthy. One that doesn't is not.

**Resource:** https://en.wikipedia.org/wiki/Cohen%27s_kappa

---

## <a id="asr"></a> Automatic speech recognition (ASR) (T14)

**What:** turning spoken audio into text. The state of the art is **Whisper** (OpenAI, 2022).

**Why for us:** we need the text of every lecture so we can reason about topic similarity between sentences.

**Resources:**
- Whisper paper: https://arxiv.org/abs/2212.04356
- faster-whisper: https://github.com/SYSTRAN/faster-whisper

---

## <a id="sentence-splitting"></a> Sentence splitting (T15)

**What:** breaking a paragraph into individual sentences. Sounds trivial but is actually tricky (abbreviations, acronyms).

**Why:** the *sentence* is the unit we reason at. Every boundary sits between two sentences.

---

## <a id="shot-boundary"></a> Shot-boundary detection (T16)

**What:** a "shot" in a video is a continuous run of frames with no visual cut. A shot boundary is where one shot ends and the next begins — usually where slides change.

**Why:** slide changes are a strong cue that a topic might be shifting. We use TransNetV2, a pretrained neural detector.

**Resource:** https://github.com/soCzech/TransNetV2

---

## <a id="ocr"></a> Optical character recognition (OCR) (T17)

**What:** turning pixels of text (slide title) into machine-readable text.

**Why:** slide titles often mention the topic directly ("Chapter 3: Entropy"). We use PaddleOCR.

---

## <a id="prosody"></a> Prosody features (T18)

**What:** features about *how* something is said, not *what* is said — pauses, pitch, speaking rate.

**Why:** humans intuitively pause longer before a topic change. The model can use that too.

---

## <a id="text-embeddings"></a> Text embeddings (T19)

**What:** a function that turns a sentence into a list of ~384–768 numbers (a *vector*) so that semantically-similar sentences have similar vectors.

**Why:** we can't compare raw text meaningfully. We compare their embeddings.

**Popular choices:**
- SBERT MiniLM — small, fast.
- MPNet — stronger.
- E5, BGE — newer, top of MTEB leaderboard.

**Resources:**
- SBERT: https://www.sbert.net/
- MTEB leaderboard: https://huggingface.co/spaces/mteb/leaderboard

---

## <a id="visual-embeddings"></a> Visual embeddings (T20)

**What:** vectors for images — same idea as text embeddings but for frames. The industry standard is **CLIP** (OpenAI 2021).

**Why:** we need to know visually how similar two frames are. Different slides → different CLIP vectors.

---

## <a id="alignment"></a> Timeline alignment (T21)

**What:** everything lives on its own timeline (sentences, shots, prosody). We force everything to line up with the sentence timeline.

**Why:** the model wants a single matrix, not 4 matrices in 4 timelines.

---

## <a id="metrics"></a> Segmentation metrics (T22)

**What:** ways to compare a predicted list of boundaries against the ground truth:

| Metric | Lower/Higher is better | One sentence |
|---|---|---|
| **Pk** | Lower | Probability a random word-window crosses a wrong boundary. |
| **WindowDiff** | Lower | Like Pk but also penalises over/under-segmentation. |
| **Boundary Similarity (BS)** | Higher | A near-miss gets partial credit. 1 = perfect. |
| **Tolerance-F1** | Higher | F1 with a ±N-second tolerance. |
| **Hierarchical WD (H-WD)** | Lower | **Our N6**. Weighted WD across chapter + subtopic levels. |

**Resources:**
- segeval library: https://segeval.readthedocs.io/
- Pevzner & Hearst 2002 (WindowDiff): https://aclanthology.org/J02-1002/

---

## <a id="baselines"></a> Baselines (T23–T24)

**What:** simple/reference methods you run *with the same evaluation* so you can claim "our method beats X".

**Why:** a new number in isolation is meaningless. It has to beat something.

---

## <a id="fusion"></a> Multimodal fusion (T25)

**What:** combining evidence from multiple sources (text, image, audio) into one prediction. Typical fusion is **early** (concat features) or **late** (vote predictions).

**Our twist (N2):** each sentence gets a *learned* per-modality weight — we call it reliability-weighted fusion. When text is noisy, the model down-weights text for that sentence.

---

## <a id="boundary-prediction"></a> Boundary prediction & Viterbi (T26)

**What:** a two-stage model. Stage 1: per-sentence neural score. Stage 2: Viterbi decoder that respects global constraints (minimum chapter length, etc.).

**Why:** neural scores are noisy. Viterbi smooths them into a globally sensible segmentation.

---

## <a id="hierarchical-output"></a> Hierarchical output (T27)

**What:** outputting *both* chapter boundaries and subtopic boundaries (inside each chapter).

**Why:** our N3 claim. Prior lecture work outputs one flat layer.

---

## <a id="llm-refinement"></a> LLM refinement (T28)

**What:** ask a local LLM "are these two blocks of text on different topics? If yes, give a title."

**Why:** neural scores don't understand semantics deeply; an LLM does. We use a *local* LLM (our N4) to stay open and reproducible.

---

## <a id="ablations"></a> Ablations (T29)

**What:** run your model with one component turned off at a time, to measure each component's contribution.

**Why:** "our full model beats the baseline" is weaker than "each of our 4 novel components adds measurable gains".

---

## <a id="statistics"></a> Statistics (T30)

**What:**
- **95% CI (confidence interval)** via bootstrap: the range in which the true mean likely lies.
- **Paired Wilcoxon signed-rank**: are the differences between method A and method B across our 30 videos non-random?

**Why:** a result that looks better but is statistically insignificant is not a result.

**Resources:** https://scipy.github.io/devdocs/reference/generated/scipy.stats.wilcoxon.html

---

## <a id="error-analysis"></a> Error analysis (T31)

**What:** going through your model's mistakes by hand and categorising them.

**Why:** gives you concrete limitations to mention in Chapter 4 and future-work items for Chapter 5. Panels love specific examples.

---

## Still confused?

- Unfamiliar word? → `docs/GLOSSARY.md`
- Got an error? → `docs/TROUBLESHOOTING.md`
- Don't know what an output file means? → `docs/OUTPUT_INTERPRETATION.md`
- External resource list? → `docs/RESOURCES.md`
