# 🗺️ PROJECT MAP — Visual Index of Everything

**One screen. Find anything in 5 seconds.**

---

## The 11 phases

```
   ┌──────────┐  ┌────────────────────┐  ┌────────────┐  ┌──────────────────┐
   │  Setup   │→ │ Literature Review  │→ │  Dataset   │→ │  Preprocessing   │
   │  T01-T05 │  │      T06-T08       │  │  T09-T13   │  │      T14-T18     │
   └──────────┘  └────────────────────┘  └────────────┘  └──────────────────┘
                                                                    │
   ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐         ▼
   │  Defense Prep    │← │ Deliverables │← │ Thesis Writing│  ┌────────────┐
   │      T44-T47     │  │    T38-T43   │  │   T32-T37     │  │  Features  │
   └──────────────────┘  └──────────────┘  └──────────────┘  │  T19-T21   │
            ↑                                                │            │
            │                                                └────────────┘
            │                                                       │
            │     ┌──────────────┐  ┌──────────────┐  ┌────────────┐│
            └─────│  Evaluation  │← │ Novel Method │← │  Baselines ││
                  │   T29-T31    │  │   T25-T28    │  │  T22-T24   │◀
                  └──────────────┘  └──────────────┘  └────────────┘
```

---

## Where every file lives

```
PreThesis2_TopicSegmentation/
│
├── 🚦 START_HERE.md        ← First-time setup
├── 🚦 README.md            ← Top-level overview
├── 🚦 STATUS.md            ← Auto-generated. What's done.
├── 🚦 NEXT.md              ← Auto-generated. What to do now.
├── 🚦 WHAT_WE_ARE_DOING.md ← Public-facing project summary
├── 🚦 PROJECT_MAP.md       ← This file
├── 🚦 progress.yaml        ← Source of truth for task status
│
├── tasks/                  ← T01–T47, one md per task
│   ├── T01_install_prerequisites.md
│   ├── ...
│   └── T47_final_checklist.md
│
├── docs/                   ← Public-facing concepts & guides
│   ├── CONCEPTS.md         ← What every topic means
│   ├── GLOSSARY.md         ← Every word, plain English
│   ├── METHODOLOGY.md      ← The research plan
│   ├── NOVELTY_TRACKER.md  ← Our 7 novelties
│   ├── LITERATURE_MATRIX.md← Auto-built from papers_summary/
│   ├── COLLABORATION.md    ← Team rules
│   ├── HANDOFF.md          ← When you pick up the project
│   ├── TROUBLESHOOTING.md  ← Errors & fixes
│   ├── SETUP.md            ← Detailed env setup
│   ├── RESOURCES.md        ← External learning links
│   ├── OUTPUT_INTERPRETATION.md ← How to read outputs
│   ├── DEFENSE_PREP.md     ← Defense-readiness habits
│   ├── DEFENSE_QA.md       ← Built in T45
│   ├── PAPER_ADDITION_GUIDE.md ← How to add a paper
│   ├── THESIS_WRITING_GUIDE.md ← Style rules
│   └── ERROR_ANALYSIS.md   ← Built in T31
│
├── papers_summary/         ← One md per paper, fixed template
│
├── thesis/                 ← LaTeX thesis source (built in T02+)
│   ├── main.tex
│   ├── chapters/
│   ├── figures/
│   └── bibliography/references.bib
│
├── paper/                  ← IEEE paper (T38)
├── webapp/                 ← Streamlit demo (T39)
├── slides/                 ← Defense slides (T41)
├── poster/                 ← Defense poster (T40)
│
├── src/lecseg/             ← All code (built in T03+)
│   ├── data/
│   ├── preprocess/
│   ├── features/
│   ├── models/
│   ├── refine/
│   ├── eval/
│   ├── viz/
│   └── cli.py
│
├── configs/                ← Hydra YAMLs
├── data/                   ← Datasets, transcripts, embeddings
├── results/                ← Per-experiment outputs
├── tests/                  ← pytest tests
│
├── scripts/                ← Helpers — run, don't edit
│   ├── today.py            ← The ONE command per day
│   ├── dashboard.py        ← Terminal dashboard
│   ├── visualize_progress.py ← HTML dashboard
│   ├── next.py             ← Print next task
│   ├── show.py             ← Print a task file
│   ├── claim.py            ← Claim a task
│   ├── mark_done.py        ← Mark a task done
│   ├── mark_progress.py    ← Update task status
│   ├── update_status.py    ← Regenerate STATUS.md / NEXT.md
│   ├── context.py          ← Claude-context helper
│   ├── resume.py           ← Older Claude-context helper
│   ├── add_paper.py        ← Stub a new paper summary
│   ├── build_literature_matrix.py
│   ├── update_thesis.py    ← Prompt to update a chapter
│   ├── interpret.py        ← Explain an output file
│   ├── pre_defense_check.py
│   └── strip_internal.py   ← Strip Claude/AI files before submission
│
└── internal/               ← Project-management notes
    ├── CLAUDE.md           ← House rules
    ├── CLAUDE_EXECUTION_PLAYBOOK.md
    └── PROMPTS/            ← Reusable prompts
        ├── paper_template.md
        └── claude_context_template.md
```

---

## Quick command map

| Goal | Command |
|---|---|
| 👋 Start the day | `python scripts/today.py` |
| 📊 HTML dashboard | `python scripts/visualize_progress.py` |
| 📖 Read a task | `python scripts/show.py T<NN>` |
| 🙋 Claim a task | `python scripts/claim.py T<NN> <yourname>` |
| ✅ Finish a task | `python scripts/mark_done.py T<NN>` |
| 🚫 Block a task | `python scripts/mark_progress.py T<NN> blocked "reason"` |
| 💬 Resume Claude | `python scripts/context.py` |
| 📝 Add a paper | `python scripts/add_paper.py "<url>"` |
| 📚 Rebuild lit. matrix | `python scripts/build_literature_matrix.py` |
| 🔬 Interpret an output | `python scripts/interpret.py <file>` |
| 🎓 Final check | `python scripts/pre_defense_check.py` |
| 🧹 Strip internal | `python scripts/strip_internal.py --dry-run` |
| 🛠️ Build thesis PDF | `cd thesis && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex` |
| 🌐 Run web demo | `streamlit run webapp/app.py` |

---

## Status legend

| Icon | Meaning |
|---|---|
| ⬜ | todo — not started |
| 🟡 | doing — claimed and in progress |
| 🟥 | blocked — waiting on something |
| ✅ | done |
| ⏭️ | skipped — intentionally omitted |
