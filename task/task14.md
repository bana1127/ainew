# Task 14. 실제 운영 모드 전환 및 자동 점검 알림 API 구현

## 목표

ClubAgent를 Mock Mode 중심의 기능 테스트 상태에서 실제 운영 테스트가 가능한 상태로 전환한다.

이번 Task의 목표는 다음이다.

```text
실제 OpenAI API를 사용한 영수증 분석/활동 보고서 생성 활성화
→ 잘못 저장된 영수증 삭제 가능
→ 회비 납부 상태를 수동으로 직접 수정 가능
→ n8n 또는 외부 스케줄러가 호출할 자동 점검 API 구현
→ 자체 Notifications에 점검 결과 저장
```

이번 Task가 완료되면 다음이 가능해야 한다.

```text
1. OPENAI_MOCK_MODE=false로 실제 영수증 분석 실행
2. 실제 활동 보고서 AI 생성 실행
3. 영수증 분석 결과 삭제
4. 미납자를 수동으로 납부 완료/부분 납부/면제로 변경
5. n8n에서 weekly-check API 호출
6. 확인 필요 영수증, 미납자, 미완성 보고서 등을 알림으로 생성
```

---

## 전제 조건

Task 1~13이 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

* FastAPI backend
* Next.js frontend
* PostgreSQL
* OpenAI mock mode 기반 LLMService
* 영수증 분석 Agent
* 활동 보고서 생성 Agent
* 거래내역서 파서
* 납부 매칭 기능
* Notifications 기본 구조
* Dashboard
* AI 작업실
* 외부 배포용 `/api` proxy 구조
* `agent.banawy.store` 배포 준비

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. 실제 OpenAI 모드 점검 및 수정
2. 영수증 실제 이미지 분석 동작 확인
3. 활동 보고서 실제 AI 생성 동작 확인
4. Mock/Real 분석 결과 UI 구분
5. 영수증 삭제 API 및 UI 추가
6. 회비 납부 상태 직접 수정 API 및 UI 추가
7. 자동 점검 서비스 구현
8. n8n 호출용 자동화 API 구현
9. 자동 점검 결과를 Notifications에 저장
10. Dashboard 또는 Notifications 페이지에서 자동 점검 결과 확인
11. README / DEMO / DEPLOY 문서에 실제 운영 모드와 자동화 사용법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* LLM 기반 Intent Classifier
* Notion 연동
* Slack/Telegram 연동
* 로그인/권한 시스템
* Qdrant 또는 pgvector
* 복잡한 회계 감사 보고서 생성
* 기존 거래내역서 파서 재구현
* 기존 납부 매칭 알고리즘 재작성
* 기존 영수증 분석 Agent 전체 재작성
* 대규모 DB 스키마 변경

필요한 위치에는 TODO 주석만 남긴다.

---

# Part A. 실제 OpenAI 분석 모드 활성화

## 1. 목적

현재 일부 기능이 Mock Mode 중심으로 동작한다.

이번 Task에서는 실제 OpenAI API key를 넣었을 때 다음 기능이 실제 모델 호출로 동작해야 한다.

```text
- 영수증 이미지 실제 분석
- 활동 보고서 실제 생성
- Assistant에서 영수증/활동 보고서 요청 시 실제 모델 호출
```

---

## 2. 환경변수 확인

