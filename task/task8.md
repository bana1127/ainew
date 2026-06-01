# Task 8. 영수증 OCR 및 감사 규정 체크 Agent 구현

## 목표

ClubAgent의 예산 관리 핵심 기능인 “영수증 분석 + 감사 규정 체크” 기능을 구현한다.

이번 Task에서는 사용자가 영수증 이미지 또는 증빙 파일을 업로드하면 다음 흐름으로 처리한다.

```text
영수증 파일 업로드
→ FileParser Agent
→ Receipt Agent
→ Classifier Agent
→ Policy Agent
→ Budget Agent
→ Publisher Agent
→ receipts 테이블 저장
→ /receipts 페이지에서 분석 결과 확인
```

이번 Task가 완료되면 사용자는 `/receipts` 페이지에서 다음을 수행할 수 있어야 한다.

```text
영수증 이미지 업로드
→ 날짜/가맹점/금액/결제 방식 추출
→ 감사 규정 기준으로 증빙 적합성 판단
→ 활동 보고서와 지출 연결
→ 확인 필요 여부 확인
→ receipts 목록에서 결과 확인
```

이번 Task에서도 OpenAI API Key가 없어도 테스트할 수 있도록 mock mode를 반드시 유지한다.

---

## 전제 조건

Task 1~7이 완료되어 있어야 한다.

Task 7 완료 기준:

* OpenAI 설정값 존재
* LLMService 구현
* mock mode 구현
* Agent 구조 일부 구현
* `/api/agents/activity-report/generate` 구현
* `/reports` 페이지에서 AI 초안 생성 가능

이번 Task에서는 Task 7에서 만든 OpenAI 설정과 LLMService 구조를 확장한다.

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. 감사 규정 rule 파일 작성
2. 영수증 분석용 schema 작성
3. Receipt Analysis Orchestrator 구현
4. FileParser Agent 확장
5. Receipt Agent 구현
6. Classifier Agent 구현
7. Policy Agent 구현
8. Budget Agent 최소 구현
9. Publisher Agent 영수증 저장 기능 보강
10. 영수증 분석 API 구현
11. `/receipts` 페이지 업로드/분석 UI 보강
12. 분석 결과 카드 및 증빙 상태 badge 구현
13. README에 영수증 분석 사용 방법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* 전체 디자인 리디자인
* 거래내역서 파서 재구현
* 납부자/미납자 매칭 수정
* 활동 보고서 AI 생성 기능 수정
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant 또는 pgvector 연동
* 로그인/권한 시스템
* 복잡한 회계 보고서 자동 생성
* 실제 외부 OCR SaaS 연동

필요한 위치에는 TODO 주석만 남긴다.

---

## OpenAI 설정

Task 7에서 추가한 설정을 그대로 사용한다.

