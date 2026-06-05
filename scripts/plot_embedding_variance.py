"""Plot sentence-to-sentence cosine similarity variance per domain.

Shows why Mathematics domain has flat embedding landscape (equation verbalization),
making boundary detection harder. Saves figure to figures/embedding_variance.pdf
and a summary JSON to results/embedding_variance.json.
"""

import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

MANIFEST = Path("data/manifest.jsonl")
EMB_DIR = Path("data/embeddings/bge_large")  # use best embedding model
OUT_FIG = Path("figures/embedding_variance.pdf")
OUT_JSON = Path("results/embedding_variance.json")

DOMAIN_COLORS = {
    "BIOLOGY": "#2196F3",
    "CS": "#4CAF50",
    "MATH": "#F44336",
    "PHILOSOPHY": "#9C27B0",
    "PHYSICS": "#FF9800",
}

def cosine_sim(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def load_embeddings(vid_id):
    p = EMB_DIR / vid_id / "embeddings.npy"
    if p.exists():
        return np.load(str(p))
    # fallback: try other common paths
    for alt in [
        Path("data/emb_text") / "bge_large" / vid_id / "embeddings.npy",
        Path("data/embeddings") / "bge" / vid_id / "embeddings.npy",
    ]:
        if alt.exists():
            return np.load(str(alt))
    return None


def consecutive_cosine_similarities(embs):
    sims = []
    for i in range(1, len(embs)):
        sims.append(cosine_sim(embs[i - 1], embs[i]))
    return np.array(sims)


def main():
    manifest = [json.loads(l) for l in open(MANIFEST)]

    domain_stats = {}  # domain -> list of per-video std-dev values
    domain_sims = {}   # domain -> all consecutive similarities

    for v in manifest:
        vid_id = v["id"]
        domain = v.get("domain", "UNKNOWN")
        embs = load_embeddings(vid_id)
        if embs is None or len(embs) < 5:
            print(f"  SKIP {vid_id} — no embeddings found")
            continue
        sims = consecutive_cosine_similarities(embs)
        domain_stats.setdefault(domain, []).append(float(np.std(sims)))
        domain_sims.setdefault(domain, []).extend(sims.tolist())

    # ── Figure 1: Box plot of sim-variance per domain ──────────────────────
    domains_ordered = ["MATH", "BIOLOGY", "CS", "PHILOSOPHY", "PHYSICS"]
    domains_ordered = [d for d in domains_ordered if d in domain_stats]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("Sentence Embedding Similarity: Domain Analysis\n"
                 "(BGE-large model, consecutive sentence pairs)", fontsize=12)

    # Left: box plot of per-video std-dev
    ax = axes[0]
    data = [domain_stats[d] for d in domains_ordered]
    bp = ax.boxplot(data, patch_artist=True, medianprops={"color": "black", "lw": 2})
    for patch, d in zip(bp["boxes"], domains_ordered):
        patch.set_facecolor(DOMAIN_COLORS.get(d, "#888"))
        patch.set_alpha(0.75)
    ax.set_xticks(range(1, len(domains_ordered) + 1))
    ax.set_xticklabels(domains_ordered, fontsize=10)
    ax.set_ylabel("Std-dev of consecutive cosine similarities", fontsize=9)
    ax.set_title("Embedding Variance Per Domain\n(higher = more discriminative boundary signal)", fontsize=10)
    ax.axhline(np.mean([v for vals in domain_stats.values() for v in vals]),
               color="grey", linestyle="--", linewidth=1, label="overall mean")
    ax.legend(fontsize=8)

    # Right: violin plot of all consecutive similarities per domain
    ax2 = axes[1]
    data2 = [domain_sims[d] for d in domains_ordered]
    vp = ax2.violinplot(data2, positions=range(1, len(domains_ordered) + 1),
                        showmedians=True, showextrema=False)
    for i, (body, d) in enumerate(zip(vp["bodies"], domains_ordered)):
        body.set_facecolor(DOMAIN_COLORS.get(d, "#888"))
        body.set_alpha(0.7)
    ax2.set_xticks(range(1, len(domains_ordered) + 1))
    ax2.set_xticklabels(domains_ordered, fontsize=10)
    ax2.set_ylabel("Consecutive cosine similarity", fontsize=9)
    ax2.set_title("Distribution of Consecutive Similarities\n(MATH flat = low boundary discriminability)", fontsize=10)

    plt.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(OUT_FIG), bbox_inches="tight", dpi=150)
    print(f"Saved figure to {OUT_FIG}")

    # ── Summary JSON ────────────────────────────────────────────────────────
    summary = {}
    for d in domains_ordered:
        vals = domain_stats[d]
        sims = domain_sims[d]
        summary[d] = {
            "n_videos": len(vals),
            "mean_std_sim": round(float(np.mean(vals)), 5),
            "median_std_sim": round(float(np.median(vals)), 5),
            "mean_consecutive_sim": round(float(np.mean(sims)), 5),
            "std_consecutive_sim": round(float(np.std(sims)), 5),
        }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary to {OUT_JSON}")

    print("\n== Domain Embedding Variance Summary ==")
    print(f"{'Domain':<12} {'mean_std':>10} {'mean_sim':>10} {'std_sim':>10} {'Interpretation'}")
    print("-" * 65)
    for d, s in sorted(summary.items(), key=lambda x: x[1]["mean_std_sim"]):
        flag = " ← FLAT" if s["mean_std_sim"] < 0.04 else ""
        print(f"{d:<12} {s['mean_std_sim']:>10.5f} {s['mean_consecutive_sim']:>10.5f} "
              f"{s['std_consecutive_sim']:>10.5f}{flag}")


