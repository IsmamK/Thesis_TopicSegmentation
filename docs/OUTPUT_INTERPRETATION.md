# 📈 OUTPUT INTERPRETATION — How to Read What Our Scripts Produce

**For every output file we generate, this doc tells you what to look at and what's good/bad.**

If you just want a one-shot answer for a single file, run:

```
python scripts/interpret.py <path-to-file>
```

---

## 1. `data/manifest.jsonl`

One JSON per line, one video per line. Keys: `id, domain, duration_sec, path, num_chapters`.

**What to check:**
- 30 lines.
- `domain` covers ≥ 5 distinct values.
- `sum(duration_sec) / 3600 ≥ 20` (total ≥ 20 h).

---

## 2. `data/whisper/<id>.json`

Whisper transcription output (T14). Top-level keys: `language, segments`.

**What to check:**
- `language` = `"en"` for all videos.
- `segments` length scales linearly with video duration (~1 segment per 5–10 s).
- Random-sample-read 20 sentences. They sound right.

**Red flags:**
- Many segments with confidence < 0.4 → noisy audio, consider re-running with `vad_filter=False`.
- Segments contain the same hallucinated phrase repeated → re-run with `medium` model.

---

## 3. `data/sentences/<id>.jsonl`

One sentence per line (T15). Keys: `idx, start_sec, end_sec, text, word_count`.

**What to check:**
- 200–2000 sentences per 1-h lecture.
- `start_sec` is monotonically increasing.
- Median `word_count` between 8 and 25.

---

## 4. `data/gt/<id>.json`

Ground-truth chapter timestamps (T11). Keys: `boundaries_sec, titles, num_chapters`.

**What to check:**
- 3 ≤ `num_chapters` ≤ 15.
- All `boundaries_sec` are inside `(0, video_duration)`.
- Titles are non-empty strings.

---

## 5. `data/features/<id>.parquet`

Aligned per-sentence multimodal feature matrix (T21).

**What to check (open in pandas):**
- Row count = number of sentences.
- No NaN in `text_emb` or `visual_emb` columns.
- `pause_before_sec` median between 0.2 and 1.0 s.

---

## 6. `results/<exp>/metrics.json`

Per-experiment metric summary. Schema:

```json
{
  "pk": 0.247,
  "wd": 0.291,
  "bs": 0.738,
  "tol_f1": {"precision": 0.61, "recall": 0.74, "f1": 0.67},
  "hwd": 0.310,
  "n_videos": 30,
  "exp_name": "ours-all-hier-llm",
  "git_sha": "a1b2c3d",
  "seed": 42
}
```

**Interpretation:**

| Metric | Lower better? | Strong threshold | What it means |
|---|---|---|---|
| pk | yes | < 0.30 | Random words rarely cross wrong boundaries. |
| wd | yes | < 0.30 | Strong: balanced segmentation. |
| bs | no (higher better) | > 0.65 | Strong boundary similarity. |
| tol_f1.f1 | no | > 0.65 | Strong: most boundaries within ±10 s of GT. |
| hwd | yes | < 0.35 | Good chapter+subtopic structure. |

A row that has a good `wd` but a bad `tol_f1` means the boundary count is right but each boundary is off by many seconds — investigate decoder constraints.

---

## 7. `results/<exp>/predictions.jsonl`

One record per video. Compare `pred_boundaries` against `gt_boundaries` to eyeball quality.

```json
{"video_id": "abc", "pred_boundaries": [612.4, 1230.7, ...], "gt_boundaries": [600.0, 1245.0, ...]}
```

**Pro tip:** copy a record into the Streamlit demo (T39) to see the predictions plotted on the timeline.

---

## 8. `results/ablations/master_table.csv`

The big comparison table. Columns: `method, pk_mean, pk_std, wd_mean, ...`.

**What to check:**
- The "Ours-all-hier+LLM" row beats every baseline on `wd_mean` and `hwd_mean`.
- Differences are at least 1 standard deviation (otherwise → not statistically meaningful, run T30).

---

## 9. `results/ablations/significance.csv`

Wilcoxon p-values comparing the proposed model against each baseline.

**What to check:**
- p < 0.05 next to the strongest comparison (e.g., `vs cosine_drop`).
- If p ≥ 0.05 against all baselines, the headline claim is "comparable" not "significantly better" — adjust the abstract accordingly.

---

## 10. `results/kappa/summary.md`

Inter-annotator agreement (T13). **Mean κ ≥ 0.6** is required to publish the dataset.

---

## 11. Figures (`results/figures/*.png`)

Open in any image viewer. Each figure must have:
- A descriptive filename: `fig_ablation_modalities.pdf`, `fig_kappa_per_video.pdf`, etc.
- Axis labels with units.
- A legend if more than one curve.
- High contrast (printable in B&W).

---

## 12. Streamlit demo (T39)

Output is a live web page. Smoke-test:
- Pasting a known YouTube URL returns a chapter list.
- Clicking a chapter timestamp jumps the embedded video to that second.
- Confidence bars next to each boundary are between 0 and 1.

---

## When you don't recognise an output file

1. Run `python scripts/interpret.py <path>` for an explanation.
2. Check the task that produced it: filename usually starts with the task ID.
3. Ask Claude: paste the file's first 20 lines + the task ID.
