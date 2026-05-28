import sys, json
from pathlib import Path
sys.path.insert(0, r'G:\THESIS\PreThesis2_TopicSegmentation\src')
from lecseg.preprocess.prosody import prosody_and_save

data_dir = Path(r'G:\THESIS\PreThesis2_TopicSegmentation\data')
done = {p.stem.replace('_prosody','') for p in (data_dir/'prosody').glob('*_prosody.npy')}
vids = [p.stem for p in (data_dir/'gt').glob('*.json')]
todo = [v for v in vids if v not in done]
print(f'Prosody: {len(done)}/30 done, {len(todo)} remaining', flush=True)
for v in todo:
    transcript = data_dir / 'transcripts' / v / 'transcript.json'
    sents = data_dir / 'sentences' / v / 'sentences.json'
    audio = data_dir / 'mp3' / f'{v}.mp3'
    out   = data_dir / 'prosody' / f'{v}_prosody'
    if not transcript.exists():
        print(f'  SKIP {v} (no transcript)', flush=True)
        continue
    if not sents.exists():
        print(f'  SKIP {v} (no sentences)', flush=True)
        continue
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        prosody_and_save(str(transcript), str(sents), str(out), str(audio) if audio.exists() else None)
        print(f'  OK {v}', flush=True)
    except Exception as e:
        print(f'  ERR {v}: {e}', flush=True)
print('Prosody COMPLETE', flush=True)
