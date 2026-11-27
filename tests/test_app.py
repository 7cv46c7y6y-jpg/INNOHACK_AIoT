import io
import json
import zipfile
from urllib.parse import unquote

import pytest
from hwpx import HwpxDocument

from app import create_app
from app import farms as farms_mod


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(farms_mod, "ADDED_PATH", tmp_path / "farms_added.json")
    app = create_app()
    app.testing = True
    return app.test_client()


def test_pages(client):
    for url in ("/", "/apply", "/map", "/healthz"):
        assert client.get(url).status_code == 200
    home = client.get("/").get_data(as_text=True)
    assert "피해보상 서류 작성" in home
    assert "<div>홈</div>" in home              # 메뉴 이름
    assert "mini-map" not in home              # 지도는 피해 지도 화면에만
    assert "layout-navbar" not in home         # 위쪽 바 없음
    assert "신고 순서" in home and "#how" not in home   # 신고 순서는 홈 카드로만 (메뉴에서 뺌)
    page = client.get("/apply").get_data(as_text=True)
    for section in ("sec-disaster", "sec-farm", "sec-records", "sec-damage", "sec-extra", "sec-evidence", "sec-review"):
        assert section in page        # 한 페이지에 모든 단계
    assert 'data-evidence-files="sales_slips"' in page


def test_review_demo(client, demo_data):
    res = client.post("/api/review", json=demo_data)
    assert res.status_code == 200
    out = res.get_json()
    assert out["validation"]["ok"]
    assert out["summary"]["stock_before"] == 90000
    assert out["summary"]["damage_rate"] == 13.33
    assert len(out["guidance"]["forms"]) == 3
    assert set(out["notes"]) == {"f01", "f02", "f03"}


@pytest.mark.parametrize("form_id", ["f01", "f02", "f03"])
def test_download_form(client, demo_data, form_id):
    res = client.post(f"/api/forms/{form_id}", json=demo_data)
    assert res.status_code == 200
    assert "초안_" in unquote(res.headers["Content-Disposition"])
    assert res.headers["Cache-Control"] == "no-store"
    HwpxDocument.open(io.BytesIO(res.data))   # 열려야 한다


def test_download_all_zip(client, demo_data):
    res = client.post("/api/forms/all", json=demo_data)
    assert res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(res.data)) as zf:
        assert len(zf.namelist()) == 3


def test_download_blocked_on_error(client, demo_data):
    demo_data["victim"]["name"] = ""
    res = client.post("/api/forms/f01", json=demo_data)
    assert res.status_code == 422
    assert res.get_json()["errors"]


def test_bad_input(client):
    assert client.post("/api/review", data="nope", content_type="text/plain").status_code == 400
    assert client.post("/api/forms/zz", json={}).status_code == 404


def test_farms_share_without_personal_info(client, demo_data):
    before = len(client.get("/api/farms").get_json()["farms"])
    res = client.post("/api/farms", json=demo_data)
    assert res.status_code == 200
    farm = res.get_json()["farm"]
    assert farm["damage_rate"] == 13.33
    assert not {"name", "address", "license", "victim"} & set(farm)
    after = client.get("/api/farms").get_json()["farms"]
    assert len(after) == before + 1


def test_farms_needs_consent(client, demo_data):
    demo_data["farm"]["share"] = False
    assert client.post("/api/farms", json=demo_data).status_code == 400


def _bundle(client, demo_data, files):
    data = {"case": json.dumps(demo_data, ensure_ascii=False)}
    for field, name, content in files:
        data.setdefault(field, [])
        data[field].append((io.BytesIO(content), name))
    return client.post("/api/bundle", data=data, content_type="multipart/form-data")


def test_bundle_with_evidence(client, demo_data):
    demo_data["evidence"]["measurement_records"] = False
    res = _bundle(client, demo_data, [
        ("evidence.sales_slips", "전표 1.pdf", b"%PDF-1.4 test"),
        ("evidence.sales_slips", "전표 1.pdf", b"%PDF-1.4 again"),          # 같은 이름은 (2)로
        ("evidence.measurement_records", "수온기록.xlsx", b"PK fake"),
    ])
    assert res.status_code == 200, res.get_data(as_text=True)
    assert "제출묶음" in unquote(res.headers["Content-Disposition"])
    with zipfile.ZipFile(io.BytesIO(res.data)) as zf:
        names = zf.namelist()
        assert sum(n.startswith("1_서식") and n.endswith(".hwpx") for n in names) == 3
        assert "2_증빙/02_매매전표/전표 1.pdf" in names
        assert "2_증빙/02_매매전표/전표 1 (2).pdf" in names
        assert "2_증빙/06_현장측정기록/수온기록.xlsx" in names
        text = zf.read("제출목록.txt").decode("utf-8-sig")
        assert "매매전표" in text and "전표 1.pdf" in text
        assert "현장 측정 기록 →" in text          # 첨부하면 준비됨으로 본다
        assert "[아직 준비하지 않은 증빙]" not in text


def test_bundle_without_files(client, demo_data):
    res = _bundle(client, demo_data, [])
    assert res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(res.data)) as zf:
        assert "제출목록.txt" in zf.namelist()


def test_bundle_rejects_bad_type(client, demo_data):
    res = _bundle(client, demo_data, [("evidence.photos", "virus.exe", b"MZ")])
    assert res.status_code == 400
    assert "형식" in res.get_json()["error"]


def test_bundle_rejects_too_big(client, demo_data, monkeypatch):
    from core import attachments
    monkeypatch.setattr(attachments, "MAX_TOTAL_BYTES", 10)
    res = _bundle(client, demo_data, [("evidence.photos", "a.jpg", b"x" * 20)])
    assert res.status_code == 400


def test_bundle_blocked_on_error(client, demo_data):
    demo_data["victim"]["name"] = ""
    res = _bundle(client, demo_data, [])
    assert res.status_code == 422
