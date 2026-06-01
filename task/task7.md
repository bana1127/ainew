# Task 7. 활동 보고서 AI 생성 Agent 구현

## 목표

ClubAgent의 핵심 AI 기능 중 하나인 “활동 보고서 자동 생성” 기능을 구현한다.

이번 Task에서는 사용자가 자체 웹페이지에서 다음 정보를 입력하면, OpenAI 기반 Agent가 활동 보고서 초안을 생성하도록 한다.

```text
활동 카테고리
활동명
활동일
장소
참여자
활동 설명 메모
레퍼런스 보고서
첨부 이미지 또는 파일 정보
```

처리 흐름:

```text
사용자 입력
→ ActivityReport Orchestrator
→ FileParser Agent
→ Post Agent
→ Publisher Agent
→ activity_reports.generated_content 저장
→ 프론트에서 초안 표시
```

이번 Task에서는 OpenAI API 키가 없어도 개발/테스트가 가능하도록 mock mode를 반드시 제공한다.

---

## 전제 조건

Task 1~6이 완료되어 있어야 한다.

Task 4에서 다음 데이터 관리 UI가 구현되어 있어야 한다.

* 부원 관리
* 활동 카테고리 관리
* 레퍼런스 보고서 관리
* 활동 보고서 수동 작성
* 참여자 연결

Task 6까지 다음 기반이 있어야 한다.

* FastAPI backend
* Next.js frontend
* PostgreSQL DB
* activity_categories
* reference_reports
* activity_reports
* activity_participants
* uploaded_files
* members

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. OpenAI API 환경변수 설정
2. LLM Service 구현
3. Agent 기본 구조 정리
4. ActivityReport Orchestrator 구현
5. FileParser Agent 최소 구현
6. Post Agent 구현
7. Publisher Agent 구현
8. 활동 보고서 생성 API 구현
9. Mock mode 구현
10. 프론트 `/reports` 페이지에서 AI 초안 생성 버튼 연결
11. 생성 결과 미리보기 및 저장
12. README에 OpenAI 키 설정 및 테스트 방법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* 영수증 OCR
* 감사 규정 체크
* 거래내역서 파서 재구현
* 납부자/미납자 매칭 수정
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant 또는 pgvector 벡터 검색
* 이미지 내용 정밀 분석
* 복잡한 멀티모달 추론
* 로그인/권한 시스템

필요한 위치에는 TODO 주석만 남긴다.

---

## OpenAI 설정

### 1. 환경변수 추가

`backend/.env.example`에 다음을 추가한다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MOCK_MODE=true
```

설명:

* `OPENAI_API_KEY`: 실제 OpenAI API 키
* `OPENAI_MODEL`: 활동 보고서 생성에 사용할 모델명
* `OPENAI_MOCK_MODE`: true이면 실제 OpenAI API를 호출하지 않고 mock 응답 사용

기본값은 안전하게 mock mode로 둔다.

```env
OPENAI_MOCK_MODE=true
```

실제 테스트 시 사용자는 `.env`에서 다음처럼 바꿀 수 있다.

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MOCK_MODE=false
```

---

## 2. Config 보강

파일:

```text
backend/app/core/config.py
```

추가 설정:

```python
openai_api_key: str | None = None
openai_model: str = "gpt-4.1-mini"
openai_mock_mode: bool = True
```

환경변수 이름은 기존 config 스타일에 맞춘다.

---

## Backend 구현 요구사항

## 1. OpenAI 의존성 추가

`backend/requirements.txt`에 다음 패키지를 추가한다.

```text
openai
```

---

## 2. LLM Service 구현

파일:

```text
backend/app/services/llm_service.py
```

역할:

* OpenAI API 호출을 한 곳으로 모은다.
* mock mode일 때는 실제 API를 호출하지 않는다.
* structured JSON 응답을 반환한다.
* API key가 없고 mock mode가 false이면 명확한 에러를 반환한다.

예상 클래스:

```python
class LLMService:
    def __init__(self, api_key: str | None, model: str, mock_mode: bool):
        ...

    async def generate_activity_report(self, payload: ActivityReportGenerationPayload) -> ActivityReportGenerationResult:
        ...
```

또는 동기 함수로 구현해도 된다. 프로젝트 기존 FastAPI 스타일에 맞춘다.

---

