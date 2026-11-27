"""서식 기재 규칙 (config/form_rules.json) 불러오기."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "form_rules.json"


@lru_cache(maxsize=1)
def load() -> dict:
    with RULES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def get(form: str, key: str, default=None):
    return load().get(form, {}).get(key, default)


def fmt_date(d: date | None) -> str:
    if d is None:
        return ""
    return get("common", "date_format", "{y}.{m:02d}.{d:02d}").format(y=d.year, m=d.month, d=d.day)


def fmt_int(n: int | float | None) -> str:
    if n is None:
        return ""
    return f"{int(round(n)):,}"


def fmt_num(n: float | None) -> str:
    """정수면 소수점 없이, 아니면 소수 첫째 자리까지."""
    if n is None:
        return ""
    if abs(n - round(n)) < 1e-9:
        return f"{int(round(n)):,}"
    return f"{n:,.1f}"
