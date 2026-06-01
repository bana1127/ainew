# Task 11. Assistant 결과 카드 고도화 및 Human-in-the-loop 반영 UX 완성

## 목표

Task 10에서 구현한 `/assistant` Command Center를 실제 사용 가능한 AI 작업 공간으로 고도화한다.

이번 Task의 핵심은 다음이다.

```text
사용자가 파일과 요청 입력
→ Assistant가 intent 판단
→ preview 또는 분석 결과 표시
→ 사용자가 결과를 확인
→ 사용자가 직접 “반영”을 눌러 DB에 저장/적용
→ 결과가 각 상세 페이지에 반영됨
```

즉, 자동 처리 결과를 즉시 DB에 반영하는 구조가 아니라, 사용자가 한 번 확인하고 승인하는 Human-in-the-loop UX를 완성한다.

---

## 전제 조건

Task 1~10이 완료되어 있어야 한다.

Task 10 완료 기준:

* Payment API 404 오류 수정
* `/assistant` 페이지 구현
* Sidebar에 AI 작업실 메뉴 추가
* 규칙 기반 Intent Router 구현
* Assistant Orchestrator 구현
* Assistant 결과 카드 기본 표시
* 기존 Agent/Service로 작업 라우팅 가능

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. Assistant 결과 카드 타입별 고도화
2. Preview 결과와 Apply 결과 분리
3. “확인 후 반영” UX 구현
4. 작업 유형별 apply API 연결
5. 결과 카드에서 상세 페이지 이동
6. Assistant 실행 결과 상태 관리
7. 결과 카드의 수정/취소/다시 실행 기본 UX
8. Assistant 작업 이력 세션 표시
9. 에러/경고/확인 필요 상태 시각화
10. README에 Assistant 사용 흐름 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* LLM 기반 Intent Classifier
* 멀티턴 대화 메모리
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant 또는 pgvector 연동
* 로그인/권한 시스템
* 대규모 DB 스키마 변경
* 기존 거래내역서 파서 재구현
* 기존 영수증 분석 Agent 재구현
* 기존 납부 매칭 알고리즘 재구현
* 기존 활동 보고서 생성 Agent 재구현

필요한 위치에는 TODO 주석만 남긴다.

---

# 핵심 UX 원칙

이번 Task의 목표는 “AI가 마음대로 저장하는 서비스”가 아니라, “AI가 초안을 만들고 사람이 확인한 뒤 반영하는 서비스”이다.

따라서 다음 원칙을 지킨다.

```text
1. auto_apply=false가 기본값이다.
2. 분석 결과는 먼저 preview로 보여준다.
3. DB 반영은 사용자가 명시적으로 클릭해야 한다.
4. 반영 전에는 어떤 데이터가 저장될지 요약해서 보여준다.
5. 반영 후에는 어느 페이지에서 확인할 수 있는지 안내한다.
6. 실패 시 복구 가능한 에러 메시지를 표시한다.
```

---

# Assistant 결과 타입

Assistant 결과 카드는 최소한 다음 result_type을 지원한다.

```text
receipt_analysis
bank_statement_preview
bank_statement_import_result
payment_matching_preview
payment_matching_result
activity_report_draft
general_message
error
```

---

# 결과 카드 공통 구조

각 결과 카드는 다음 정보를 공통으로 표시한다.

```text
- 작업 유형
- 처리 상태
- 신뢰도 confidence
- 실행된 Agent flow
- 요약 메시지
- 주요 결과
- 확인 필요 여부
- 액션 버튼
- 상세 페이지 이동 링크
```

처리 상태 값:

```text
preview
applied
need_check
failed
cancelled
```

---

# Frontend 구현 요구사항

## 1. Assistant 결과 컴포넌트 구조

다음 컴포넌트를 구현 또는 보강한다.

```text
frontend/components/assistant/
  AssistantResultCard.tsx
  ReceiptResultCard.tsx
  BankStatementResultCard.tsx
  PaymentMatchingResultCard.tsx
  ActivityReportResultCard.tsx
  GeneralResultCard.tsx
  AgentFlow.tsx
  IntentBadge.tsx
  ApplyConfirmDialog.tsx
  ResultSummaryGrid.tsx
```

이미 유사한 파일이 있으면 중복 생성하지 말고 확장한다.

---

## 2. AssistantResultCard

`AssistantResultCard`는 result_type에 따라 적절한 하위 카드를 렌더링한다.

예시:

```text
receipt_analysis → ReceiptResultCard
bank_statement_preview → BankStatementResultCard
payment_matching_preview → PaymentMatchingResultCard
activity_report_draft → ActivityReportResultCard
error → GeneralResultCard
```

---

## 3. ReceiptResultCard

영수증 분석 결과를 보기 좋게 표시한다.

표시 항목:

```text
- 날짜
- 가맹점
- 금액
- 결제 방식
- 지출 분류
- 증빙 상태
- 확인 필요 여부
- 필요 증빙
- 판단 사유
```

액션:

```text
- 영수증 목록에서 보기 → /receipts
- 수정하러 가기 → /receipts
- 취소
```

