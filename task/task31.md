# Task 31. 활동 상세 활동비 탭 UI 정리

현재 프로젝트는 ClubAgent입니다.

Task 29에서 회비와 활동비 화면 구조를 분리했고, Task 30에서 활동 내부 활동비 거래내역 매칭 구조를 수정했습니다.

이번 Task 31의 목표는 **활동 상세 페이지의 활동비 탭을 실제 사용하기 편하게 정리하는 것**입니다.

현재 문제:

```text
1. 활동비 탭에 버튼과 상태가 너무 많이 노출되어 있음
2. 수정 / 환불 필요 / 환불 대기 / 환불 완료 / 취소 / 매칭 취소 등이 한 줄에 몰려 있어 난잡함
3. 활동비 설정, 요약, 매칭, 개별 납부 관리가 한 화면에서 구분되지 않음
4. 활동비 매칭 결과와 납부 현황이 섞여 보임
5. 사용자가 어떤 작업을 먼저 해야 하는지 흐름이 명확하지 않음
```

---

# 핵심 목표

활동비 탭을 다음 4개 섹션으로 정리합니다.

```text
1. 활동비 설정
2. 활동비 요약
3. 거래내역 매칭
4. 납부 현황
```

위험하거나 복잡한 작업은 테이블에 전부 노출하지 말고, row별 더보기 메뉴 또는 모달에서 처리합니다.

---

# 1. 활동비 설정 섹션

위치: 활동비 탭 상단

표시 내용:

```text
1인당 활동비
[금액 입력]
[활동비 대상 생성/갱신]
```

설명 문구:

```text
현재 활동 참가자를 기준으로 활동비 납부 대상을 생성합니다.
기존 납부 금액은 유지되고, 필요 금액만 갱신됩니다.
```

동작:

```text
1. 사용자가 금액 입력
2. 활동비 대상 생성/갱신 클릭
3. 바로 반영하지 않고 preview 표시
4. 확인 후 반영 시 activity_fee PaymentRecord 생성/갱신
```

필수 조건:

```text
- 현재 activity_id 기준으로만 처리
- membership_fee는 절대 수정하지 않음
- 기존 paid_amount는 유지
- required_amount 변경 시 status 재계산
```

---

# 2. 활동비 요약 섹션

활동비 설정 아래에 요약 카드를 배치합니다.

표시 항목:

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

예시:

```text
참가자 19명
납부 완료 8명
미납 10명
부분 납부 1명
환불 필요 0명
총 예정 금액 475,000원
총 납부 금액 200,000원
```

요약 값은 현재 activity_id의 activity_fee record만 기준으로 계산해야 합니다.

---

# 3. 거래내역 매칭 섹션

버튼:

```text
[거래내역에서 이 활동 활동비 매칭]
```

동작:

```text
1. 전체 거래내역 원장에서 입금 거래 조회
2. 현재 활동 참가자와 activity_fee PaymentRecord 기준으로 매칭
3. required_amount와 deposit_amount exact match만 자동 후보
4. 금액 불일치, 이름 애매함, 이미 납부, 이미 매칭 거래는 확인 필요로 표시
5. preview 후 확인 반영
```

Preview 분류:

```text
자동 매칭 후보
금액 불일치
이름 확인 필요
이미 납부 완료
이미 매칭된 거래
미매칭
```

Preview row 표시:

```text
거래일
적요
추정 참가자
필요 금액
입금액
차액
상태
사유
```

Confirm 후:

```text
- 자동 매칭 후보만 반영
- payment_record.paid_amount = transaction.deposit_amount
- status = paid
- matched_transaction_id 저장
- 현재 활동 activity_fee만 수정
```

---

# 4. 납부 현황 테이블

테이블 컬럼:

```text
이름
학번
필요 금액
납부 금액
상태
환불 상태
매칭 거래
작업
```

상태 badge:

```text
미납
부분 납부
납부 완료
초과 납부
확인 필요
면제
```

환불 상태 badge:

```text
없음
환불 필요
환불 대기
환불 완료
```

작업 컬럼은 버튼을 과하게 늘리지 마세요.

기본 노출:

```text
[수정]
[더보기]
```

더보기 메뉴 안에 넣을 작업:

```text
납부 완료 처리
부분 납부 처리
미납 처리
환불 필요 표시
환불 완료 처리
매칭 취소
납부 기록 메모
```

위험 작업은 반드시 확인 모달을 띄웁니다.

---

# 5. 개별 수정 모달

수정 버튼 클릭 시 모달을 띄웁니다.

수정 가능 항목:

```text
필요 금액
납부 금액
상태
환불 상태
메모
```

수정 규칙:

```text
paid_amount = 0 → unpaid
0 < paid_amount < required_amount → partial
paid_amount == required_amount → paid
paid_amount > required_amount → overpaid
```

단, 사용자가 직접 status를 선택한 경우에는 경고를 표시하고 확인 후 반영합니다.

---

# 6. 매칭 취소

매칭 취소는 다음처럼 동작해야 합니다.

