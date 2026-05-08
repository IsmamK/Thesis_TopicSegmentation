# T43 — Model Release on Hugging Face

**Phase 10 · Deliverables · Estimated time: 0.5 day · Owner: Ismam**

---

## 🎯 What you are doing
Uploading our best fine-tuned checkpoint to Hugging Face Hub, so anyone can `from_pretrained` and use the model without retraining. Supports N7 (reproducibility).

## ✅ How to know you are done
- Hugging Face repo `<org>/lecseg-base` exists and is public.
- A short Model Card is published.
- Loading it with `transformers`/`sentence_transformers` works in a fresh Colab.

---

## 📝 Steps

### Step 1 — Sign in to Hugging Face

```
pip install huggingface_hub
hf auth login     # paste an access token from https://huggingface.co/settings/tokens
```

### Step 2 — Upload

> Execute T43. Write `scripts/upload_model.py` that:
> 1. Loads the best checkpoint from `results/<best_exp>/checkpoints/best.pt`.
> 2. Exports tokenizer + encoder weights to `models/lecseg-base/`.
> 3. Writes a MODEL_CARD.md describing: training data (LECSEG-30), metrics on LECSEG-30 test fold, intended use, known limitations.
> 4. Uploads: `huggingface_hub.HfApi().create_repo(...)` + `upload_folder(...)`.

### Step 3 — Smoke test on Colab

Paste in a fresh Colab:
```python
!pip install sentence-transformers
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("<your-hf-user>/lecseg-base")
print(m.encode(["hello world"]).shape)
```

Should print `(1, 768)` or similar.

---

## ➡️ When done

```
python scripts/mark_done.py T43
python scripts/today.py
```
