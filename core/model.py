"""입력 데이터 구조.

화면(브라우저)이 보내는 JSON을 이 구조로 바꾼다. 빈 문자열은 None(모름)으로 다룬다.
주민등록번호와 계좌번호는 받지 않는다 (PRD 9절).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

MAX_STOCKING_ROWS = 4   # ③ 입식 표 행 수 (원본)
MAX_OUT_ROWS = 4        # ③ 출하·폐사 표 행 수 (원본)
MAX_FEED_ROWS = 2       # ③ 사료 표 행 수 (원본)
MAX_HIGH_SCHOOLS = 2    # ① 고등학생 칸 수 (원본)

YES, NO, UNKNOWN = "예", "아니오", "모름"
HOUSING_OPTIONS = ("소유자(실거주)", "소유자(미거주)", "세입자", "공공임대 세입자")
CARRIERS = ("KT", "SKT", "LGU+", "기타")
RELATIONS = ("본인", "가족", "이장ㆍ통장", "이웃")
OUT_KINDS = ("출하", "폐사")


# ---------------------------------------------------------------- 값 변환
def s(value: Any) -> str | None:
    """문자열로 바꾸고 앞뒤 공백을 지운다. 비어 있으면 None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def num(value: Any) -> float | None:
    """'12,000' 같은 문자열도 숫자로 바꾼다. 비어 있거나 숫자가 아니면 None."""
    text = s(value)
    if text is None:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def integer(value: Any) -> int | None:
    n = num(value)
    if n is None:
        return None
    return int(round(n))


def day(value: Any) -> date | None:
    """'2026-08-10' 또는 '2026.08.10' 형식의 날짜."""
    text = s(value)
    if text is None:
        return None
    text = text.replace(".", "-").replace("/", "-")
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def flag(value: Any) -> bool | None:
    """체크 여부. True/False, 'true'/'false', '예'/'아니오'. 모르면 None."""
    if isinstance(value, bool):
        return value
    text = s(value)
    if text is None:
        return None
    if text.lower() in ("true", "1", "yes", "y", YES):
        return True
    if text.lower() in ("false", "0", "no", "n", NO):
        return False
    return None


def choice(value: Any, options: tuple[str, ...]) -> str | None:
    text = s(value)
    if text is None:
        return None
    text = text.replace("·", "ㆍ") if "ㆍ" in "".join(options) else text
    return text if text in options else None


def yes_no(value: Any) -> str | None:
    """'예' / '아니오' / None(모름)."""
    text = s(value)
    if text in (YES, NO):
        return text
    f = flag(value)
    if f is True:
        return YES
    if f is False:
        return NO
    return None


def _get(data: Any, key: str) -> Any:
    return data.get(key) if isinstance(data, dict) else None


def _rows(data: Any, key: str) -> list[dict]:
    value = _get(data, key)
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


# ---------------------------------------------------------------- 구조
@dataclass
class Person:
    name: str | None = None
    name_hanja: str | None = None
    birth: date | None = None
    address: str | None = None
    mobile: str | None = None
    phone: str | None = None

    @classmethod
    def from_dict(cls, data: Any) -> "Person":
        return cls(
            name=s(_get(data, "name")),
            name_hanja=s(_get(data, "name_hanja")),
            birth=day(_get(data, "birth")),
            address=s(_get(data, "address")),
            mobile=s(_get(data, "mobile")),
            phone=s(_get(data, "phone")),
        )


@dataclass
class Disaster:
    kind: str | None = None            # 재해 종류 (예: 고수온)
    damage_start: date | None = None   # 피해 발생 기간 시작
    damage_end: date | None = None     # 피해 발생 기간 끝
    disaster_end: date | None = None   # 재난 종료일 (예: 고수온 특보 해제일)
    report_date: date | None = None    # 신고(작성) 예정일

    @classmethod
    def from_dict(cls, data: Any) -> "Disaster":
        return cls(
            kind=s(_get(data, "kind")),
            damage_start=day(_get(data, "damage_start")),
            damage_end=day(_get(data, "damage_end")),
            disaster_end=day(_get(data, "disaster_end")),
            report_date=day(_get(data, "report_date")),
        )


