import urllib.request, json
from pathlib import Path

def ls(path):
    api = "https://api.github.com/repos/koomri/text-segmentation/contents/" + path
    with urllib.request.urlopen(api, timeout=10) as r:
        return json.loads(r.read())

def dl_text(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")

out = Path(r'G:\\THESIS\\PreThesis2_TopicSegmentation\data\benchmarks\choi_original')
out.mkdir(parents=True, exist_ok=True)

count = 0
subdirs = ls("data/choi/1")
for cond in subdirs:
    if cond["type"] != "dir":
        continue
    cond_dir = out / cond["name"]
    cond_dir.mkdir(exist_ok=True)
    files = ls("data/choi/1/" + cond["name"])
    for f in files[:50]:
        if f.get("download_url"):
            content = dl_text(f["download_url"])
            (cond_dir / f["name"]).write_text(content, encoding="utf-8")
            count += 1
    print("  " + cond["name"] + ": " + str(min(50, len(files))) + " files", flush=True)

print("Total: " + str(count) + " Choi files downloaded")
