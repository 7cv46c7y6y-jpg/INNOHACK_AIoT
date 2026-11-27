from datetime import date

from core import calc
from core.model import Case


def test_demo_numbers(demo):
    s = calc.summary(demo)
    assert s["stock_before"] == 90_000          # 100,000 − 7,000 − 3,000
    assert s["damage_rate"] == 13.33            # 12,000 ÷ 90,000
    assert s["remaining_by_row"] == [93_000, 90_000]


def test_same_input_same_result(demo_data):
    a = calc.summary(Case.from_dict(demo_data))
    b = calc.summary(Case.from_dict(demo_data))
    assert a == b


def _case_with_end(end: str) -> Case:
    return Case.from_dict({"disaster": {"disaster_end": end}})


def test_deadline_weekday():
    assert calc.report_deadline(_case_with_end("2026-08-25")).due == date(2026, 9, 4)


def test_deadline_rolls_over_weekend():
    # 2026-09-02 + 10일 = 9/12(토) → 9/14(월)
    assert calc.report_deadline(_case_with_end("2026-09-02")).due == date(2026, 9, 14)


def test_deadline_rolls_over_holiday():
    # 2026-09-25 + 10일 = 10/5 (개천절 대체공휴일) → 10/6
    assert calc.report_deadline(_case_with_end("2026-09-25")).due == date(2026, 10, 6)


def test_deadline_unknown():
    assert calc.report_deadline(Case.from_dict({})).due is None


def test_rate_needs_stock():
    case = Case.from_dict({"damage": {"dead_count": "10"}})
    assert calc.damage_rate(case) is None