`backend/.env.example`에 다음 값이 명확히 있어야 한다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_VISION_MODEL=gpt-4.1-mini
OPENAI_MOCK_MODE=true
```

실제 테스트 시 사용자는 `backend/.env`를 다음처럼 바꾼다.

```env
OPENAI_API_KEY=실제_API_KEY
OPENAI_MODEL=gpt-4.1-mini
OPENAI_VISION_MODEL=gpt-4.1-mini
OPENAI_MOCK_MODE=false
```

주의:

```text
- 실제 API key를 코드, README, .env.example, 로그에 절대 넣지 않는다.
- API key 전체를 에러 메시지에 출력하지 않는다.
- OPENAI_MOCK_MODE=false인데 OPENAI_API_KEY가 비어 있으면 명확한 에러를 반환한다.
```

---

## 3. Backend 점검 대상

다음 파일을 확인한다.

```text
backend/app/core/config.py
backend/app/services/llm_service.py
backend/app/agents/receipt_agent.py
backend/app/agents/post_agent.py
backend/app/agents/receipt_analysis_orchestrator.py
backend/app/agents/activity_report_orchestrator.py
backend/app/routers/receipt_agents.py
backend/app/routers/agents.py
backend/app/schemas/receipt_agent.py
backend/app/schemas/agent.py
```

---

## 4. LLMService 요구사항

`backend/app/services/llm_service.py`를 중심으로 실제 OpenAI 호출 구조를 점검하고 보강한다.

필수 조건:

```text
1. OPENAI_MOCK_MODE=true이면 기존 mock 응답 사용
2. OPENAI_MOCK_MODE=false이면 실제 OpenAI API 호출
3. API key가 없으면 명확한 예외 발생
4. 영수증 분석은 업로드된 이미지 파일을 실제 모델에 전달
5. 활동 보고서 생성은 기존 카테고리/레퍼런스/참여자/입력 메모를 실제 모델에 전달
6. 응답은 기존 schema에 맞는 JSON으로 파싱
7. JSON 파싱 실패 시 안전한 에러 반환
8. API key는 로그에 출력하지 않음
```

---

## 5. 영수증 실제 분석 출력 schema

영수증 분석 결과는 기존 schema와 호환되어야 한다.

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

불확실한 경우:

```text
payment_method = "unknown"
confidence 낮게 설정
Policy Agent에서 need_check가 되도록 기존 흐름 유지
```

---

## 6. 활동 보고서 실제 생성 출력 schema

활동 보고서 생성은 기존 schema와 호환되어야 한다.

```json
{
  "title": "string",
  "summary": "string",
  "content": "string",
  "missing_fields": ["string"],
  "confidence": 0.0,
  "model": "실제 모델명"
}
```

보고서 본문에는 가능하면 다음 항목을 포함한다.

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

---

## 7. Frontend 표시

다음 화면에서 Mock/Real 상태를 구분한다.

```text
frontend/app/receipts/page.tsx
frontend/app/reports/page.tsx
frontend/app/assistant/page.tsx
frontend/components/assistant/ReceiptResultCard.tsx
frontend/components/assistant/ActivityReportResultCard.tsx
```

표시 규칙:

```text
model === "mock" → Mock Mode / 테스트 분석
model !== "mock" → 실제 AI 분석 / 실제 모델명 표시
```

예시:

```text
실제 AI 분석 결과
모델: gpt-4.1-mini
```

Mock Mode일 때만:

```text
Mock Mode
테스트용 샘플 결과입니다.
```

---

# Part B. 영수증 삭제 기능

## 1. 목표

사용자가 `/receipts` 페이지에서 잘못 저장된 영수증 분석 결과를 삭제할 수 있어야 한다.

---

## 2. Backend API

다음 API를 확인하거나 추가한다.

```http
DELETE /api/receipts/{receipt_id}
```

동작:

```text
1. receipt_id로 영수증 조회
2. 없으면 404 반환
3. 있으면 receipts row 삭제
4. uploaded_files 원본 파일은 삭제하지 않음
5. 삭제 결과 반환
```

응답 예시:

```json
{
  "ok": true,
  "deleted_id": "receipt-id"
}
```

404 예시:

```json
{
  "detail": "Receipt not found"
}
```

---

## 3. Frontend API

`frontend/lib/api.ts`에 추가한다.

```ts
deleteReceipt(id: string)
```

호출 경로:

```text
DELETE /api/receipts/{id}
```

api.ts 내부 endpoint는 다음처럼 작성한다.

```ts
apiFetch(`/receipts/${id}`, { method: "DELETE" })
```

---

## 4. Receipts 페이지 UI

`frontend/app/receipts/page.tsx`에서 저장된 영수증 목록에 삭제 버튼을 추가한다.

요구사항:

```text
- 각 영수증 row 또는 card에 삭제 버튼 표시
- 삭제 전 confirm 창 표시
- 삭제 성공 시 목록 새로고침
- 삭제 실패 시 에러 메시지 표시
```

confirm 문구:

```text
이 영수증 분석 결과를 삭제하시겠습니까?
업로드된 원본 파일은 삭제되지 않습니다.
```

---

# Part C. 회비 납부 상태 직접 수정 기능

## 1. 현재 문제

현재 회비 납부 상태는 거래내역서 입금 내역이 부원과 매칭되어야 바뀐다.

하지만 실제 운영에서는 다음 상황이 있다.

```text
- 자동 매칭이 실패했지만 총무가 납부 사실을 알고 있음
- 현장 납부 또는 별도 확인 건이 있음
- 부분 납부, 면제, 확인 필요 상태를 직접 기록해야 함
- 미납자 목록에서 바로 납부 완료로 바꾸고 싶음
```

따라서 `/payments` 페이지에서 거래내역 매칭 없이도 부원별 납부 상태를 직접 수정할 수 있어야 한다.

---

## 2. Backend API 1: PaymentRecord 직접 수정

기존 API가 있으면 재사용하고, 부족하면 추가한다.

```http
PATCH /api/payment-records/{payment_record_id}
```

요청 예시:

```json
{
  "required_amount": 30000,
  "paid_amount": 30000,
  "status": "paid",
  "payment_type": "membership_fee",
  "period": "2026-1"
}
```

수정 가능 필드:

```text
required_amount
paid_amount
status
payment_type
period
transaction_id
```

status 값:

```text
unpaid
paid
partial
need_check
exempt
```

대상 record가 없으면 404를 반환한다.

---

## 3. Backend API 2: 부원 기준 직접 생성/갱신

미납자는 payment_record가 없을 수도 있으므로, member_id 기준 upsert API를 추가한다.

```http
PUT /api/payment-records/manual
```

요청 예시:

```json
{
  "member_id": "member-id",
  "period": "2026-1",
  "payment_type": "membership_fee",
  "required_amount": 30000,
  "paid_amount": 30000,
  "status": "paid"
}
```

동작:

```text
1. member_id 존재 여부 확인
2. 같은 member_id + period + payment_type의 payment_record 조회
3. 있으면 update
4. 없으면 create
5. 결과 payment_record 반환
```

중복 생성 방지 기준:

```text
member_id + period + payment_type
```

---

## 4. status 자동 계산

요청에 status가 있으면 해당 status를 우선 사용한다.

status가 비어 있으면 다음 기준으로 자동 계산한다.

```text
paid_amount >= required_amount and required_amount > 0 → paid
0 < paid_amount < required_amount → partial
paid_amount == 0 → unpaid
```

단, 사용자가 `exempt` 또는 `need_check`를 명시하면 그대로 유지한다.

---

## 5. Summary / Unpaid API 반영

직접 수정 후 다음 API 결과에 반영되어야 한다.

```http
GET /api/payments/summary?period=2026-1&payment_type=membership_fee
GET /api/payments/unpaid?period=2026-1&payment_type=membership_fee
GET /api/payment-records?period=2026-1&payment_type=membership_fee
```

예시:

```text
미납자를 paid로 직접 수정
→ unpaid 목록에서 사라짐
→ summary의 paid_count 증가
→ unpaid_count 감소
```

`exempt`는 미납자 목록에서 제외한다.

summary schema에 `exempt_count`를 optional로 추가할 수 있다.

---

## 6. Frontend: Payments 직접 수정 UI

수정 대상:

```text
frontend/app/payments/page.tsx
frontend/lib/api.ts
frontend/components/ui/
```

최소 구현:

```text
미납자 테이블에서 각 부원 row에 "직접 수정" 버튼 추가
```

가능하면 다음 영역에서도 수정 가능하게 한다.

```text
- 납부 기록 목록
- 확인 필요 거래 테이블
```

---

## 7. 직접 수정 모달

`직접 수정` 버튼을 누르면 모달을 띄운다.

필드:

```text
부원명 표시
학번 표시
납부 기간 period
납부 유형 payment_type
필요 금액 required_amount
납부 금액 paid_amount
상태 status
```

status select:

```text
unpaid → 미납
paid → 납부 완료
partial → 부분 납부
need_check → 확인 필요
exempt → 면제
```

기본값:

```text
period = 현재 payments 페이지 period
payment_type = 현재 payments 페이지 payment_type
required_amount = 현재 기준 금액
paid_amount = 기존 record가 있으면 기존 값, 없으면 0
status = 기존 status 또는 unpaid
```

---

## 8. 저장 동작

저장 버튼 클릭 시 다음 API를 호출한다.

```ts
upsertManualPaymentRecord(payload)
```

endpoint:

```text
PUT /api/payment-records/manual
```

성공 시:

```text
- 모달 닫기
- payment summary 새로고침
- unpaid 목록 새로고침
- payment_records 목록 새로고침
- 성공 메시지 표시
```

실패 시:

```text
- 에러 메시지 표시
- 모달은 닫지 않음
```

---

## 9. Frontend API 함수

`frontend/lib/api.ts`에 추가한다.

```ts
updatePaymentRecord(id: string, payload: Partial<PaymentRecord>)
upsertManualPaymentRecord(payload: ManualPaymentRecordPayload)
```

타입:

```ts
type ManualPaymentRecordPayload = {
  member_id: string;
  period: string;
  payment_type: string;
  required_amount: number;
  paid_amount: number;
  status?: "unpaid" | "paid" | "partial" | "need_check" | "exempt";
};
```

---

# Part D. n8n 자동 점검 API 및 내부 알림

## 1. 목표

과제 요구사항에는 “주기적 혹은 빈번한 이벤트에 대한 자동 처리”가 포함되어 있다.

이번 Task에서는 n8n에서 일정 주기로 호출할 수 있는 자동 점검 API를 구현한다.

자동 점검 결과는 외부 메신저가 아니라 자체 Notifications에 저장한다.

---

## 2. 자동 점검 대상

weekly-check는 다음을 점검한다.

```text
1. 확인 필요 영수증
2. 미납자
3. 확인 필요 거래내역
4. 작성 중 또는 생성만 된 활동 보고서
5. 읽지 않은 알림 수
```

audit-check는 다음을 점검한다.

```text
1. 증빙 상태가 need_check 또는 invalid인 영수증
2. 활동 보고서와 연결되지 않은 영수증
3. 금액이 0이거나 확인이 필요한 영수증
4. 감사 자료 준비가 필요한 항목
```

quarterly-summary는 다음을 요약한다.

```text
1. 분기 활동 보고서 수
2. 분기 영수증 수
3. 분기 총 입금액
4. 분기 총 출금액
5. 미납자 수
6. 확인 필요 증빙 수
```

---

## 3. Backend 서비스 구현

파일:

```text
backend/app/services/automation_service.py
```

주요 함수:

```python
run_weekly_check(db: Session) -> AutomationCheckResult
run_audit_check(db: Session) -> AutomationCheckResult
run_quarterly_summary(db: Session, year: int | None = None, quarter: int | None = None) -> AutomationCheckResult
```

결과 구조 예시:

```json
{
  "type": "weekly_check",
  "title": "주간 운영 점검 결과",
  "summary": "확인 필요 영수증 2건, 미납자 3명, 작성 중 보고서 1건이 있습니다.",
  "items": [
    {
      "label": "확인 필요 영수증",
      "count": 2,
      "detail_url": "/receipts"
    },
    {
      "label": "미납자",
      "count": 3,
      "detail_url": "/payments"
    }
  ],
  "created_notification_id": "notification-id"
}
```

---

## 4. Notifications 저장

자동 점검 결과는 `notifications` 테이블에 저장한다.

알림 필드 매핑은 기존 모델에 맞춘다.

권장 값:

```text
type = automation
title = 점검 제목
message = 점검 summary
status = unread
payload 또는 metadata = items JSON
```

만약 notifications 테이블에 payload/metadata 필드가 없다면, message에 요약만 저장하고 TODO를 남긴다.

DB 스키마 대규모 변경은 하지 않는다.

---

## 5. Backend Router

파일:

```text
backend/app/routers/automations.py
```

API:

```http
POST /api/automations/weekly-check
POST /api/automations/audit-check
POST /api/automations/quarterly-summary
```

quarterly-summary 요청 예시:

```json
{
  "year": 2026,
  "quarter": 2
}
```

응답은 `AutomationCheckResult` 형식을 따른다.

---

## 6. n8n 호출 보안

로그인 시스템이 없으므로 간단한 token 방식만 선택적으로 구현한다.

환경변수:

```env
AUTOMATION_API_TOKEN=
```

동작:

```text
- AUTOMATION_API_TOKEN이 비어 있으면 로컬/개발 편의를 위해 토큰 검사 생략
- 값이 있으면 요청 header X-Automation-Token이 일치해야 실행
```

잘못된 token이면 401 반환.

주의:

```text
- 복잡한 로그인/권한 시스템은 구현하지 않는다.
- 토큰 원문은 로그에 남기지 않는다.
```

---

## 7. n8n workflow 문서화

README 또는 `AUTOMATION.md`에 n8n 연결 방법을 작성한다.

권장 파일:

```text
AUTOMATION.md
```

내용:

```text
1. n8n Schedule Trigger 추가
2. HTTP Request node 추가
3. Method: POST
4. URL: https://agent.banawy.store/api/automations/weekly-check
5. Header: X-Automation-Token: 설정한 토큰
6. 응답 확인
7. Notifications 페이지에서 알림 확인
```

---

## 8. Frontend Notifications 반영

`/notifications` 페이지에서 자동 점검 알림이 보기 좋게 표시되어야 한다.

최소 요구사항:

```text
- type 또는 title이 automation인 알림 표시
- unread/read 상태 badge 표시
- 메시지 표시
- 생성일 표시
- detail_url이 message에 있거나 payload가 있으면 관련 페이지 링크 제공
```

기존 Notifications 페이지가 있다면 보강만 한다.

---

## 9. Dashboard 반영

Dashboard의 “오늘 처리할 일” 또는 “추천 작업” 영역에서 자동 점검 알림 수를 반영한다.

이미 unread notifications count가 있으면 그대로 사용한다.

없으면 이번 Task에서 최소한 unread 알림 수가 보이도록 보강한다.

---

# 실행 검증

## Backend

```bash
cd backend
python -m compileall app
pytest
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Frontend

