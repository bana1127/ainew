# Task 21. 활동비 오납/환불 정산 관리

## 목표

ClubAgent의 활동비 납부 관리에 **오납, 중복 납부, 불참자 환불, 환불 거래내역 매칭** 기능을 추가한다.

현재 ClubAgent는 회비/활동비 납부 대상 생성, 거래내역 자동 매칭, 매칭 취소까지 지원한다.
하지만 실제 운영에서는 활동비가 단순히 paid/unpaid로 끝나지 않는다.

예시 상황:

```text
- 활동비 10,000원인데 12,000원을 입금함
- 활동비를 두 번 입금함
- 활동비를 냈지만 개인 사정으로 참여하지 못함
- 신청 후 취소했는데 이미 입금함
- 활동비 환불을 했지만 거래내역과 아직 연결되지 않음
- 입금자명이 달라서 다른 사람에게 잘못 매칭됨
```

이번 Task의 목표는 다음이다.

```text
1. 활동비 오납 상태 감지
2. 중복 납부 상태 감지
3. 참여 취소/불참자 환불 필요 상태 감지
4. 환불 상태 관리
5. 환불 거래내역 매칭
6. 납부/환불 정산 로그 기록
7. 활동 상세와 Payments에서 정산 상태 확인
8. 잘못된 납부/환불 매칭 취소 가능
```

---

## 전제 조건

Task 1~20이 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

```text
- Activities 중심 운영 구조
- 활동 참여자 상태 관리
- activity_fee payment_records 생성
- 거래내역 업로드/파싱
- 회비/활동비 거래내역 매칭
- 매칭 취소
- 활동별 파일함
- 활동별 제출 문서 생성
- Members 상세 이력
```

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

```text
1. 활동비 payment status 확장
2. refund_status 추가 또는 보강
3. 오납/부분납부/중복납부 감지
4. 참여 상태와 납부 상태를 조합한 환불 필요 판단
5. 환불 대상 목록 조회
6. 환불 처리 수동 등록
7. 출금 거래내역을 환불로 매칭
8. 환불 매칭 취소
9. 정산 로그 기록
10. 활동 상세 활동비 탭에 정산 상태 표시
11. Payments 활동비 탭에 오납/환불 상태 표시
12. Members 상세에 환불/오납 이력 표시
13. 자동 점검에 환불 필요/오납 항목 반영
14. README 또는 DEMO 문서 업데이트
```

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

```text
- 실제 은행 API 연동
- 실제 환불 송금 자동 실행
- QR/PG 결제 기능
- 카카오페이/토스페이 연동
- 회계 감사 보고서 자동 생성
- 복잡한 복식부기 장부 시스템
- Notion/Slack/Telegram 연동
- 로그인/권한 시스템
```

이번 Task는 **환불 필요 여부 판단, 환불 기록, 거래내역 매칭, 정산 상태 관리**까지만 구현한다.

---

# Part A. 상태 모델 정리

## 1. payment status 확장

기존 payment_record.status가 있다면 다음 값을 지원한다.

```text
unpaid
partial
paid
overpaid
need_check
exempt
refunded
cancelled
```

의미:

```text
unpaid
→ 납부 없음

partial
→ 필요 금액보다 적게 납부

paid
→ 정확히 납부 완료

overpaid
→ 필요 금액보다 많이 납부

need_check
→ 자동 판단 불가 또는 수동 확인 필요

exempt
→ 면제

refunded
→ 환불 완료

cancelled
→ 납부 대상 취소
```

기존 status enum이 있으면 migration 또는 schema validation을 보강한다.

---

## 2. refund_status 추가

PaymentRecord에 환불 상태를 추가한다.

권장 필드:

```text
refund_status
refund_amount
refund_transaction_id
refund_reason
refunded_at
```

refund_status 값:

```text
none
refund_required
refund_pending
refunded
refund_denied
```

의미:

```text
none
→ 환불 필요 없음

refund_required
→ 환불 필요

refund_pending
→ 환불 처리 예정 또는 처리 중

refunded
→ 환불 완료

refund_denied
→ 환불하지 않기로 처리
```

기존 DB 변경이 부담되면 nullable 필드로 최소 migration을 추가한다.

---

## 3. 참여 상태와 환불 판단

ActivityParticipant.status를 기준으로 환불 필요 여부를 판단한다.

참여 상태 예시:

```text
applied
confirmed
attended
completed
cancelled
no_show
```

환불 필요 판단 기본 규칙:

```text
participant.status in [cancelled, no_show]
AND payment_record.paid_amount > 0
AND refund_status != refunded
→ refund_required
```

