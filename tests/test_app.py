import io
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
    for url in ("/", "/map", "/healthz"):
        assert client.get(url).status_code == 200


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
