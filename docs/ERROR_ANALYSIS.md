# ERROR ANALYSIS

This file summarizes the main error patterns observed in the LECSEG runs. The
current best Pk/WD method is conservative, so many errors are false negatives
or near misses rather than obvious over-segmentation.

## Error Taxonomy

| ID | Error type | When it occurs | Main cause |
|---|---|---|---|
| E1 | Boundary merge | Several gold topics are merged | Conservative boundary selection and weak local contrast |
| E2 | Over-segmentation | False boundary inside one topic | Transition phrases or noisy gap spikes |
| E3 | Auxiliary signal mismatch | Shot/OCR/prosody does not align with semantic boundary | Flat slides, whiteboard use, noisy OCR, weak prosody |
| E4 | Title drift | Generated title names an example instead of the concept | Local LLM lacks domain context |

## E1 - Boundary Merge

The model merges adjacent gold segments when vocabulary remains similar across
a conceptual transition. This is common in technical lectures where a definition,
example, and derivation reuse the same terms. The best Pk/WD method intentionally
predicts fewer boundaries, so E1 is the dominant failure mode.

Mitigation: supervised candidate ranking with a high-recall candidate pool,
followed by non-max suppression and minimum-duration constraints.

## E2 - Over-Segmentation

False boundaries occur when a speaker uses transition language inside a single
topic, for example "now let us look deeper" before continuing the same concept.
Prosody can amplify this by adding pause or pitch-reset signals.

Mitigation: require agreement between semantic contrast and auxiliary cues, or
calibrate auxiliary weights per video.

## E3 - Auxiliary Signal Mismatch

Shot, OCR, and prosody features are available for all videos, but current
ablations show they do not automatically improve Pk/WD. In slide-light or
whiteboard-heavy lectures, visual changes are sparse. In dense technical
lectures, OCR and transcript terms can remain stable across real topic changes.

Mitigation: use auxiliary modalities as candidate features for a ranker, not as
blind additive fusion terms.

## E4 - Title Drift

The local LLM can generate titles that summarize an example rather than the
underlying concept. This mainly affects usability and presentation quality, not
boundary metrics.

Mitigation: constrain title prompts to prefer terms repeated in the segment and
validate titles separately from boundary scores.

## Reproduction

Primary files:

- `results/error_analysis.json`
- `results/eval_bge.json`
- `results/eval_bgelarge_fine2.json`
- `results/oracle_k_experiment.json`

The main conclusion is that boundary scoring/ranking, not segment-count
selection, is the central bottleneck.
