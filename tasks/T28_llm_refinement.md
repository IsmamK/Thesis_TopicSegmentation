# T28 — LLM Boundary Refinement + Auto-Titling (Novelty N4)

**Phase 7 · Novel Method · Estimated time: 6 h · Owner: Ismam (model), Alimool (prompts)**

---

## 🎯 What you are doing
Feeding each candidate boundary from T27 into a **local** LLM (Llama 3.1 via Ollama from T04) and asking: "Is this a real topic boundary? If yes, what is the title of the next segment?" The LLM can reject boundaries that look spurious and generate human-readable chapter titles.

## 🤔 Why
Every prior lecture-segmentation paper that does LLM refinement uses GPT-4 — not reproducible. Our claim: **open local LLM gives comparable quality** at zero cost and full auditability. **This is novelty N4.**

## ✅ How to know you are done
- `src/lecseg/refine/llm_refine.py` with `refine_boundaries(candidates, sentences) -> (kept, titles)`.
- `data/llm_cache/` caches every prompt+response so re-running is free.
- Adding LLM refinement improves H-WD by ≥ 1.5 points on our 30 videos.

---

## 📝 Steps

### Ask Claude

> Execute T28. Prompt design is critical — keep it simple and deterministic.
>
> **Prompt template for each candidate boundary b:**
> ```
> System: You are an expert at deciding if two consecutive blocks of lecture text
> are about different topics. Respond JSON ONLY.
>
> User:
> Block A (last 120 seconds before the boundary):
>   <sentences>
> Block B (first 120 seconds after the boundary):
>   <sentences>
>
> Question: Do A and B cover different topics?
> Respond:
>   {"different_topic": true|false, "new_title": "<5-8 word title if true>", "reason": "<one sentence>"}
> ```
>
> - Temperature 0, seed 42 for determinism.
> - Cache by sha256(prompt) → response in `data/llm_cache/`.
> - Batch via `ollama.chat()` with concurrency 2.
>
> Ablations to record:
>   - `refine_ON`: full pipeline.
>   - `refine_OFF`: skip LLM (T27 output as-is).
>   - `title_OFF_refine_ON`: reject only, no auto-titles.

### Verify

```
python scripts/run_refine.py
python scripts/interpret.py results/<latest>/metrics.json
```

Check at least one video's predicted titles — do they sound reasonable?

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **LLM** | Large Language Model. A neural net that generates text. |
| **Local LLM** | One that runs on your computer (Ollama + Llama 3.1). No API. |
| **Prompt** | The input you give the LLM. |
| **Temperature 0** | Forces the LLM to be as deterministic as possible. |
| **Caching** | Saving each response so re-running is free. |

More: [docs/CONCEPTS.md#llm-refinement](../docs/CONCEPTS.md#llm-refinement)

---

## ➡️ When done

```
python scripts/mark_done.py T28
python scripts/update_thesis.py T28
python scripts/today.py
```
