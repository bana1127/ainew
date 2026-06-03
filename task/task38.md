# Task 38. Finance 예산 관리 페이지 구축

현재 프로젝트는 ClubAgent입니다.

이번 Task 38의 목표는 **FINANCE 영역에 동아리 전체 예산·수입·지출·정산 흐름을 관리하는 예산 관리 페이지를 추가**하는 것입니다.

현재 문제:

```text
1. Dashboard를 줄이거나 없애면 동아리 전체 재무 상태를 한눈에 볼 중심 화면이 없음
2. 회비, 활동비, 거래내역, 영수증, 증빙, 환불 정보가 각각 흩어져 있음
3. 자동 매칭은 있지만 사람이 전체 돈 흐름을 검토하고 수정할 수 있는 화면이 부족함
4. 활동별 정산 상태, 예산 대비 실제 사용액, 증빙 누락, 미분류 거래를 한 번에 확인하기 어려움
5. 활동비 미납은 활동 내부에서 처리해야 하는데, 전체 재무 화면에서는 이를 활동별로 연결해서 보여줄 필요가 있음
```

---

# 핵심 목표

`FINANCE` 아래에 새 메뉴를 추가합니다.

```text
FINANCE
- 예산 관리
- 회비
- 거래내역
- 영수증
```

예산 관리 페이지는 동아리 전체 돈 흐름을 보는 재무 허브입니다.

```text
예산 관리
- 전체 수입/지출 요약
- 예산 대비 실제
- 처리 필요 항목
- 활동별 정산 현황
- 거래 검토/수동 분류
- 보고서/내보내기
```

이번 Task에서는 오른쪽 아래 플로팅 챗봇은 구현하지 않습니다.
단, 다음 Task에서 챗봇이 사용할 수 있도록 summary API와 링크 구조는 깔끔하게 만들어주세요.

---

# 1. 사이드바 메뉴 추가

사이드바 `FINANCE` 영역에 `예산 관리` 메뉴를 추가하세요.

권장 순서:

```text
FINANCE
- 예산 관리
- 회비
- 거래내역
- 영수증
```

라우트:

```text
/frontend/app/budget/page.tsx
또는
/frontend/app/finance/budget/page.tsx
```

프로젝트 기존 라우팅 규칙에 맞춰 선택하세요.

---

# 2. 예산 관리 페이지 구성

페이지 구조는 다음 순서로 구성합니다.

```text
1. 기간 필터
2. 재무 요약 카드
3. 수입·지출 흐름
4. 예산 대비 실제
5. 처리 필요 항목
6. 활동별 정산 현황
7. 거래 검토/수동 분류
8. 보고서/내보내기
```

---

# 3. 기간 필터

상단에 기간 필터를 둡니다.

필터 옵션:

```text
이번 학기
이번 달
최근 3개월
전체
직접 선택
```

필터 값은 다음 데이터 집계에 적용됩니다.

```text
거래내역
회비 납부 현황
활동비 납부 현황
영수증/증빙
활동별 정산
예산 대비 실제
```

---

# 4. 재무 요약 카드

상단 요약 카드는 너무 많지 않게 6~8개 정도로 구성합니다.

필수 카드:

```text
현재 잔액
총 수입
총 지출
순증감
받을 돈
환불 예정
확인 필요 거래
증빙 누락
```

계산 기준:

```text
현재 잔액
→ Transactions 최신 balance 또는 거래내역 기준 계산값

총 수입
→ 기간 내 입금 합계

총 지출
→ 기간 내 출금 합계

순증감
→ 총 수입 - 총 지출

받을 돈
→ membership_fee 미납 + activity_fee 미납

환불 예정
→ refund_needed / refund_pending 금액

확인 필요 거래
→ unmatched / needs_review / amount_mismatch 거래

증빙 누락
→ 출금 또는 활동 지출 중 receipt/evidence 미연결 건
```

주의:

```text
회비 미납은 회비 화면으로 연결
활동비 미납은 해당 활동 상세 > 활동비 탭으로 연결
```

---

# 5. 수입·지출 흐름

월별 수입/지출 흐름을 표시하세요.

1차 구현은 그래프가 어려우면 표로 시작해도 됩니다.

표시 항목:

```text
월
수입
지출
순증감
누적 잔액
주요 메모
```

가능하면 간단한 bar 또는 line chart를 사용하세요.
복잡한 차트 라이브러리를 새로 넣기보다 기존 UI 기준으로 구현하세요.

---

# 6. 예산 대비 실제

예산 항목별 계획 금액과 실제 금액을 비교하는 섹션을 만듭니다.

컬럼:

```text
항목
구분
예산 금액
실제 금액
차이
집행률
상태
작업
```

구분:

```text
income
expense
```

기본 예산 항목 예시:

```text
수입
- 회비
- 활동비
- 학교 지원금
- 기타 수입

지출
- 재료비
- 대관비
- 식비
- 홍보비
- 비품비
- 환불
- 기타 지출
```

상태 예시:

```text
정상
예산 초과
미달
확인 필요
```

사용자가 직접 할 수 있어야 하는 작업:

```text
예산 항목 추가
예산 항목 수정
예산 금액 수정
항목 비활성화
메모 추가
```

---

# 7. 예산 모델

필요하면 신규 모델을 추가하세요.

권장 모델:

```text
BudgetCategory
- id
- name
- type: income / expense
- parent_id nullable
- sort_order
- is_active
- created_at
- updated_at

BudgetPlan
- id
- period
- category_id
- planned_amount
- note
- created_at
- updated_at
```

거래내역 분류까지 저장하려면 다음도 고려하세요.

```text
TransactionBudgetLink
- id
- transaction_id
- budget_category_id
- amount
- note
- created_at
```

이미 비슷한 모델이 있으면 새로 만들지 말고 기존 구조를 확장하세요.

---

# 8. 처리 필요 항목

예산 관리 페이지에는 재무 담당자가 바로 처리해야 할 항목을 모아 보여주세요.

항목:

```text
회비 미납
활동비 미납
확인 필요 거래
미분류 거래
금액 불일치 거래
증빙 없는 지출
환불 필요
예산 초과 항목
```

각 항목은 관련 화면으로 이동해야 합니다.

링크 정책:

```text
회비 미납
→ /payments

활동비 미납
→ /activities/{activity_id}?tab=activity-fee

증빙 누락
→ /activities/{activity_id}?tab=evidence

미분류 거래
→ /transactions

예산 초과
→ 현재 예산 관리 페이지의 예산 항목 섹션
```

활동비는 절대 Payments로 보내지 마세요.

---

# 9. 활동별 정산 현황

활동별로 수입/지출/증빙/보고서 상태를 한눈에 보여주세요.

컬럼:

```text
활동명
활동일
참가자 수
활동비 예정 수입
활동비 실제 수입
지출
차액
증빙 상태
보고서 상태
작업
```

계산 기준:

```text
활동비 예정 수입
→ 해당 활동 activity_fee required_amount 합계

활동비 실제 수입
→ 해당 활동 activity_fee paid_amount 합계

지출
→ 해당 활동에 연결된 receipt 또는 expense transaction 합계

차액
→ 실제 수입 - 지출

증빙 상태
→ 증빙 있음 / 증빙 부족 / 확인 필요

보고서 상태
→ 보고서 있음 / HWPX 생성됨 / 미작성
```

작업 링크:

```text
활동 상세
활동비 탭
증빙 탭
파일함
감사자료 패키지
```

---

# 10. 거래 검토/수동 분류

예산 관리 페이지 하단에 문제 있는 거래를 모아 보여주세요.

대상:

```text
미분류 거래
미매칭 거래
금액 불일치 거래
동명이인 후보 거래
증빙 미연결 지출
```

사용자가 할 수 있어야 하는 작업:

```text
거래 분류 변경
예산 항목 연결
회비로 연결
특정 활동의 활동비로 연결
특정 활동 지출로 연결
영수증 연결
매칭 취소
검토 완료 처리
메모 추가
```

위험 작업은 바로 반영하지 말고 preview/confirm 또는 확인 모달을 사용하세요.

```text
선택
→ 변경 예정 preview
→ 확인 후 반영
→ 목록 refetch
```

---

# 11. 보고서/내보내기

예산 관리 페이지에서 간단한 내보내기를 제공합니다.

1차 구현 범위:

```text
예산 대비 실제 CSV 다운로드
활동별 정산 CSV 다운로드
미납자 목록 CSV 다운로드
확인 필요 거래 CSV 다운로드
```

추후 감사자료 패키지와 연결할 수 있게 API 구조를 열어두세요.

---

# 12. Backend API

권장 API:

```http
GET /api/budget/summary
GET /api/budget/cashflow
GET /api/budget/categories
POST /api/budget/categories
PATCH /api/budget/categories/{id}

GET /api/budget/plans
POST /api/budget/plans
PATCH /api/budget/plans/{id}

GET /api/budget/activity-settlements
GET /api/budget/review-items
POST /api/budget/review-items/{id}/resolve

POST /api/budget/transactions/{transaction_id}/classify-preview
POST /api/budget/transactions/{transaction_id}/classify-confirm
```

기존 router 구조에 맞게 `/api/finance/budget` 등으로 조정해도 됩니다.

---

# 13. Frontend 수정 대상

```text
frontend/app/budget/page.tsx
frontend/app/layout/sidebar 관련 파일
frontend/lib/api.ts
frontend/components/*
```

