"""② 어업피해발생신고서 (어업재해 피해조사·보고 및 복구지원 요령 별지 제1호서식).

원본은 HWPX 1쪽, 표 하나(12행×7열). 칸 위치는 docs/FIELD_MAP.md 참고.
"""

from __future__ import annotations

from .. import calc, rules
from ..model import Case
from .common import FormFiller, visual_len

TEMPLATE = "form02_fishery_damage_report.hwpx"
T = 0  # 표 번호


def _period(start, end) -> str:
    if start and end:
        return f"{rules.fmt_date(start)} ~ {rules.fmt_date(end)}"
    if start:
        return f"{rules.fmt_date(start)} ~"
    if end:
        return f"~ {rules.fmt_date(end)}"
    return ""


def _situation(case: Case) -> str:
    stock = calc.stock_before(case)
    rate = calc.damage_rate(case)
    species = case.license.species or ""
    count = rules.fmt_int(case.damage.dead_count)
    if stock is not None and rate is not None:
        line1 = rules.get("form02", "situation_format").format(
            species=species, count=count, stock=rules.fmt_int(stock), rate=f"{rate:.2f}")
    else:
        line1 = f"피해량: {species} {count}마리".strip()
    if case.damage.dead_weight_kg:
        line1 += f", 약 {rules.fmt_num(case.damage.dead_weight_kg)}kg"
    d = case.damage
    if d.amount_krw and d.amount_basis:
        line2 = rules.get("form02", "amount_format").format(amount=rules.fmt_int(d.amount_krw), basis=d.amount_basis)
    else:
        line2 = rules.get("form02", "amount_unknown")
    return f"{line1} / {line2}"


def build(case: Case) -> tuple[bytes, list[str]]:
    f = FormFiller(TEMPLATE)
    min_pt = rules.get("form02", "min_font_pt", 7.0)
    v, lic, d = case.victim, case.license, case.disaster

    f.set_cell(T, 1, 2, v.address, min_pt=min_pt, label="주소")
    f.set_cell(T, 2, 2, v.name, min_pt=min_pt, label="성명")
    f.set_cell(T, 3, 2, lic.number, min_pt=min_pt, label="면허(허가)번호")
    f.set_cell(T, 3, 4, lic.species, min_pt=min_pt, label="품종")
    if lic.area_ha is not None:
        f.set_cell(T, 3, 6, f"{rules.fmt_num(lic.area_ha)}ha", min_pt=min_pt, label="면적")
    f.set_cell(T, 4, 2, _period(lic.period_from, lic.period_to), min_pt=min_pt, label="면허(허가)기간")
    f.set_cell(T, 5, 1, lic.location, min_pt=min_pt, label="어장 위치")

    cause = case.damage.cause_note or d.kind
    if cause:
        f.set_cell(T, 6, 1, cause + rules.get("form02", "cause_suffix", " (추정)"), min_pt=min_pt, label="피해 원인")
    f.set_cell(T, 7, 1, _period(d.damage_start, d.damage_end), min_pt=min_pt, label="피해발생기간")
    if case.damage.dead_count is not None:
        f.set_cell(T, 8, 1, _situation(case), min_pt=min_pt, label="피해 상황")
    f.set_cell(T, 9, 1, case.damage.emergency, min_pt=min_pt, label="응급조치사항")
    f.set_cell(T, 10, 1, case.damage.other, min_pt=min_pt, label="기타 사항")

    # 맨 아래 칸: 날짜, 신고자 주소·성명. '(인)'은 비워 둔다.
    if d.report_date:
        para = f.para(T, 11, 0, 1)
        old = para.text
        target = f"{d.report_date.year}년  {d.report_date.month}월  {d.report_date.day}일"
        pad = max(0, visual_len(old) - visual_len(target))
        para.replace_range(0, len(old), " " * pad + target)
    filer = case.filer
    f.append(T, 11, 0, filer.address, p=3)
    f.fill_gap(T, 11, 0, ":", filer.name, p=5)
    return f.to_bytes(), f.notes
