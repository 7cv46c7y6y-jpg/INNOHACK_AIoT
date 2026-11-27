"""시연 사례(data/demo_case.json)로 서식 3종 샘플을 samples/에 만든다.

실행: python scripts/make_samples.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.forms import FORMS, build  # noqa: E402
from core.model import Case  # noqa: E402


def main() -> int:
    data = json.loads((ROOT / "data" / "demo_case.json").read_text(encoding="utf-8"))
    case = Case.from_dict(data)
    out = ROOT / "samples"
    out.mkdir(exist_ok=True)
    for form_id in FORMS:
        name, content, notes = build(form_id, case)
        (out / name).write_bytes(content)
        print(f"[생성] samples/{name}")
        for note in notes:
            print(f"   - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
