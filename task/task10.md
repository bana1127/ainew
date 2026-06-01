# Task 10. Payment API 경로 수정 및 Command Center 통합 입력 화면 구현

## 목표

이번 Task의 목표는 두 가지이다.

첫째, 현재 `/payments` 페이지에서 발생하는 Payment API 404 오류를 수정한다.

둘째, 원래 기획 의도에 맞게 사용자가 한 곳에서 파일과 요청을 입력하면 ClubAgent가 영수증, 거래내역서, 납부 확인, 활동 보고서 생성 중 적절한 작업으로 연결하는 통합 입력 화면인 Command Center를 구현한다.

현재 오류 예시:

```text
GET http://localhost:8001/api/payments/payment-matching/summary?period=2026-1&payment_type=membership_fee 404
GET http://localhost:8001/api/payments/payment-matching/unpaid?period=2026-1&payment_type=membership_fee 404
```

이 오류는 프론트엔드 `api.ts`에서 호출하는 Payment API 경로와 백엔드 라우터 경로가 일치하지 않아서 발생한 것으로 보인다.

이번 Task는 단순히 새 화면을 만드는 것뿐 아니라, 기존 주요 기능을 하나의 AI 비서형 작업 흐름으로 묶기 위한 첫 단계이다.

---

## 전제 조건

Task 1~9가 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

* 기본 프로젝트 구조
* DB 모델 및 마이그레이션
* CRUD API
* 관리 UI
* 거래내역서 파서
* 납부 매칭 및 미납자 판별
* 활동 보고서 생성 Agent
* 영수증 분석 및 감사 규정 체크 Agent
* 고급 디자인 시스템 및 전역 레이아웃

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. Payment API 404 오류 수정
2. 프론트엔드 API 경로와 백엔드 라우터 경로 일치화
3. 주요 API endpoint smoke check
4. `/assistant` 또는 `/workspace` Command Center 페이지 생성
5. 파일 업로드 + 자연어 요청 입력 UI 구현
6. 요청 의도 분류 Intent Router 1차 구현
7. 기존 기능 API로 라우팅
8. 실행 결과 카드 표시
9. 확인 후 반영하는 Human-in-the-loop 기본 구조 구현
10. 사이드바에 Assistant 메뉴 연결
11. README에 Command Center 사용 방법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* 새로운 LLM 기반 intent classifier
* 복잡한 멀티턴 채팅
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant 또는 pgvector 연동
* 로그인/권한 시스템
* DB 스키마 대규모 변경
* 기존 Agent 로직 재구현
* 기존 디자인 시스템 전체 재작업

필요한 위치에는 TODO 주석만 남긴다.

---

# Part A. Payment API 404 오류 수정

## 문제 상황

현재 `/payments` 페이지에서 다음 경로로 API를 호출하고 있다.

```text
/api/payments/payment-matching/summary
/api/payments/payment-matching/unpaid
```

하지만 백엔드에는 해당 경로가 없어서 404가 발생한다.

Task 6에서 의도한 표준 API 경로는 다음에 가깝다.

```text
/api/payments/summary
/api/payments/unpaid
/api/payments/match-preview
/api/payments/match-apply
/api/payments/transactions/{transaction_id}/confirm
/api/payments/transactions/{transaction_id}/exclude
```

---

## 수정 방향

### 1. 백엔드 실제 라우터 확인

먼저 다음 파일들을 확인한다.

```text
backend/app/routers/payment_records.py
backend/app/routers/payment_matching.py
backend/app/routers/payments.py
backend/app/main.py
frontend/lib/api.ts
frontend/app/payments/page.tsx
```

확인할 것:

```text
- payment 관련 router가 main.py에 등록되어 있는지
- prefix가 /api/payments인지
- summary endpoint가 실제로 존재하는지
- unpaid endpoint가 실제로 존재하는지
- frontend/lib/api.ts에서 잘못된 경로를 호출하고 있는지
```

---

### 2. 표준 경로로 통일

가능하면 다음 경로를 표준으로 사용한다.

```text
GET  /api/payments/summary
GET  /api/payments/unpaid
POST /api/payments/match-preview
POST /api/payments/match-apply
PATCH /api/payments/transactions/{transaction_id}/confirm
PATCH /api/payments/transactions/{transaction_id}/exclude
```