@dataclass
class License:
    number: str | None = None          # 면허(허가)번호
    period_from: date | None = None
    period_to: date | None = None
    area_ha: float | None = None       # 면허 면적(ha)
    fishery_type: str | None = None    # 어업의 종류
    method: str | None = None          # 시설방법 또는 양식방법
    location: str | None = None        # 어장 위치
    species: str | None = None         # 주 품종

    @classmethod
    def from_dict(cls, data: Any) -> "License":
        return cls(
            number=s(_get(data, "number")),
            period_from=day(_get(data, "period_from")),
            period_to=day(_get(data, "period_to")),
            area_ha=num(_get(data, "area_ha")),
            fishery_type=s(_get(data, "fishery_type")),
            method=s(_get(data, "method")),
            location=s(_get(data, "location")),
            species=s(_get(data, "species")),
        )


@dataclass
class StockingRow:
    species: str | None = None
    size_cm: float | None = None
    size_g: float | None = None
    weight_kg: float | None = None
    count: int | None = None
    place: str | None = None
    date: date | None = None

    @classmethod
    def from_dict(cls, data: Any) -> "StockingRow":
        return cls(
            species=s(_get(data, "species")),
            size_cm=num(_get(data, "size_cm")),
            size_g=num(_get(data, "size_g")),
            weight_kg=num(_get(data, "weight_kg")),
            count=integer(_get(data, "count")),
            place=s(_get(data, "place")),
            date=day(_get(data, "date")),
        )

    def is_empty(self) -> bool:
        return all(v is None for v in vars(self).values())


@dataclass
class OutRow:
    kind: str | None = None            # 출하 / 폐사 (재해 전 기존 폐사)
    species: str | None = None
    stock_year: int | None = None      # 입식 연도
    size_cm: float | None = None
    weight_kg: float | None = None
    count: int | None = None
    unit_price: int | None = None      # 판매단가 (원/마리)
    amount_kwon: float | None = None   # 금액 (천원)

    @classmethod
    def from_dict(cls, data: Any) -> "OutRow":
        return cls(
            kind=choice(_get(data, "kind"), OUT_KINDS),
            species=s(_get(data, "species")),
            stock_year=integer(_get(data, "stock_year")),
            size_cm=num(_get(data, "size_cm")),
            weight_kg=num(_get(data, "weight_kg")),
            count=integer(_get(data, "count")),
            unit_price=integer(_get(data, "unit_price")),
            amount_kwon=num(_get(data, "amount_kwon")),
        )

    def is_empty(self) -> bool:
        return all(v is None for k, v in vars(self).items() if k != "kind")


@dataclass
class FeedRow:
    date: date | None = None
    supplier: str | None = None
    phone: str | None = None
    name: str | None = None
    qty: str | None = None             # 수량 (단위 포함 문자열, 예: 40포)
    unit_price: int | None = None      # 구입단가 (원)

    @classmethod
    def from_dict(cls, data: Any) -> "FeedRow":
        return cls(
            date=day(_get(data, "date")),
            supplier=s(_get(data, "supplier")),
            phone=s(_get(data, "phone")),
            name=s(_get(data, "name")),
            qty=s(_get(data, "qty")),
            unit_price=integer(_get(data, "unit_price")),
        )

    def is_empty(self) -> bool:
        return all(v is None for v in vars(self).values())


@dataclass
class Damage:
    dead_count: int | None = None      # 이번 피해량 (마리)
    dead_weight_kg: float | None = None
    cause_note: str | None = None      # 신고인이 쓴 원인 설명 (공식 원인 아님)
    amount_krw: int | None = None      # 피해액 (근거가 있을 때만 서식에 적음)
    amount_basis: str | None = None
    emergency: str | None = None       # 응급조치
    other: str | None = None           # 기타 사항
    water_temp_c: float | None = None  # 어가가 잰 수온 (선택)
    temp_measured_at: str | None = None

    @classmethod
    def from_dict(cls, data: Any) -> "Damage":
        return cls(
            dead_count=integer(_get(data, "dead_count")),
            dead_weight_kg=num(_get(data, "dead_weight_kg")),
            cause_note=s(_get(data, "cause_note")),
            amount_krw=integer(_get(data, "amount_krw")),
            amount_basis=s(_get(data, "amount_basis")),
            emergency=s(_get(data, "emergency")),
            other=s(_get(data, "other")),
            water_temp_c=num(_get(data, "water_temp_c")),
            temp_measured_at=s(_get(data, "temp_measured_at")),
        )


