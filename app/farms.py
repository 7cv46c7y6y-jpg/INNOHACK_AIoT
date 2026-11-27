"""가두리 피해 지도 데이터.

data/seed_farms.json 의 시연용 가상 어가를 보여 준다.
지도에는 이름·주소·면허번호 같은 개인 식별 정보가 없다.
(작성 화면에서 가두리 위치를 받지 않으므로 화면에서 지도에 올리는 기능은 없다.)
"""

from __future__ import annotations

import json
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_farms.json"


def all_farms() -> list[dict]:
    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    farms = data.get("farms", []) if isinstance(data, dict) else data
    return [dict(f, source="가상 데이터") for f in farms if isinstance(f, dict)]