가능하면 컴포넌트 분리:

```text
BudgetSummaryCards
BudgetCashflowSection
BudgetVsActualTable
BudgetTodoList
ActivitySettlementTable
TransactionReviewTable
BudgetExportPanel
```

---

# 14. Backend 수정 대상

```text
backend/app/routers/budget.py
backend/app/main.py
backend/app/models/*
backend/app/schemas/*
backend/app/services/budget_service.py
backend/app/services/budget_review_service.py
backend/app/services/file_storage_service.py
backend/alembic/versions/*
```

---

# 15. AI/챗봇 연동 준비

이번 Task에서는 플로팅 챗봇을 구현하지 않습니다.

다만 다음 Task에서 챗봇이 예산 관리 정보를 쉽게 조회할 수 있도록 다음 API는 응답 구조를 명확히 유지하세요.

```text
GET /api/budget/summary
GET /api/budget/activity-settlements
GET /api/budget/review-items
```

챗봇이 나중에 답할 질문 예시:

```text
이번 학기 총 수입 얼마야?
활동 몇 개 했어?
활동비 미납 있는 활동 뭐야?
시향 활동에 몇 명 참여했어?
증빙 빠진 활동 있어?
```

따라서 API 응답에는 관련 페이지로 이동 가능한 URL도 포함하면 좋습니다.

---

# 16. 테스트

추가 또는 보강:

```text
backend/tests/test_budget_summary.py
backend/tests/test_budget_cashflow.py
backend/tests/test_budget_vs_actual.py
backend/tests/test_activity_settlement_summary.py
backend/tests/test_budget_review_items.py
```

필수 테스트:

```text
1. 기간 내 총 수입/지출/순증감이 계산됨
2. membership_fee 미납은 받을 돈에 포함됨
3. activity_fee 미납은 받을 돈에 포함됨
4. activity_fee 미납 target_url은 활동 상세 활동비 탭
5. 회비 미납 target_url은 /payments
6. 예산 항목별 planned_amount와 actual_amount가 비교됨
7. 활동별 정산에서 activity_fee 수입과 receipt 지출이 계산됨
8. 미분류 거래가 review item으로 반환됨
9. 증빙 없는 지출이 review item으로 반환됨
10. 거래 수동 분류 preview는 confirm 전 DB를 수정하지 않음
```

---

# 17. 브라우저 검증

```text
1. FINANCE > 예산 관리 메뉴 확인
2. 예산 관리 페이지 접속
3. 재무 요약 카드 확인
4. 기간 필터 변경 확인
5. 수입·지출 흐름 확인
6. 예산 대비 실제 표 확인
7. 예산 항목 추가/수정 확인
8. 처리 필요 항목 클릭 시 올바른 페이지로 이동 확인
9. 활동비 미납은 활동 상세 > 활동비 탭으로 이동 확인
10. 활동별 정산 현황 확인
11. 거래 검토에서 수동 분류 preview 확인
12. CSV 내보내기 확인
13. 모바일/좁은 화면에서도 심하게 깨지지 않는지 확인
```

---

# 완료 기준

```text
1. FINANCE 아래 예산 관리 페이지가 추가된다.
2. 전체 수입/지출/잔액/받을 돈/환불/확인 필요 항목을 볼 수 있다.
3. 예산 대비 실제 표를 볼 수 있고 예산 항목을 수정할 수 있다.
4. 활동별 정산 현황을 볼 수 있다.
5. 처리 필요 항목에서 회비/활동비/증빙/거래 문제로 이동할 수 있다.
6. 활동비 미납은 활동 상세 활동비 탭으로 이동한다.
7. 거래 검토/수동 분류 preview가 가능하다.
8. CSV 내보내기가 가능하다.
9. 다음 Task의 챗봇이 재사용할 summary API가 준비된다.
10. pytest 통과
11. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 38 완료 보고

1. 원인
- 전체 예산 관리 페이지가 필요했던 이유:
- Dashboard만으로 부족했던 이유:

2. 수정 파일
- backend:
- frontend:
- migration:
- tests:

3. 예산 관리 화면
- 요약 카드:
- 수입·지출 흐름:
- 예산 대비 실제:
- 처리 필요 항목:
- 활동별 정산:
- 거래 검토:
- 내보내기:

4. 모델/API
- BudgetCategory:
- BudgetPlan:
- summary:
- cashflow:
- activity settlements:
- review items:

5. 수동 수정
- 예산 항목 수정:
- 거래 분류:
- preview/confirm:

6. 링크 정책
- 회비 미납:
- 활동비 미납:
- 증빙 누락:

7. 챗봇 연동 준비
- summary API:
- target_url:
- structured response:

8. 검증
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task38: add finance budget management page
```
