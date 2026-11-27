"""③ 어류 등(패류·수산종자)의 입식 및 출하·판매 신고서 (같은 규정 별지 제2호서식).

원본은 HWP 1쪽이며 forms_tpl의 HWPX 템플릿으로 채운다. 표 하나(36행×19열).
- 입식 표: '계' 13행 위의 12행, 자료 13~16행 (4줄)
- 출하·폐사 표: '계' 19행, 자료 20~23행 (4줄)
- 사료 표: 자료 27~28행 (2줄)
재난 전에 이미 신고한 내용과 같아야 한다 (과거 신고 이력을 대신하지 못함).
이번 재해의 폐사는 ①②에 적고, 이 서식에는 재해 전까지의 기록(입식·출하·기존 폐사)만 적는다.
"""

from __future__ import annotations

from .. import calc, rules
from ..model import MAX_FEED_ROWS, MAX_OUT_ROWS, MAX_STOCKING_ROWS, Case
from .common import FormFiller

TEMPLATE = "form03_stocking_report.hwpx"
T = 0

STOCK_TOTAL_ROW, STOCK_ROWS = 12, (13, 14, 15, 16)
STOCK_COLS = {"species": 1, "size": 3, "kg": 5, "count": 9, "place": 12, "date": 16}
OUT_TOTAL_ROW, OUT_ROWS = 19, (20, 21, 22, 23)
OUT_COLS = {"species": 1, "year": 3, "size": 4, "kg": 6, "count": 8, "price": 11, "amount": 14, "remain": 18}
FEED_ROWS = (27, 28)
FEED_COLS = {"date": 1, "supplier": 3, "phone": 5, "name": 9, "qty": 12, "price": 16}


def _size(cm: float | None, g: float | None) -> str:
    if cm is not None and g is not None:
        return rules.get("form03", "size_format").format(cm=rules.fmt_num(cm), g=rules.fmt_num(g))
    if cm is not None:
        return f"{rules.fmt_num(cm)}cm"
    if g is not None:
        return f"{rules.fmt_num(g)}g"
    return ""


def _license_no(number: str | None) -> str | None:
    """'제2020-0123호' → '2020-0123' (서식에 '제 … 호'가 이미 있음)."""
    if not number:
        return None
    n = number.strip()
    if n.startswith("제"):
        n = n[1:]
    if n.endswith("호"):
        n = n[:-1]
    return n.strip() or None