프론트엔드 `frontend/lib/api.ts`의 관련 함수는 위 경로를 호출하도록 수정한다.

예상 함수:

```ts
getPaymentSummary(params)
getUnpaidPayments(params)
previewPaymentMatching(payload)
applyPaymentMatching(payload)
confirmPaymentTransaction(transactionId, payload)
excludePaymentTransaction(transactionId, payload)
```

---

### 3. Backward compatibility alias 선택 구현

이미 프론트나 문서에서 `/api/payments/payment-matching/*` 경로를 사용하고 있다면, 혼란을 줄이기 위해 백엔드에 alias endpoint를 추가해도 된다.

허용되는 alias:

```text
GET /api/payments/payment-matching/summary
→ 내부적으로 /api/payments/summary와 동일한 결과 반환

GET /api/payments/payment-matching/unpaid
→ 내부적으로 /api/payments/unpaid와 동일한 결과 반환
```

단, README에는 표준 경로가 `/api/payments/summary`, `/api/payments/unpaid`라고 명시한다.

---

### 4. Payment 페이지 오류 처리 개선

`/payments` 페이지에서 summary 또는 unpaid API가 실패하더라도 페이지 전체가 깨지면 안 된다.

요구사항:

```text
- summary API 실패 시 기본값 표시
- unpaid API 실패 시 빈 목록 표시
- 사용자에게 짧은 에러 메시지 표시
- 콘솔에 과도한 반복 에러가 쌓이지 않도록 useEffect 의존성 확인
```

---

### 5. API smoke check 추가

가능하면 간단한 API smoke check 문서 또는 테스트를 추가한다.

검증해야 할 URL:

```text
http://localhost:8001/api/payments/summary?period=2026-1&payment_type=membership_fee
http://localhost:8001/api/payments/unpaid?period=2026-1&payment_type=membership_fee
http://localhost:8001/api/payment-records
http://localhost:8001/api/transactions
```

---

# Part B. Command Center 통합 입력 화면 구현

## 목표

기능별 메뉴에 들어가지 않아도 사용자가 한 화면에서 파일과 요청을 입력하면 ClubAgent가 적절한 작업을 실행할 수 있게 한다.

원래 의도한 사용 경험:

```text
사용자:
"이거 영수증인데 활동비로 정리해줘"
+ 영수증 이미지 업로드

ClubAgent:
영수증 분석 Agent 실행
→ 날짜/가맹점/금액 추출
→ 감사 규정 체크
→ 결과 카드 표시
→ 사용자가 확인 후 DB 반영
```

또 다른 예:

```text
사용자:
"이 거래내역서 분석해서 회비 납부 반영해줘"
+ xlsx 파일 업로드

ClubAgent:
거래내역서 파서 실행
→ 미리보기 결과 표시
→ 사용자가 확인 후 가져오기
→ 납부 매칭 미리보기 제안
```

---

## URL

새 페이지를 만든다.

```text
/frontend/app/assistant/page.tsx
```

접속 경로:

```text
/assistant
```

Sidebar에도 Assistant 메뉴를 추가한다.

---

## 화면 구성

### 1. Hero 영역

```text
ClubAgent Assistant
파일을 올리거나 요청을 입력하면 활동 보고서, 영수증, 거래내역, 납부 상태를 자동으로 정리합니다.
```

---

### 2. 통합 입력 카드

구성:

```text
- 파일 업로드 영역
- 다중 파일 선택 가능
- 자연어 요청 입력 textarea
- 예시 요청 chip
- 실행 버튼
```

예시 요청 chip:

```text
이 영수증 활동비로 정리해줘
이 거래내역서에서 회비 납부 확인해줘
이 사진으로 활동 보고서 초안 만들어줘
이번 달 미납자 확인해줘
```

---

### 3. 처리 유형 선택 보조 UI

자동 분류가 애매할 수 있으므로 수동 선택 옵션도 제공한다.

```text
자동 감지
영수증 분석
거래내역서 분석
납부 매칭
활동 보고서 생성
```

기본값은 `자동 감지`이다.