`backend/.env.example`에 이미 다음 값이 있다면 유지한다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_MOCK_MODE=true
```

이번 Task에서 선택적으로 다음 값을 추가할 수 있다.

```env
OPENAI_VISION_MODEL=
```

규칙:

* `OPENAI_VISION_MODEL`이 비어 있으면 `OPENAI_MODEL`을 사용한다.
* `OPENAI_MOCK_MODE=true`이면 실제 OpenAI API를 호출하지 않는다.
* API key가 없고 mock mode가 false이면 명확한 에러를 반환한다.
* API key는 절대 로그에 출력하지 않는다.

---

## 감사 규정 rule 파일

다음 파일을 추가한다.

```text
backend/app/data/audit_rules.json
```

초기 rule 예시:

```json
{
  "card": {
    "label": "카드 결제",
    "status": "allowed",
    "required_evidence": ["receipt"],
    "message": "카드 결제는 관련 지출 영수증 첨부가 필요합니다."
  },
  "online_card": {
    "label": "온라인 카드 결제",
    "status": "allowed",
    "required_evidence": ["credit_card_sales_slip"],
    "message": "온라인 결제는 신용카드 매출전표 첨부가 필요합니다."
  },
  "transfer_student": {
    "label": "학생 계좌이체",
    "status": "need_check",
    "required_evidence": ["student_certificate_or_timetable"],
    "message": "학교 학생에게 계좌이체한 경우 재학증명서 또는 학번/이름이 포함된 시간표가 필요합니다."
  },
  "transfer_company": {
    "label": "기업/기관 계좌이체",
    "status": "need_check",
    "required_evidence": ["business_registration", "bankbook_copy"],
    "message": "기업 또는 기관에게 계좌이체한 경우 사업자등록증과 통장사본이 필요합니다."
  },
  "cash_withdrawal": {
    "label": "현금 인출",
    "status": "not_allowed",
    "required_evidence": [],
    "message": "현금인출은 불가능합니다."
  },
  "personal_card_reimbursement": {
    "label": "개인카드 대리 결제 후 이체",
    "status": "not_allowed",
    "required_evidence": [],
    "message": "개인카드로 대신 결제 후 금액을 이체하는 방식은 불가능합니다."
  },
  "recurring_payment": {
    "label": "주기적 결제",
    "status": "need_check",
    "required_evidence": ["subscription_statement"],
    "message": "주기적으로 지출되는 금액은 가입내역서 또는 정기결제 증빙이 필요합니다."
  },
  "unknown": {
    "label": "확인 필요",
    "status": "need_check",
    "required_evidence": [],
    "message": "결제 방식이 명확하지 않아 임원 확인이 필요합니다."
  }
}
```

---

## DB 사용 원칙

이번 Task에서는 DB 마이그레이션을 새로 만들지 않는 것을 우선한다.

기존 `receipts` 테이블의 다음 필드를 사용한다.

```text
activity_report_id
file_id
receipt_date
store_name
amount
payment_method
category
evidence_status
need_check
reason
created_at
updated_at
```

상세 분석 결과는 우선 API 응답으로 반환한다.
DB에는 핵심 요약만 저장한다.

저장 매핑:

```text
receipt_date → 추출된 날짜
store_name → 추출된 가맹점
amount → 추출된 금액
payment_method → 결제 방식
category → 지출 분류
evidence_status → valid / need_check / invalid / pending
need_check → true / false
reason → 감사 규정 판단 사유 요약
file_id → uploaded_files.id
activity_report_id → 연결된 활동 보고서 ID
```

---

## Backend 구현 요구사항

## 1. Schema 작성

파일 예시:

```text
backend/app/schemas/receipt_agent.py
```

필수 schema:

```python
class ReceiptAnalyzeRequest(BaseModel):
    file_id: UUID | None = None
    activity_report_id: UUID | None = None
    save_to_db: bool = True
    manual_payment_method: str | None = None
    manual_category: str | None = None

class ReceiptExtractedData(BaseModel):
    receipt_date: date | None = None
    store_name: str | None = None
    amount: int = 0
    payment_method: str = "unknown"
    category: str | None = None
    raw_text: str | None = None
    confidence: float = 0.0

class ReceiptPolicyCheckResult(BaseModel):
    evidence_status: str
    need_check: bool
    required_evidence: list[str]
    reason: str
    rule_key: str

class ReceiptAnalyzeResponse(BaseModel):
    receipt_id: UUID | None = None
    file_id: UUID | None = None
    activity_report_id: UUID | None = None
    extracted: ReceiptExtractedData
    policy: ReceiptPolicyCheckResult
    saved: bool
    model: str
```

프로젝트 기존 schema 스타일에 맞춰도 된다.

---

## 2. LLMService 확장

파일:

```text
backend/app/services/llm_service.py
```

추가 함수 예시:

```python
async def analyze_receipt(self, payload: ReceiptAnalysisPayload) -> ReceiptExtractedData:
    ...