def plot_domain_performance():
    """Also plot domain Pk performance vs chapter density — the real Math failure diagnosis."""
    import json
    dp_path = Path("results/domain_performance_analysis.json")
    if not dp_path.exists():
        return
    d = json.load(open(dp_path))
    rows = d["rows"]

    domains = [r["domain"] for r in rows]
    baseline_pk = [r["baseline"]["pk"] for r in rows]
    selector_pk = [r["selector"]["pk"] for r in rows]
    n_videos = [r["n_videos"] for r in rows]
    avg_chaps = [r["n_chapters"] / r["n_videos"] for r in rows]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("Domain-Level Failure Analysis", fontsize=12)

    # Left: Pk comparison per domain
    ax = axes[0]
    x = np.arange(len(domains))
    w = 0.35
    bars1 = ax.bar(x - w/2, baseline_pk, w, label="BGE-divisive baseline",
                   color=[DOMAIN_COLORS.get(d, "#888") for d in domains], alpha=0.5)
    bars2 = ax.bar(x + w/2, selector_pk, w, label="Balanced selector",
                   color=[DOMAIN_COLORS.get(d, "#888") for d in domains], alpha=0.9)
    ax.axhline(0.367, color="black", linestyle="--", linewidth=1.2, label="TreeSeg (TinyRec, indicative)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{d}\n(n={n})" for d, n in zip(domains, n_videos)], fontsize=8)
    ax.set_ylabel("Pk (lower is better)", fontsize=9)
    ax.set_title("Pk Per Domain: Baseline vs Selector\n(MATH: selector hurts)", fontsize=10)
    ax.legend(fontsize=7)
    ax.set_ylim(0.25, 0.50)
    # annotate MATH failure
    math_idx = domains.index("MATH") if "MATH" in domains else -1
    if math_idx >= 0:
        ax.annotate("Selector\nhurts here",
                    xy=(math_idx + w/2, selector_pk[math_idx]),
                    xytext=(math_idx + 0.6, selector_pk[math_idx] + 0.03),
                    arrowprops=dict(arrowstyle="->", color="red"),
                    fontsize=8, color="red")

    # Right: n_videos per domain (root cause of LOO instability)
    ax2 = axes[1]
    colors = [DOMAIN_COLORS.get(d, "#888") for d in domains]
    bars = ax2.bar(domains, n_videos, color=colors, alpha=0.8)
    ax2.axhline(5, color="orange", linestyle="--", linewidth=1.2, label="Min recommended n=5")
    ax2.set_ylabel("Number of videos", fontsize=9)
    ax2.set_title("Videos Per Domain\n(MATH n=4: insufficient LOO training signal)", fontsize=10)
    ax2.legend(fontsize=8)
    for bar, n in zip(bars, n_videos):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.05,
                 str(n), ha="center", va="bottom", fontsize=11, fontweight="bold")

    plt.tight_layout()
    out = Path("figures/domain_failure_analysis.pdf")
    plt.savefig(str(out), bbox_inches="tight", dpi=150)
    print(f"Saved domain failure figure to {out}")


if __name__ == "__main__":
    main()
    plot_domain_performance()