---

### 4. 결과 카드 영역

실행 후 결과를 카드 형태로 보여준다.

결과 유형:

```text
receipt_analysis
bank_statement_preview
payment_matching_preview
activity_report_draft
general_message
error
```

각 결과 카드는 다음을 포함한다.

```text
- 실행된 작업 유형
- 사용된 Agent flow
- 주요 결과 요약
- 확인/반영 버튼
- 상세 보기 링크
```

---

# Backend 구현 요구사항

## 1. Assistant schema 구현

파일 예시:

```text
backend/app/schemas/assistant.py
```

필수 schema:

```python
class AssistantExecuteRequest(BaseModel):
    message: str | None = None
    file_ids: list[UUID] = []
    requested_intent: str = "auto"
    auto_apply: bool = False
    period: str | None = None
    payment_type: str | None = "membership_fee"
    required_amount: int | None = None

class AssistantExecuteResponse(BaseModel):
    intent: str
    confidence: float
    agent_flow: list[str]
    result_type: str
    result: dict
    requires_confirmation: bool
    message: str
```

multipart 요청을 지원할 경우 별도 schema 없이 Form/File을 사용해도 된다.

---

## 2. Assistant router 구현

파일:

```text
backend/app/routers/assistant.py
```

필수 API:

```http
POST /api/assistant/execute
```

권장 요청 방식:

```text
multipart form
```

필드:

```text
message: optional string
requested_intent: auto | receipt_analysis | bank_statement_import | payment_matching | activity_report_generate
auto_apply: true/false
period: optional string
payment_type: optional string
required_amount: optional integer
files: optional list of files
```

JSON 요청도 가능하면 지원한다.

```http
POST /api/assistant/execute-json
```

단, multipart 하나만 구현해도 된다.

---

## 3. Assistant Orchestrator 구현

파일:

```text
backend/app/agents/assistant_orchestrator.py
```

역할:

```text
입력 메시지와 파일 메타데이터 수집
→ Intent Router 호출
→ 적절한 기존 기능 호출
→ 결과를 표준 AssistantExecuteResponse로 변환
```

---

## 4. Intent Router 구현

파일:

```text
backend/app/agents/intent_router.py
```

이번 Task에서는 LLM을 쓰지 않고 규칙 기반으로 구현한다.

### 규칙

```text
requested_intent가 auto가 아니면 해당 intent 우선 사용

파일 확장자 .xls, .xlsx, .csv
→ bank_statement_import 후보

메시지에 "거래내역", "입금", "출금", "계좌", "은행"
→ bank_statement_import

메시지에 "회비", "납부", "미납"
→ payment_matching

이미지 파일 + 메시지에 "영수증", "결제", "지출", "증빙"
→ receipt_analysis

메시지에 "활동보고서", "보고서", "활동 사진", "초안"
→ activity_report_generate

이미지 파일만 있고 메시지가 비어 있으면
→ receipt_analysis 또는 activity_report_generate 중 confidence 낮게 반환

분류 실패
→ general_message 또는 unknown
```

Intent 값:

```text
receipt_analysis
bank_statement_import
payment_matching
activity_report_generate
unknown
```

---

## 5. 기존 기능 연결

Assistant Orchestrator는 기존 API를 직접 HTTP 호출하지 말고, 가능하면 기존 service/agent 함수를 내부에서 호출한다.

### receipt_analysis

연결 대상:

```text
ReceiptAnalysisOrchestrator
또는 /api/agents/receipt/analyze에서 사용한 내부 함수
```

결과:

```text
result_type = receipt_analysis
requires_confirmation = false 또는 true
```

mock mode에서는 바로 저장 가능하게 하되, auto_apply=false이면 preview 성격으로 반환한다.

---

### bank_statement_import

연결 대상:

```text
bank_statement_parser
transactions parse-preview 또는 import 로직
```

기본 동작:

```text
auto_apply=false → parse-preview
auto_apply=true → import
```

결과:

```text
result_type = bank_statement_preview 또는 bank_statement_import_result
requires_confirmation = true when auto_apply=false
```

---

### payment_matching

연결 대상:

```text
payment_matching_service.preview_payment_matching
payment_matching_service.apply_payment_matching
```

