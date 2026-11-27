"""서식 채우기 공통 도구.

원본 서식의 표 칸을 (표 번호, 행, 열)로 찾아 값을 넣는다.
- 빈 칸: set_cell (값이 칸에 맞도록 줄바꿈 → 글자 축소, 행 높이는 유지)
- 이름표가 있는 칸: append (이름표 뒤에 값을 붙임)
- '(휴대폰:        )'처럼 빈칸이 있는 칸: fill_gap (빈칸 너비를 최대한 유지)
- '[  ]' 체크 칸: check
회색 칸·서명란·주민등록번호·계좌번호 칸은 건드리지 않는다.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from hwpx import HwpxDocument
from hwpx.form_fit import FitPolicy

from .. import rules

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "forms_tpl"


def visual_len(text: str) -> int:
    """한글·전각 문자는 2칸, 나머지는 1칸으로 센 너비."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F", "A") and ord(ch) > 0x2000 else 1 for ch in text)


class FormFiller:
    def __init__(self, template_name: str):
        self.doc = HwpxDocument.open(TEMPLATE_DIR / template_name)
        self.notes: list[str] = []   # 글자 축소 등 확인할 점
        self.mark = rules.get("common", "check_mark", "√")

    # ------------------------------------------------------------ 찾기
    def cell(self, t: int, r: int, c: int):
        return self.doc.tables[t].cell(r, c)

    def para(self, t: int, r: int, c: int, p: int = 0):
        return self.cell(t, r, c).paragraphs[p]

    # ------------------------------------------------------------ 쓰기
    def set_cell(self, t: int, r: int, c: int, text: str | None, *, min_pt: float = 6.0,
                 mode: str = "wrap_then_shrink", label: str = "") -> None:
        """칸 전체를 text로 바꾼다. 칸에 다 안 들어가면 글자를 줄이고, 그래도 안 되면 기록한다."""
        if not text:
            return
        policy = FitPolicy(mode=mode, min_font_pt=min_pt, overflow="warn")
        result = self.doc.tables[t].set_cell_text(r, c, text, fit=policy)
        self._note(result, label or text)

    def append(self, t: int, r: int, c: int, value: str | None, p: int = 0, sep: str = " ") -> None:
        """이름표 문단 끝에 값을 붙인다 (예: '생년월일' → '생년월일 1970.01.01')."""
        if not value:
            return
        para = self.para(t, r, c, p)
        text = para.text
        trimmed = len(text.rstrip(" "))
        if trimmed < len(text):           # 끝 공백은 값으로 대신한다
            para.replace_range(trimmed, len(text), sep + value)
        else:
            para.insert_text(len(text), sep + value)

    def fill_gap(self, t: int, r: int, c: int, after: str, value: str | None, p: int = 0,
                 occurrence: int = 0) -> None:
        """`after` 바로 뒤의 공백 묶음을 값으로 바꾼다. 남는 너비는 공백으로 채워 배치를 유지한다."""
        if not value:
            return
        para = self.para(t, r, c, p)
        text = para.text
        idx = -1
        for _ in range(occurrence + 1):
            idx = text.find(after, idx + 1)
            if idx < 0:
                raise ValueError(f"표{t} r{r}c{c}에서 '{after}'를 찾지 못했습니다: {text!r}")
        start = idx + len(after)
        end = start
        while end < len(text) and text[end] == " ":
            end += 1
        gap = end - start
        new = f" {value} "
        pad = gap - visual_len(new)
        if pad > 0:
            new += " " * pad
        para.replace_range(start, end, new)

    def fill_before(self, t: int, r: int, c: int, before: str, value: str | None, p: int = 0) -> None:
        """`before` 바로 앞의 공백 묶음을 값으로 바꾼다 (예: '         명' → '      4 명')."""
        if not value:
            return
        para = self.para(t, r, c, p)
        text = para.text
        idx = text.find(before)
        if idx < 0:
            raise ValueError(f"표{t} r{r}c{c}에서 '{before}'를 찾지 못했습니다: {text!r}")
        start = idx
        while start > 0 and text[start - 1] == " ":
            start -= 1
        gap = idx - start
        new = f"{value} "
        pad = gap - visual_len(new)
        if pad > 0:
            new = " " * pad + new
        para.replace_range(start, idx, new)

    def replace_text(self, t: int, r: int, c: int, old: str, new: str, p: int = 0) -> None:
        para = self.para(t, r, c, p)
        idx = para.text.find(old)
        if idx < 0:
            raise ValueError(f"표{t} r{r}c{c}에서 '{old}'를 찾지 못했습니다: {para.text!r}")
        para.replace_range(idx, idx + len(old), new)

    def check(self, t: int, r: int, c: int, label: str, *, side: str = "after", p: int | None = None) -> None:
        """label 옆의 '[  ]'를 '[√]'로 바꾼다. side='after'는 '예[  ]', 'before'는 '[ ]KT' 모양."""
        cell = self.cell(t, r, c)
        paragraphs = cell.paragraphs if p is None else [cell.paragraphs[p]]
        if side == "after":
            pattern = re.compile(re.escape(label) + r" ?\[( *)\]")
        else:
            pattern = re.compile(r"\[( *)\]" + re.escape(label))
        for para in paragraphs:
            m = pattern.search(para.text)
            if m:
                para.replace_range(m.start(1), m.end(1), self.mark)
                return
        raise ValueError(f"표{t} r{r}c{c}에서 '{label}' 체크 칸을 찾지 못했습니다.")

    def check_box_only(self, t: int, r: int, c: int) -> None:
        """칸에 '[  ]' 하나만 있는 경우."""
        para = self.para(t, r, c, 0)
        m = re.search(r"\[( *)\]", para.text)
        if not m:
            raise ValueError(f"표{t} r{r}c{c}에 체크 칸이 없습니다.")
        para.replace_range(m.start(1), m.end(1), self.mark)

    # ------------------------------------------------------------ 결과
    def _note(self, result, label: str) -> None:
        if result is None:
            return
        ok = getattr(result, "ok", True)
        overflow = getattr(result, "overflow_detected", False)
        font = getattr(result, "font_pt", None)
        if not ok or overflow:
            self.notes.append(f"'{label}' 값이 칸에 다 들어가지 않아 줄이 늘어날 수 있습니다. 한글에서 확인해 주세요.")
        elif getattr(result, "style_changed", False) and font:
            before = (getattr(result, "applied_style_changes", {}) or {}).get("from_font_pt")
            if before is not None and before > font:
                self.notes.append(f"'{label}' 값은 칸에 맞추려고 글자를 {font:g}pt로 줄였습니다.")

    def to_bytes(self) -> bytes:
        return self.doc.to_bytes()
