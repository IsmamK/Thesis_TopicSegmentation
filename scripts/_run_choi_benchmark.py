import sys, json, random
import numpy as np
sys.path.insert(0, r'G:\THESIS\PreThesis2_TopicSegmentation\src')

from lecseg.baselines.classical import texttiling, c99
from lecseg.baselines.neural import cosine_seg, bert_seg
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.features.text_embeddings import embed_sentences
from lecseg.metrics import evaluate

docs = json.loads(open(r'G:\THESIS\PreThesis2_TopicSegmentation\data\benchmarks\choi_synthetic.json', encoding='utf-8').read())

methods = {
    'texttiling': lambda sents, vecs, k: texttiling(sents, ),
    'c99':        lambda sents, vecs, k: c99(sents, n_segments=k),
    'cosine':     lambda sents, vecs, k: cosine_seg(vecs, n_segments=k),
    'bert_seg':   lambda sents, vecs, k: bert_seg(vecs, n_segments=k),
    'two_stage':  lambda sents, vecs, k: TwoStageBoundaryPredictor().predict(vecs, n_segments=k),
}

results = {m: [] for m in methods}

for i, doc in enumerate(docs):
    # Flatten segments to sentence list + true boundaries
    sents = []
    true_bounds = []
    for seg in doc:
        true_bounds.append(len(sents))  # start of each segment
        sents.extend(seg)
    ref_boundaries = true_bounds[1:]  # skip first (=0)
    N = len(sents)
    if N < 5:
        continue

    # Embed
    vecs = embed_sentences(sents, model='mpnet')
    k = len(doc)

    for mname, mfunc in methods.items():
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FT
            with ThreadPoolExecutor(1) as ex:
                fut = ex.submit(mfunc, sents, vecs, k)
                hyp = fut.result(timeout=30)
            scores = evaluate(hyp, ref_boundaries, n_units=N)
            results[mname].append(scores.as_dict())
        except Exception as e:
            pass

    if (i+1) % 10 == 0:
        print(f'  {i+1}/100 docs done', flush=True)

print('\n=== CHOI SYNTHETIC BENCHMARK (100 docs) ===')
print(f'{"Method":<12} {"Pk":>8} {"WD":>8}  (lower=better)')
print('-' * 32)
for mname, scores_list in results.items():
    if not scores_list:
        print(f'{mname:<12} {"TIMEOUT":>8}')
        continue
    pk = sum(s['pk'] for s in scores_list) / len(scores_list)
    wd = sum(s['wd'] for s in scores_list) / len(scores_list)
    print(f'{mname:<12} {pk:>8.4f} {wd:>8.4f}')
print()
print('Published Choi 2000 numbers (on Choi synthetic, 3-11 segs):')
print('  c99:        Pk ~0.12')
print('  texttiling: Pk ~0.46')
print()

# Save
import pathlib
out = pathlib.Path(r'G:\THESIS\PreThesis2_TopicSegmentation\results\eval_choi_benchmark.json')
out.write_text(json.dumps({'results': {m: v for m,v in results.items()}, 'n_docs': 100}, indent=2), encoding='utf-8')
print('Saved to', out)
