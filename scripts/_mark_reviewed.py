import json
from pathlib import Path

gt_hier = Path(r'G:\\THESIS\\PreThesis2_TopicSegmentation') / "data" / "gt_hier"
updated = 0
for f in gt_hier.glob("*.json"):
    if f.name == "iaa_report.json":
        continue
    data = json.loads(f.read_text(encoding="utf-8"))
    if data.get("status") != "reviewed":
        data["status"] = "reviewed"
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        updated += 1
print(f"Marked {updated} annotations as reviewed")
