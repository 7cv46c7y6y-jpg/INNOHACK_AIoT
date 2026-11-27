import io
import zipfile

import pytest
from hwpx import HwpxDocument, validate_editor_open_safety
from hwpx.experimental import estimate_pages

from core.forms import build, build_all
from core.forms.common import TEMPLATE_DIR

TEMPLATES = {
    "f01": "form01_disaster_report.hwpx",
    "f02": "form02_fishery_damage_report.hwpx",
    "f03": "form03_stocking_report.hwpx",
}
PAGES = {"f01": 3, "f02": 1, "f03": 1}


def texts(doc: HwpxDocument) -> dict:
    """(표, 행, 열) → 칸 글자."""
    out = {}
    for t in doc.tables.map()["tables"]:
        for c in t["cells"]:
            out[(t["table_index"], c["row"], c["col"])] = c["text"]
    return out


@pytest.fixture(params=["f01", "f02", "f03"])
def built(request, demo):
    form_id = request.param
    name, data, notes = build(form_id, demo)
    filled = HwpxDocument.open(io.BytesIO(data))
    blank = HwpxDocument.open(TEMPLATE_DIR / TEMPLATES[form_id])
    return form_id, name, data, texts(filled), texts(blank)


def test_opens_and_keeps_pages(built):
    form_id, name, data, _, _ = built
    assert name.startswith("초안_") and name.endswith(".hwpx")
    assert validate_editor_open_safety(data).ok
    assert estimate_pages(data).pages == PAGES[form_id]


def test_same_table_grid(built):
    _, _, _, filled, blank = built
    assert filled.keys() == blank.keys()


# ① 회색 칸·서명·동의·주민등록번호·계좌 칸은 그대로여야 한다
F01_UNCHANGED = [
    (0, 3, 0), (0, 3, 5), (0, 3, 7), (0, 3, 10), (0, 3, 14), (0, 3, 16),   # 접수번호·접수일·처리기간
    (0, 11, 4),                                                          # 지급통장
    *[(0, r, c) for r in (20, 21, 22, 30, 31, 32) for c in (4, 6, 11, 13, 17)],  # 확정·피해 구분·피해 원인
    (1, 16, 1),                                                          # 담당 공무원 확인 사항
]


def test_f01_untouched_cells(demo):
    _, data, _ = build("f01", demo)
    filled = texts(HwpxDocument.open(io.BytesIO(data)))
    blank = texts(HwpxDocument.open(TEMPLATE_DIR / TEMPLATES["f01"]))
    for key in F01_UNCHANGED:
        assert filled[key] == blank[key], key
    # 3쪽(동의서)은 한 글자도 바뀌지 않는다
    assert {k: v for k, v in filled.items() if k[0] == 2} == {k: v for k, v in blank.items() if k[0] == 2}
    # 주민등록번호 자리는 비어 있고, 서명 자리는 그대로
    assert "(주민등록번호:              -              )" in filled[(0, 8, 4)]
    assert "(서명 또는 인)" in filled[(1, 13, 0)]


def test_f01_values(demo):
    _, data, _ = build("f01", demo)
    t = texts(HwpxDocument.open(io.BytesIO(data)))
    assert t[(0, 8, 4)].strip().startswith("김바다")
    assert "소유자(실거주) [√]" in t[(0, 7, 4)]
    assert "[√]SKT" in t[(0, 12, 9)]
    assert t[(0, 16, 4)] == "① 해상가두리"
    assert t[(0, 19, 4)] == "① 12,000마리"
    assert "(품종: 조피볼락)" in t[(0, 15, 4)]
    assert "본인[√]" in t[(1, 13, 0)]
    assert "2026년" in t[(1, 13, 0)]


def test_f02_values(demo):
    _, data, _ = build("f02", demo)
    t = texts(HwpxDocument.open(io.BytesIO(data)))
    assert t[(0, 2, 2)] == "김바다"
    assert t[(0, 6, 1)] == "고수온 (추정)"
    assert "13.33%" in t[(0, 8, 1)] and "피해액: 미확인" in t[(0, 8, 1)]
    assert "(인)" in t[(0, 11, 0)]


def test_f03_values(demo):
    _, data, _ = build("f03", demo)
    t = texts(HwpxDocument.open(io.BytesIO(data)))
    assert t[(0, 13, 9)] == "100,000"          # 입식 마리 수
    assert t[(0, 12, 9)] == "100,000"          # 입식 계
    assert t[(0, 21, 1)] == "조피볼락(폐사)"
    assert t[(0, 19, 8)] == "10,000"           # 출하·폐사 계 (7,000 + 3,000)
    assert t[(0, 19, 18)] == "90,000"          # 잔량 = 재해 직전 사육량
    assert "제 2020-0123 호" in t[(0, 9, 1)]


def test_bundle_has_three_files(demo):
    name, data, notes = build_all(demo)
    assert name.endswith(".zip")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert len(zf.namelist()) == 3
