# T08 — Lock Novelty Claims & Identify Research Gap

**Phase 2 · Literature Review · Estimated time: 45 min · Owner: Ismam + Sadia together**

---

## 🎯 What you are doing
Writing a 2-page document `docs/NOVELTY_TRACKER.md` that locks in our 7 novelty claims, each with: (a) the paper gap it addresses, (b) the specific module that implements it, (c) the experiment that proves it works.

## 🤔 Why
Every time the panel asks "but what's new?" — we point here. No hand-waving. Every claim is pinned to evidence.

## ✅ How to know you are done
- `docs/NOVELTY_TRACKER.md` has a row for each of N1–N7.
- Each row lists: gap addressed (cites specific prior work), module name/file path, experiment config name, expected table/figure number in thesis.

---

## 📝 Steps

### Step 1 — Ask Claude
> Execute T08. Read `docs/LITERATURE_MATRIX.md` and the existing `CLAUDE_EXECUTION_PLAYBOOK.md` (novelty section). Produce `docs/NOVELTY_TRACKER.md` with a row per novelty claim. Schema: | ID | Name | Gap it closes (with citations from matrix) | Implementing module (file path) | Experiment config | Proof artifact (table/figure) |. Stop if any claim lacks a clear gap-to-proof chain, and ask the user.

### Step 2 — Human sanity-check

Read the tracker. For each novelty:
- Does a real paper admit the gap you claim it leaves open? (If no, the novelty is fake.)
- Is the module you will build actually different from what that paper did?

If any novelty fails either check, either:
- Strengthen it with a more specific differentiator, or
- Drop it and replace with one from the backup list in the tracker.

---

## ➡️ When done

```
python scripts/mark_done.py T08
python scripts/next.py
```
