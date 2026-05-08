# T42 — Dataset Release on Zenodo

**Phase 10 · Deliverables · Estimated time: 0.5 day · Owner: Fahmida**

---

## 🎯 What you are doing
Packaging LECSEG-30 (URLs, metadata, ground-truth timestamps, annotation guidelines) as a public Zenodo dataset with a DOI. **This is the artefact behind novelty N5.**

## ⚠️ What we do NOT release
- The actual video files (YouTube terms of service forbid redistribution).
- The audio files.
- Transcripts, if those contain copyrighted text.

We release **URLs + metadata + GT + code to reproduce**.

## ✅ How to know you are done
- A Zenodo DOI exists for LECSEG-30.
- The download ZIP contains: `video_list.csv`, `gt/`, `gt_hier/`, `README.md`, `LICENSE.md`, `annotation_guidelines.md`, `reproduce.md`.

---

## 📝 Steps

### Step 1 — Prepare the package

> Execute T42. Write `scripts/package_dataset.py` that:
> 1. Copies `data/video_list.csv`, `data/gt/`, `data/gt_hier/` into `data/release/LECSEG-30/`.
> 2. Writes a `README.md` inside it with: contents, how to reproduce (run `python scripts/download_all.py` after cloning the codebase), κ value, domains, licence (CC-BY-4.0).
> 3. Writes a `LICENSE.md`.
> 4. Zips the folder to `data/release/LECSEG-30-v1.0.zip`.

### Step 2 — Upload to Zenodo

1. Go to https://zenodo.org/ → log in with ORCID.
2. Click "New upload".
3. Upload `data/release/LECSEG-30-v1.0.zip`.
4. Fill in: Title = "LECSEG-30: A hierarchical multimodal lecture-video segmentation dataset"; Authors = our team; Description = copy from `README.md`; Keywords = topic segmentation, lecture videos, multimodal; Licence = CC-BY-4.0; Related identifier = GitHub repo.
5. Publish.

Zenodo gives you a DOI. Copy it into:
- `README.md` (root)
- `thesis/chapters/chapter3_methodology.tex`
- `paper/ieee.tex`

### Verify

Search Zenodo for "LECSEG-30". Your record should appear within 30 min.

---

## ➡️ When done

```
python scripts/mark_done.py T42
python scripts/today.py
```