영수증 분석이 이미 save_to_db=true로 저장된 경우에는 “저장 완료” 상태를 표시한다.

save_to_db=false 또는 preview 성격이면 “영수증으로 저장” 버튼을 제공할 수 있다.

복잡하면 이번 Task에서는 상세 페이지 이동으로 처리하고 TODO를 남긴다.

---

## 4. BankStatementResultCard

거래내역서 preview/import 결과를 표시한다.

표시 항목:

```text
- 전체 행 수
- 파싱 성공 행 수
- 저장된 행 수
- 스킵 행 수
- 중복 행 수
- 경고 수
- 오류 수
```

Preview 상태일 때 액션:

```text
- 거래내역 반영
- 거래내역 페이지에서 보기
- 취소
```

반영 버튼 클릭 시 기존 거래내역 import API 또는 Assistant apply API를 호출한다.

반영 후 상태:

```text
bank_statement_import_result
applied
```

상세 링크:

```text
/transactions
```

---

## 5. PaymentMatchingResultCard

납부 매칭 preview/apply 결과를 표시한다.

표시 항목:

```text
- 납부 기간
- 납부 유형
- 기준 금액
- 전체 대상자 수
- 납부 완료자 수
- 미납자 수
- 확인 필요 거래 수
- 제외 거래 수
```

Preview 상태일 때 액션:

```text
- 납부 상태 반영
- 확인 필요 거래 보기
- 납부 페이지에서 보기
- 취소
```

반영 버튼 클릭 시:

```text
POST /api/payments/match-apply
```

반영 후:

```text
payment_matching_result
applied
```

상세 링크:

```text
/payments
```

---

## 6. ActivityReportResultCard

활동 보고서 초안 생성 결과를 표시한다.

표시 항목:

```text
- 제목
- 요약
- 누락 필드
- 신뢰도
- 본문 preview
```

액션:

```text
- 보고서 저장 또는 이미 저장됨 표시
- 보고서 작성 화면에서 수정
- 활동 보고서 목록에서 보기
- 다시 생성
```

상세 링크:

```text
/reports
/activities
```

---

## 7. ApplyConfirmDialog

반영 버튼을 누르면 바로 실행하지 말고 확인 모달을 띄운다.

공통 문구:

```text
이 결과를 실제 데이터에 반영하시겠습니까?
반영 후에는 각 관리 페이지에서 수정할 수 있습니다.
```

타입별 문구:

```text
거래내역서:
파싱된 거래내역을 bank_transactions에 저장합니다.

납부 매칭:
현재 납부 매칭 결과를 payment_records와 bank_transactions에 반영합니다.

영수증:
분석 결과를 receipts에 저장합니다.

활동 보고서:
생성된 초안을 activity_reports에 저장합니다.
```

버튼:

```text
반영하기
취소
```

---

## 8. Assistant 페이지 상태 관리

`frontend/app/assistant/page.tsx`에서 다음 상태를 관리한다.

```text
- current request
- selected files
- requested intent
- auto_apply
- loading
- error
- results list
```

결과는 현재 세션 동안 누적 표시한다.

구조 예시:

```ts
type AssistantRun = {
  id: string
  createdAt: string
  requestMessage: string
  response: AssistantExecuteResponse
  status: "preview" | "applied" | "failed" | "cancelled"
}
```

DB에 assistant_runs 테이블을 만들지는 않는다.
이번 Task에서는 프론트 state에만 유지한다.

---

## 9. 예시 요청 chip 개선

현재 예시 요청 chip을 더 실사용 흐름에 맞게 정리한다.

예시:

```text
이 영수증 활동비로 정리해줘
이 거래내역서에서 회비 납부 확인해줘
이번 달 미납자 확인해줘
이 사진과 메모로 활동 보고서 초안 만들어줘
이 증빙이 감사 기준에 맞는지 확인해줘
```

chip 클릭 시 textarea에 입력된다.

---

## 10. Assistant 실행 후 자동 스크롤

실행 결과가 생성되면 결과 카드 영역으로 부드럽게 스크롤한다.

과한 애니메이션은 사용하지 않는다.

---

# Backend 구현 요구사항

## 1. Assistant apply endpoint 추가 여부 검토

가능하면 Assistant 전용 apply endpoint를 추가한다.

```http
POST /api/assistant/apply
```

요청 예시:

```json
{
  "intent": "payment_matching",
  "result_type": "payment_matching_preview",
  "payload": {
    "period": "2026-1",
    "payment_type": "membership_fee",
    "required_amount": 30000
  }
}
```

응답은 `AssistantExecuteResponse` 형식을 따른다.

단, 기존 API로 충분히 처리 가능하면 새 endpoint를 만들지 않고 프론트에서 기존 API를 직접 호출해도 된다.

권장:

```text
payment matching apply → 기존 /api/payments/match-apply 사용
bank statement apply → 기존 /api/transactions/import 사용
receipt apply → 기존 /api/agents/receipt/analyze save_to_db=true 사용
activity report apply → 기존 /api/agents/activity-report/generate save_to_db=true 사용
```

이번 Task에서는 불필요한 백엔드 중복을 피한다.