@dataclass
class Answer:
    """예/아니오 질문과 딸린 내용."""
    answer: str | None = None
    detail: str | None = None
    name: str | None = None
    birth: date | None = None

    @classmethod
    def from_dict(cls, data: Any) -> "Answer":
        if not isinstance(data, dict):
            return cls(answer=yes_no(data))
        return cls(
            answer=yes_no(data.get("answer")),
            detail=s(data.get("detail")),
            name=s(data.get("name")),
            birth=day(data.get("birth")),
        )


INDIRECT_KEYS = (
    "gas",                # 도시가스 사용 여부 (+ 가입자명, 생년월일)
    "car",                # 자동차 소유 여부 (+ 검사 유효기간 만료일 → detail)
    "public_housing",     # 공공주택 임대 신청 희망 여부
    "crisis_family",      # 위기가족 긴급지원 희망 여부
    "health_arrears",     # 건강보험료 체납 여부
    "fine_deferral",      # 과태료 징수 유예 희망 여부
    "inheritance_loss",   # 재해손실 공제 신청 희망 여부
)


@dataclass
class Form01Extra:
    housing: str | None = None
    family_count: int | None = None
    high_schools: list[tuple[str | None, int | None]] = field(default_factory=list)
    carrier: str | None = None
    mobile_subscriber: Answer = field(default_factory=Answer)
    landline_subscriber: Answer = field(default_factory=Answer)
    loan_request: bool | None = None       # 융자신청 여부 (시설 ①)
    public_property: bool | None = None    # 국·공유재산 사용 또는 대부 여부 (시설 ①)
    indirect: dict[str, Answer] = field(default_factory=dict)
    same_household: Answer = field(default_factory=Answer)
    other_region: Answer = field(default_factory=Answer)
    storm_insurance: str | None = None
    storm_insurance_intent: str | None = None

    @classmethod
    def from_dict(cls, data: Any) -> "Form01Extra":
        schools = []
        for row in _rows(data, "high_schools")[:MAX_HIGH_SCHOOLS]:
            school, count = s(row.get("school")), integer(row.get("count"))
            if school or count:
                schools.append((school, count))
        indirect_data = _get(data, "indirect") or {}
        return cls(
            housing=choice(_get(data, "housing"), HOUSING_OPTIONS),
            family_count=integer(_get(data, "family_count")),
            high_schools=schools,
            carrier=choice(_get(data, "carrier"), CARRIERS),
            mobile_subscriber=Answer.from_dict(_get(data, "mobile_subscriber") or {}),
            landline_subscriber=Answer.from_dict(_get(data, "landline_subscriber") or {}),
            loan_request=flag(_get(data, "loan_request")),
            public_property=flag(_get(data, "public_property")),
            indirect={k: Answer.from_dict(indirect_data.get(k)) for k in INDIRECT_KEYS},
            same_household=Answer.from_dict(_get(data, "same_household") or {}),
            other_region=Answer.from_dict(_get(data, "other_region") or {}),
            storm_insurance=yes_no(_get(data, "storm_insurance")),
            storm_insurance_intent=yes_no(_get(data, "storm_insurance_intent")),
        )


EVIDENCE_ITEMS = {
    "photos": "피해 사진 (생존·폐사·빈사 개체, 양식장 전경)",
    "sales_slips": "매매전표 (출하·판매)",
    "seed_docs": "수산종자 구입(생산) 관련 서류",
    "license_copy": "면허(허가)증 사본",
    "feed_receipts": "사료 구입 영수증",
    "measurement_records": "현장 측정 기록 (수온·용존산소 등, 측정자·시각·위치·기기)",
    "emergency_records": "응급조치·사료 공급 기록",
}