```

또는 동기 함수로 구현해도 된다.

### mock mode 동작

`OPENAI_MOCK_MODE=true`일 때는 실제 OpenAI API를 호출하지 않는다.

mock 응답 예시:

```json
{
  "receipt_date": "2026-05-30",
  "store_name": "스타벅스",
  "amount": 50700,
  "payment_method": "card",
  "category": "간식비",
  "raw_text": "MOCK RECEIPT 스타벅스 50,700원 카드결제",
  "confidence": 0.75
}
```

파일명에 힌트가 있으면 최대한 반영한다.

예시:

```text
receipt_card_50700.jpg → card, 50700
transfer_student_30000.png → transfer_student, 30000
online_12000.png → online_card, 12000
```

### 실제 OpenAI 호출

`OPENAI_MOCK_MODE=false`이고 API key가 있으면 이미지 또는 파일 정보를 기반으로 분석한다.

요구 출력 JSON:

```json
{
  "receipt_date": "YYYY-MM-DD 또는 null",
  "store_name": "string 또는 null",
  "amount": 0,
  "payment_method": "card | online_card | transfer_student | transfer_company | cash_withdrawal | personal_card_reimbursement | recurring_payment | unknown",
  "category": "string 또는 null",
  "raw_text": "string 또는 null",
  "confidence": 0.0
}
```

주의:

* API key를 로그에 출력하지 않는다.
* 모델 응답 JSON 파싱 실패 시 명확한 에러를 반환한다.
* mock mode일 때는 OpenAI API를 호출하지 않는다.
* 이미지를 base64로 읽는 경우 경로는 pathlib.Path 기반으로 처리한다.

---

## 3. Agent 구조 구현

다음 파일을 추가 또는 보강한다.

```text
backend/app/agents/receipt_analysis_orchestrator.py
backend/app/agents/receipt_agent.py
backend/app/agents/classifier_agent.py
backend/app/agents/policy_agent.py
backend/app/agents/budget_agent.py
```

기존 `file_parser_agent.py`, `publisher_agent.py`가 있으면 재사용/보강한다.

---

### ReceiptAnalysisOrchestrator

역할:

```text
file_id 또는 업로드 파일 정보 확인
→ FileParser Agent 호출
→ Receipt Agent 호출
→ Classifier Agent 호출
→ Policy Agent 호출
→ Budget Agent 호출
→ Publisher Agent 호출
→ 결과 반환
```

---

### FileParser Agent

이번 Task에서 역할을 보강한다.

```text
uploaded_files 메타데이터 조회
파일 경로 확인
mime_type 확인
이미지/파일 존재 여부 확인
```

실제 OCR은 하지 않는다.
이미지 분석은 Receipt Agent 또는 LLMService에서 수행한다.

---

### Receipt Agent

역할:

```text
영수증 이미지 또는 파일 메타데이터를 LLMService에 전달
날짜, 가맹점, 금액, 결제방식, 지출분류 추출
```

---

### Classifier Agent

역할:

```text
payment_method가 unknown이거나 애매한 경우 보정
manual_payment_method가 있으면 사용자 입력을 우선
manual_category가 있으면 사용자 입력을 우선
```

기본 결제 방식:

```text
card
online_card
transfer_student
transfer_company
cash_withdrawal
personal_card_reimbursement
recurring_payment
unknown
```

---

### Policy Agent

역할:

```text
audit_rules.json 로드
payment_method 기준 rule 선택
evidence_status 결정
need_check 결정
required_evidence 반환
reason 생성
```

판정 기준:

```text
rule.status == allowed → evidence_status = valid, need_check = false
rule.status == need_check → evidence_status = need_check, need_check = true
rule.status == not_allowed → evidence_status = invalid, need_check = true
unknown → evidence_status = need_check, need_check = true
```

---

### Budget Agent

이번 Task에서는 최소 구현만 한다.

역할:

```text
amount가 0 이하이면 need_check 처리
activity_report_id가 있으면 활동과 지출 연결 가능
잔액 계산은 이번 Task에서 구현하지 않음
```

잔액 계산은 추후 Task에서 구현한다.

---

### Publisher Agent 보강

기존 `publisher_agent.py`에 영수증 저장 기능을 추가한다.

역할:

```text
ReceiptAnalyzeResponse 결과를 receipts 테이블에 저장
이미 receipt_id가 있으면 업데이트 가능
file_id 연결
activity_report_id 연결
```

---

## 4. API 구현

파일:

```text
backend/app/routers/receipt_agents.py
```

또는 기존 `agents.py`에 포함해도 된다.

필수 API:

```http
POST /api/agents/receipt/analyze
```

요청 방식은 multipart form을 우선 지원한다.

### multipart 요청 필드

```text
file: 영수증 이미지 또는 파일
activity_report_id: optional UUID
save_to_db: true/false
manual_payment_method: optional string
manual_category: optional string
```

동작:

1. 파일이 있으면 uploaded_files에 저장
2. file_id 생성
3. ReceiptAnalysisOrchestrator 호출
4. save_to_db=true이면 receipts 테이블 저장
5. 결과 반환

### JSON 요청도 가능하면 지원

이미 업로드된 파일을 분석할 수 있도록 다음 형태도 선택적으로 지원한다.

```http
POST /api/agents/receipt/analyze-file
```

요청:

```json
{
  "file_id": "uploaded-file-id",
  "activity_report_id": "activity-report-id",
  "save_to_db": true,
  "manual_payment_method": "card",
  "manual_category": "간식비"
}
```

어려우면 multipart API만 구현하고 TODO를 남긴다.

---

## 5. 기존 Receipts API 보강

기존 `GET /api/receipts`가 있다면 다음 필터를 확인/보강한다.

```text
activity_report_id
evidence_status
need_check
payment_method
category
start_date
end_date
q
```

q 검색 대상:

```text
store_name
reason
category
payment_method
```

기존 `PATCH /api/receipts/{id}`가 있다면 사용자가 분석 결과를 수동 수정할 수 있게 유지한다.

---

## Frontend 구현 요구사항

## 1. Receipts 페이지 보강

파일:

```text
frontend/app/receipts/page.tsx
```

필수 기능:

1. 영수증 파일 업로드
2. 활동 보고서 선택
3. 결제 방식 수동 선택
4. 지출 분류 수동 입력
5. 분석 버튼
6. 분석 결과 카드 표시
7. 증빙 상태 badge 표시
8. 필요 증빙 목록 표시
9. 확인 필요 사유 표시
10. 저장된 영수증 목록 표시
11. 필터 UI 보강
12. 최소 디자인 정리

---

## 2. 업로드 UI

필드:

```text
영수증 파일
연결할 활동 보고서
결제 방식 수동 선택
지출 분류
```

결제 방식 옵션:

```text
unknown
card
online_card
transfer_student
transfer_company
cash_withdrawal
personal_card_reimbursement
recurring_payment
```

버튼:

```text
영수증 분석
```

---

## 3. 분석 결과 카드

분석 후 다음을 카드 형태로 표시한다.

```text
날짜
가맹점
금액
결제 방식
지출 분류
증빙 상태
확인 필요 여부
필요 증빙
판단 사유
모델
```

금액은 천 단위 콤마로 표시한다.

---

## 4. Badge 스타일

증빙 상태에 따라 badge를 표시한다.

```text
valid → 적합
need_check → 확인 필요
invalid → 부적합
pending → 대기
```

권장 스타일:

```text
valid: green 계열
need_check: yellow 계열
invalid: red 계열
pending: gray 계열
```

프로젝트 기존 색상/스타일이 있으면 그 스타일을 따른다.

---

## 5. 저장된 영수증 목록

컬럼:

```text
날짜
가맹점
금액
결제 방식
분류
증빙 상태
확인 필요
사유
활동 연결
생성일
```

필터:

```text
증빙 상태
확인 필요 여부
결제 방식
검색어
```

---

## 6. Dashboard 반영

기존 `/api/dashboard/summary`와 `/dashboard`에서 다음 값이 이미 있다면 잘 표시되는지 확인한다.

```text
total_receipts
pending_receipts
```

`pending_receipts` 계산 기준은 다음을 권장한다.

```text
evidence_status in ("pending", "need_check", "invalid") 또는 need_check == true
```

필요하면 Task 8에서 보강한다.

---

## 7. Frontend API 함수 추가

파일:

```text
frontend/lib/api.ts
```

추가 함수:

```ts
analyzeReceipt(formData: FormData)
getReceipts(params?)
updateReceipt(id, payload)
```

필요 타입:

```ts
ReceiptAnalyzeResponse
ReceiptExtractedData
ReceiptPolicyCheckResult
ReceiptQueryParams
```

---

## 테스트 및 검증

가능하면 테스트를 추가한다.

파일 예시:

```text
backend/tests/test_receipt_policy_agent.py
backend/tests/test_receipt_agent_mock.py
```

테스트 항목:

1. card → valid
2. online_card → valid 또는 need_check 여부 rule에 맞게 반환
3. transfer_student → need_check
4. transfer_company → need_check
5. cash_withdrawal → invalid
6. unknown → need_check
7. mock mode에서 API key 없이 분석 가능
8. save_to_db=true이면 receipts 테이블 저장 가능

실제 OpenAI API 호출 테스트는 자동 테스트에 포함하지 않는다.

---

## README 업데이트

README에 다음 내용을 추가한다.

### 영수증 분석 사용 방법

```text
1. /receipts 페이지 접속
2. 영수증 이미지 선택
3. 연결할 활동 보고서가 있으면 선택
4. 결제 방식을 모르면 unknown 유지
5. 영수증 분석 클릭
6. 분석 결과와 증빙 상태 확인
7. 확인 필요 항목은 사유와 필요 증빙 확인
```

### OpenAI mock mode

```text
OPENAI_MOCK_MODE=true이면 API key 없이도 mock 분석 결과로 기능을 테스트할 수 있다.
```

### 실제 OpenAI 테스트

```text
1. backend/.env에 OPENAI_API_KEY 입력
2. OPENAI_MOCK_MODE=false로 변경
3. 필요 시 OPENAI_VISION_MODEL 설정
4. 백엔드 재시작
5. /receipts에서 영수증 분석 실행
```

### API 테스트 예시

WSL/Linux:

```bash
curl -X POST http://localhost:8000/api/agents/receipt/analyze \
  -F "file=@sample_receipt.jpg" \
  -F "save_to_db=true" \
  -F "manual_payment_method=card" \
  -F "manual_category=간식비"
