import pytest

from core.attachments import AttachmentError, collect, safe_name


def test_safe_name_strips_paths_and_symbols():
    assert safe_name("C:\\fake\\dir\\사진.jpg") == "사진.jpg"
    assert safe_name("../../etc/passwd.txt") == "passwd.txt"
    assert safe_name('a<b>c:"d".pdf') == "a_b_c__d_.pdf"
    assert safe_name("   ") == "파일"
    assert len(safe_name("가" * 200 + ".pdf")) <= 80


def test_unknown_item_rejected():
    with pytest.raises(AttachmentError):
        collect({"nope": [("a.jpg", b"1")]})


def test_empty_files_skipped():
    assert collect({"photos": [("a.jpg", b"")]}) == []
