import sys
sys.path.insert(0, r'G:\THESIS\PreThesis2_TopicSegmentation\src')
from lecseg.preprocess.shot_detection import detect_and_save
from pathlib import Path

missing = ['jGwO_UgTS7I', 'lUUte2o2Sn8', 'NK-BxowMIfg']
for vid_id in missing:
    video = rf'G:\THESIS\PreThesis2_TopicSegmentation\data\raw\{vid_id}\video.mp4'
    out = rf'G:\THESIS\PreThesis2_TopicSegmentation\data\shots\{vid_id}_shots.json'
    shots = detect_and_save(video, out)
    print(f'{vid_id}: {len(shots)} shots -> {out}')