```bash
cd frontend
npm install
npm run build
npm run dev -- -H 0.0.0.0 -p 3000
```

외부 테스트용:

```bash
npm run build
npm run start -- -H 0.0.0.0 -p 3000
```

---

## 확인 URL

```text
https://agent.banawy.store
https://agent.banawy.store/api/health
https://agent.banawy.store/api/receipts
https://agent.banawy.store/api/payments/summary?period=2026-1&payment_type=membership_fee
https://agent.banawy.store/api/automations/weekly-check
```

POST 테스트:

```bash
curl -X POST https://agent.banawy.store/api/automations/weekly-check
```

토큰 사용 시:

```bash
curl -X POST https://agent.banawy.store/api/automations/weekly-check \
  -H "X-Automation-Token: your-token"
```

Windows PowerShell:

```powershell
curl.exe -X POST https://agent.banawy.store/api/automations/weekly-check
```

---

## 완료 기준

Task 14는 다음을 모두 만족해야 완료로 본다.

1. OPENAI_MOCK_MODE=false에서 실제 OpenAI 호출 구조가 동작한다.
2. 실제 영수증 이미지 분석이 가능하다.
3. 실제 활동 보고서 생성이 가능하다.
4. API key가 없을 때 안전한 에러가 표시된다.
5. 영수증 삭제 API가 동작한다.
6. `/receipts`에서 영수증 삭제가 가능하다.
7. 회비 납부 상태를 거래내역 매칭 없이 직접 수정할 수 있다.
8. 미납자를 paid/partial/exempt/need_check로 수정할 수 있다.
9. 수정 후 summary/unpaid 결과가 갱신된다.
10. `/api/automations/weekly-check`가 동작한다.
11. `/api/automations/audit-check`가 동작한다.
12. `/api/automations/quarterly-summary`가 동작한다.
13. 자동 점검 결과가 Notifications에 저장된다.
14. n8n에서 호출할 수 있는 방법이 문서화되어 있다.
15. frontend build가 성공한다.
16. backend compile/test가 성공한다.
17. 이번 Task에서 Notion, Slack, 로그인 시스템은 구현하지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 14 완료 보고

1. 생성/수정한 주요 파일
- ...

2. OpenAI 실제 모드 활성화
- 환경변수:
- LLMService:
- 영수증 실제 분석:
- 활동 보고서 실제 생성:
- 에러 처리:

3. 영수증 삭제 기능
- Backend DELETE API:
- Frontend deleteReceipt 함수:
- Receipts 페이지 삭제 UI:
- 삭제 후 목록 갱신:

4. 회비 납부 직접 수정 기능
- Backend manual upsert API:
- PaymentRecord update API:
- Frontend 직접 수정 모달:
- 미납자 직접 수정:
- summary/unpaid 갱신:

5. 자동 점검 API
- weekly-check:
- audit-check:
- quarterly-summary:
- AUTOMATION_API_TOKEN:
- Notifications 저장:

6. n8n 연동 문서
- AUTOMATION.md:
- 호출 URL:
- Header:
- 테스트 방법:

7. 실행 검증 결과
- backend compile/test:
- frontend build:
- /api/health:
- 실제 영수증 분석:
- 실제 활동 보고서 생성:
- 영수증 삭제:
- 납부 직접 수정:
- weekly-check:
- notifications:

8. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

9. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task14: enable real ai mode and automation checks
```
