# T27 — Hierarchical Output (Novelty N3)

**Phase 7 · Novel Method · Estimated time: 4 h · Owner: Ismam**

---

## 🎯 What you are doing
Extending the predictor from T26 to output **two levels**: chapter boundaries AND subtopic boundaries. Subtopics live strictly inside chapters.

## ✅ How to know you are done
- `src/lecseg/models/hier_output.py` defines a dual-head decoder.
- Output format: `{"chapters": [s1, s2, ...], "subtopics": [s1, s2, ...]}` where every subtopic s is between two chapter boundaries.
- Evaluated with H-WD (T22) on 30 videos.

---

## 📝 Steps

### Ask Claude

> Execute T27. Extend T26's model with a second head that predicts subtopic probabilities at every sentence position. Constraints: a subtopic boundary may only occur strictly between two chapter boundaries, and not within 30 s of a chapter boundary.
>
> Enforce via a second Viterbi pass after chapter decoding. Loss = weighted sum of chapter BCE + subtopic BCE (weight chapter 2× for class imbalance).
>
> Report: chapter-WD, subtopic-WD, hierarchical H-WD, and a figure showing one video's predicted hierarchy against GT.

### Verify

```
python scripts/run_hier.py --video <some_id>
```

Output JSON should parse; subtopic count per chapter in [1, 6].

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **Hierarchical output** | Two levels: coarse (chapter) and fine (subtopic), with subtopics nested inside chapters. |
| **Dual-head decoder** | Two prediction heads sharing the same encoder. Common in multi-task learning. |

More: [docs/CONCEPTS.md#hierarchical-output](../docs/CONCEPTS.md#hierarchical-output)

---

## ➡️ When done

```
python scripts/mark_done.py T27
python scripts/update_thesis.py T27
python scripts/today.py
```
