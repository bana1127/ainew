# Task 30. 활동 내부 활동비 거래내역 매칭 구조 수정

현재 프로젝트는 ClubAgent입니다.

Task 29에서 회비와 활동비 화면 구조를 분리했습니다.

현재 정책:

```text
Payments / 회비 화면
→ membership_fee만 관리

Activities > 특정 활동 > 활동비 탭
→ activity_fee만 관리

Transactions
→ 전체 거래내역 원장
```

이번 Task 30의 목표는 **특정 활동 내부에서 해당 활동 참가자 기준으로 활동비 거래내역 매칭을 정확하게 수행하는 것**입니다.

---

# 현재 문제

현재 활동비 매칭에는 다음 문제가 있습니다.

```text
1. 활동비 매칭이 전역 Payments 흐름과 섞일 수 있음
2. 특정 활동의 참가자만 대상으로 매칭해야 하는데 범위가 불명확함
3. 활동비 PaymentRecord가 있어도 거래내역과 연결이 잘 안 됨
4. 금액이 정확히 일치하지 않아도 후보가 될 수 있음
5. 이미 매칭된 거래/이미 납부된 기록에 대한 보호가 부족함
6. 활동 내부 AI가 활동비 매칭을 제대로 실행하지 못함
7. 활동비 탭 UI에서 매칭 결과를 보기 어렵고 난잡함
```

---

# 핵심 정책

활동비 매칭은 반드시 현재 활동 내부에서만 처리합니다.

```text
activity_fee 매칭 기준:
activity_report_id + member_id + payment_type=activity_fee
```

거래내역은 전체 Transactions 원장에서 가져오되, 매칭 대상은 현재 활동의 참가자와 활동비 record로 제한합니다.

자동 매칭 후보 조건:

```text
1. 현재 activity_id의 참가자이다.
2. 해당 참가자의 activity_fee PaymentRecord가 존재한다.
3. 거래내역이 입금 거래이다.
4. 거래 금액이 PaymentRecord.required_amount와 정확히 일치한다.
5. 거래 적요/입금자명에서 참가자 이름 또는 식별자가 매칭된다.
6. PaymentRecord가 이미 paid 상태가 아니다.
7. 거래내역이 이미 다른 PaymentRecord에 매칭되지 않았다.
```

금액은 반드시 exact match입니다.

```text
deposit_amount == required_amount
```

금액이 다르면 자동 매칭 금지입니다.

---

# 구현 목표

## 1. 활동 상세 활동비 탭에 매칭 버튼 추가/정리

위치:

```text
Activities > 특정 활동 상세 > 활동비 탭
```

버튼:

```text
[거래내역에서 이 활동 활동비 매칭]
```

동작:

```text
1. 현재 activity_id 확인
2. 해당 활동 참가자 조회
3. 해당 활동 activity_fee PaymentRecord 조회
4. 전체 거래내역 중 입금 내역 조회
5. 현재 활동 참가자와 거래내역 매칭 preview 생성
6. 사용자 확인 후 반영
```

---

# 2. 활동비 매칭 Preview API

다음 API를 구현하거나 기존 API를 보강하세요.

```http
POST /api/activities/{activity_id}/activity-fees/match-transactions-preview
POST /api/activities/{activity_id}/activity-fees/match-transactions-confirm
POST /api/activities/{activity_id}/activity-fees/match-transactions-cancel
```

Task 25의 Proposed Action 구조가 있다면 confirm/cancel은 공통 API를 사용해도 됩니다.

```http
POST /api/assistant/actions/{action_id}/confirm
POST /api/assistant/actions/{action_id}/cancel
```

Preview 단계에서는 DB를 변경하지 마세요.

응답 예시:

```json
{
  "requires_confirmation": true,
  "auto_apply": false,
  "activity_id": "...",
  "payment_type": "activity_fee",
  "summary": {
    "participants": 19,
    "payment_records": 19,
    "auto_match_candidates": 8,
    "amount_mismatch": 2,
    "name_needs_review": 3,
    "already_paid": 1,
    "already_matched_transactions": 1,
    "unmatched": 5
  },
  "rows": [
    {
      "transaction_id": "...",
      "payment_record_id": "...",
      "member_id": "...",
      "member_name": "박민서",
      "transaction_date": "2026-06-03",
      "description": "박민서",
      "required_amount": 25000,
      "deposit_amount": 25000,
      "difference": 0,
      "status": "auto_match_candidate",
      "reason": "이름 및 활동비 금액 정확히 일치"
    },
    {
      "transaction_id": "...",
      "payment_record_id": "...",
      "member_name": "김성래",
      "transaction_date": "2026-06-03",
      "description": "김성래",
      "required_amount": 25000,
      "deposit_amount": 10000,
      "difference": -15000,
      "status": "amount_mismatch",
      "reason": "활동비 필요 금액과 입금액 불일치"
    }
  ],
  "confirm_payload": {
    "action_id": "..."
  }
}
```

---

# 3. Matching Rule

## 자동 매칭 가능

```text
member matched
required_amount == deposit_amount
payment_record.status != paid
transaction not already matched
```

결과:

```text
status = auto_match_candidate
```

## 금액 불일치

```text
member matched
required_amount != deposit_amount
```

결과:

```text
status = amount_mismatch
auto_apply 금지
```

세부 분류:

```text
deposit_amount < required_amount → amount_mismatch_partial
deposit_amount > required_amount → amount_mismatch_overpaid
```

## 이름 확인 필요

```text
amount exact match
but name ambiguous
```

결과:

```text
status = name_needs_review
```

## 이미 납부 완료

```text
payment_record.status == paid
```

결과:

```text
status = already_paid
```

## 이미 매칭된 거래

```text
transaction already linked to another payment_record
```

결과:

```text
status = already_matched_transaction
```

---

# 4. Confirm 반영

Confirm 시에도 반드시 재검증하세요.

동작:

```text
1. action_id 조회
2. preview payload 조회
3. 각 row의 transaction_id, payment_record_id 재조회
4. activity_id가 현재 활동과 같은지 확인
5. payment_type이 activity_fee인지 확인
6. transaction.deposit_amount == payment_record.required_amount 재검증
7. transaction이 이미 다른 record에 매칭되어 있으면 skip
8. payment_record가 이미 paid이면 skip
9. 조건을 만족한 row만 반영
```

반영:

```text
payment_record.paid_amount = transaction.deposit_amount
payment_record.status = paid
payment_record.matched_transaction_id = transaction.id
payment_record.matched_at = now
```

금액 불일치/확인 필요 row는 자동 반영하지 않습니다.

---

# 5. 활동비 탭 UI 정리

활동비 탭을 다음 구조로 정리하세요.

## 활동비 요약

```text
참가자 수
납부 완료
미납
부분 납부
초과 납부
환불 필요
총 예정 금액
총 납부 금액
```

## 거래내역 매칭 섹션

```text
[거래내역에서 이 활동 활동비 매칭]
```

매칭 결과 preview:

```text
자동 매칭 후보
금액 불일치
이름 확인 필요
이미 납부 완료
이미 매칭된 거래
미매칭
```

row 표시:

```text
거래일
적요
추정 참가자
필요 금액
입금액
차액
상태
사유
작업
```

## 납부 현황 테이블

기본 컬럼:

```text
이름
학번
필요 금액
납부 금액
상태
환불 상태
작업
```

작업은 너무 많이 노출하지 말고, 위험 작업은 더보기/모달로 이동하세요.

---

# 6. AI 연동

활동 상세 내부 AI에서 다음 요청을 처리해야 합니다.

```text
이 거래내역으로 활동비 매칭해줘
현재 활동 활동비 매칭해줘
참가자들 활동비 입금 확인해줘
```

조건:

```text
source = activity_detail
activity_id 존재
```

이 경우:

```text
activity_fee_transaction_match_for_activity
```

전역 AI 작업실에서 다음처럼 요청하면 바로 실행하지 마세요.

```text
활동비 매칭해줘
거래내역으로 활동비 확인해줘
```

응답:

```text
어떤 활동의 활동비를 매칭할까요?
기존 활동을 선택해주세요.
```

---

# 7. Backend 수정 대상

확인 대상:

```text
backend/app/routers/activities.py
backend/app/routers/payment_matching.py
backend/app/services/payment_matching_service.py
backend/app/services/activity_fee_generation_service.py
backend/app/services/assistant_action_service.py
backend/app/agents/assistant_orchestrator.py
backend/app/models/payment.py
backend/app/schemas/payment.py
```

필요하면 신규 서비스 추가:

```text
backend/app/services/activity_fee_transaction_matching_service.py
```

---

# 8. Frontend 수정 대상

확인 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/components/assistant/AssistantResultCard.tsx
frontend/lib/api.ts
```

필요하면 컴포넌트 분리:

```text
ActivityFeeTab
ActivityFeeMatchPreviewCard
ActivityFeeSummaryCards
```

---

# 9. 테스트

추가 또는 보강:

```text
backend/tests/test_activity_fee_transaction_matching.py
backend/tests/test_activity_fee_matching_scope.py
backend/tests/test_activity_fee_matching_exact_amount.py
backend/tests/test_assistant_activity_fee_match_intent.py
```

필수 테스트:

```text
1. 현재 activity_id의 activity_fee만 매칭 대상
2. 다른 활동의 activity_fee는 제외
3. membership_fee는 제외
4. required_amount=25000, deposit_amount=25000 → auto_match_candidate
5. required_amount=25000, deposit_amount=10000 → amount_mismatch
6. 이름이 같아도 금액이 다르면 자동 매칭 금지
7. 금액이 같아도 이름이 애매하면 needs_review
8. 이미 paid인 record는 자동 매칭 금지
9. 이미 다른 record에 연결된 transaction은 자동 매칭 금지
10. confirm 시에도 amount/scope/payment_type 재검증
11. 전역 AI에서 activity_id 없이 활동비 매칭 요청 시 clarification 반환
12. 활동 상세 AI에서 활동비 매칭 요청 시 현재 activity_id로 preview 생성
```

---

# 10. 브라우저 검증

```text
1. DB 초기화
2. 부원 명단 업로드
3. 활동 생성
4. 활동 참가자 import
5. 활동비 25,000원 대상 생성
6. 거래내역 업로드
7. 활동 상세 > 활동비 탭 접속
8. [거래내역에서 이 활동 활동비 매칭] 실행
9. preview 확인
10. 금액이 정확히 맞는 거래만 자동 후보인지 확인
11. 금액 불일치 거래는 확인 필요인지 확인
12. 확인 후 반영
13. 해당 활동의 activity_fee만 paid 처리되는지 확인
14. membership_fee가 변경되지 않는지 확인
15. 다른 활동의 activity_fee가 변경되지 않는지 확인
```

---

# 완료 기준

```text
1. 활동비 거래내역 매칭은 활동 상세 내부에서 수행된다.
2. 현재 activity_id의 activity_fee만 매칭 대상이다.
3. membership_fee는 절대 수정되지 않는다.
4. 다른 활동의 activity_fee도 수정되지 않는다.
5. required_amount와 deposit_amount가 정확히 일치할 때만 자동 후보가 된다.
6. 금액 불일치는 확인 필요로 표시된다.
7. Preview 후 Confirm 구조를 따른다.
8. Confirm 시에도 scope/payment_type/amount를 재검증한다.
9. 활동 내부 AI에서 활동비 매칭 명령이 동작한다.
10. 전역 AI에서는 activity_id 없으면 활동 선택 요청을 반환한다.
11. pytest 통과
12. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 30 완료 보고

1. 원인
- 활동비 매칭이 전역 payment 흐름과 섞인 이유:
- activity_id scope가 불명확했던 이유:

2. 수정한 파일
- backend:
- frontend:
- tests:

3. Matching Service
- scope:
- exact amount:
- already paid:
- already matched transaction:

4. API
- preview:
- confirm:
- cancel:

5. UI
- 활동비 탭:
- 매칭 preview:
- 납부 현황:

6. AI 연동
- 활동 내부 AI:
- 전역 AI clarification:

7. 검증
- 현재 활동 매칭:
- 다른 활동 제외:
- membership_fee 보호:
- 금액 불일치:
- pytest:
- npm run build:

권장 커밋 메시지:
task30: implement scoped activity fee transaction matching
```