## 3. Mock mode 요구사항

`OPENAI_MOCK_MODE=true`일 때는 다음처럼 더미 보고서를 생성한다.

입력 예시:

```json
{
  "category_name": "정기 모임 / 스터디",
  "title": "5월 AI 스터디",
  "activity_date": "2026-05-30",
  "location": "동아리방",
  "participant_names": ["김가온", "이도윤"],
  "input_text": "PBL-C 개발 방향 회의와 역할 분담 진행",
  "reference_content": "기존 활동 보고서 예시..."
}
```

출력 예시:

```json
{
  "title": "5월 AI 스터디 활동 보고서",
  "summary": "정기 모임을 통해 PBL-C 프로젝트 개발 방향을 논의하고 역할을 분담하였다.",
  "content": "활동명: 5월 AI 스터디\n활동 일시: 2026-05-30\n활동 장소: 동아리방\n참석자: 김가온, 이도윤\n\n활동 목적:\nPBL-C 프로젝트의 구현 방향을 정리하고 팀원 간 역할을 분담하기 위해 활동을 진행하였다.\n\n주요 내용:\n참석자들은 ClubAgent의 핵심 기능과 개발 순서를 검토하고, 거래내역서 분석 및 활동 보고서 자동 생성 기능의 구현 방식을 논의하였다.\n\n활동 결과:\n프로젝트의 우선순위와 Task 기반 개발 계획을 확정하였다.\n\n향후 계획:\n다음 활동에서는 활동 보고서 생성 Agent와 영수증 분석 기능을 구현할 예정이다.",
  "missing_fields": [],
  "confidence": 0.75,
  "model": "mock"
}
```

Mock mode도 입력값을 최대한 반영해 자연스럽게 생성한다.

---

## 4. OpenAI 실제 호출 요구사항

`OPENAI_MOCK_MODE=false`이고 `OPENAI_API_KEY`가 있으면 OpenAI API를 호출한다.

권장 방식:

* OpenAI Python SDK 사용
* JSON schema 또는 structured output 사용
* 응답은 반드시 정해진 schema에 맞게 파싱
* 실패 시 사용자에게 명확한 에러 반환

출력 schema:

```json
{
  "title": "string",
  "summary": "string",
  "content": "string",
  "missing_fields": ["string"],
  "confidence": 0.0,
  "model": "string"
}
```

`content`는 한국어 활동 보고서 본문이어야 한다.

필수 포함 항목:

```text
활동명
활동 일시
활동 장소
참석자
활동 목적
주요 내용
활동 결과
향후 계획
```

모델 호출 프롬프트는 다음 정보를 활용한다.

```text
활동 카테고리
카테고리별 report_template
레퍼런스 보고서 content
사용자 입력 메모
참여자 이름
활동일
장소
첨부 파일 이름
```

주의:

* OpenAI 호출 코드는 `llm_service.py`에만 집중시킨다.
* API key를 로그에 출력하지 않는다.
* 에러 발생 시 키 전체를 노출하지 않는다.
* 모델 응답이 JSON 파싱에 실패하면 fallback error를 반환한다.
* mock mode일 때는 openai 패키지 호출을 하지 않는다.

---

## 5. Agent 구조 구현

파일 구조:

```text
backend/app/agents/
  __init__.py
  activity_report_orchestrator.py
  file_parser_agent.py
  post_agent.py
  publisher_agent.py
```

이번 Task에서는 7개 Agent를 전부 구현하지 않는다.
다만 앞으로 확장할 수 있도록 아래 3개 Agent와 Orchestrator만 구현한다.

### ActivityReportOrchestrator

역할:

```text
입력 수집
→ FileParser Agent 호출
→ Post Agent 호출
→ Publisher Agent 호출
→ 결과 반환
```

### FileParser Agent

이번 Task에서는 최소 구현만 한다.

역할:

```text
첨부 파일 ID 목록을 받아 uploaded_files 메타데이터 조회
파일명, file_type, mime_type 정리
이미지 내용 분석은 하지 않음
```

이미지 분석은 Task 8 또는 이후 Task에서 구현한다.

### Post Agent

역할:

```text
활동 카테고리, 레퍼런스 보고서, 참여자, 사용자 메모를 바탕으로 활동 보고서 초안 생성
LLMService 호출
```

