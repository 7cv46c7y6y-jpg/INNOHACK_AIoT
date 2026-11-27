"""서식 3종 생성.

build(form_id, case) → (파일 이름, HWPX 바이트, 확인할 점)
build_all(case)       → 3종을 묶은 zip 바이트
"""

from __future__ import annotations

import io
import zipfile
from datetime import date

from ..model import Case
from . import f01_disaster_report, f02_fishery_report, f03_stocking_report

FORMS = {
    "f02": ("어업피해발생신고서", f02_fishery_report.build),
    "f01": ("자연재난피해신고서", f01_disaster_report.build),
    "f03": ("입식출하판매신고서", f03_stocking_report.build),
}


def file_name(form_id: str, case: Case) -> str:
    title = FORMS[form_id][0]
    d = case.disaster.report_date or date.today()
    return f"초안_{title}_{d:%Y%m%d}.hwpx"


def build(form_id: str, case: Case) -> tuple[str, bytes, list[str]]:
    if form_id not in FORMS:
        raise KeyError(form_id)
    data, notes = FORMS[form_id][1](case)
    return file_name(form_id, case), data, notes


def build_all(case: Case) -> tuple[str, bytes, dict[str, list[str]]]:
    buf = io.BytesIO()
    notes: dict[str, list[str]] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for form_id in FORMS:
            name, data, form_notes = build(form_id, case)
            zf.writestr(name, data)
            notes[form_id] = form_notes
    d = case.disaster.report_date or date.today()
    return f"초안_피해신고서류_3종_{d:%Y%m%d}.zip", buf.getvalue(), notes