기본 동작:

```text
auto_apply=false → match-preview
auto_apply=true → match-apply
```

결과:

```text
result_type = payment_matching_preview 또는 payment_matching_result
requires_confirmation = true when auto_apply=false
```

---

### activity_report_generate

연결 대상:

```text
ActivityReportOrchestrator
```

이번 Task에서 assistant로 활동 보고서를 생성할 때 category_id나 title이 부족할 수 있다.

따라서 1차 구현은 다음 방식으로 처리한다.

```text
- category_id가 없으면 첫 번째 활동 카테고리 또는 "정기 모임 / 스터디" 카테고리 사용
- title이 없으면 메시지에서 제목 추정, 실패 시 "새 활동 보고서"
- save_to_db는 auto_apply 값에 따라 결정
```

너무 복잡하면 결과로 “추가 정보 필요”를 반환해도 된다.

---

## 6. Assistant 결과 표준화

모든 결과는 다음 형태로 맞춘다.

```json
{
  "intent": "receipt_analysis",
  "confidence": 0.85,
  "agent_flow": ["FileParser", "Receipt", "Classifier", "Policy", "Publisher"],
  "result_type": "receipt_analysis",
  "result": {},
  "requires_confirmation": false,
  "message": "영수증 분석이 완료되었습니다."
}
```

---

## 7. Assistant 실행 로그

이번 Task에서 DB 테이블을 새로 만들지 않는다.

실행 로그는 우선 프론트 상태에만 표시한다.

추후 Task에서 `assistant_runs` 테이블을 만들 수 있도록 TODO를 남긴다.

---

# Frontend 구현 요구사항

## 1. Sidebar 메뉴 추가

`/assistant` 메뉴를 Sidebar에 추가한다.

표시 이름:

```text
Assistant
```

또는

```text
Command Center
```

한국어 UI라면:

```text
AI 작업실
```

권장 표시:

```text
AI 작업실
```

---

## 2. Assistant 페이지 구현

파일:

```text
frontend/app/assistant/page.tsx
```

구성:

```text
- AppShell 적용
- Hero 섹션
- 통합 업로드/요청 카드
- 처리 유형 선택
- 예시 요청 chip
- 실행 버튼
- 결과 카드 영역
- 최근 실행 결과는 현재 세션 state로만 유지
```

---

## 3. 업로드 UI

요구사항:

```text
- 파일 선택 input
- 다중 파일 선택 가능
- 선택된 파일 목록 표시
- 파일 제거 가능
- 지원 파일 안내
```

지원 파일:

```text
영수증 이미지: jpg, jpeg, png, webp
거래내역서: xls, xlsx, csv
활동 자료: jpg, png, webp, pdf
```

---

## 4. 요청 입력 UI

요구사항:

```text
- textarea
- placeholder 제공
- 예시 요청 chip 클릭 시 textarea에 입력
```

placeholder 예시:

```text
예: 이 거래내역서 분석해서 2026-1 회비 납부 상태에 반영해줘
```

---

## 5. 처리 유형 선택

select 옵션:

```text
자동 감지
영수증 분석
거래내역서 분석
납부 매칭
활동 보고서 생성
```

값:

```text
auto
receipt_analysis
bank_statement_import
payment_matching
activity_report_generate
```

---

## 6. 추가 옵션

Command Center에서 최소한 다음 옵션을 제공한다.

```text
자동 반영 여부 auto_apply
납부 기간 period
납부 유형 payment_type
기준 금액 required_amount
```

payment_matching 또는 bank_statement_import 요청에서 사용한다.

기본값:

```text
auto_apply = false
period = 2026-1
payment_type = membership_fee
required_amount = 30000
```

---

## 7. Frontend API 함수 추가

파일:

```text
frontend/lib/api.ts
```

추가 함수:

```ts
executeAssistant(formData: FormData)
```

필요 타입:

```ts
AssistantExecuteResponse
AssistantIntent
AssistantResultType
```

---

## 8. 결과 카드 구현

파일 예시:

```text
frontend/components/assistant/AssistantResultCard.tsx
frontend/components/assistant/IntentBadge.tsx
frontend/components/assistant/AgentFlow.tsx
```