### Publisher Agent

역할:

```text
생성된 활동 보고서 초안을 activity_reports.generated_content에 저장
status를 "generated"로 변경
필요하면 final_content가 비어 있을 때 generated_content를 복사
```

---

## 6. Schema 구현

파일 예시:

```text
backend/app/schemas/agent.py
```

또는 프로젝트 스타일에 맞게 `activity_report_generation.py`로 분리해도 된다.

필수 schema:

```python
class ActivityReportGenerateRequest(BaseModel):
    activity_report_id: UUID | None = None
    category_id: UUID
    reference_report_id: UUID | None = None
    title: str
    activity_date: date | None = None
    location: str | None = None
    input_text: str | None = None
    participant_ids: list[UUID] = []
    file_ids: list[UUID] = []
    save_to_db: bool = True

class ActivityReportGenerateResponse(BaseModel):
    activity_report_id: UUID | None
    title: str
    summary: str
    content: str
    missing_fields: list[str]
    confidence: float
    model: str
    saved: bool
```

필요하면 내부용 schema를 추가한다.

---

## 7. API 구현

파일:

```text
backend/app/routers/agents.py
```

또는 기존 구조에 맞춰:

```text
backend/app/routers/activity_report_agents.py
```

필수 API:

```http
POST /api/agents/activity-report/generate
```

요청 예시:

```json
{
  "category_id": "category-id",
  "reference_report_id": "reference-id",
  "title": "5월 AI 스터디",
  "activity_date": "2026-05-30",
  "location": "동아리방",
  "input_text": "PBL-C 개발 방향 회의와 역할 분담 진행",
  "participant_ids": ["member-id-1", "member-id-2"],
  "file_ids": [],
  "save_to_db": true
}
```

응답 예시:

```json
{
  "activity_report_id": "report-id",
  "title": "5월 AI 스터디 활동 보고서",
  "summary": "정기 모임을 통해 PBL-C 프로젝트 개발 방향을 논의하고 역할을 분담하였다.",
  "content": "...",
  "missing_fields": [],
  "confidence": 0.75,
  "model": "mock",
  "saved": true
}
```

### 동작 방식

1. category_id 검증
2. reference_report_id가 있으면 reference report 조회
3. participant_ids로 member 조회
4. file_ids로 uploaded_files 조회
5. activity_report_id가 있으면 기존 보고서에 결과 저장
6. activity_report_id가 없고 save_to_db=true이면 새 activity_report 생성
7. generated_content 저장
8. status = generated
9. 결과 반환

---

## 8. 기존 Reports UI 보강

파일:

```text
frontend/app/reports/page.tsx
```

기존 보고서 작성 UI가 있다면 다음 기능을 추가한다.

### 필수 기능

* 카테고리 선택
* 레퍼런스 선택
* 제목 입력
* 활동일 입력
* 장소 입력
* 참여자 선택
* 입력 메모 입력
* 파일 선택 또는 기존 uploaded_files 선택은 선택사항
* `AI 초안 생성` 버튼
* 생성 중 로딩 표시
* 생성 결과 미리보기
* 생성된 content를 최종 내용 textarea에 반영
* 저장된 activity_report_id 표시 또는 activities 목록에서 확인 가능
* mock mode 여부 표시

### 버튼 동작

```text
AI 초안 생성 클릭
→ POST /api/agents/activity-report/generate
→ 결과 content 표시
→ final_content textarea에 자동 입력 또는 “초안 적용” 버튼 제공
```

### API Key가 없거나 mock mode일 때

프론트에서는 에러로 보이지 않아야 한다.

mock mode인 경우:

```text
Mock mode로 생성된 초안입니다. OPENAI_MOCK_MODE=false 및 OPENAI_API_KEY 설정 시 실제 모델을 사용할 수 있습니다.
```

비슷한 안내를 표시한다.

---

## 9. Frontend API 함수 추가

파일:

```text
frontend/lib/api.ts
```

추가 함수:

```ts
generateActivityReportDraft(payload)
```

필요 타입:

```ts
ActivityReportGenerateRequest
ActivityReportGenerateResponse
```

---

## 10. Settings 화면 보강

파일:

```text
frontend/app/settings/page.tsx
```

가능하면 OpenAI 설정 안내 영역을 추가한다.

표시 내용:

```text
OpenAI API Key는 backend/.env의 OPENAI_API_KEY에 설정합니다.
현재 기본값은 OPENAI_MOCK_MODE=true입니다.
실제 모델 테스트 시 OPENAI_MOCK_MODE=false로 변경하세요.
```

실제 API key를 웹에서 입력받아 저장하는 기능은 구현하지 않는다.
키는 `.env`에만 넣는 방식으로 유지한다.

---

## README 업데이트

README에 다음 내용을 추가한다.

### OpenAI 설정

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MOCK_MODE=true
```

### Mock mode 테스트

```text
기본값은 OPENAI_MOCK_MODE=true이므로 API key 없이도 활동 보고서 초안 생성 기능을 테스트할 수 있다.
```

### 실제 OpenAI 테스트

```text
1. backend/.env에 OPENAI_API_KEY 입력
2. OPENAI_MOCK_MODE=false로 변경
3. 백엔드 재시작
4. /reports 페이지에서 AI 초안 생성 실행
```

### API 테스트 예시

WSL/Linux:

```bash
curl -X POST http://localhost:8000/api/agents/activity-report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "category-id",
    "title": "5월 AI 스터디",
    "activity_date": "2026-05-30",
    "location": "동아리방",
    "input_text": "PBL-C 개발 방향 회의와 역할 분담 진행",
    "participant_ids": [],
    "file_ids": [],
    "save_to_db": true
  }'
```

Windows PowerShell 예시도 추가한다.

---

## 테스트 및 검증

가능하면 테스트를 추가한다.

파일 예시:

```text
backend/tests/test_activity_report_agent.py
```

테스트 항목:

1. mock mode에서 보고서 생성 가능
2. category_id가 없으면 404 또는 400
3. reference_report_id가 있으면 내용 반영
4. save_to_db=true이면 activity_reports에 저장
5. activity_report_id가 있으면 기존 보고서 갱신

실제 OpenAI API 호출 테스트는 자동 테스트에 포함하지 않는다.

---

## 실행 검증

가능하면 다음을 실행한다.

```bash
docker compose up -d db
cd backend
alembic upgrade head
python -m app.scripts.seed
python -m compileall app
pytest
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

새 터미널:

```bash
cd frontend
npm install
npm run build
npm run dev
```

확인 URL:

```text
http://localhost:3000/reports
http://localhost:8000/api/agents/activity-report/generate
```

---

## 완료 기준

Task 7은 다음을 모두 만족해야 완료로 본다.

1. `.env.example`에 OpenAI 설정값이 추가되어 있다.
2. mock mode에서 API key 없이 활동 보고서 초안 생성이 가능하다.
3. OpenAI API key를 넣고 mock mode를 false로 바꾸면 실제 모델 호출 구조가 동작 가능해야 한다.
4. LLMService가 구현되어 있다.
5. ActivityReportOrchestrator가 구현되어 있다.
6. FileParser Agent 최소 구현이 되어 있다.
7. Post Agent가 구현되어 있다.
8. Publisher Agent가 generated_content를 DB에 저장한다.
9. `POST /api/agents/activity-report/generate` API가 동작한다.
10. `/reports` 페이지에서 AI 초안 생성 버튼을 사용할 수 있다.
11. 생성된 초안이 화면에 표시되고 final_content에 반영 가능하다.
12. README에 OpenAI 설정 및 mock mode 테스트 방법이 추가되어 있다.
13. 이번 Task에서 영수증 OCR, n8n, Notion, Slack 기능은 구현되지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 7 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 구현된 Backend 기능
- ...

3. 구현된 Agent 구조
- ActivityReportOrchestrator:
- FileParser Agent:
- Post Agent:
- Publisher Agent:

4. OpenAI 설정 방식
- ...

5. Mock mode 동작 방식
- ...

6. 구현된 Frontend 기능
- ...

7. 실행 검증 결과
- docker compose up -d db:
- alembic upgrade head:
- python -m app.scripts.seed:
- backend compile/test:
- pytest:
- frontend build:
- 주요 URL 확인:

8. 활동 보고서 생성 테스트 결과
- mock mode:
- DB 저장:
- reports 페이지:

9. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

10. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

11. 다음 Task에서 해야 할 일
- Task 8: 영수증 OCR + 감사 규정 체크 Agent 구현
```
