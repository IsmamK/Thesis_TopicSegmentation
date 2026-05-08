# T20 — Visual Embeddings (CLIP on Keyframes)

**Phase 5 · Features · Estimated time: 2 h · Owner: Ismam**

---

## 🎯 What you are doing
Running CLIP (a joint image-text model) on every shot's keyframe, producing a visual vector per shot. When the visual vector changes a lot between shots, the scene has likely shifted.

## ✅ How to know you are done
- `data/emb_visual/<video_id>.npy` exists for all 30 videos.
- Shape: `(n_shots, 512)` or `(n_shots, 768)` depending on CLIP model.

---

## 📝 Steps

### Ask Claude

> Execute T20. Write `src/lecseg/features/visual_emb.py` and `scripts/embed_visual.py`.
>
> Use `open_clip` (`ViT-B-32`, `laion2b_s34b_b79k` pretrained) or HuggingFace `openai/clip-vit-base-patch32`.
>
> For each video:
> 1. Use keyframes from `data/raw/<id>/keyframes/` (cached in T17).
> 2. For each keyframe, run CLIP image encoder → 512-dim vector.
> 3. Stack into shape `(n_shots, 512)`; save as `.npy`.
>
> Batch size 64 on GPU, 8 on CPU.

### Verify

```
python -c "import numpy as np; x = np.load('data/emb_visual/<id>.npy'); print(x.shape)"
```

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **CLIP** | OpenAI's "Contrastive Language-Image Pretraining". Maps images and text into the same vector space. |
| **Keyframe** | One representative frame per shot. From T17. |
| **Vector space** | A high-dimensional space where semantic similarity is distance. |

More: [docs/CONCEPTS.md#visual-embeddings](../docs/CONCEPTS.md#visual-embeddings)

---

## ➡️ When done

```
python scripts/mark_done.py T20
python scripts/today.py
```
