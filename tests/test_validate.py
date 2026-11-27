from core import validate
from core.model import Case


def fields(result, level="errors"):
    return {i["field"] for i in result[level]}


def test_demo_is_valid(demo):
    result = validate.check(demo)
    assert result["ok"], result["errors"]


def test_missing_required(demo_data):
    demo_data["victim"]["name"] = ""
    demo_data["license"]["number"] = ""
    result = validate.check(Case.from_dict(demo_data))
    assert not result["ok"]
    assert {"victim.name", "license.number"} <= fields(result)


def test_damage_more_than_stock(demo_data):
    demo_data["damage"]["dead_count"] = "95000"
    result = validate.check(Case.from_dict(demo_data))
    assert "damage.dead_count" in fields(result)


def test_negative_count(demo_data):
    demo_data["stocking"][0]["count"] = "-5"
    result = validate.check(Case.from_dict(demo_data))
    assert "stocking.1" in fields(result)


def test_date_order(demo_data):
    demo_data["disaster"]["damage_end"] = "2026-08-01"
    demo_data["stocking"][0]["date"] = "2026-09-01"
    result = validate.check(Case.from_dict(demo_data))
    assert {"disaster.damage_end", "stocking.1"} <= fields(result)


def test_too_many_rows(demo_data):
    demo_data["outs"] = demo_data["outs"] * 3   # 6줄 > 4줄
    result = validate.check(Case.from_dict(demo_data))
    assert "rows" in fields(result)


def test_pre_disaster_report_warning(demo_data):
    demo_data["pre_disaster_reported"] = "아니오"
    result = validate.check(Case.from_dict(demo_data))
    assert result["ok"]
    assert "pre_disaster_reported" in fields(result, "warnings")


def test_amount_mismatch_warning(demo_data):
    demo_data["outs"][0]["amount_kwon"] = "10000"
    result = validate.check(Case.from_dict(demo_data))
    assert "outs.1" in fields(result, "warnings")


def test_unknown_items_listed(demo_data):
    demo_data["form01"]["housing"] = ""
    result = validate.check(Case.from_dict(demo_data))
    assert "주거 형태" in result["unknown"][validate.F1]
