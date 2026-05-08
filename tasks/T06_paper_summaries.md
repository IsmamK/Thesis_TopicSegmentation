# T06 — Write Summaries for 20 Core Papers

**Phase 2 · Literature Review · Estimated time: 3 hours (Claude does most of it) · Owner: Sadia**

---

## 🎯 What you are doing
Creating one markdown summary per paper (20 papers total), each written in the exact same template, stored in `papers_summary/`. Each summary includes a BibTeX citation which auto-appends to `thesis/bibliography/references.bib`.

## 🤔 Why
Chapter 2 of the thesis (Literature Review) needs rigorous, consistent coverage. Panels hate inconsistent citation depth. A fixed template forces us to extract the same facts from every paper.

## ✅ How to know you are done
- `ls papers_summary/` shows 20 .md files.
- Every summary has all 8 sections (see template below).
- `thesis/bibliography/references.bib` has 20 valid BibTeX entries.
- [`docs/LITERATURE_MATRIX.md`](../docs/LITERATURE_MATRIX.md) lists all 20 with a 1-line contribution.

---

## 📝 Steps

### Step 1 — Claim the task
```
python scripts/claim.py T06 sadia
```

### Step 2 — Open a Claude session

Paste this prompt:

> Execute T06. Read `internal/CLAUDE.md` and `internal/PROMPTS/paper_template.md`. For each of the 20 papers in the list below, launch the paper-summarizer subagent **in parallel** (batches of 5) to write a summary to `papers_summary/<firstauthor>_<year>.md`. Append a BibTeX entry to `thesis/bibliography/references.bib`. After all 20 done, run `python scripts/build_literature_matrix.py` to regenerate `docs/LITERATURE_MATRIX.md`.

**The 20 papers to summarize:**

| # | Citation hint | Source |
|---|---|---|
| 1 | Hearst 1997, "TextTiling" | https://aclanthology.org/J97-1003/ |
| 2 | Choi 2000, "C99" | https://aclanthology.org/A00-2004/ |
| 3 | Beeferman et al. 1999, "Pk" | https://doi.org/10.1023/A:1007506220214 |
| 4 | Pevzner & Hearst 2002, "WindowDiff" | https://aclanthology.org/J02-1002/ |
| 5 | Fournier 2013, "Boundary Similarity" | https://aclanthology.org/P13-1120/ |
| 6 | Tuna et al. 2015, "Classroom Videos" | https://www.cs.uh.edu/~subhlok/ |
| 7 | Zhang et al. 2016, "MOOC Segmentation" | IEEE ICALT 2016 |
| 8 | Gandhi et al. 2018, "Visually Salient Words" | Xerox Research India |
| 9 | Chand & Ogul 2021, "Framework for Lecture Video Segmentation" | Østfold University |
| 10 | Freisinger et al. 2023, "Unsupervised Multilingual Topic Segmentation" | SLATE 2023 |
| 11 | D.S.S. et al. 2023, "AVLectures" | WACV 2023 |
| 12 | Sun et al. 2019, "Contrastive Bidirectional Transformer" | arxiv 1906.05743 |
| 13 | Karim et al. 2024, "MED-VT++" | arxiv 2306.03409 |
| 14 | Wei et al. 2024, "PreMind" | arxiv 2409.xxxxx |
| 15 | Yu et al. 2024, "Multimodal Fusion & Coherence Modeling" | arxiv 2408.xxxxx |
| 16 | Fan et al. 2023, "Topic Segmentation via LLMs" | EMNLP 2023 |
| 17 | Sener & Yao 2018, "Unsupervised Activity Segmentation" | CVPR 2018 |
| 18 | Che & Yang 2018, "Slide Synchronization" | |
| 19 | Reimers & Gurevych 2019, "Sentence-BERT" | arxiv 1908.10084 |
| 20 | Radford et al. 2023, "Whisper" | arxiv 2212.04356 |

### Step 3 — Human review

Pick **any 3 at random** and read them yourself. Check:
- Does the "Method" section match what the paper says in the abstract?
- Is the BibTeX key `<firstauthor><year>_<keyword>`, lowercase?
- Are "Limitations" actually from the paper, not invented?

If any summary is wrong, tell Claude: *"Redo papers_summary/<filename>.md. The [Method | Limitations | Results] section is incorrect because [specific issue]."*

### Step 4 — Verify

```
ls papers_summary/*.md | wc -l    # should print 20
grep -c "^@" thesis/bibliography/references.bib    # should print >= 20
```

---

## 📄 The paper-summary template (lives at `internal/PROMPTS/paper_template.md`)

Every summary MUST have exactly these 8 sections:

```markdown
# <Short Title>

**Authors:** <names>
**Year:** <YYYY>
**Venue:** <conference/journal>
**Citation key:** `<firstauthor><year>_<keyword>`

## BibTeX
```
@article{<key>, ... }
```

## Problem (2 sentences)
<what problem they solve, why it matters>

## Method (5 bullets)
- ...

## Datasets used

| Dataset | Size | Domain |
|---|---|---|

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|

## Limitations (3 bullets, from the paper itself)
- ...

## How it relates to our work
<1 paragraph — which chapter/section we cite it in; what our system does differently>

## Differences from our approach (tied to novelty claims)
- N1: ...
- N2: ...
```

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| Claude can't fetch a paper PDF | Give it the arXiv abstract URL instead; it can still produce a summary from the abstract |
| BibTeX keys collide | Rename to `<firstauthor><year>_<secondword>` (e.g., `hearst1997_texttiling`) |
| Summary is hallucinated | Redo with prompt: "Do not invent results. If unknown, write 'not reported in abstract'." |

---

## ➡️ When done

```
python scripts/mark_done.py T06
python scripts/next.py
```
