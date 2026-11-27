"""검증: 오류(서식을 만들 수 없음), 주의, 참고, 미확인 항목."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from . import calc
from .model import EVIDENCE_ITEMS, INDIRECT_KEYS, NO, YES, Case

F1, F2, F3 = "자연재난 피해신고서", "어업피해발생신고서", "입식·출하·판매 신고서"

INDIRECT_LABELS = {
    "gas": "도시가스 사용 여부",
    "car": "자동차 소유 여부",
    "public_housing": "공공주택 임대 신청 희망 여부",
    "crisis_family": "위기가족 긴급지원 희망 여부",
    "health_arrears": "건강보험료 체납 여부",
    "fine_deferral": "과태료 징수 유예 희망 여부",
    "inheritance_loss": "재해손실 공제 신청 희망 여부",
}


@dataclass
class Issue:
    level: str      # error / warning / info
    field: str      # 화면의 입력 위치
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def check(case: Case) -> dict:
    errors: list[Issue] = []
    warnings: list[Issue] = []
    infos: list[Issue] = []

    def err(field: str, msg: str) -> None:
        errors.append(Issue("error", field, msg))

    def warn(field: str, msg: str) -> None:
        warnings.append(Issue("warning", field, msg))

    # 1) 꼭 있어야 하는 값
    required = [
        ("victim.name", case.victim.name, "피해자(어업권자) 성명"),
        ("victim.address", case.victim.address, "피해자 주소"),
        ("license.number", case.license.number, "면허(허가)번호"),
        ("license.location", case.license.location, "어장 위치"),
        ("license.species", case.license.species, "품종"),
        ("disaster.damage_start", case.disaster.damage_start, "피해 발생일"),
        ("damage.dead_count", case.damage.dead_count, "이번 피해량(마리)"),
    ]
    for field, value, label in required:
        if value is None:
            err(field, f"{label}을(를) 입력해 주세요.")
    if not any(r.count for r in case.stocking):
        err("stocking", "입식 기록(마리 수)을 한 줄 이상 입력해 주세요.")
    if not case.reporter_same and not case.filer.name:
        err("reporter.name", "대신 신고하는 경우 신고인 성명을 입력해 주세요.")

    # 2) 숫자
    for i, r in enumerate(case.stocking, 1):
        if r.count is not None and r.count <= 0:
            err(f"stocking.{i}", f"입식 {i}번째 줄의 마리 수는 0보다 커야 합니다.")
        if r.weight_kg is not None and r.weight_kg < 0:
            err(f"stocking.{i}", f"입식 {i}번째 줄의 수량(kg)이 음수입니다.")
    for i, r in enumerate(case.outs, 1):
        if r.kind is None:
            err(f"outs.{i}", f"출하·폐사 {i}번째 줄이 출하인지 폐사인지 골라 주세요.")
        if r.count is not None and r.count <= 0:
            err(f"outs.{i}", f"출하·폐사 {i}번째 줄의 마리 수는 0보다 커야 합니다.")
        if r.kind == "출하" and r.unit_price and r.count and r.amount_kwon is not None:
            expected = r.unit_price * r.count / 1000
            if abs(expected - r.amount_kwon) > max(1.0, expected * 0.01):
                warn(f"outs.{i}", f"출하 {i}번째 줄의 금액({r.amount_kwon:,.0f}천원)이 단가×마리 수({expected:,.0f}천원)와 다릅니다.")
    dead = case.damage.dead_count
    if dead is not None and dead <= 0:
        err("damage.dead_count", "이번 피해량은 0보다 커야 합니다.")
    stock = calc.stock_before(case)
    if stock is not None and stock <= 0:
        err("outs", f"출하·기존 폐사 합계가 입식보다 많습니다 (재해 직전 사육량 {stock:,}마리).")
    elif stock is not None and dead is not None and dead > stock:
        err("damage.dead_count", f"이번 피해량({dead:,}마리)이 재해 직전 사육량({stock:,}마리)보다 많습니다.")

    # 3) 날짜 순서
    d = case.disaster
    if d.damage_start and d.damage_end and d.damage_end < d.damage_start:
        err("disaster.damage_end", "피해 발생 기간의 끝이 시작보다 빠릅니다.")
    if d.damage_start and d.disaster_end and d.disaster_end < d.damage_start:
        err("disaster.disaster_end", "재난 종료일이 피해 발생일보다 빠릅니다.")
    for i, r in enumerate(case.stocking, 1):
        if r.date and d.damage_start and r.date > d.damage_start:
            err(f"stocking.{i}", f"입식 {i}번째 줄의 입식 일자가 피해 발생일보다 늦습니다.")
    lic = case.license
    if lic.period_from and lic.period_to and lic.period_to < lic.period_from:
        err("license.period_to", "면허 기간의 끝이 시작보다 빠릅니다.")
    if lic.period_to and d.damage_start and lic.period_to < d.damage_start:
        warn("license.period_to", "피해 발생일에 면허 기간이 이미 끝나 있습니다. 면허 정보를 확인해 주세요.")

    # 4) 서식 행 수
    for msg in case.overflow:
        err("rows", msg)

    # 5) 놓치기 쉬운 조건과 기한
    if case.pre_disaster_reported != YES:
        warn("pre_disaster_reported",
             "재난 전에 입식·출하·판매 신고를 하지 않았다면 양식업 재난지원금 대상에서 빠질 수 있습니다 "
             "(자연재난 규정 제9조 제4항). 지금 만드는 입식·출하·판매 신고서가 과거 신고 이력을 대신하지는 못합니다.")
    deadline = calc.report_deadline(case)
    if deadline.due and d.report_date and d.report_date > deadline.due:
        warn("disaster.report_date",
             f"신고 예정일이 참고 기한({deadline.due.isoformat()})보다 늦습니다. 장기 여행 같은 부득이한 사유가 있었다면 "
             "그 사유가 끝난 날부터 10일 안에 신고할 수 있습니다 (제9조 제6항).")
    warn("deadline.02", "어업피해발생신고서는 피해가 나면 지체 없이 읍·면·동에 내야 합니다. "
                        "늦게 내면 피해조사 대상에서 빠질 수 있습니다.")
    if case.damage.amount_krw and not case.damage.amount_basis:
        warn("damage.amount_basis", "피해액의 산정 근거가 없어 어업피해발생신고서에는 피해액을 '미확인'으로 적습니다.")
    stocked_species = {r.species for r in case.stocking if r.species}
    if lic.species and stocked_species and lic.species not in stocked_species:
        warn("license.species", f"면허 정보의 품종({lic.species})이 입식 기록의 품종({', '.join(sorted(stocked_species))})과 다릅니다.")
    missing_evidence = [label for key, label in EVIDENCE_ITEMS.items() if not case.evidence.get(key)]
    if missing_evidence:
        warn("evidence", "아직 준비하지 않은 증빙: " + ", ".join(missing_evidence))

    rate = calc.damage_rate(case)
    if rate is not None:
        infos.append(Issue("info", "damage_rate",
                           f"피해율 참고값 {rate:.2f}% (재해 직전 사육량 {stock:,}마리 대비 {dead:,}마리). 공적으로 확정된 값이 아닙니다."))

    return {
        "ok": not errors,
        "errors": [i.to_dict() for i in errors],
        "warnings": [i.to_dict() for i in warnings],
        "infos": [i.to_dict() for i in infos],
        "unknown": unknown_items(case),
        "manual": manual_items(),
    }


def unknown_items(case: Case) -> dict[str, list[str]]:
    """모름으로 남아 서식에서 빈칸이 되는 항목."""
    f = case.form01
    filer = case.filer
    u1, u2, u3 = [], [], []

    def need(bucket: list[str], value, label: str) -> None:
        if value is None or value == "" or value == []:
            bucket.append(label)

    need(u1, f.housing, "주거 형태")
    need(u1, f.family_count, "가족 수")
    need(u1, case.victim.mobile, "이동전화")
    need(u1, f.carrier, "통신사")
    need(u1, f.loan_request, "융자신청 여부")
    need(u1, f.public_property, "국·공유재산 사용·대부 여부")
    for key in INDIRECT_KEYS:
        need(u1, f.indirect.get(key).answer if f.indirect.get(key) else None, INDIRECT_LABELS[key])
    need(u1, f.same_household.answer, "동일세대 신고 여부")
    need(u1, f.other_region.answer, "다른 시·군·구 동일 피해신고 여부")
    need(u1, f.storm_insurance, "풍수해·지진재해보험 가입 여부")
    if f.storm_insurance == NO:
        need(u1, f.storm_insurance_intent, "풍수해·지진재해보험 가입 의사")
    need(u1, case.relation, "피해자와의 관계")
    need(u1, case.disaster.report_date, "신고일")

    need(u2, case.license.period_from, "면허(허가)기간")
    need(u2, case.license.area_ha, "면적")
    need(u2, case.disaster.damage_end, "피해 발생 기간의 끝")
    need(u2, case.damage.cause_note, "피해 원인(신고인 설명)")
    need(u2, case.damage.emergency, "응급조치사항")
    if not (case.damage.amount_krw and case.damage.amount_basis):
        u2.append("피해액 (근거가 없어 '미확인'으로 적음)")

    need(u3, filer.birth, "신고인 생년월일")
    need(u3, filer.mobile, "신고인 휴대폰")
    need(u3, case.victim.birth, "어업권자 생년월일")
    need(u3, case.license.fishery_type, "어업의 종류")
    need(u3, case.license.method, "시설방법 또는 양식방법")
    need(u3, case.seed_source_name, "수산종자 구입처")
    if any(r.kind == "출하" for r in case.outs):
        need(u3, case.buyer, "판매처")
    need(u3, case.feed, "사료 구입 내역")
    return {F1: u1, F2: u2, F3: u3}


def manual_items() -> list[str]:
    """앱이 채우지 않고 사람이 직접 해야 하는 일."""
    return [
        "자연재난 피해신고서의 주민등록번호와 재난지원금 지급통장(은행명·계좌번호·예금주)은 내려받은 뒤 직접 적어 주세요.",
        "자연재난 피해신고서 서명 6곳: 2쪽 신고인 1곳, 3쪽 동의 5곳(동의하는 항목에만). "
        "행정정보 공동이용에 동의하지 않으면 주민등록표 등본·소득금액 증명·가족관계증명서를 직접 내야 합니다.",
        "어업피해발생신고서의 '(인)' 자리와 입식·출하·판매 신고서의 '(서명 또는 인)' 자리는 직접 서명하거나 도장을 찍어 주세요.",
    ]