@dataclass
class Case:
    disaster: Disaster = field(default_factory=Disaster)
    victim: Person = field(default_factory=Person)          # 피해자 = 어업권자(행사자)
    reporter_same: bool = True                              # 신고인이 피해자 본인인지
    reporter: Person = field(default_factory=Person)        # 신고인 (본인이 아니면)
    relation: str | None = "본인"                            # 피해자와의 관계
    license: License = field(default_factory=License)
    stocking: list[StockingRow] = field(default_factory=list)
    seed_source_name: str | None = None
    seed_source_phone: str | None = None
    outs: list[OutRow] = field(default_factory=list)
    sold_at: str | None = None        # 판매일시
    buyer_contact: str | None = None  # 연락처
    buyer: str | None = None          # 판매처
    feed: list[FeedRow] = field(default_factory=list)
    pre_disaster_reported: str | None = None   # 재난 전 입식·출하 신고 여부: 예/아니오/모름
    damage: Damage = field(default_factory=Damage)
    form01: Form01Extra = field(default_factory=Form01Extra)
    evidence: dict[str, bool] = field(default_factory=dict)
    farm_lat: float | None = None
    farm_lng: float | None = None
    share_on_map: bool = False
    overflow: list[str] = field(default_factory=list)   # 원본 행 수를 넘긴 표

    @property
    def filer(self) -> Person:
        """서식에 '신고인'으로 적을 사람."""
        return self.victim if self.reporter_same else self.reporter

    @classmethod
    def from_dict(cls, data: dict) -> "Case":
        data = data if isinstance(data, dict) else {}
        stocking = [StockingRow.from_dict(r) for r in _rows(data, "stocking")]
        stocking = [r for r in stocking if not r.is_empty()]
        outs = [OutRow.from_dict(r) for r in _rows(data, "outs")]
        outs = [r for r in outs if not r.is_empty()]
        feed = [FeedRow.from_dict(r) for r in _rows(data, "feed")]
        feed = [r for r in feed if not r.is_empty()]
        overflow = []
        if len(stocking) > MAX_STOCKING_ROWS:
            overflow.append(f"입식 기록은 서식에 {MAX_STOCKING_ROWS}줄까지만 들어갑니다 ({len(stocking)}줄 입력).")
        if len(outs) > MAX_OUT_ROWS:
            overflow.append(f"출하·폐사 기록은 서식에 {MAX_OUT_ROWS}줄까지만 들어갑니다 ({len(outs)}줄 입력).")
        if len(feed) > MAX_FEED_ROWS:
            overflow.append(f"사료 구입 기록은 서식에 {MAX_FEED_ROWS}줄까지만 들어갑니다 ({len(feed)}줄 입력).")
        reporter_same = flag(data.get("reporter_same"))
        evidence_data = data.get("evidence") or {}
        farm = data.get("farm") or {}
        pre = s(data.get("pre_disaster_reported"))
        return cls(
            disaster=Disaster.from_dict(data.get("disaster")),
            victim=Person.from_dict(data.get("victim")),
            reporter_same=True if reporter_same is None else reporter_same,
            reporter=Person.from_dict(data.get("reporter")),
            relation=choice(data.get("relation"), RELATIONS) or ("본인" if reporter_same in (None, True) else None),
            license=License.from_dict(data.get("license")),
            stocking=stocking,
            seed_source_name=s(_get(data.get("seed_source"), "name")),
            seed_source_phone=s(_get(data.get("seed_source"), "phone")),
            outs=outs,
            sold_at=s(_get(data.get("sale"), "sold_at")),
            buyer_contact=s(_get(data.get("sale"), "contact")),
            buyer=s(_get(data.get("sale"), "buyer")),
            feed=feed,
            pre_disaster_reported=pre if pre in (YES, NO, UNKNOWN) else None,
            damage=Damage.from_dict(data.get("damage")),
            form01=Form01Extra.from_dict(data.get("form01")),
            evidence={k: bool(flag(evidence_data.get(k))) for k in EVIDENCE_ITEMS},
            farm_lat=num(farm.get("lat")),
            farm_lng=num(farm.get("lng")),
            share_on_map=bool(flag(farm.get("share"))),
            overflow=overflow,
        )
