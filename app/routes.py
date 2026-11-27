"""화면과 API.

- GET  /                 입력 화면 (단계별)
- GET  /map              가두리 피해 지도
- GET  /api/demo         시연 사례
- POST /api/review       계산·검증·안내 (입력 JSON)
- POST /api/forms/<id>   서식 HWPX 내려받기 (f01, f02, f03, all=zip). 생성 파일은 서버에 저장하지 않는다.
- GET  /api/farms        지도 데이터
- POST /api/farms        지도에 올리기 (개인 식별 정보는 저장하지 않음)
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException

from core import calc, guidance, validate
from core.forms import FORMS, build, build_all
from core.model import Case

from . import farms

bp = Blueprint("main", __name__)
DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_case.json"
HWPX_MIME = "application/hwp+zip"


class BadInput(Exception):
    pass


def _case() -> Case:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadInput("입력 형식이 올바르지 않습니다.")
    return Case.from_dict(data)


@bp.errorhandler(BadInput)
def _bad_input(err: BadInput):
    return jsonify(error=str(err)), 400


@bp.app_errorhandler(HTTPException)
def _http_error(err: HTTPException):
    if request.path.startswith("/api/"):
        messages = {413: "입력이 너무 큽니다.", 404: "찾는 주소가 없습니다.", 405: "허용되지 않는 요청입니다."}
        return jsonify(error=messages.get(err.code, err.description)), err.code
    return err


# ------------------------------------------------------------------ 화면
@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/map")
def map_page():
    return render_template("map.html")


@bp.get("/healthz")
def healthz():
    return "ok"


# ------------------------------------------------------------------ API
@bp.get("/api/demo")
def demo():
    data = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
    data.pop("_설명", None)
    return jsonify(data)


@bp.post("/api/review")
def review():
    case = _case()
    result = validate.check(case)
    notes = {}
    if result["ok"]:
        for form_id in FORMS:
            _, _, form_notes = build(form_id, case)
            notes[form_id] = form_notes
    return jsonify(
        summary=calc.summary(case),
        validation=result,
        guidance=guidance.build(case),
        notes=notes,
    )


@bp.post("/api/forms/<form_id>")
def download(form_id: str):
    if form_id != "all" and form_id not in FORMS:
        return jsonify(error="없는 서식입니다."), 404
    case = _case()
    result = validate.check(case)
    if not result["ok"]:
        return jsonify(error="입력 오류를 먼저 고쳐 주세요.", errors=result["errors"]), 422
    if form_id == "all":
        name, data, _ = build_all(case)
        mime = "application/zip"
    else:
        name, data, _ = build(form_id, case)
        mime = HWPX_MIME
    response = send_file(io.BytesIO(data), mimetype=mime, as_attachment=True, download_name=name)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/api/farms")
def list_farms():
    return jsonify(farms=farms.all_farms())


@bp.post("/api/farms")
def add_farm():
    case = _case()
    if not case.share_on_map:
        raise BadInput("지도에 올리려면 공유에 동의해 주세요.")
    try:
        point = farms.point_from_case(case)
    except ValueError as err:
        raise BadInput(str(err)) from err
    return jsonify(farm=farms.add(point))
