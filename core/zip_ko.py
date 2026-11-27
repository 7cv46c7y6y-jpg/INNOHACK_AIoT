"""한글 파일 이름이 깨지지 않는 zip 쓰기.

파이썬 zipfile 은 한글 이름을 UTF-8로 쓰고 'UTF-8 이름' 표시를 붙인다. 그런데 Windows 탐색기의
'압축 풀기'는 이 표시를 무시하고 시스템 코드 페이지(한국어 Windows는 CP949)로 읽어서 이름이 깨진다.
그래서 이름은 CP949로 쓰고, UTF-8을 읽는 프로그램(7-Zip, 반디집, macOS·리눅스 unzip, 파이썬)을 위해
같은 이름을 Info-ZIP Unicode Path 확장 필드(0x7075)에 UTF-8로도 넣는다.
"""

from __future__ import annotations

import struct
import time
import zipfile
import zlib

UTF8_FLAG = 0x800          # 일반 목적 비트 11: 이름이 UTF-8
UNICODE_PATH_EXTRA = 0x7075


def cp949_safe(text: str) -> str:
    """CP949로 쓸 수 없는 글자(이모지 등)를 '_'로 바꾼다."""
    out = []
    for ch in text:
        try:
            ch.encode("cp949")
        except UnicodeEncodeError:
            ch = "_"
        out.append(ch)
    return "".join(out)


class _CP949Info(zipfile.ZipInfo):
    """이름을 CP949로 쓰는 ZipInfo. CP949로 못 쓰는 이름은 파이썬 기본(UTF-8 + 표시)으로 쓴다."""

    def _encodeFilenameFlags(self):
        try:
            return self.filename.encode("cp949"), self.flag_bits & ~UTF8_FLAG
        except UnicodeEncodeError:
            return self.filename.encode("utf-8"), self.flag_bits | UTF8_FLAG


def add(zf: zipfile.ZipFile, name: str, data: bytes | str) -> None:
    """zf 에 name 으로 data 를 넣는다 (압축 방식은 zf 를 따름)."""
    info = _CP949Info(name, date_time=time.localtime()[:6])
    info.compress_type = zf.compression
    info.external_attr = 0o600 << 16
    if not name.isascii():
        try:
            raw = name.encode("cp949")
        except UnicodeEncodeError:
            raw = None
        if raw is not None:
            body = struct.pack("<BI", 1, zlib.crc32(raw)) + name.encode("utf-8")
            info.extra = struct.pack("<HH", UNICODE_PATH_EXTRA, len(body)) + body
    zf.writestr(info, data)
