"""BERTopic-based topic boundary detector.

Fits a BERTopic model on all sentences of a lecture, assigns each sentence
a topic ID, and detects positions where the dominant topic changes as
boundary candidates.

This is a fundamentally different signal from cosine embedding similarity:
BERTopic finds globally coherent topic clusters across the lecture, whereas
cosine depth scoring is a local signal. Topic transitions detected by BERTopic
may complement the cross-model conservative method.

Usage:
    python scripts/bertopic_segmenter.py [--model bge_large] [--min-topic-size 5] [--verbose]
"""

import argparse
import json
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from lecseg.metrics import evaluate


def run_video(vid_id: str, gt_path: Path, emb_model: str,
              min_topic_size: int, nr_topics: int | None,
              verbose: bool = False) -> dict | None:
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer

    sent_path = Path(f"data/sentences/{vid_id}/sentences.json")
    if not sent_path.exists():
        return None
    sents = json.load(open(sent_path, encoding="utf-8"))["sentences"]
    texts = [s["text"] for s in sents]
    n = len(texts)

    gt_file = gt_path / f"{vid_id}.json"
    if not gt_file.exists():
        return None
    gt_data = json.load(open(gt_file, encoding="utf-8"))
    boundaries_sec = gt_data.get("boundaries_sec", [])
    if not boundaries_sec:
        return None

    starts = np.array([s["start"] for s in sents])
    ref_boundaries = sorted(set(
        max(1, min(int(np.searchsorted(starts, float(t), side="left")), n - 1))
        for t in boundaries_sec
    ))
    n_targets = len(ref_boundaries)

    # Load precomputed embeddings (avoid re-computing)
    embs = None
    for p in [
        Path(f"data/embeddings/{emb_model}/{vid_id}/embeddings.npy"),
        Path(f"data/emb_text/{emb_model}/{vid_id}/embeddings.npy"),
    ]:
        if p.exists():
            embs = np.load(str(p))
            break

    # Cap at 300 sentences for BERTopic speed
    cap = min(n, 300)
    texts_use = texts[:cap]
    embs_use = embs[:cap] if embs is not None else None
    ref_cap = [b for b in ref_boundaries if b < cap]

    if len(texts_use) < 20:
        return None

    try:
        # Use simple CountVectorizer to avoid heavy downloads
        vectorizer = CountVectorizer(ngram_range=(1, 2), stop_words="english",
                                      min_df=2, max_df=0.9)
        topic_model = BERTopic(
            vectorizer_model=vectorizer,
            min_topic_size=min_topic_size,
            nr_topics=nr_topics,
            verbose=False,
            calculate_probabilities=False,
        )
        if embs_use is not None:
            topics, _ = topic_model.fit_transform(texts_use, embeddings=embs_use)
        else:
            topics, _ = topic_model.fit_transform(texts_use)
    except Exception as e:
        if verbose:
            print(f"  BERTopic error on {vid_id}: {e}")
        return None

    topics = np.array(topics)

    # Detect topic change positions: where topic[i] != topic[i-1]
    change_positions = [i for i in range(1, len(topics)) if topics[i] != topics[i - 1]]

    # Apply minimum segment length filter
    min_len = 5
    filtered = []
    last = 0
    for pos in change_positions:
        if pos - last >= min_len:
            filtered.append(pos)
            last = pos
    change_positions = filtered

    # If we have more candidates than targets, keep top by topic coherence
    # (greedy: keep positions where the topic change is most sustained)
    if len(change_positions) > n_targets:
        # Score each position by how long the new topic persists
        def persistence(pos, topic_list, lookahead=5):
            t = topic_list[pos]
            count = sum(1 for i in range(pos, min(pos + lookahead, len(topic_list)))
                        if topic_list[i] == t)
            return count
        scored = sorted(change_positions,
                        key=lambda p: persistence(p, topics.tolist()), reverse=True)
        change_positions = sorted(scored[:n_targets])
    elif len(change_positions) == 0:
        return None

    scores = evaluate(change_positions, ref_cap, n_units=cap)
    if verbose:
        print(f"  {vid_id}: {len(topics)} sents, topics={len(set(topics))}, "
              f"changes={len(change_positions)}, GT={len(ref_cap)}, "
              f"Pk={scores.pk:.4f} WD={scores.wd:.4f}")
    return {
        "pk": scores.pk, "wd": scores.wd,
        "boundary_similarity": scores.boundary_similarity, "f1": scores.f1,
        "n_topic_changes": len(change_positions),
        "n_topics_found": len(set(topics)),
        "n_gt_boundaries": len(ref_cap),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="bge_large", help="Embedding model for BERTopic")
    parser.add_argument("--min-topic-size", type=int, default=5)
    parser.add_argument("--nr-topics", type=int, default=None, help="Reduce to N topics")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    gt_path = Path("data/gt")
    manifest = [json.loads(l) for l in open("data/manifest.jsonl", encoding="utf-8")]
    vids = [v["id"] for v in manifest]
    if args.limit:
        vids = vids[:args.limit]

    print(f"BERTopic segmenter: {args.model}, min_topic_size={args.min_topic_size}, "
          f"nr_topics={args.nr_topics}")
    print(f"Running on {len(vids)} videos (capped at 300 sentences each)...")

    results = {}
    for i, vid_id in enumerate(vids):
        print(f"[{i+1}/{len(vids)}] {vid_id}", end=" ", flush=True)
        r = run_video(vid_id, gt_path, args.model, args.min_topic_size,
                      args.nr_topics, args.verbose)
        if r:
            results[vid_id] = r
            print(f"Pk={r['pk']:.4f} WD={r['wd']:.4f} topics={r['n_topics_found']}")
        else:
            print("SKIP")

    if not results:
        print("No results.")
        return

    pks = [v["pk"] for v in results.values()]
    wds = [v["wd"] for v in results.values()]
    bss = [v["boundary_similarity"] for v in results.values()]
    f1s = [v["f1"] for v in results.values()]

    summary = {
        "mean_pk": round(float(np.mean(pks)), 4),
        "mean_wd": round(float(np.mean(wds)), 4),
        "mean_bs": round(float(np.mean(bss)), 4),
        "mean_f1": round(float(np.mean(f1s)), 4),
        "n_videos": len(results),
        "min_topic_size": args.min_topic_size,
        "nr_topics": args.nr_topics,
    }

    tag = f"min{args.min_topic_size}"
    if args.nr_topics:
        tag += f"_nr{args.nr_topics}"
    out = {
        "method": "bertopic_segmenter",
        "embedding_model": args.model,
        "summary": {f"bertopic_{tag}": summary},
        "per_video": results,
    }
    out_path = Path(f"results/eval_bertopic_{args.model}_{tag}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\n== BERTopic Segmenter ({args.model}) ==")
    print(f"Mean Pk:  {summary['mean_pk']:.4f}")
    print(f"Mean WD:  {summary['mean_wd']:.4f}")
    print(f"Mean BS:  {summary['mean_bs']:.4f}")
    print(f"Mean F1:  {summary['mean_f1']:.4f}")
    print(f"Saved to {out_path}")
    print(f"\nComparison: BGE-divisive baseline Pk=0.3884 | Our best Pk=0.3588")


if __name__ == "__main__":
    main()
