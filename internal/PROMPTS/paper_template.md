# Paper Summary Template

**Every paper in `papers_summary/` MUST follow this 8-section structure.**
**Filename: `<firstauthor><year>.md` (lowercase), e.g. `hearst1997.md`.**

---

```markdown
# <Short Title>

**Authors:** <First A, Second B, Third C>
**Year:** YYYY
**Venue:** <conference/journal>
**Citation key:** `<firstauthor><year>_<keyword>`
**Link:** <url>

## BibTeX
```
@article{<key>,
  author  = {...},
  title   = {...},
  journal = {...},
  year    = {YYYY},
}
```

## Problem (2 sentences max)
<What problem they solve. Why it matters.>

## Method (5 bullets)
- <step 1>
- <step 2>
- <step 3>
- <step 4>
- <step 5>

## Datasets used

| Dataset | Size | Domain |
|---|---|---|
| ... | ... | ... |

## Metrics & headline results

| Metric | Value | Dataset |
|---|---|---|
| ... | ... | ... |

## Limitations (3 bullets, in the paper's own words)
- ...
- ...
- ...

## How it relates to our work (1 paragraph)
<Which chapter/section of OUR thesis cites this paper. What our system does differently.>

## Differences from our approach (tied to novelty claims)
- **N1** (hierarchical multimodal): ...
- **N2** (reliability-weighted fusion): ...
- **N3** (two-level output): ...
- **N4** (local-LLM refinement): ...
- **N5** (LECSEG-30 dataset): ...
- **N6** (5-metric eval + CIs): ...
- **N7** (reproducibility): ...
```

---

## Rules when filling this in

1. **Do not invent numbers.** If a value is not in the abstract or intro, write `not reported in abstract` (then come back to the PDF).
2. **Use the paper's own words for limitations.** Do not exaggerate.
3. **BibTeX key format:** `<firstauthor><year>_<shortkeyword>` — all lowercase, no spaces.
4. **Match our 5-domain focus:** if the paper is not on video/text/audio segmentation, say so in "How it relates".