```text
1. matched_transaction_id 제거
2. matched_at 제거
3. paid_amount를 0으로 되돌릴지, 유지할지 사용자에게 선택하게 함
4. 기본값은 paid_amount 유지 + status 재계산
5. 모든 작업은 확인 후 반영
```

모달 문구:

```text
이 거래내역 매칭을 취소하시겠습니까?
납부 금액을 유지할지 초기화할지 선택해주세요.
```

옵션:

```text
납부 금액 유지
납부 금액 0원으로 초기화
```

---

# 7. 환불 처리

초과 납부 또는 참여 취소 시 환불 상태를 관리할 수 있어야 합니다.

환불 상태:

```text
none
refund_needed
refund_pending
refunded
```

화면 표시:

```text
없음
환불 필요
환불 대기
환불 완료
```

환불 관련 작업도 더보기 메뉴 안에서 처리하세요.

---

# 8. AI 결과 카드와 연동

활동 내부 AI에서 다음 요청이 들어오면 활동비 탭의 구조와 같은 결과를 보여야 합니다.

```text
박민서 활동비 25000원 냈어
이 거래내역으로 활동비 매칭해줘
참가자들 활동비 완납 처리해줘
```

결과 카드 제목:

```text
활동비 납부 상태 변경 미리보기
활동비 거래내역 매칭 미리보기
활동비 일괄 완납 처리 미리보기
```

결과 카드에는 반드시 현재 활동명이 표시되어야 합니다.

---

# 9. Frontend 수정 대상

확인 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/lib/api.ts
frontend/components/assistant/AssistantResultCard.tsx
```

가능하면 컴포넌트 분리:

```text
ActivityFeeTab
ActivityFeeSummaryCards
ActivityFeeSettingsPanel
ActivityFeeMatchPreview
ActivityFeeRecordsTable
ActivityFeeEditModal
```

---

# 10. Backend 확인 대상

확인 대상:

```text
backend/app/routers/activities.py
backend/app/routers/payment_records.py
backend/app/services/activity_fee_generation_service.py
backend/app/services/activity_fee_transaction_matching_service.py
backend/app/services/payment_manual_update_service.py
backend/app/services/assistant_action_service.py
```

필수 보장:

```text
- 모든 activity_fee 작업은 activity_id scope 검증
- membership_fee 수정 금지
- confirm 시 payment_type=activity_fee 재검증
- 다른 활동의 activity_fee 수정 금지
```

---

# 11. 테스트

추가 또는 보강:

```text
backend/tests/test_activity_fee_tab_summary.py
backend/tests/test_activity_fee_manual_update.py
backend/tests/test_activity_fee_refund_status.py
backend/tests/test_activity_fee_match_cancel.py
```

필수 테스트:

```text
1. 활동비 요약은 현재 activity_id의 activity_fee만 집계
2. 다른 활동 activity_fee는 요약에 포함되지 않음
3. membership_fee는 요약에 포함되지 않음
4. 개별 납부 수정 시 status가 올바르게 재계산됨
5. 매칭 취소 시 matched_transaction_id가 제거됨
6. 환불 상태 변경이 activity_fee record에만 적용됨
7. confirm 없이 DB가 변경되지 않음
```

---

# 12. 브라우저 검증

```text
1. 활동 생성
2. 참가자 import
3. 활동비 탭 접속
4. 1인당 활동비 설정
5. 활동비 대상 생성/갱신
6. 요약 카드 확인
7. 거래내역 매칭 preview 확인
8. 확인 후 반영
9. 납부 현황 테이블 확인
10. 개별 수정 모달 확인
11. 환불 상태 변경 확인
12. 매칭 취소 확인
13. 다른 활동 또는 회비 데이터가 변경되지 않는지 확인
```

---

# 완료 기준

```text
1. 활동비 탭이 설정/요약/매칭/현황으로 명확히 분리된다.
2. 버튼이 과하게 노출되지 않고, 위험 작업은 모달 또는 더보기로 이동한다.
3. 활동비 요약이 현재 활동 기준으로 정확히 계산된다.
4. 거래내역 매칭 preview가 활동비 탭 안에서 동작한다.
5. 개별 납부 수정이 가능하다.
6. 환불 상태 관리가 가능하다.
7. 매칭 취소가 가능하다.
8. 모든 작업은 현재 activity_id의 activity_fee만 수정한다.
9. membership_fee는 수정되지 않는다.
10. pytest 통과
11. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 31 완료 보고

1. 원인
- 활동비 탭이 난잡했던 이유:
- 위험 작업이 과하게 노출된 이유:

2. 수정한 파일
- backend:
- frontend:
- tests:

3. UI 구조
- 설정:
- 요약:
- 매칭:
- 납부 현황:

4. 개별 작업
- 수정:
- 환불:
- 매칭 취소:

5. Scope 보호
- activity_id:
- payment_type:
- membership_fee 보호:

6. 검증
- 활동비 요약:
- 거래내역 매칭:
- 개별 수정:
- 환불:
- 매칭 취소:
- pytest:
- npm run build:

권장 커밋 메시지:
task31: simplify activity fee tab and scoped payment actions
```
