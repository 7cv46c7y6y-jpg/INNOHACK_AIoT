"""계산: 재해 직전 사육량, 피해율, 잔량, 신고 기한."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .model import Case

try:  # 공휴일 목록 (없으면 주말만 넘긴다)
    import holidays as _holidays
except ImportError:  # pragma: no cover
    _holidays = None

REPORT_DAYS = 10  # 자연재난 규정 제9조: 재난이 종료된 날부터 10일 이내


def total_stocked(case: Case) -> int:
    return sum(r.count or 0 for r in case.stocking)


def total_out(case: Case, kind: str) -> int:
    return sum(r.count or 0 for r in case.outs if r.kind == kind)


def stock_before(case: Case) -> int | None:
    """재해 직전 사육량 = 입식 − 출하 − 기존 폐사 (마리). 입식 기록이 없으면 None."""
    if not any(r.count for r in case.stocking):
        return None
    return total_stocked(case) - total_out(case, "출하") - total_out(case, "폐사")


def damage_rate(case: Case) -> float | None:
    """피해율(%) = 이번 피해량 ÷ 재해 직전 사육량 × 100, 소수 둘째 자리 반올림.

    요령의 양식수산물 피해 기준(피해 당시 사육 물량 대비 피해물량)과 같은 정의.
    공적으로 확정된 값이 아닌 참고값이다.
    """
    stock = stock_before(case)
    dead = case.damage.dead_count
    if not stock or stock <= 0 or dead is None:
        return None
    return round(dead / stock * 100, 2)


def remaining_by_row(case: Case) -> list[int | None]:
    """③ 출하·폐사 표의 행별 잔량(마리). 같은 품종의 입식 합계에서 차례로 뺀다."""
    stocked: dict[str | None, int] = {}
    for r in case.stocking:
        stocked[r.species] = stocked.get(r.species, 0) + (r.count or 0)
    left = dict(stocked)
    result: list[int | None] = []
    for r in case.outs:
        key = r.species if r.species in left else (next(iter(left)) if len(left) == 1 else None)
        if key is None or r.count is None:
            result.append(None)
            continue
        left[key] -= r.count
        result.append(left[key])
    return result


def is_day_off(d: date) -> bool:
    if d.weekday() >= 5:
        return True
    if _holidays is not None:
        return d in _holidays.country_holidays("KR", years=[d.year])
    return False


@dataclass
class Deadline:
    due: date | None
    note: str


def report_deadline(case: Case) -> Deadline:
    """①③ 신고 기한 (참고). 재난 종료일 다음 날부터 세어 10일째, 쉬는 날이면 다음 평일."""
    end = case.disaster.disaster_end
    if end is None:
        return Deadline(None, "재난 종료일(예: 고수온 특보 해제일)을 입력하면 기한을 계산합니다.")
    due = end + timedelta(days=REPORT_DAYS)
    while is_day_off(due):
        due += timedelta(days=1)
    return Deadline(due, "참고 기한이며 지자체 공고가 우선합니다.")


def summary(case: Case) -> dict:
    """화면과 서식에서 함께 쓰는 계산 결과."""
    deadline = report_deadline(case)
    return {
        "total_stocked": total_stocked(case) if case.stocking else None,
        "total_shipped": total_out(case, "출하"),
        "total_prior_dead": total_out(case, "폐사"),
        "stock_before": stock_before(case),
        "dead_count": case.damage.dead_count,
        "damage_rate": damage_rate(case),
        "remaining_by_row": remaining_by_row(case),
        "deadline_01_03": deadline.due.isoformat() if deadline.due else None,
        "deadline_note": deadline.note,
        "deadline_02": "지체 없이 (피해를 알게 된 즉시)",
    }