---

## 2. Assistant response에 apply_payload 포함

가능하면 `AssistantExecuteResponse`에 프론트가 반영 버튼을 누를 때 사용할 수 있는 apply payload를 포함한다.

추가 필드:

```python
apply_payload: dict | None = None
detail_url: str | None = None
```

예시:

```json
{
  "intent": "payment_matching",
  "result_type": "payment_matching_preview",
  "requires_confirmation": true,
  "apply_payload": {
    "period": "2026-1",
    "payment_type": "membership_fee",
    "required_amount": 30000
  },
  "detail_url": "/payments"
}
```

기존 응답과 호환되게 optional로 추가한다.

---

## 3. Assistant Orchestrator 보강

`backend/app/agents/assistant_orchestrator.py`를 보강한다.

필수 보강:

```text
- result_type별 detail_url 제공
- preview 결과에는 apply_payload 제공
- error 결과는 표준 error response로 반환
- unknown intent는 친절한 안내 메시지 반환
```

---

## 4. Intent Router 보강

intent가 unknown이면 다음 메시지를 반환한다.

```text
요청을 정확히 분류하지 못했습니다. 영수증 분석, 거래내역서 분석, 납부 매칭, 활동 보고서 생성 중 하나를 선택해 다시 실행해 주세요.
```

---

# Frontend API 보강

파일:

```text
frontend/lib/api.ts
```

추가 또는 보강 함수:

```ts
executeAssistant(formData: FormData)
applyAssistantResult(response: AssistantExecuteResponse)
applyPaymentMatching(payload)
importTransactionsFromAssistant(payload)
```

단, 이미 유사 함수가 있다면 재사용한다.

---

# 디자인 요구사항

Task 9에서 잡은 luxury minimal 디자인을 유지한다.

Assistant 결과 카드는 다음 스타일을 따른다.

```text
- 큰 흰색 카드
- 얇은 border
- 부드러운 shadow
- 상단에 intent badge
- 오른쪽에 confidence 표시
- Agent flow는 작은 pill 형태
- 주요 결과는 2~4열 summary grid
- 확인 필요 항목은 warning-soft 배경
- 적용 완료 항목은 success-soft 배경
```

---

# README 업데이트

README에 다음 내용을 추가한다.

```text
- Assistant 결과 카드 종류
- preview와 applied 상태 차이
- 확인 후 반영 UX 설명
- auto_apply=false 기본 원칙
- 결과 카드에서 상세 페이지로 이동하는 방법
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
http://localhost:3000/assistant
http://localhost:3000/payments
http://localhost:3000/transactions
http://localhost:3000/receipts
http://localhost:3000/reports
```

확인할 것:

```text
- /assistant에서 요청 실행 가능
- 결과 카드가 타입별로 다르게 표시됨
- payment_matching preview 결과에서 납부 상태 반영 가능
- bank_statement preview 결과에서 거래내역 반영 가능
- 결과 카드에서 상세 페이지 이동 가능
- 취소 버튼이 카드 상태를 cancelled로 바꿈
- frontend build 성공
```

---

## 완료 기준

Task 11은 다음을 모두 만족해야 완료로 본다.

1. Assistant 결과 카드가 result_type별로 구분되어 표시된다.
2. 영수증 분석 결과 카드가 표시된다.
3. 거래내역서 preview/import 결과 카드가 표시된다.
4. 납부 매칭 preview/apply 결과 카드가 표시된다.
5. 활동 보고서 초안 결과 카드가 표시된다.
6. auto_apply=false일 때 확인 후 반영 UX가 제공된다.
7. 반영 전 확인 모달이 표시된다.
8. 납부 매칭 preview 결과를 실제로 반영할 수 있다.
9. 거래내역 preview 결과를 실제로 반영할 수 있다.
10. 결과 카드에서 관련 상세 페이지로 이동할 수 있다.
11. 실패 결과가 error 카드로 표시된다.
12. unknown intent가 친절한 안내 메시지로 표시된다.
13. Task 9 디자인 톤과 일관된다.
14. README에 Assistant 결과 카드 및 확인 후 반영 UX 설명이 추가되어 있다.
15. 이번 Task에서 n8n, Notion, Slack, LLM 기반 intent classifier는 구현되지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 11 완료 보고

1. 생성/수정한 주요 파일
- ...

2. Assistant 결과 카드 고도화
- ReceiptResultCard:
- BankStatementResultCard:
- PaymentMatchingResultCard:
- ActivityReportResultCard:
- GeneralResultCard:

3. Human-in-the-loop UX 구현 내용
- 확인 모달:
- 반영 버튼:
- 취소 처리:
- 상세 페이지 이동:

4. Backend 보강 내용
- Assistant response 보강:
- apply_payload:
- detail_url:
- Intent Router 보강:

5. Frontend API 보강
- ...

6. 실행 검증 결과
- backend compile/test:
- pytest:
- frontend build:
- /assistant 동작:
- 결과 카드 표시:
- 반영 UX:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

9. 다음 Task에서 해야 할 일
- Task 12: 실사용형 Dashboard 재설계 및 자동 점검 알림 준비
```
