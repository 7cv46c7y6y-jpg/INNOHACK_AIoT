"""zip 안 한글 이름: Windows 탐색기가 읽는 CP949로 쓰고, UTF-8 이름은 0x7075 확장 필드에 함께 넣는지."""

import struct
import unicodedata
import zlib

from core import zip_ko
from core.attachments import Attachment, safe_name
from core.forms import build_all, build_bundle
from core.model import Case


def _central_entries(data: bytes):
    """중앙 디렉터리를 직접 읽어 (이름 바이트, 일반 목적 비트, 확장 필드) 목록을 돌려준다."""
    eocd = data.rfind(b"PK\x05\x06")
    count, _size, offset = struct.unpack("<HII", data[eocd + 10: eocd + 20])
    pos, out = offset, []
    for _ in range(count):
        assert data[pos: pos + 4] == b"PK\x01\x02"
        flag = struct.unpack("<H", data[pos + 8: pos + 10])[0]
        n, m, k = struct.unpack("<HHH", data[pos + 28: pos + 34])
        name = data[pos + 46: pos + 46 + n]
        extra = data[pos + 46 + n: pos + 46 + n + m]
        out.append((name, flag, extra))
        pos += 46 + n + m + k
    return out


def _unicode_path(extra: bytes):
    """0x7075 확장 필드에서 (버전, 이름 CRC, UTF-8 이름)을 꺼낸다. 없으면 None."""
    pos = 0
    while pos + 4 <= len(extra):
        tag, size = struct.unpack("<HH", extra[pos: pos + 4])
        body = extra[pos + 4: pos + 4 + size]
        if tag == zip_ko.UNICODE_PATH_EXTRA:
            version, crc = struct.unpack("<BI", body[:5])
            return version, crc, body[5:]
        pos += 4 + size
    return None


def _check_names(data: bytes, expected: set[str]):
    names = set()
    for raw, flag, extra in _central_entries(data):
        assert not flag & zip_ko.UTF8_FLAG, "UTF-8 표시가 붙으면 탐색기에서 깨진다"
        name = raw.decode("cp949")
        names.add(name)
        if not name.isascii():
            version, crc, utf8 = _unicode_path(extra)
            assert version == 1
            assert crc == zlib.crc32(raw)
            assert utf8.decode("utf-8") == name
    assert names == expected


def test_bundle_names_are_cp949(demo_data):
    demo_case = Case.from_dict(demo_data)
    attachments = [Attachment("sales_slips", "8월 매매전표.pdf", b"%PDF-1.4")]
    _, data = build_bundle(demo_case, attachments)
    day = demo_case.disaster.report_date.strftime("%Y%m%d")
    _check_names(data, {
        f"1_서식(서명 전 초안)/초안_어업피해발생신고서_{day}.hwpx",
        f"1_서식(서명 전 초안)/초안_자연재난피해신고서_{day}.hwpx",
        f"1_서식(서명 전 초안)/초안_입식출하판매신고서_{day}.hwpx",
        "2_증빙/02_매매전표/8월 매매전표.pdf",
        "제출목록.txt",
    })


def test_three_form_zip_names_are_cp949(demo_data):
    demo_case = Case.from_dict(demo_data)
    _, data, _ = build_all(demo_case)
    day = demo_case.disaster.report_date.strftime("%Y%m%d")
    _check_names(data, {
        f"초안_어업피해발생신고서_{day}.hwpx",
        f"초안_자연재난피해신고서_{day}.hwpx",
        f"초안_입식출하판매신고서_{day}.hwpx",
    })


def test_attachment_names_fit_cp949():
    assert safe_name("폐사 사진😀.jpg") == "폐사 사진_.jpg"
    nfd = unicodedata.normalize("NFD", "매매전표.pdf")      # macOS에서 올린 이름
    assert safe_name(nfd) == "매매전표.pdf"
    safe_name("현장 측정 기록 (수온·DO).xlsx").encode("cp949")
