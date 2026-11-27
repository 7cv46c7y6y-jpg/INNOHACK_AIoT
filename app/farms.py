"""가두리 피해 지도 데이터.

- data/seed_farms.json: 미리 넣은 가상 어가 (항상 표시)
- data/farms_added.json: 화면에서 새로 올린 값 (서버가 재시작되면 지워질 수 있음)
지도에는 이름·주소·면허번호 같은 개인 식별 정보를 저장하지도, 보여 주지도 않는다.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import date
from pathlib import Path

from core import calc
from core.model import Case

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEED_PATH = DATA_DIR / "seed_farms.json"
ADDED_PATH = DATA_DIR / "farms_added.json"
MAX_ADDED = 500

# 대한민국 바다 근처로 위치를 제한한다 (잘못 찍힌 값 방지)
LAT_RANGE = (32.5, 39.0)
LNG_RANGE = (124.0, 132.0)

_lock = threading.Lock()


def _read(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    farms = data.get("farms", []) if isinstance(data, dict) else data
    return [f for f in farms if isinstance(f, dict)]


def all_farms() -> list[dict]:
    seeds = [dict(f, source="가상 데이터") for f in _read(SEED_PATH)]
    with _lock:
        added = [dict(f, source="화면에서 입력") for f in _read(ADDED_PATH)]
    return seeds + added


def point_from_case(case: Case) -> dict:
    """사례에서 지도에 올릴 값만 뽑는다 (개인 식별 정보 제외)."""
    if case.farm_lat is None or case.farm_lng is None:
        raise ValueError("지도에서 가두리 위치를 먼저 찍어 주세요.")
    if not (LAT_RANGE[0] <= case.farm_lat <= LAT_RANGE[1] and LNG_RANGE[0] <= case.farm_lng <= LNG_RANGE[1]):
        raise ValueError("위치가 우리나라 바다 범위를 벗어났습니다.")
    rate = calc.damage_rate(case)
    if rate is None:
        raise ValueError("피해율을 계산할 수 없습니다. 입식·출하 기록과 피해량을 확인해 주세요.")
    temp = case.damage.water_temp_c
    if temp is not None and not (-5 <= temp <= 40):
        raise ValueError("수온 값이 이상합니다 (-5~40℃).")
    return {
        "id": f"user-{uuid.uuid4().hex[:8]}",
        "lat": round(case.farm_lat, 4),
        "lng": round(case.farm_lng, 4),
        "species": case.license.species,
        "damage_rate": rate,
        "water_temp_c": temp,
        "measured_at": case.damage.temp_measured_at,
        "recorded_on": date.today().isoformat(),
    }


def add(point: dict) -> dict:
    with _lock:
        added = _read(ADDED_PATH)
        added.append(point)
        added = added[-MAX_ADDED:]
        ADDED_PATH.parent.mkdir(parents=True, exist_ok=True)
        ADDED_PATH.write_text(json.dumps({"farms": added}, ensure_ascii=False, indent=1), encoding="utf-8")
    return dict(point, source="화면에서 입력")
