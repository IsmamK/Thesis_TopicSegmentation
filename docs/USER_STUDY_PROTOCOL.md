# User Study Protocol: Does LECSEG Improve Lecture Navigation?

Purpose: test whether generated chapters help real users find lecture content faster and more accurately.

## Participants

- Target: 10-15 undergraduate students.
- Basic familiarity with online lecture videos is enough.
- No machine learning knowledge required.

## Materials

- 5 lecture clips or full lectures from LECSEG-30.
- For each video, prepare 2-3 search tasks such as:
  - "Find where the lecturer starts explaining eigenvalues."
  - "Find the section where the example problem begins."
  - "Find the point where the lecture moves from definitions to applications."

## Conditions

| Condition | Description |
|---|---|
| No chapters | Standard video scrubber only |
| YouTube chapters | Creator-provided chapters |
| LECSEG chapters | System-generated chapters |

Use counterbalancing so the same participant does not always see the same condition first.

## Measurements

| Measure | Meaning |
|---|---|
| Success rate | Whether the participant found the correct section |
| Time to find | Seconds from task start to answer |
| Confidence rating | 1-5 self-rated confidence |
| Usefulness rating | 1-5 perceived usefulness |
| Preference | Which navigation aid they preferred |

## Output Table

| Condition | Success rate | Median time | Mean usefulness | Notes |
|---|---:|---:|---:|---|
| No chapters | TBD | TBD | TBD | Baseline |
| YouTube chapters | TBD | TBD | TBD | Human creator reference |
| LECSEG chapters | TBD | TBD | TBD | System output |

## Interpretation Rules

- If LECSEG beats no-chapters but not YouTube chapters, the system is useful but below human creator metadata.
- If LECSEG approaches YouTube chapters, it is a strong deployment argument.
- If LECSEG performs poorly, keep it as a research benchmark and improve boundary/title quality before deployment.

## Evidence Files to Produce

- `results/user_study_raw.csv`
- `results/user_study_summary.json`
- `docs/USER_STUDY_RESULTS.md`

## Defense Sentence

"Automatic segmentation metrics evaluate boundary quality, but a user study is needed to prove navigation usefulness. The study protocol compares no chapters, creator chapters, and LECSEG-generated chapters on concrete search tasks."
