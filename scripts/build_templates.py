"""원본 서식(forms_src)으로 채우기용 HWPX 템플릿(forms_tpl)을 만든다.

- HWP(①③)는 python-hwpx로 HWPX로 변환한다. 변환하면서 빠진 내용이 있으면 멈춘다.
- HWPX(②)는 그대로 복사한다.
- 표가 본문 폭(용지 폭 - 왼쪽·오른쪽 여백)보다 1mm 넘게 넓으면 왼쪽·오른쪽 여백을 같게 줄여
  표가 여백 선 안에 들어오게 한다. ② 원본은 여백 30mm에 표 폭이 약 160mm라
  한글에서 오른쪽 여백 선 밖으로 10mm쯤 나가 있다. 표·글자는 건드리지 않는다.

실행: python scripts/build_templates.py
"""

from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path

from hwpx import HwpxDocument

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "forms_src"
TPL = ROOT / "forms_tpl"

CONVERT = {
    "form01_disaster_report.hwp": "form01_disaster_report.hwpx",
    "form03_stocking_report.hwp": "form03_stocking_report.hwpx",
}
COPY = {
    "form02_fishery_damage_report.hwpx": "form02_fishery_damage_report.hwpx",
}


TOLERANCE = 283   # 1mm (HWPUNIT, 1mm = 283.46)


def fit_table_in_margins(path: Path) -> tuple[int, int] | None:
    """첫 표(서식 본문)가 본문 폭보다 넓으면 왼쪽·오른쪽 여백을 같은 값으로 줄인다. 바꾼 경우 (원래 여백, 새 여백)."""
    with zipfile.ZipFile(path) as zf:
        entries = [(info, zf.read(info)) for info in zf.infolist()]
    changed = None
    out = []
    for info, data in entries:
        if re.fullmatch(r"Contents/section\d+\.xml", info.filename) and changed is None:
            xml = data.decode("utf-8")
            page_w = int(re.search(r'<hp:pagePr\b[^>]*\bwidth="(\d+)"', xml).group(1))
            margin = re.search(r"<hp:margin\b[^>]*/>", xml).group(0)
            left = int(re.search(r'\bleft="(\d+)"', margin).group(1))
            right = int(re.search(r'\bright="(\d+)"', margin).group(1))
            tbl = re.search(r'<hp:tbl\b.*?<hp:sz width="(\d+)".*?<hp:outMargin left="(\d+)" right="(\d+)"', xml, re.S)
            need = int(tbl.group(1)) + int(tbl.group(2)) + int(tbl.group(3))
            if need - (page_w - left - right) > TOLERANCE:
                side = (page_w - need) // 2
                new = re.sub(r'\bleft="\d+"', f'left="{side}"', margin, count=1)
                new = re.sub(r'\bright="\d+"', f'right="{side}"', new, count=1)
                data = xml.replace(margin, new, 1).encode("utf-8")
                changed = (left, side)
        out.append((info, data))
    if changed:
        tmp = path.with_name(path.name + ".tmp")
        with zipfile.ZipFile(tmp, "w") as zf:
            for info, data in out:   # 원래 순서와 압축 방식 그대로 (mimetype 은 맨 앞, 무압축)
                zf.writestr(info, data)
        tmp.replace(path)
    return changed


def main() -> int:
    TPL.mkdir(exist_ok=True)
    for src_name, out_name in CONVERT.items():
        doc = HwpxDocument.open(SRC / src_name)
        report = doc.conversion_report
        unconverted = dict(getattr(report, "unconverted", {}) or {})
        dropped = dict(getattr(report, "dropped", {}) or {})
        if unconverted or dropped:
            print(f"[중단] {src_name}: 변환하지 못한 내용 {unconverted}, 빠진 내용 {dropped}")
            return 1
        doc.save(TPL / out_name)
        print(f"[변환] {src_name} -> forms_tpl/{out_name} (빠진 내용 없음)")
    for src_name, out_name in COPY.items():
        shutil.copyfile(SRC / src_name, TPL / out_name)
        print(f"[복사] {src_name} -> forms_tpl/{out_name}")
    for out_name in [*CONVERT.values(), *COPY.values()]:
        changed = fit_table_in_margins(TPL / out_name)
        if changed:
            before, after = changed
            print(f"[여백] {out_name}: 표가 여백 선 밖으로 나가서 왼쪽·오른쪽 여백 {before / 283.46:.1f}mm -> {after / 283.46:.1f}mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