단, 동아리 운영상 불참 환불 불가 정책이 있을 수 있으므로 수동 override가 가능해야 한다.

---

# Part B. 정산 계산 규칙

## 1. 기본 계산

PaymentRecord 기준:

```text
required_amount = 내야 하는 금액
paid_amount = 실제 입금된 금액
refund_amount = 환불해야 하거나 환불한 금액
net_paid_amount = paid_amount - refunded_amount
```

상태 계산:

```text
paid_amount == 0
→ unpaid

0 < paid_amount < required_amount
→ partial

paid_amount == required_amount
→ paid

paid_amount > required_amount
→ overpaid

participant cancelled/no_show and paid_amount > 0
→ refund_required
```

---

## 2. 오납 계산

활동비가 10,000원인데 12,000원을 입금한 경우:

```text
required_amount = 10000
paid_amount = 12000
overpaid_amount = 2000
status = overpaid
refund_status = refund_required 또는 none
```

운영 정책상 오납분을 환불해야 하면:

```text
refund_amount = overpaid_amount
refund_status = refund_required
```

---

## 3. 중복 납부 계산

같은 member_id + activity_id + payment_type에 여러 transaction이 연결되거나 같은 사람이 같은 활동비 금액을 여러 번 입금하면 중복 납부 후보로 본다.

조건 예시:

```text
payment_type = activity_fee
member_id 같음
activity_id/activity_report_id 같음
입금 transaction 2개 이상
paid_amount > required_amount
```

처리:

```text
status = overpaid 또는 need_check
refund_status = refund_required
note = 중복 납부 가능성
```

---

## 4. 환불 완료 계산

환불 출금 거래내역이 연결되면:

```text
refund_transaction_id = transaction.id
refund_status = refunded
refunded_at = transaction date 또는 now
```

환불 후 net 상태:

```text
paid_amount - refund_amount == required_amount
→ paid

paid_amount - refund_amount == 0 and participant cancelled/no_show
→ cancelled 또는 refunded

paid_amount - refund_amount < required_amount
→ partial 또는 need_check
```

---

# Part C. 정산 로그

## 1. PaymentAdjustmentLog 모델

정산 관련 변경 이력을 남긴다.

권장 모델:

```text
PaymentAdjustmentLog
- id
- payment_record_id
- transaction_id nullable
- action
- previous_status nullable
- new_status nullable
- previous_paid_amount nullable
- new_paid_amount nullable
- refund_amount nullable
- reason nullable
- metadata_json nullable
- created_at
```

action 값:

```text
match
unmatch
manual_update
overpayment_detected
refund_required
refund_pending
refund_completed
refund_cancelled
refund_denied
status_recalculated
```

이번 Task에서 모든 변경에 로그를 남기기 어렵다면 최소한 다음 액션에 로그를 남긴다.

```text
manual_update
unmatch
refund_required
refund_completed
refund_cancelled
```

---

# Part D. Backend Service

## 1. settlement_service 구현

권장 파일:

```text
backend/app/services/settlement_service.py
```

주요 함수:

```python
recalculate_payment_status(db, payment_record_id)
detect_overpayment(db, payment_record_id)
detect_refund_required(db, activity_id=None)
mark_refund_required(db, payment_record_id, reason=None)
mark_refund_pending(db, payment_record_id, refund_amount, reason=None)
mark_refunded(db, payment_record_id, refund_transaction_id=None, refund_amount=None)
cancel_refund(db, payment_record_id, reason=None)
create_adjustment_log(...)
```

---

## 2. 기존 매칭 서비스와 연동

Task 18에서 구현한 거래내역 매칭 후 settlement recalculation을 호출한다.

흐름:

```text
거래내역 매칭
→ paid_amount 갱신
→ status 재계산
→ overpaid/partial/paid 판단
→ participant status와 비교
→ refund_required 여부 판단
```

매칭 취소 후에도 재계산한다.

```text
매칭 취소
→ transaction 연결 해제
→ paid_amount 재계산
→ status 재계산
→ refund_status 재계산
```

---

# Part E. Backend API

## 1. 정산 요약 API

```http
GET /api/settlements/summary
```

Query:

```text
activity_id optional
period optional
payment_type optional default activity_fee
```

응답 예시:

```json
{
  "total_records": 10,
  "paid_count": 6,
  "unpaid_count": 2,
  "partial_count": 1,
  "overpaid_count": 1,
  "refund_required_count": 1,
  "refunded_count": 0,
  "need_check_count": 1,
  "total_required_amount": 100000,
  "total_paid_amount": 112000,
  "total_overpaid_amount": 12000,
  "total_refund_required_amount": 12000
}
```

