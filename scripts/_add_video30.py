import openpyxl, shutil, tempfile
from pathlib import Path

src = Path("data/video_list.csv")
tmp = Path(tempfile.mktemp(suffix=".xlsx"))
shutil.copy(src, tmp)

wb = openpyxl.load_workbook(str(tmp), data_only=True)
ws = wb.active

new_row = (
    "https://www.youtube.com/watch?v=HtSuA80QTyo",
    "CS",
    "Lecture 1: Algorithmic Thinking, Peak Finding",
    "Erik Demaine",
    "ENGLISH",
    54,
    9,
    "MIT OpenCourseWare",
    "MIT 6.006 Introduction to Algorithms, Fall 2011.",
)
ws.append(new_row)
wb.save(str(tmp))
shutil.copy(tmp, src)
print(f"Done. Rows now: {ws.max_row - 1}")
