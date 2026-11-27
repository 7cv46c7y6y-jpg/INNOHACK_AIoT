"""원본 서식(forms_src)으로 채우기용 HWPX 템플릿(forms_tpl)을 만든다.

- HWP(①③)는 python-hwpx로 HWPX로 변환한다. 변환하면서 빠진 내용이 있으면 멈춘다.
- HWPX(②)는 그대로 복사한다.

실행: python scripts/build_templates.py
"""

from __future__ import annotations

import shutil
import sys
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
