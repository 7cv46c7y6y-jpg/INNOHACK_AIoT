# 아쿠아클레임 (INNOHACK_AIoT)

피해 양식어업인이 기록을 한 번 입력하면, 어업인이 직접 써야 하는 공식 서식 3종의 초안(HWPX)을 만들고, 누락·오류·기한을 알려 주며, 입력한 피해를 가두리 단위 지도로 보여 주는 웹 서비스입니다.

| 서식 | 앱이 하는 일 |
|---|---|
| ② 어업피해발생신고서 | 자동 작성 (피해가 나면 지체 없이, 읍·면·동) |
| ① 자연재난 피해신고서 | 자동 작성 (재난이 끝난 날부터 10일 안, 시·군·구) |
| ③ 입식·출하·판매 신고서 | 자동 작성 + 재난 전 신고 여부 확인 |
| ④ 양식생물 피해조사 | 조사반 서식이라 준비 자료만 안내 |

> 시연용입니다. 실제 개인정보를 넣지 마세요. 주민등록번호·계좌번호는 받지 않고, 서명·도장·공무원 칸(회색 칸)은 채우지 않습니다. 만든 서식은 서버에 저장하지 않습니다.

자세한 요구사항은 [docs/PRD.md](docs/PRD.md), 입력 항목과 서식 칸의 대응은 [docs/FIELD_MAP.md](docs/FIELD_MAP.md)에 있습니다.

## 노트북에서 실행하기 (Windows, VS Code)

Python 3.11 이상이 필요합니다 (3.14에서 확인).

```bat
git clone https://github.com/7cv46c7y6y-jpg/INNOHACK_AIoT.git
cd INNOHACK_AIoT
git checkout dev
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python run.py
```

브라우저에서 http://127.0.0.1:5000 을 열고 **시연 데이터로 채우기**를 누르면 통영 가상 어가 사례로 바로 시연할 수 있습니다.

- PowerShell에서 `.venv\Scripts\activate`가 막히면 먼저 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`를 실행하세요.
- VS Code에서는 `Ctrl+Shift+P` → "Python: Select Interpreter"에서 `.venv`를 고르면 됩니다.

## 테스트와 샘플

```bat
pytest                              :: 계산·검증·서식·화면 테스트
python scripts\make_samples.py      :: samples\ 에 서식 3종 샘플 생성
python scripts\build_templates.py   :: 원본(forms_src)으로 템플릿(forms_tpl) 다시 만들기
```

샘플(`samples/`)은 한글(한컴오피스)에서 열어 쪽 수(① 3쪽, ② 1쪽, ③ 1쪽)와 글자 잘림을 확인합니다.

## 서식 기재 규칙 바꾸기

공식 작성 예시가 없어 정한 기본값은 [config/form_rules.json](config/form_rules.json)에 있습니다. 지자체 확인 결과가 나오면 이 파일만 고치면 됩니다. 예를 들어 ①의 시설별 칸은 폭이 약 2.4cm라 "품종 + 마리 수"가 한 줄에 들어가지 않아서, 피해물량에는 마리 수만 적고 품종은 "피해 발생 위치" 칸에 적도록 정해 두었습니다.

## 폴더 구조

```
app/            Flask 화면과 API (templates/, static/, farms.py)
core/           입력 구조(model), 계산(calc), 검증(validate), 안내(guidance)
core/forms/     서식별 채우기 (① f01, ② f02, ③ f03)
config/         서식 기재 규칙
data/           시연 사례, 지도 가상 데이터
forms_src/      원본 서식 (HWP·HWPX, 법령 별지 서식)
forms_tpl/      채우기용 HWPX 템플릿 (원본에서 변환)
samples/        시연 사례로 만든 서식 샘플
tests/          pytest
docs/           PRD, 칸 대응표
```

## 배포 (Render 무료)

1. [Render](https://render.com)에 로그인하고 GitHub 저장소를 연결합니다.
2. **New → Blueprint**에서 이 저장소를 고르면 `render.yaml` 설정대로 만들어집니다 (main 브랜치 기준).
3. 무료 인스턴스는 15분 동안 접속이 없으면 잠들고, 깨어날 때 1분쯤 걸립니다. **시연 직전에 한 번 열어 두세요.**
4. 서버가 재시작되면 지도에 새로 올린 값은 지워집니다. 미리 넣은 가상 어가 데이터는 항상 다시 나타납니다.

## 근거 자료

- 어업재해 피해조사·보고 및 복구지원 요령 제6조 (어업피해발생신고서, 지체 없이 신고)
- 자연재난 구호 및 복구 비용 부담기준 등에 관한 규정 제9조 (자연재난 피해신고서, 입식·출하·판매 신고)
- [python-hwpx](https://pypi.org/project/python-hwpx/) (HWP/HWPX 읽고 쓰기), [Leaflet](https://leafletjs.com/) + OpenStreetMap (지도)
