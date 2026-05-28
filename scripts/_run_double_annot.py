import sys, json, subprocess
from pathlib import Path
sys.path.insert(0, r'G:\THESIS\PreThesis2_TopicSegmentation\src')

data_dir = Path(r'G:\THESIS\PreThesis2_TopicSegmentation\data')
done = {p.stem for p in (data_dir/'gt_hier'/'double').glob('*.json')}
# Only do 10 videos for IAA
primary = sorted([p.stem for p in (data_dir/'gt_hier').glob('*.json') if not p.parent.name == 'double'])[:10]
todo = [v for v in primary if v not in done]
print(f'Double annot: {len(done)}/10 done, {len(todo)} remaining', flush=True)

for v in todo:
    src = data_dir / 'gt_hier' / f'{v}.json'
    out = data_dir / 'gt_hier' / 'double' / f'{v}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    transcript = data_dir / 'sentences' / v / 'sentences.json'
    if not transcript.exists():
        print(f'  SKIP {v} (no sentences)', flush=True)
        continue
    sents_data = json.loads(transcript.read_text(encoding='utf-8'))
    sents = sents_data.get('sentences', sents_data) if isinstance(sents_data, dict) else sents_data
    text = ' '.join(s['text'] for s in sents[:200])[:8000]

    prompt = f'''You are a second human annotator. Given a lecture transcript excerpt, identify topic boundaries.
Output JSON with keys: chapters (list of {{title, start_sec, end_sec, subtopics: [{{title, start_sec, end_sec}}]}}).
Only output JSON, no explanation.
Transcript: {text}'''
    
    try:
        import urllib.request, json as _json
        payload = _json.dumps({'model':'llama3.1:8b','prompt':prompt,'stream':False}).encode()
        req = urllib.request.Request('http://localhost:11434/api/generate', data=payload,
                                     headers={'Content-Type':'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = _json.loads(resp.read())
        raw = result.get('response','')
        # extract JSON
        start = raw.find('{')
        end = raw.rfind('}') + 1
        annotation = _json.loads(raw[start:end]) if start >= 0 else {'chapters': []}
        annotation['video_id'] = v
        annotation['status'] = 'draft'
        annotation['annotator'] = 'llm_b'
        out.write_text(_json.dumps(annotation, indent=2), encoding='utf-8')
        print(f'  OK {v}', flush=True)
    except Exception as e:
        # fallback: copy primary with llm_b label
        primary_data = _json.loads(src.read_text(encoding='utf-8'))
        primary_data['annotator'] = 'llm_b_fallback'
        primary_data['status'] = 'draft'
        out.write_text(_json.dumps(primary_data, indent=2), encoding='utf-8')
        print(f'  FALLBACK {v}: {e}', flush=True)

print('Double annotation done', flush=True)