---

## 2. 환불 대상 목록 API

```http
GET /api/settlements/refunds
```

Query:

```text
activity_id optional
status optional
```

응답 row:

```json
{
  "payment_record_id": "record-id",
  "member_id": "member-id",
  "member_name": "김가온",
  "student_id": "20260001",
  "activity_id": "activity-id",
  "activity_title": "교내 조향 활동",
  "participant_status": "cancelled",
  "required_amount": 10000,
  "paid_amount": 10000,
  "refund_amount": 10000,
  "refund_status": "refund_required",
  "reason": "참여 취소 후 납부 완료"
}
```

---

## 3. 환불 필요 표시 API

```http
POST /api/payment-records/{payment_record_id}/refund-required
```

요청:

```json
{
  "refund_amount": 10000,
  "reason": "참여 취소로 인한 환불 필요"
}
```

---

## 4. 환불 대기 처리 API

```http
POST /api/payment-records/{payment_record_id}/refund-pending
```

요청:

```json
{
  "refund_amount": 10000,
  "reason": "환불 처리 예정"
}
```

---

## 5. 환불 완료 처리 API

```http
POST /api/payment-records/{payment_record_id}/mark-refunded
```

요청:

```json
{
  "refund_transaction_id": "transaction-id optional",
  "refund_amount": 10000,
  "reason": "거래내역 출금 확인"
}
```

---

## 6. 환불 취소 API

```http
POST /api/payment-records/{payment_record_id}/refund-cancel
```

요청:

```json
{
  "reason": "환불 대상 아님으로 확인"
}
```

---

## 7. 환불 거래내역 매칭 API

```http
POST /api/transactions/{transaction_id}/match-refund
```

요청:

```json
{
  "payment_record_id": "payment-record-id",
  "refund_amount": 10000
}
```

동작:

```text
1. transaction이 출금 거래인지 확인
2. payment_record 환불 대상인지 확인
3. refund_transaction_id 연결
4. refund_status = refunded
5. refund_amount 기록
6. transaction.match_status = refund_matched
7. 정산 로그 기록
```

---

## 8. 환불 매칭 취소 API

```http
POST /api/transactions/{transaction_id}/unmatch-refund
```

동작:

```text
1. refund_transaction_id로 연결된 payment_record 찾기
2. refund_transaction_id = null
3. refund_status = refund_required 또는 refund_pending으로 복구
4. transaction.match_status = unmatched
5. 정산 로그 기록
```

---

# Part F. Frontend UI

## 1. 활동 상세 > 활동비 탭 보강

