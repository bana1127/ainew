# Task 29. 회비 / 활동비 화면 구조 분리

현재 프로젝트는 ClubAgent입니다.

Task 28에서 AI 자연어 명령 라우팅을 회비/활동비/거래내역 기준으로 분리했습니다.
이번 Task 29의 목표는 **화면과 사용자 흐름도 같은 기준으로 분리하는 것**입니다.

현재 문제는 다음과 같습니다.

```text
1. Payments 화면에서 회비와 활동비가 섞여 보임
2. 활동비 매칭을 Payments에서 처리하려고 해서 사용 흐름이 어색함
3. 활동비는 특정 활동의 참가자와 연결되어야 하는데 전역 화면에서 처리되어 혼란스러움
4. 활동 내부 활동비 탭은 너무 많은 기능이 한 번에 보여 난잡함
5. 거래내역은 공통 원장이지만 회비/활동비 매칭 화면과 섞여 있음
```

---

# 핵심 정책

앞으로 화면 역할은 다음처럼 분리합니다.

```text
Payments / 회비
- 학기별 부원 회비 관리 전용
- 신규 15,000원 / 기존 10,000원 / 임원 0원
- member_id + period + payment_type=membership_fee 기준

Activities > 특정 활동 > 활동비
- 해당 활동의 활동비 관리 전용
- activity_report_id + member_id + payment_type=activity_fee 기준
- 활동 참가자 기준으로만 납부 대상 생성/매칭/수정

Transactions / 거래내역
- 전체 통장 거래내역 원장
- 업로드, 조회, 삭제, 배치 관리
- 회비/활동비 매칭은 각 도메인 화면에서 거래내역을 가져와 처리
```

---

# 구현 목표

## 1. Payments 화면을 회비 전용으로 정리

현재 `Payments`는 회비 화면으로 역할을 명확히 합니다.

변경 방향:

```text
기존: Payments
변경 표시명: 회비 또는 회비 관리
```

사이드바도 가능하면 다음처럼 바꿉니다.

```text
FINANCE
- 회비
- 거래내역
- 영수증
```

Payments 화면에서 활동비 관련 UI는 제거하거나 숨깁니다.

제거/이동 대상:

```text
1. 활동비 탭
2. 전체 활동비 납부 현황
3. 활동 선택 dropdown
4. 활동비 납부 대상 생성
5. 활동비 매칭
```

Payments 화면에 남길 것:

```text
1. 현재 학기 선택
2. 회비 대상 생성/갱신
3. 회비 납부 현황
4. 회비 거래내역 매칭
5. 회비 미납자 확인
6. 신규/기존/임원 구분
7. 회비 수동 수정
```

---

## 2. 활동비는 활동 상세 내부로 이동

활동비 관련 기능은 모두 특정 활동 상세 안에서 처리합니다.

위치:

```text
Activities > 특정 활동 상세 > 활동비 탭
```

활동비 탭에서 제공할 기능:

```text
1. 1인당 활동비 설정
2. 참가자 기준 활동비 대상 생성/갱신
3. 활동비 납부 현황
4. 이 활동 기준 거래내역 매칭
5. 개별 납부 상태 수정
6. 환불 필요 / 환불 완료
7. 매칭 취소
```

전역 Payments 화면에서 activity_fee record를 직접 생성/수정하지 마세요.

---

## 3. 거래내역은 공통 원장으로 유지

Transactions 화면은 전체 통장 내역만 관리합니다.

역할:

```text
1. 거래내역 업로드
2. 거래내역 목록 조회
3. 입금/출금 필터
4. 기간 필터
5. 업로드 배치 관리
6. 삭제/되돌리기
7. 거래 상세 보기
```

Transactions 화면에서 회비나 활동비를 직접 납부 완료 처리하지 않습니다.

단, 각 도메인 화면에서 거래내역을 가져와 매칭할 수 있어야 합니다.

```text
회비 화면 → 거래내역에서 회비 매칭
활동 상세 활동비 탭 → 거래내역에서 해당 활동비 매칭
```

---

# 활동비 탭 UI 정리

현재 활동비 탭이 너무 난잡하므로 아래 구조로 정리하세요.

## 섹션 1. 활동비 설정

```text
1인당 활동비
[금액 입력] [대상 생성/갱신]
```

설명:

```text
현재 활동 참가자를 대상으로 활동비 납부 대상을 생성합니다.
기존 납부 금액은 유지됩니다.
```

## 섹션 2. 활동비 요약

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

## 섹션 3. 거래내역 매칭

```text
[거래내역에서 이 활동 활동비 매칭]
```

매칭 조건:

```text
1. 현재 activity_id 기준
2. 현재 활동 참가자만 대상
3. payment_type=activity_fee만 대상
4. transaction.deposit_amount == payment_record.required_amount exact match
5. 이름/학번/전화번호 후보가 맞아야 함
6. 금액 불일치 시 확인 필요
7. 바로 반영하지 않고 preview 후 confirm
```

## 섹션 4. 납부 현황 테이블

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

작업 버튼은 너무 많이 노출하지 마세요.

권장:

```text
[수정]
[더보기]
```

더보기 안에 넣을 작업:

```text
환불 필요
환불 완료
납부 취소
매칭 취소
```

---

# API 구조

## 회비 전용 API

기존 API를 유지하되 payment_type이 membership_fee인 경우만 Payments 화면에서 사용하세요.

예:

```http
GET /api/payment-records?payment_type=membership_fee&period=2026-1
POST /api/payments/membership/generate-preview
POST /api/payments/membership/match-transactions-preview
```

