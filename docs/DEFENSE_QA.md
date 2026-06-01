# 🎓 DEFENSE Q&A

**This file is built in T45. It will contain 50+ rehearsed Q&A pairs.**

Each pair follows the format:

```
## Q: <Panel question>

**A (60 sec version):** <Your answer — concise, cite a number>

**A (extended, if pressed):** <Two-paragraph follow-up>

**Trap to avoid:** <What not to say>
```

---

## Category 1: Motivation & scope

## Q: Why lecture videos specifically? Why not general video segmentation?

**A (60 sec):** Lectures have unique structure — topics change at predictable
semantic boundaries, slides reset visual context, and speech contains prosodic
cues like pause length and pitch reset that signal transitions. General video
segmentation methods optimise for shot cuts and action changes, which are rare
in lectures. We exploit the domain-specific multimodal structure explicitly,
which is why our fusion module weights modalities by their reliability on the
specific input (e.g., chalkboard vs.\ slide-based lectures).

**Trap to avoid:** Don't say "lectures are easier". They are harder in some
ways — fewer visual events, heavily overlapping topics, disfluency in speech.

---

## Category 2: Dataset

## Q: 30 videos — isn't that too small to draw conclusions?

**A (60 sec):** Segmentation benchmarks are almost uniformly small: Wiki-727K
uses text only, and the standard lecture/meeting corpora (AMI, ICSI) have fewer
than 50 recordings at the segment level. We replicate the evaluation protocol
of the strongest prior works on their own benchmark sizes. We additionally
report 5-fold cross-validation (not a single split), bootstrap 95% CIs, and
paired Wilcoxon tests — so our confidence intervals account for the small
sample explicitly.

**Trap to avoid:** Don't say "30 is enough". Say "30 matches prior work;
our uncertainty quantification is honest about it".

---

## Category 3: Evaluation

## Q: Pk and WindowDiff are old metrics — why use them?

**A (60 sec):** They are the standard in the segmentation community for
15+ years, which means our numbers can be directly compared to every prior
work. We also add Boundary Similarity (Fournier 2013), tolerance-F1, and our
new hierarchical WindowDiff — so reviewers who dislike Pk can look at the
other four metrics and reach the same conclusion.

---

## Category 4: Novel contributions

## Q: How does the reliability-weighted fusion differ from attention?

**A (60 sec):** Attention learns to up-weight informative positions globally
across training data. Our reliability score is computed locally from the
input's own statistics at test time — SNR proxy for ASR, OCR confidence for
the visual stream — without any training on those reliability signals. This
means it adapts to a chalkboard video that was never seen during training.

---

## Category 5: LLM refinement

## Q: Why not just use GPT-4 for the whole thing?

**A (60 sec):** Three reasons: (1) reproducibility — a closed API changes
without notice and cannot be re-run offline; (2) cost — 30 videos × repeated
experiments would incur significant API spend; (3) data privacy — lecture
content from universities may be sensitive. A local 8B model with zero API
calls satisfies all three constraints. In the current thesis we present it as an
implemented refinement and titling module, while avoiding unsupported claims
about large boundary-metric gains.

---

## [Fill remaining Q&A pairs in T45]

See `docs/DEFENSE_PREP.md` for the six question categories and the suggested
50-question coverage list.
