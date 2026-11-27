import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def demo_data() -> dict:
    with (ROOT / "data" / "demo_case.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def demo(demo_data):
    from core.model import Case
    return Case.from_dict(copy.deepcopy(demo_data))