## 활동비 전용 API

활동 상세에서 사용할 API를 명확히 하세요.

예:

```http
GET /api/activities/{activity_id}/activity-fees
POST /api/activities/{activity_id}/activity-fees/generate-preview
POST /api/activities/{activity_id}/activity-fees/match-transactions-preview
PATCH /api/activities/{activity_id}/activity-fees/{record_id}
```

기존 API가 있다면 위 역할을 만족하도록 정리하면 됩니다.

---

# AI 연동 규칙

AI 결과도 화면 구조와 맞아야 합니다.

```text
회비 관련 요청
→ Payments/회비 도메인
→ membership_fee만 처리

활동비 관련 요청
→ 활동 상세 내부면 현재 activity_id 기준 처리
→ 전역 AI면 활동 선택 요청

거래내역 매칭 요청
→ 회비 매칭인지 활동비 매칭인지 명확해야 실행
```

예:

```text
전체 회비 완납 처리해줘
→ membership_fee bulk preview

거래내역에서 회비 납부 확인해줘
→ membership_fee transaction matching preview

이 활동 거래내역으로 활동비 매칭해줘
→ 현재 activity_id의 activity_fee matching preview

활동비 매칭해줘
→ 전역 AI에서는 활동 선택 요청
```

---

# Frontend 수정 대상

확인 대상:

```text
frontend/app/payments/page.tsx
frontend/app/activities/[id]/page.tsx
frontend/app/transactions/page.tsx
frontend/lib/api.ts
frontend/components/assistant/AssistantResultCard.tsx
```

수정 내용:

```text
1. Payments 화면에서 활동비 탭 제거
2. Payments 화면 제목을 회비 관리로 명확화
3. 활동비 관련 UI는 Activities 상세 활동비 탭으로 이동
4. 활동비 탭 섹션 정리
5. 거래내역 매칭 버튼을 회비/활동비 각각의 위치에 배치
6. 결과 카드에 회비/활동비 도메인 표시
```

---

# Backend 수정 대상

확인 대상:

```text
backend/app/routers/payment_records.py
backend/app/routers/payment_matching.py
backend/app/routers/activities.py
backend/app/services/payment_matching_service.py
backend/app/services/activity_fee_generation_service.py
backend/app/services/membership_fee_generation_service.py
backend/app/agents/assistant_orchestrator.py
```

수정 내용:

```text
1. Payments 회비 화면에서 membership_fee만 조회되도록 보장
2. 활동 상세 activity_fee API에서 현재 activity_id만 처리
3. activity_fee 매칭 시 membership_fee record 접근 금지
4. membership_fee 매칭 시 activity_fee record 접근 금지
5. confirm 시에도 payment_type과 scope 재검증
```

---

# 테스트 추가

추가 또는 보강할 테스트:

```text
backend/tests/test_payment_screen_domain_separation.py
backend/tests/test_activity_fee_scoped_matching.py
backend/tests/test_membership_fee_screen_only.py
```

필수 테스트:

```text
1. Payments 회비 조회는 membership_fee만 반환
2. Payments 화면용 API가 activity_fee를 반환하면 실패
3. 활동 상세 activity_fee 조회는 해당 activity_id의 activity_fee만 반환
4. activity_fee 매칭이 membership_fee를 수정하면 실패
5. membership_fee 매칭이 activity_fee를 수정하면 실패
6. 전역 AI의 활동비 요청은 activity_id 없으면 clarification 반환
```

---

# 브라우저 검증

```text
1. Payments/회비 화면 접속
2. 활동비 관련 UI가 보이지 않는지 확인
3. 회비 대상 생성/회비 현황/회비 거래내역 매칭만 보이는지 확인
4. 특정 활동 상세 접속
5. 활동비 탭에서 활동비 설정/현황/거래내역 매칭이 보이는지 확인
6. 활동비 매칭이 현재 활동 참가자만 대상으로 하는지 확인
7. Transactions 화면은 원장 관리만 하는지 확인
8. AI 작업실에서 회비/활동비 요청이 각각 올바른 위치와 scope로 처리되는지 확인
```

---

# 완료 기준

```text
1. Payments 화면은 회비 중심으로 정리된다.
2. Payments 화면에서 활동비 관리 UI가 제거된다.
3. 활동비 생성/매칭/수정은 활동 상세 내부에서 처리된다.
4. Transactions는 거래내역 원장 역할만 한다.
5. 회비 매칭은 membership_fee만 수정한다.
6. 활동비 매칭은 현재 activity_id의 activity_fee만 수정한다.
7. AI 결과 카드에서 회비/활동비 도메인이 명확하다.
8. pytest 통과
9. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 29 완료 보고

1. 원인
- Payments에서 회비/활동비가 섞인 이유:
- 활동비 처리가 전역 화면에 있던 문제:

2. 수정한 파일
- backend:
- frontend:
- tests:

3. 화면 구조
- Payments/회비:
- Activities 활동비:
- Transactions:

4. API 분리
- membership_fee:
- activity_fee:
- transaction source:

5. 활동비 탭 정리
- 설정:
- 요약:
- 매칭:
- 납부 현황:

6. AI 연동
- 회비 요청:
- 활동비 요청:
- 거래내역 매칭 요청:

7. 검증
- Payments 화면:
- 활동 상세 활동비 탭:
- 거래내역 화면:
- pytest:
- npm run build:

권장 커밋 메시지:
task29: separate membership fees from activity fee workflows
```
