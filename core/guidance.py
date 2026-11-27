"""검토 화면과 제출목록에 쓰는 서식별 제출 안내 (누가, 언제, 어디에, 참고 기한)."""

from __future__ import annotations

from . import calc
from .model import EVIDENCE_ITEMS, Case

FORMS = [
    {
        "id": "f02",
        "name": "어업피해발생신고서",
        "who": "피해 어업인",
        "when": "피해가 나면 지체 없이",
        "where": "피해 어장을 관할하는 읍·면·동장",
        "basis": "어업재해 피해조사·보고 및 복구지원 요령 제6조",
        "note": "지체 없이 신고한 어가만 어업재해 피해조사 대상이 됩니다.",
    },
    {
        "id": "f01",
        "name": "자연재난 피해신고서",
        "who": "신고인 (본인·가족·이장·통장·이웃)",
        "when": "재난이 끝난 날부터 10일 이내",
        "where": "시장·군수·구청장 (읍·면사무소, 동 주민센터에도 제출 가능)",
        "basis": "자연재난 구호 및 복구 비용 부담기준 등에 관한 규정 제9조",
        "note": "양식업은 입식·출하·판매 신고서와 매매전표·수산종자 구입 서류를 함께 냅니다.",
    },
    {
        "id": "f03",
        "name": "입식·출하·판매 신고서",
        "who": "신고인·어업권자",
        "when": "평소: 입식 후 20일 이내, 출하·판매는 다음 달 5일까지 / 피해 신고 때 자연재난 피해신고서와 함께",
        "where": "시장·군수·구청장",
        "basis": "같은 규정 제9조 제3·4항",
        "note": "재난 전에 이 신고를 해 둔 경우에만 양식업 재난지원금이 나옵니다.",
    },
]

def build(case: Case) -> dict:
    deadline = calc.report_deadline(case)
    forms = []
    for f in FORMS:
        item = dict(f)
        if f["id"] in ("f01", "f03"):
            item["due"] = deadline.due.isoformat() if deadline.due else None
            item["due_note"] = deadline.note
        else:
            item["due"] = None
            item["due_note"] = "지체 없이"
        forms.append(item)
    return {
        "forms": forms,
        "evidence": [
            {"key": k, "label": label, "ready": bool(case.evidence.get(k))}
            for k, label in EVIDENCE_ITEMS.items()
        ],
    }
