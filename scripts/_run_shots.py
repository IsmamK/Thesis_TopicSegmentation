import sys, json, time
from pathlib import Path
sys.path.insert(0, r'G:\THESIS\PreThesis2_TopicSegmentation\src')
from lecseg.preprocess.shot_detection import detect_and_save

data = Path(r'G:\THESIS\PreThesis2_TopicSegmentation\data')
done = {p.stem.replace('_shots','') for p in (data/'shots').glob('*_shots.json')}
vids = [p.name for p in (data/'raw').iterdir() if p.is_dir()]
todo = [v for v in sorted(vids) if v not in done]
print(f'Shot detection: {len(done)}/30 done, {len(todo)} remaining', flush=True)

for v in todo:
    mp4 = data/'raw'/v/'video.mp4'
    out = data/'shots'/f'{v}_shots.json'
    if not mp4.exists():
        print(f'  SKIP {v} (no mp4)', flush=True)
        continue
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        shots = detect_and_save(str(mp4), str(out))
        print(f'  OK {v}: {len(shots)} shots in {time.time()-t0:.0f}s', flush=True)
    except Exception as e:
        print(f'  ERR {v}: {e}', flush=True)

print('Shot detection COMPLETE', flush=True)
