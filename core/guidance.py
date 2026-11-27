"""검토 화면에 보여 줄 안내 (서식별 제출 정보, 동의, 조사 준비)."""

from __future__ import annotations

from . import calc
from .model import EVIDENCE_ITEMS, Case

FORMS = [
    {
        "id": "f02",
        "name": "② 어업피해발생신고서",
        "who": "피해 어업인",
        "when": "피해가 나면 지체 없이",
        "where": "피해 어장을 관할하는 읍·면·동장",
        "basis": "어업재해 피해조사·보고 및 복구지원 요령 제6조",
        "note": "지체 없이 신고한 어가만 어업재해 피해조사 대상이 됩니다.",
    },
    {
        "id": "f01",
        "name": "① 자연재난 피해신고서",
        "who": "신고인 (본인·가족·이장·통장·이웃)",
        "when": "재난이 끝난 날부터 10일 이내",
        "where": "시장·군수·구청장 (읍·면사무소, 동 주민센터에도 제출 가능)",
        "basis": "자연재난 구호 및 복구 비용 부담기준 등에 관한 규정 제9조",
        "note": "양식업은 ③ 신고서와 매매전표·수산종자 구입 서류를 함께 냅니다.",
    },
    {
        "id": "f03",
        "name": "③ 입식·출하·판매 신고서",
        "who": "신고인·어업권자",
        "when": "평소: 입식 후 20일 이내, 출하·판매는 다음 달 5일까지 / 피해 신고 때 ①과 함께",
        "where": "시장·군수·구청장",
        "basis": "같은 규정 제9조 제3·4항",
        "note": "재난 전에 이 신고를 해 둔 경우에만 양식업 재난지원금이 나옵니다.",
    },
]

CONSENTS = [
    {
        "name": "행정정보 공동이용 동의",
        "meaning": "담당 공무원이 주민등록표 등본, 소득금액 증명, 가족관계증명서를 직접 확인합니다.",
        "if_not": "동의하지 않으면 신고인이 이 서류를 직접 내야 합니다.",
    },
    {
        "name": "개인정보 수집·이용 동의",
        "meaning": "시·군·구가 재난지원금 등 지원 확인 자료로 개인정보를 씁니다.",
        "if_not": "서식에는 동의하지 않을 때의 처리 방법이 적혀 있지 않습니다. 담당 공무원에게 확인해 주세요.",
    },
    {
        "name": "제3자 제공·활용 동의: 융자 등 간접 지원 기관",
        "meaning": "융자 등 간접 지원을 위해 공공기관과 관련 기관에 정보를 제공합니다.",
        "if_not": "동의하지 않으면 그 기관에 관련 서류를 직접 내야 합니다.",
    },
    {
        "name": "제3자 제공·활용 동의: 의연금 배분위원회",
        "meaning": "의연금품 배분을 위해 배분위원회에 정보를 제공합니다.",
        "if_not": "동의하지 않으면 배분위원회에 관련 서류를 직접 내야 합니다.",
    },
    {
        "name": "제3자 제공·활용 동의: 행정안전부 접수 알림",
        "meaning": "피해신고서 접수 여부를 알려 주기 위해 행정안전부에 정보를 제공합니다.",
        "if_not": "동의하지 않으면 접수 여부 알림이 오지 않습니다.",
    },
]

SURVEY_PREP = [
    "양식장·면허 정보와 최초 신고 일시",
    "폐사 추정 기간과 폐사 전 기상 상황",
    "시설량, 전체 입식량과 입식 일시 (입식·출하 기록)",
    "현장 측정 기록: 수온·용존산소·pH·염분 (측정자·시각·위치·기기를 함께 기록)",
    "생존·폐사·빈사 개체의 아가미·체표·행동 사진",
    "먹이 공급 여부와 종류, 응급조치 기록",
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
        "consents": CONSENTS,
        "survey_prep": SURVEY_PREP,
        "survey_note": "④ 양식생물 피해조사 서식은 피해정밀조사반이 씁니다. 어업인은 조사에 참여하고 아래 자료를 준비합니다.",
        "evidence": [
            {"key": k, "label": label, "ready": bool(case.evidence.get(k))}
            for k, label in EVIDENCE_ITEMS.items()
        ],
    }
