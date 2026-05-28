import sys, json, subprocess, time
from pathlib import Path

root = Path(r'G:\THESIS\PreThesis2_TopicSegmentation')
data = root / 'data'

# Wait for double annotation to complete (max 30 min)
double_dir = data / 'gt_hier' / 'double'
for _ in range(360):  # 30 min
    done = list(double_dir.glob('*.json'))
    log = (double_dir / '_progress.log').read_text() if (double_dir / '_progress.log').exists() else ''
    if 'Double annotation done' in log or len(done) >= 10:
        break
    time.sleep(5)

print(f'Double annot: {len(list(double_dir.glob("*.json")))} files', flush=True)

# Run compute_iaa if we have pairs
double_files = list(double_dir.glob('*.json'))
primary_files = [data/'gt_hier'/f.name for f in double_files 
                 if (data/'gt_hier'/f.name).exists()]
print(f'IAA pairs available: {len(primary_files)}', flush=True)

if len(primary_files) >= 5:
    result = subprocess.run(
        [r'G:\THESIS\PreThesis2_TopicSegmentation\.venv\Scripts\python.exe', '-u', str(root/'scripts'/'compute_iaa.py'), '--tolerance', '1', '--verbose'],
        capture_output=True, text=True, cwd=str(root), timeout=300
    )
    print('IAA stdout:', result.stdout[-2000:] if result.stdout else '(none)', flush=True)
    print('IAA stderr:', result.stderr[-500:] if result.stderr else '(none)', flush=True)

print('Monitor DONE', flush=True)
