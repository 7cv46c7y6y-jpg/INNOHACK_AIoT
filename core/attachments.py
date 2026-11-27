"""증빙 첨부 파일 검사.

첨부 파일은 제출 묶음(zip)을 만들 때만 메모리에서 쓰고 서버에 저장하지 않는다.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import PurePath

from .model import EVIDENCE

MAX_TOTAL_BYTES = 20 * 1024 * 1024   # 합계 20MB
MAX_FILES = 30
ALLOWED_EXT = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff",
    ".pdf", ".hwp", ".hwpx", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt",
}
ACCEPT = ",".join(sorted(ALLOWED_EXT))


class AttachmentError(ValueError):
    pass


@dataclass
class Attachment:
    key: str        # 증빙 항목 (EVIDENCE의 키)
    filename: str   # 묶음 안 파일 이름 (정리된 이름)
    data: bytes


def safe_name(name: str) -> str:
    """경로·특수문자를 빼고 80자 안으로 줄인 파일 이름."""
    base = PurePath(str(name).replace("\\", "/")).name
    base = unicodedata.normalize("NFC", base)
    base = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", base).strip(" .")
    if not base:
        base = "파일"
    stem, dot, ext = base.rpartition(".")
    if not dot:
        stem, ext = base, ""
    ext = f".{ext}" if ext else ""
    stem = stem[: max(1, 80 - len(ext))]
    return stem + ext


def collect(files: dict[str, list[tuple[str, bytes]]]) -> list[Attachment]:
    """항목별 (파일 이름, 내용) 목록을 검사해 Attachment 목록으로 바꾼다."""
    out: list[Attachment] = []
    total = 0
    count = 0
    used: dict[str, set[str]] = {}
    for key, items in files.items():
        if key not in EVIDENCE:
            raise AttachmentError(f"알 수 없는 증빙 항목입니다: {key}")
        for original, data in items:
            if not data:
                continue
            count += 1
            total += len(data)
            if count > MAX_FILES:
                raise AttachmentError(f"증빙 파일은 {MAX_FILES}개까지 첨부할 수 있습니다.")
            if total > MAX_TOTAL_BYTES:
                raise AttachmentError(f"증빙 파일은 합계 {MAX_TOTAL_BYTES // (1024 * 1024)}MB까지 첨부할 수 있습니다.")
            name = safe_name(original)
            ext = PurePath(name).suffix.lower()
            if ext not in ALLOWED_EXT:
                raise AttachmentError(f"'{name}'은(는) 첨부할 수 없는 형식입니다. 사진·PDF·한글·워드·엑셀 파일만 됩니다.")
            seen = used.setdefault(key, set())
            unique, n = name, 2
            while unique in seen:
                stem = PurePath(name).stem
                unique = f"{stem} ({n}){ext}"
                n += 1
            seen.add(unique)
            out.append(Attachment(key, unique, data))
    return out
