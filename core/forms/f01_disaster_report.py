"""① 자연재난 피해신고서 (자연재난 구호 및 복구 비용 부담기준 등에 관한 규정 별지 제1호서식).

원본은 HWP 3쪽이며 forms_tpl의 HWPX 템플릿으로 채운다. 쪽마다 큰 표가 하나씩 있다.
- 표0 (1쪽): 1. 피해자 정보, 2. 피해 내용
- 표1 (2쪽): 3. 간접 지원, 4. 확인 사항, 신고일·신고인·관계
- 표2 (3쪽): 동의서·유의사항·작성방법. 아무것도 쓰지 않는다 (동의는 본인 서명으로 표시).

채우지 않는 칸: 주민등록번호, 지급통장(은행명·계좌번호·예금주), 회색 칸(접수번호·접수일·처리기간,
피해물량 확정, 피해 구분, 피해 원인), 담당 공무원 확인 사항, 모든 서명란.
시연에서는 시설 1곳(①)만 쓴다.
"""

from __future__ import annotations

import re

from .. import rules
from ..model import NO, YES, Case, day
from .common import FormFiller, visual_len

TEMPLATE = "form01_disaster_report.hwpx"
P1, P2 = 0, 1  # 1쪽, 2쪽 표 번호

# 시설 ①의 칸 (행, 열) — ②~⑩은 시연 범위 밖
FACILITY_1 = {"name": (16, 4), "area": (17, 4), "license": (18, 4), "qty": (19, 4), "loan": (23, 4), "public": (24, 4)}

# 2쪽 간접 지원 행 (키 → 행)
INDIRECT_ROWS = {"gas": 2, "car": 3, "public_housing": 4, "crisis_family": 5,
                 "health_arrears": 6, "fine_deferral": 7, "inheritance_loss": 8}


def landline(phone: str | None) -> str | None:
    """'055-123-4567' → '(055) 123-4567'."""
    if not phone:
        return None
    parts = re.split(r"[-\s]", phone.strip())
    if len(parts) == 3 and all(parts):
        return f"({parts[0]}) {parts[1]}-{parts[2]}"
    return phone


def _yes_no(f: FormFiller, t: int, r: int, c: int, answer: str | None) -> None:
    if answer == YES:
        f.check(t, r, c, "예")
    elif answer == NO:
        f.check(t, r, c, "아니오")


def build(case: Case) -> tuple[bytes, list[str]]:
    f = FormFiller(TEMPLATE)
    min_pt = rules.get("form01", "min_font_pt", 6.0)
    v, x, lic = case.victim, case.form01, case.license

    # ---------------- 1쪽: 1. 피해자 정보
    f.set_cell(P1, 6, 4, v.address, min_pt=min_pt, label="주소(사업장)")
    if x.housing:
        f.check(P1, 7, 4, x.housing)
    if v.name:  # 성명 칸: 앞쪽 빈칸에 이름. 주민등록번호 자리는 비워 둔다.
        f.fill_gap(P1, 8, 4, "", v.name)
    if x.family_count is not None:
        f.fill_before(P1, 9, 4, "명(", str(x.family_count))
    for i, (school, count) in enumerate(x.high_schools[:2]):
        if school:
            f.fill_gap(P1, 10, 4, "(", school, p=i)
        if count is not None:
            f.fill_before(P1, 10, 4, "명", str(count), p=i)
    if v.mobile:
        para = f.para(P1, 12, 4)
        para.replace_range(0, len(para.text), f" {v.mobile}")
    if x.carrier:
        f.check(P1, 12, 9, x.carrier, side="before")
    sub = x.mobile_subscriber
    f.fill_gap(P1, 12, 15, "성명:", sub.name)
    f.fill_gap(P1, 12, 15, "생년월일:", rules.fmt_date(sub.birth) or None)
    if v.phone:
        para = f.para(P1, 13, 4)
        para.replace_range(0, len(para.text), f"  {landline(v.phone)}")
    sub = x.landline_subscriber
    f.fill_gap(P1, 13, 15, "성명:", sub.name)
    f.fill_gap(P1, 13, 15, "생년월일:", rules.fmt_date(sub.birth) or None)

    # ---------------- 1쪽: 2. 피해 내용 (시설 ①)
    if lic.location:
        location = lic.location
        if lic.species:
            location = rules.get("form01", "location_format").format(location=lic.location, species=lic.species)
        f.set_cell(P1, 15, 4, location, min_pt=min_pt, label="피해 발생 위치")
    r, c = FACILITY_1["name"]
    f.set_cell(P1, r, c, f"① {rules.get('form01', 'facility_name')}", min_pt=min_pt, mode="wrap_then_shrink", label="피해시설명")
    if lic.area_ha is not None:
        r, c = FACILITY_1["area"]
        area = rules.get("form01", "area_format").format(area=rules.fmt_num(lic.area_ha))
        f.set_cell(P1, r, c, f"① {area}", min_pt=min_pt, mode="wrap_then_shrink", label="총면적")
    if lic.number:
        r, c = FACILITY_1["license"]
        f.set_cell(P1, r, c, f"① {lic.number}", min_pt=min_pt, mode="wrap_then_shrink", label="면허번호")
    if case.damage.dead_count is not None:
        r, c = FACILITY_1["qty"]
        qty = rules.get("form01", "damage_qty_format").format(
            count=rules.fmt_int(case.damage.dead_count), species=lic.species or "")
        f.set_cell(P1, r, c, f"① {qty}", min_pt=min_pt, mode="wrap_then_shrink", label="피해물량 신고")
    if x.loan_request:
        f.check_box_only(P1, *FACILITY_1["loan"])
    if x.public_property:
        f.check_box_only(P1, *FACILITY_1["public"])

    # ---------------- 2쪽: 3. 간접 지원
    for key, row in INDIRECT_ROWS.items():
        ans = x.indirect.get(key)
        if ans is None:
            continue
        _yes_no(f, P2, row, 2, ans.answer)
        if key == "gas" and ans.answer == YES:
            f.fill_gap(P2, row, 2, "가입자명:", ans.name)
            f.fill_gap(P2, row, 2, "생년월일:", rules.fmt_date(ans.birth) or None)
        if key == "car" and ans.answer == YES:
            f.fill_gap(P2, row, 2, "만료일:", rules.fmt_date(day(ans.detail)) or ans.detail)

    # ---------------- 2쪽: 4. 확인 사항
    _yes_no(f, P2, 10, 2, x.same_household.answer)
    if x.same_household.answer == YES:
        f.fill_gap(P2, 10, 4, "내용:", x.same_household.detail)
    _yes_no(f, P2, 11, 2, x.other_region.answer)
    if x.other_region.answer == YES:
        f.fill_gap(P2, 11, 4, "내용:", x.other_region.detail)
    _yes_no(f, P2, 12, 2, x.storm_insurance)
    if x.storm_insurance == NO:
        _yes_no(f, P2, 12, 5, x.storm_insurance_intent)

    # ---------------- 2쪽: 신고일, 신고인(이름만, 서명은 비움), 피해자와의 관계
    d = case.disaster.report_date
    if d:
        para = f.para(P2, 13, 0, 2)
        old = para.text
        target = f"{d.year}년  {d.month}월  {d.day}일"
        pad = max(0, visual_len(old) - visual_len(target))
        para.replace_range(0, len(old), " " * (pad // 2) + target + " " * (pad - pad // 2))
    f.fill_gap(P2, 13, 0, "신고인:", case.filer.name, p=3)
    if case.relation:
        f.check(P2, 13, 0, case.relation, p=4)

    return f.to_bytes(), f.notes