def build(case: Case) -> tuple[bytes, list[str]]:
    f = FormFiller(TEMPLATE)
    min_pt = rules.get("form03", "min_font_pt", 6.0)
    filer, owner, lic = case.filer, case.victim, case.license

    def cell(r: int, c: int, text: str | None, label: str) -> None:
        f.set_cell(T, r, c, text, min_pt=min_pt, label=label)

    # 신고인
    f.append(T, 3, 1, filer.name, p=0)
    f.append(T, 3, 1, filer.name_hanja, p=1)
    f.append(T, 3, 9, rules.fmt_date(filer.birth) or None)
    f.append(T, 4, 1, filer.address)
    f.fill_gap(T, 4, 10, "(휴대폰:", filer.mobile, p=0)
    f.fill_gap(T, 4, 10, "(전화번호:", filer.phone, p=1)
    # 어업권자·양식업권자(행사자) = 피해자
    f.append(T, 6, 1, owner.name, p=0)
    f.append(T, 6, 1, owner.name_hanja, p=1)
    f.append(T, 6, 9, rules.fmt_date(owner.birth) or None)
    f.append(T, 7, 1, owner.address, p=0)
    f.fill_gap(T, 7, 1, "(전화번호:", owner.phone or owner.mobile, p=1)
    f.append(T, 8, 0, lic.fishery_type)
    f.append(T, 8, 9, lic.method)
    # 어업권·양식업권 현황
    f.fill_gap(T, 9, 1, "제", _license_no(lic.number), p=1)
    if lic.period_from or lic.period_to:
        period = f"{rules.fmt_date(lic.period_from)} ~ {rules.fmt_date(lic.period_to)}".strip()
        f.append(T, 9, 9, period)
    if lic.area_ha is not None:
        para = f.para(T, 10, 1, 1)
        para.insert_text(0, f"{rules.fmt_num(lic.area_ha)}ha  ")
    f.append(T, 10, 9, lic.location)

    # 입식 표
    rows = case.stocking[:MAX_STOCKING_ROWS]
    for r, row in zip(STOCK_ROWS, rows):
        cell(r, STOCK_COLS["species"], row.species, "입식 품종")
        cell(r, STOCK_COLS["size"], _size(row.size_cm, row.size_g), "입식 크기")
        cell(r, STOCK_COLS["kg"], rules.fmt_num(row.weight_kg), "입식 수량(kg)")
        cell(r, STOCK_COLS["count"], rules.fmt_int(row.count), "입식 마리 수")
        cell(r, STOCK_COLS["place"], row.place, "입식 장소")
        cell(r, STOCK_COLS["date"], rules.fmt_date(row.date), "입식 일자")
    if rows:
        kg = [r.weight_kg for r in rows if r.weight_kg is not None]
        cell(STOCK_TOTAL_ROW, STOCK_COLS["kg"], rules.fmt_num(sum(kg)) if kg else "", "입식 계(kg)")
        cell(STOCK_TOTAL_ROW, STOCK_COLS["count"], rules.fmt_int(sum(r.count or 0 for r in rows)), "입식 계(마리)")
    f.append(T, 17, 3, case.seed_source_name)
    f.append(T, 17, 11, case.seed_source_phone)

    # 출하(판매) 또는 폐사등 표 (재해 전 기록)
    outs = case.outs[:MAX_OUT_ROWS]
    remaining = calc.remaining_by_row(case)[:MAX_OUT_ROWS]
    dead_suffix = rules.get("form03", "dead_row_suffix", "(폐사)")
    for r, row, left in zip(OUT_ROWS, outs, remaining):
        species = (row.species or lic.species or "") + (dead_suffix if row.kind == "폐사" else "")
        cell(r, OUT_COLS["species"], species, "출하·폐사 품종")
        cell(r, OUT_COLS["year"], str(row.stock_year) if row.stock_year else "", "입식 연도")
        cell(r, OUT_COLS["size"], rules.fmt_num(row.size_cm), "크기(cm)")
        cell(r, OUT_COLS["kg"], rules.fmt_num(row.weight_kg), "출하·폐사 수량(kg)")
        cell(r, OUT_COLS["count"], rules.fmt_int(row.count), "출하·폐사 마리 수")
        if row.kind == "출하":
            cell(r, OUT_COLS["price"], rules.fmt_int(row.unit_price), "판매단가")
            cell(r, OUT_COLS["amount"], rules.fmt_num(row.amount_kwon), "금액(천원)")
        cell(r, OUT_COLS["remain"], rules.fmt_int(left), "잔량")
    if outs:
        kg = [r.weight_kg for r in outs if r.weight_kg is not None]
        amounts = [r.amount_kwon for r in outs if r.kind == "출하" and r.amount_kwon is not None]
        cell(OUT_TOTAL_ROW, OUT_COLS["kg"], rules.fmt_num(sum(kg)) if kg else "", "출하 계(kg)")
        cell(OUT_TOTAL_ROW, OUT_COLS["count"], rules.fmt_int(sum(r.count or 0 for r in outs)), "출하 계(마리)")
        cell(OUT_TOTAL_ROW, OUT_COLS["amount"], rules.fmt_num(sum(amounts)) if amounts else "", "출하 계(금액)")
        if remaining and remaining[len(outs) - 1] is not None:
            cell(OUT_TOTAL_ROW, OUT_COLS["remain"], rules.fmt_int(remaining[len(outs) - 1]), "잔량 계")
    f.append(T, 24, 3, case.sold_at)
    f.append(T, 24, 11, case.buyer_contact)
    f.append(T, 25, 3, case.buyer)

    # 사료 구입(확보)
    for r, row in zip(FEED_ROWS, case.feed[:MAX_FEED_ROWS]):
        cell(r, FEED_COLS["date"], rules.fmt_date(row.date), "사료 구입일자")
        cell(r, FEED_COLS["supplier"], row.supplier, "사료 구입처")
        cell(r, FEED_COLS["phone"], row.phone, "사료 구입처 전화번호")
        cell(r, FEED_COLS["name"], row.name, "사료명")
        cell(r, FEED_COLS["qty"], row.qty, "사료 수량")
        cell(r, FEED_COLS["price"], rules.fmt_int(row.unit_price), "사료 구입단가")

    # 신고일과 신고인 (서명은 비움)
    d = case.disaster.report_date
    if d:
        para = f.para(T, 30, 0, 0)
        old = para.text
        para.replace_range(0, len(old), f"{d.year}년   {d.month}월   {d.day}일")
    if filer.name:
        f.fill_gap(T, 31, 0, "신고인", filer.name)
    return f.to_bytes(), f.notes