```

Windows PowerShell:

```powershell
curl.exe -X POST http://localhost:8000/api/agents/receipt/analyze -F "file=@sample_receipt.jpg" -F "save_to_db=true" -F "manual_payment_method=card" -F "manual_category=간식비"
```

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
http://localhost:3000/receipts
http://localhost:8000/api/agents/receipt/analyze
http://localhost:8000/api/receipts
http://localhost:3000/dashboard
```

---

## 완료 기준

Task 8은 다음을 모두 만족해야 완료로 본다.

1. 영수증 파일 업로드 UI가 동작한다.
2. mock mode에서 API key 없이 영수증 분석이 가능하다.
3. 실제 OpenAI API key를 넣고 mock mode를 false로 바꾸면 실제 분석 구조가 동작 가능하다.
4. ReceiptAnalysisOrchestrator가 구현되어 있다.
5. Receipt Agent가 구현되어 있다.
6. Classifier Agent가 구현되어 있다.
7. Policy Agent가 audit_rules.json 기준으로 증빙 상태를 판단한다.
8. Budget Agent가 amount/activity 연결에 대한 최소 검증을 수행한다.
9. Publisher Agent가 receipts 테이블에 분석 결과를 저장한다.
10. `POST /api/agents/receipt/analyze` API가 동작한다.
11. `/receipts` 페이지에서 업로드, 분석, 결과 카드, 증빙 상태 badge, 목록 확인이 가능하다.
12. `/dashboard`에서 확인 필요 영수증 수가 반영된다.
13. README에 영수증 분석 사용 방법이 추가되어 있다.
14. 이번 Task에서 n8n, Notion, Slack 기능은 구현되지 않았다.
15. 전체 디자인 리디자인은 하지 않고, `/receipts` 기능에 필요한 최소 UI만 정리했다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 8 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 구현된 Backend 기능
- ...

3. 구현된 Agent 구조
- ReceiptAnalysisOrchestrator:
- FileParser Agent:
- Receipt Agent:
- Classifier Agent:
- Policy Agent:
- Budget Agent:
- Publisher Agent:

4. 감사 규정 rule 구성
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

8. 영수증 분석 테스트 결과
- mock mode:
- DB 저장:
- receipts 페이지:
- dashboard 반영:

9. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

10. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

11. 다음 Task에서 해야 할 일
- Task 9: 통합 테스트, UX 개선, 데모용 디자인 정리
```
