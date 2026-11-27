"""서식 3종 생성과 제출 묶음.

build(form_id, case)              → (파일 이름, HWPX 바이트, 확인할 점)
build_all(case)                   → 서식 3종만 묶은 zip
build_bundle(case, attachments)   → 서식 3종 + 증빙(항목별 폴더) + 제출목록.txt 를 묶은 zip
"""

from __future__ import annotations

import io
import zipfile
from datetime import date

from .. import calc, guidance, validate, zip_ko
from ..attachments import Attachment
from ..model import EVIDENCE, Case
from . import f01_disaster_report, f02_fishery_report, f03_stocking_report

FORMS = {
    "f02": ("어업피해발생신고서", f02_fishery_report.build),
    "f01": ("자연재난피해신고서", f01_disaster_report.build),
    "f03": ("입식출하판매신고서", f03_stocking_report.build),
}
FORM_DIR = "1_서식(서명 전 초안)"
EVIDENCE_DIR = "2_증빙"


def _day(case: Case) -> date:
    return case.disaster.report_date or date.today()


def file_name(form_id: str, case: Case) -> str:
    return f"초안_{FORMS[form_id][0]}_{_day(case):%Y%m%d}.hwpx"


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
            zip_ko.add(zf, name, data)
            notes[form_id] = form_notes
    return f"초안_피해신고서류_3종_{_day(case):%Y%m%d}.zip", buf.getvalue(), notes


def checklist(case: Case, attachments: list[Attachment], notes: dict[str, list[str]]) -> str:
    """제출목록.txt: 무엇을 어디에 언제 내는지, 첨부한 증빙과 아직 없는 증빙, 직접 할 일."""
    g = guidance.build(case)
    v = validate.check(case)
    s = calc.summary(case)
    lines = [f"아쿠아클레임 제출 묶음 (서명 전 초안) · {_day(case):%Y-%m-%d}", ""]
    lines.append("[서식] 빈칸을 채우고 서명한 뒤 제출하세요")
    for f in g["forms"]:
        due = f" (참고 기한 {f['due']})" if f.get("due") else ""
        lines.append(f"- {f['name']}: {f['when']}{due} → {f['where']}")
        for note in notes.get(f["id"], []):
            lines.append(f"    · {note}")
    lines.append("")
    if s["stock_before"] is not None:
        rate = f"{s['damage_rate']:.2f}%" if s["damage_rate"] is not None else "-"
        lines.append(f"[계산] 재해 직전 사육량 {s['stock_before']:,}마리, 이번 피해량 {s['dead_count'] or 0:,}마리, 피해율 참고값 {rate}")
        lines.append("")
    lines.append("[첨부한 증빙]")
    by_key: dict[str, list[str]] = {}
    for a in attachments:
        by_key.setdefault(a.key, []).append(a.filename)
    any_file = False
    for key, item in EVIDENCE.items():
        files = by_key.get(key)
        if files:
            any_file = True
            lines.append(f"- {item['label']} → {EVIDENCE_DIR}/{item['folder']}/ : {', '.join(files)}")
        elif case.evidence.get(key):
            lines.append(f"- {item['label']}: 파일 첨부 없음 (종이·원본으로 가지고 있음)")
    if not any_file and not any(case.evidence.values()):
        lines.append("- 없음")
    missing = [item["label"] for key, item in EVIDENCE.items() if not case.evidence.get(key)]
    if missing:
        lines += ["", "[아직 준비하지 않은 증빙]"] + [f"- {m}" for m in missing]
    lines += ["", "[직접 하실 일]"] + [f"- {m}" for m in v["manual"]]
    warnings = [w["message"] for w in v["warnings"] if w["field"] != "evidence"]
    if warnings:
        lines += ["", "[확인할 것]"] + [f"- {w}" for w in warnings]
    unknown = [(form, items) for form, items in v["unknown"].items() if items]
    if unknown:
        lines += ["", "[직접 채울 곳 (빈칸 또는 '미확인')]"] + [f"- {form}: {', '.join(items)}" for form, items in unknown]
    lines += ["", "이 묶음은 시연용 서비스에서 만든 초안입니다. 공적 피해 확인과 제출은 담당 기관 안내를 따르세요."]
    return "\r\n".join(lines) + "\r\n"


def build_bundle(case: Case, attachments: list[Attachment]) -> tuple[str, bytes]:
    """서식 3종 + 증빙 + 제출목록을 묶는다. 증빙을 첨부한 항목은 준비됨으로 본다."""
    for a in attachments:
        case.evidence[a.key] = True
    buf = io.BytesIO()
    notes: dict[str, list[str]] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for form_id in FORMS:
            name, data, form_notes = build(form_id, case)
            zip_ko.add(zf, f"{FORM_DIR}/{name}", data)
            notes[form_id] = form_notes
        order = {key: i for i, key in enumerate(EVIDENCE)}
        for a in sorted(attachments, key=lambda a: order[a.key]):
            zip_ko.add(zf, f"{EVIDENCE_DIR}/{EVIDENCE[a.key]['folder']}/{a.filename}", a.data)
        # 메모장에서 한글이 깨지지 않게 UTF-8 BOM 을 붙인다
        zip_ko.add(zf, "제출목록.txt", "\ufeff" + checklist(case, attachments, notes))
    return f"초안_피해신고_제출묶음_{_day(case):%Y%m%d}.zip", buf.getvalue()