수정 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/components/payments/*
frontend/lib/api.ts
```

활동비 탭에 정산 상태를 추가한다.

표시 항목:

```text
이름
학번
참여 상태
필요 금액
납부 금액
오납 금액
환불 상태
정산 상태
작업 버튼
```

작업 버튼:

```text
직접 수정
환불 필요 표시
환불 대기
환불 완료
환불 취소
매칭 취소
```

---

## 2. Payments > 활동비 탭 보강

활동비 전체 현황에 다음 필터를 추가한다.

```text
전체
미납
부분 납부
납부 완료
오납
환불 필요
환불 완료
확인 필요
```

각 row/card에 다음을 표시한다.

```text
활동명
부원명
필요 금액
납부 금액
오납 금액
참여 상태
환불 상태
정산 상태
```

---

## 3. Transactions 페이지 보강

거래내역 목록에서 출금 거래를 환불로 매칭할 수 있게 한다.

출금 거래 row에 버튼:

```text
환불로 매칭
```

클릭 시 모달:

```text
환불 대상 선택
검색: 이름/활동명
환불 금액
확인
```

이미 환불 매칭된 거래에는:

```text
환불 매칭됨
환불 매칭 취소
```

---

## 4. Members 상세 보강

부원 상세 페이지에 정산 이력을 표시한다.

섹션:

```text
활동비 정산 이력
```

표시:

```text
활동명
필요 금액
납부 금액
오납 금액
환불 상태
환불 금액
상태
```

---

## 5. 정산 로그 보기

선택사항이지만 가능하면 payment record 상세 또는 row 확장 영역에서 로그를 볼 수 있게 한다.

```text
정산 이력 보기
```

표시:

```text
일시
작업
이전 상태
변경 상태
사유
```

---

# Part G. 자동 점검 반영

## 1. weekly-check 보강

자동 점검 서비스에 다음 항목을 추가한다.

```text
오납 납부 기록 수
환불 필요 기록 수
환불 대기 기록 수
확인 필요 활동비 기록 수
```

Notifications 메시지 예시:

```text
환불이 필요한 활동비 납부 기록 2건, 오납 1건이 있습니다.
```

---

# Part H. 문서화

README 또는 DEMO 문서에 다음 내용을 추가한다.

```text
- 활동비 오납 감지 기준
- 중복 납부 확인 방법
- 참여 취소/불참 시 환불 필요 처리
- 환불 대기/완료 처리 방법
- 출금 거래내역을 환불로 매칭하는 방법
- 환불 매칭 취소 방법
- 정산 로그 확인 방법
```

---

# 실행 검증

## Backend

```bash
cd backend
alembic upgrade head
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

# 확인 시나리오

## 시나리오 1. 오납 감지

```text
1. 활동비 required_amount = 10000인 payment_record 준비
2. 12000원 입금 거래내역 매칭
3. status = overpaid 확인
4. overpaid_amount = 2000 확인
5. refund_status = refund_required 또는 need_check 확인
```

## 시나리오 2. 부분 납부 감지

```text
1. required_amount = 10000
2. 5000원 입금 매칭
3. status = partial 확인
```

## 시나리오 3. 참여 취소 후 환불 필요

```text
1. 활동 참여자 status = cancelled로 변경
2. 해당 참여자의 paid_amount > 0 확인
3. refund_status = refund_required 확인
```

## 시나리오 4. 환불 완료 처리

```text
1. refund_required record 선택
2. 환불 완료 처리
3. refund_status = refunded 확인
4. refund_amount 기록 확인
```

## 시나리오 5. 출금 거래내역 환불 매칭

```text
1. 출금 transaction 준비
2. 환불 대상 payment_record와 매칭
3. transaction.match_status = refund_matched 확인
4. payment_record.refund_transaction_id 연결 확인
5. refund_status = refunded 확인
```

## 시나리오 6. 환불 매칭 취소

```text
1. refund_matched transaction 선택
2. 환불 매칭 취소
3. transaction.match_status = unmatched 확인
4. payment_record.refund_status가 refund_required 또는 refund_pending으로 복구되는지 확인
```

## 시나리오 7. UI 확인

```text
1. /activities/{id} 활동비 탭에서 오납/환불 상태 확인
2. /payments?tab=activity_fee에서 필터 확인
3. /transactions에서 환불 매칭 버튼 확인
4. /members/{id}에서 정산 이력 확인
```

---

## 완료 기준

Task 21은 다음을 모두 만족해야 완료로 본다.

```text
1. payment status에 overpaid/refunded/cancelled 처리가 가능하다.
2. refund_status를 관리할 수 있다.
3. 오납을 자동 감지할 수 있다.
4. 부분 납부를 자동 감지할 수 있다.
5. 참여 취소/불참자 환불 필요를 감지할 수 있다.
6. 환불 대상 목록을 조회할 수 있다.
7. 환불 필요/대기/완료/취소 처리가 가능하다.
8. 출금 거래내역을 환불로 매칭할 수 있다.
9. 환불 매칭 취소가 가능하다.
10. 정산 로그가 기록된다.
11. 활동 상세 활동비 탭에서 정산 상태를 볼 수 있다.
12. Payments 활동비 탭에서 오납/환불 필터가 가능하다.
13. Transactions에서 환불 매칭을 처리할 수 있다.
14. Members 상세에서 활동비 정산 이력을 확인할 수 있다.
15. 자동 점검에 환불 필요/오납 항목이 반영된다.
16. frontend build가 성공한다.
17. backend compile/test가 성공한다.
18. 이번 Task에서 실제 송금/은행 API/PG 연동은 구현하지 않았다.
```

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 21 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 정산 데이터 구조
- payment status:
- refund_status:
- migration:
- adjustment log:

3. Settlement service
- status recalculation:
- overpayment detection:
- refund detection:
- refund processing:
- log creation:

4. Backend API
- summary:
- refunds list:
- refund required:
- refund pending:
- mark refunded:
- refund cancel:
- match refund:
- unmatch refund:

5. Frontend UI
- Activity detail:
- Payments:
- Transactions:
- Members detail:
- settlement log:

6. 자동 점검 반영
- weekly-check:
- notifications:

7. 실행 검증 결과
- alembic upgrade:
- backend compile/test:
- frontend build:
- 오납 감지:
- 부분 납부:
- 환불 필요:
- 환불 완료:
- 환불 매칭:
- 환불 매칭 취소:

8. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

9. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task21: add activity fee settlement and refunds
```
