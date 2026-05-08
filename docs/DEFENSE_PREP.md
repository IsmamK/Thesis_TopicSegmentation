# 🎓 DEFENSE PREP — Continuous Throughout the Project

**Defense readiness is not a Phase-11 thing. It is a habit from Day 1.**
Every task contributes to the defense. Here's how, by phase.

---

## Phase 1–2 (Setup + Literature)

After each task, write 2 lines in `docs/DEFENSE_QA.md` answering:

- "Why did you do it this way and not another way?"
- "What's the alternative and why did you reject it?"

Example after T03 (Python deps):

> **Why pin to Python 3.11?**
> faster-whisper and PaddleOCR have wheels for 3.11 but not for 3.13 yet. Pinning saves install pain across team members.
>
> **Why open libraries (Whisper, CLIP, Llama) and not commercial APIs?**
> Reproducibility: closed APIs are a black box and may change silently. Cost: APIs charge per call. Compliance: BracU rules favour open-source for thesis work.

This way, by T31 you already have ~30 Q&A pairs without dedicated effort.

---

## Phase 3 (Dataset)

The most likely panel question: **"Why 30 videos? Is that enough?"**

Prepare the answer now:
- Total ≈ 20 h of content (~10× larger than classical TextTiling test sets).
- 5 domains × 6 videos = decent diversity.
- Limited by hand-annotation cost — 30 videos × ~1 h subtopic-annotation × 2 annotators (10 of them) = 50 person-hours, the realistic limit.
- 30 is consistent with prior small-scale lecture datasets (Tuna 2015 ~15 videos).

Write this into `docs/DEFENSE_QA.md` after T13.

---

## Phase 4–7 (Implementation)

For each novel module (T25–T28), write a 1-page **design rationale** in `docs/DESIGN_RATIONALES/T<NN>.md`:

- The problem
- The alternatives considered
- The choice + why
- The downside

This becomes raw material for Chapter 3 of the thesis AND for the panel's "why not X?" questions.

---

## Phase 8 (Evaluation)

After T29, every number on the master table must have a **memorised one-line explanation**. Example:

> "Ours-all-hier+LLM gets H-WD = 0.298 vs the strongest baseline's 0.341 — a 12.6 % relative reduction with p = 0.014 by paired Wilcoxon (n = 30)."

Practise these aloud. The panel rewards confident numbers.

---

## Phase 9 (Writing)

While Sadia writes, every other team member reviews their own chapter section and **writes the matching defense Q&A** to `docs/DEFENSE_QA.md`. This guarantees alignment between thesis prose and what you'll say in the room.

---

## Phase 10 (Deliverables)

Slides (T41) follow the **rule of one**:
- One idea per slide.
- One figure per slide.
- One sentence in your head before you click "next".

Poster (T40) follows the **5-second rule**: the title + 3 numbers must be readable from 1 m in 5 s.

---

## Phase 11 (T44–T47)

The home stretch. Run the rehearsals. Print the poster. Pack the USB. Sleep.

---

## What the panel typically asks

Six categories. Have ≥ 8 answers prepared per category.

1. **Motivation & novelty** — "What's actually new?"
2. **Dataset** — "Why this size? How is it different from AVLectures?"
3. **Methods** — "Walk me through reliability-weighted fusion. Why softmax?"
4. **Experiments & statistics** — "Is the improvement statistically significant?"
5. **Limitations** — "What does your model fail on?"
6. **Implementation** — "How would I run this on my own video?"

See `docs/DEFENSE_QA.md` (built in T45) for the live answer set.

---

## Day-of tactics

- **First 30 seconds:** look at every panel member, smile, state your name and the title clearly.
- **When you don't know:** "That's a great question. We don't have evidence on that yet — what we *do* know is …". Pivot to a known answer.
- **When you do know:** answer in ≤ 90 s, then stop. Don't ramble.
- **When asked about future work:** show 3 concrete next steps. Confidence wins.
- **Never:** disagree with a panel member's premise harshly. Reframe: "If I understand the question, I'd say …".

---

## After the defense

- Send the supervisor and panel a thank-you email within 24 h.
- Push the final commit + tag `v1.0`.
- Celebrate.