결과 카드 표시 내용:

```text
- 작업 유형
- confidence
- agent flow
- message
- result summary
- 상세 페이지 이동 링크
```

상세 링크 예시:

```text
receipt_analysis → /receipts
bank_statement_import → /transactions
payment_matching → /payments
activity_report_generate → /activities 또는 /reports
```

---

## 9. Human-in-the-loop 기본 구조

auto_apply=false이면 결과 카드에 다음 버튼을 표시한다.

```text
확인 후 반영
상세 페이지에서 확인
취소
```

이번 Task에서 모든 반영 버튼을 완벽히 구현하지 않아도 된다.

우선 다음은 구현한다.

```text
payment_matching preview → 확인 후 반영 클릭 시 match-apply 실행
bank_statement preview → 확인 후 반영 클릭 시 import 실행
```

영수증과 활동 보고서는 이미 API에서 save_to_db 처리 구조가 있으면 사용한다.

복잡하면 TODO를 남기고 상세 페이지 링크를 제공한다.

---

# README 업데이트

README에 다음 내용을 추가한다.

```text
- Payment API 404 수정 내용
- 표준 Payment API 경로
- /assistant Command Center 사용 방법
- 자동 감지 규칙
- auto_apply=false와 true 차이
- 이번 Task에서는 LLM 기반 intent classifier는 구현하지 않았다는 설명
```

---

# 실행 검증

가능하면 다음을 실행한다.

```bash
docker compose up -d db
cd backend
alembic upgrade head
python -m app.scripts.seed
python -m compileall app
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
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
http://localhost:3000/payments
http://localhost:3000/assistant
http://localhost:8001/api/payments/summary?period=2026-1&payment_type=membership_fee
http://localhost:8001/api/payments/unpaid?period=2026-1&payment_type=membership_fee
```

확인할 것:

```text
- /payments에서 404가 사라지는지
- /assistant에서 파일/메시지 입력이 가능한지
- 자동 감지 또는 수동 intent 선택이 가능한지
- 영수증/거래내역/납부/활동보고서 요청이 적절한 결과 카드로 표시되는지
- frontend build가 성공하는지
```

---

## 완료 기준

Task 10은 다음을 모두 만족해야 완료로 본다.

1. `/payments` 페이지의 payment summary 404 오류가 해결되어 있다.
2. `/payments` 페이지의 unpaid 404 오류가 해결되어 있다.
3. Payment API 경로가 프론트와 백엔드에서 일치한다.
4. `/api/payments/summary`가 정상 응답한다.
5. `/api/payments/unpaid`가 정상 응답한다.
6. `/assistant` 페이지가 추가되어 있다.
7. Sidebar에서 Assistant 또는 AI 작업실 메뉴로 이동할 수 있다.
8. `/assistant`에서 파일 업로드와 자연어 요청 입력이 가능하다.
9. 요청 의도 자동 감지 또는 수동 선택이 가능하다.
10. Assistant Orchestrator가 기존 기능으로 라우팅한다.
11. 실행 결과가 카드 형태로 표시된다.
12. auto_apply=false일 때 preview/확인 UX가 제공된다.
13. README에 Payment API 수정 및 Command Center 사용 방법이 추가되어 있다.
14. 이번 Task에서 n8n, Notion, Slack, LLM 기반 intent classifier는 구현되지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 10 완료 보고

1. 생성/수정한 주요 파일
- ...

2. Payment API 404 수정 내용
- 원인:
- 수정한 프론트 경로:
- 수정한 백엔드 경로:
- alias 추가 여부:

3. 구현된 Backend 기능
- Assistant router:
- Intent Router:
- Assistant Orchestrator:
- Payment API 보강:

4. 구현된 Frontend 기능
- Assistant 페이지:
- Sidebar:
- Result Card:
- Payments 오류 처리:

5. Intent Router 규칙
- ...

6. 실행 검증 결과
- backend compile/test:
- pytest:
- frontend build:
- /payments 404 해결:
- /assistant 동작:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

9. 다음 Task에서 해야 할 일
- Task 11: Assistant 결과 카드 고도화 및 Human-in-the-loop 반영 UX 완성
```
