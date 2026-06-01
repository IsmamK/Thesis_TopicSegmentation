import sys, os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
sys.path.insert(0, "src")
from lecseg.features.text_embeddings import embed_all

print("Computing e5large embeddings...")
r = embed_all(model="e5large", force=False)
print(f"Done: {len(r)} videos embedded")
for vid, shape in sorted(r.items()):
    print(f"  {vid}: {shape}")
