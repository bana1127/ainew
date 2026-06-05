# Task 43. 분기별 거래/예산 관리, 증빙 문서 확장, 수동 매칭 개선

현재 프로젝트는 ClubAgent입니다.

이번 Task 43의 목표는 다음 문제들을 한 번에 정리하는 것입니다.

```text
1. 거래내역과 예산 관리를 분기 기준으로 볼 수 있게 수정
2. 예산 관리에서 지출/수입 제외 처리를 가능하게 수정
3. 증빙 업로드 시 모든 파일을 영수증으로만 보지 않고 사업자등록증, 통장 사본, 계좌이체 증빙 등을 구분
4. 증빙 OCR/파싱 결과를 사람이 계속 수정 가능하게 개선
5. 활동 내부 증빙 업로드 버튼이 로딩만 뜨고 실제 업로드/연결이 안 되는 문제 수정
6. 거래내역 매칭에서 이름 확인 필요 상태라도 금액이 정확히 일치하면 사용자가 수동 매칭 확정 가능하게 수정
```

사용자가 업로드한 예시 이미지처럼, 활동 증빙에는 영수증뿐 아니라 사업자등록증, 통장 사본, 계좌이체 확인서, 사업자 계좌 증빙 같은 문서가 올라올 수 있습니다.
따라서 증빙 시스템은 “영수증 OCR” 중심에서 “증빙 문서 관리” 중심으로 확장되어야 합니다.

---

# 1. 거래내역 분기 기준 정리

현재 거래내역은 기간 필터는 있으나 동아리 운영 기준의 분기별 정리가 부족합니다.

이번 Task에서는 다음 분기 기준을 적용합니다.

```text
1분기: 12월, 1월, 2월
2분기: 3월, 4월, 5월
3분기: 6월, 7월, 8월
4분기: 9월, 10월, 11월
```

주의:

```text
12월은 다음 해 1분기에 포함됩니다.
예: 2025년 12월, 2026년 1월, 2026년 2월 → 2026년 1분기
```

## 1-1. 분기 계산 정책

함수 또는 service로 공통화하세요.

예:

```python
get_operating_quarter(date)
```

반환 예:

```text
2025-12-15 → 2026-Q1
2026-01-10 → 2026-Q1
2026-02-28 → 2026-Q1
2026-03-01 → 2026-Q2
2026-06-01 → 2026-Q3
2026-09-01 → 2026-Q4
```

## 1-2. 거래내역 화면 수정

거래내역 화면에 분기 필터를 추가하세요.

필터:

```text
운영연도
분기
전체 / 1분기 / 2분기 / 3분기 / 4분기
거래 유형
매칭 상태
납부 유형
검색
```

표시 예:

```text
2026년 1분기 거래내역
기간: 2025-12-01 ~ 2026-02-28
총 입금:
총 출금:
순증감:
거래 수:
```

## 1-3. 분기별 거래 요약

거래내역 화면 또는 예산 관리에서 분기별 요약을 볼 수 있어야 합니다.

요약 필드:

```text
분기
기간
총 입금
총 출금
순증감
미분류 거래 수
확인 필요 거래 수
증빙 누락 거래 수
제외된 거래 수
```

---

# 2. 예산 관리 분기별 관리

예산 관리 페이지도 분기별로 볼 수 있게 수정하세요.

## 2-1. 예산 관리 기간 필터

기존 기간 필터에 분기를 추가합니다.

```text
전체
이번 달
이번 분기
1분기
2분기
3분기
4분기
직접 선택
```

분기 기준은 위의 운영 분기 기준을 사용하세요.

## 2-2. 예산 관리 분기별 화면

예산 관리 페이지에서 다음을 분기별로 계산하세요.

```text
총 수입
총 지출
순증감
현재 잔액
회비 수입
활동비 수입
기타 수입
증빙 연결된 지출
증빙 누락 지출
제외된 수입
제외된 지출
확인 필요 거래
```

## 2-3. 증빙 추출

예산 관리에서 분기별 증빙 추출 기능을 추가하세요.

버튼 예:

```text
[분기 증빙 모아보기]
[분기 증빙 ZIP 생성]
[분기 정산 CSV 다운로드]
```

분기 증빙 추출 대상:

```text
해당 분기 거래내역
해당 분기 출금 거래
해당 분기 활동 지출
해당 분기 연결 영수증
사업자등록증
통장 사본
계좌이체 증빙
기타 증빙 파일
```

ZIP 구성 예:

```text
2026-Q2_증빙패키지.zip
- 거래내역.csv
- 예산요약.csv
- 지출증빙/
  - 2026-03-15_재료비_영수증.jpg
  - 2026-04-02_계좌이체확인서.pdf
  - 2026-04-02_사업자등록증.jpg
  - 2026-04-02_통장사본.pdf
- 활동별/
  - 위퍼퓸_교내조향활동/
    - 영수증.jpg
    - 사업자등록증.jpg
    - 통장사본.pdf
```

---

# 3. 예산 관리에서 수입/지출 제외 기능

현재 예산 관리에서 특정 거래를 지출 또는 수입 계산에서 제외하기 어렵습니다.

## 3-1. 제외 기능 추가

거래 검토/수동 분류 섹션에 다음 버튼을 추가하세요.

```text
[수입에서 제외]
[지출에서 제외]
[예산 집계에서 제외]
[제외 해제]
```

## 3-2. 제외 정책

거래별로 budget exclusion 상태를 저장하세요.

필드 예시:

```text
exclude_from_income
exclude_from_expense
exclude_from_budget
exclude_reason
excluded_at
excluded_by nullable
```

또는 별도 테이블:

```text
BudgetExclusion
- id
- transaction_id
- exclude_type: income / expense / budget
- reason
- created_at
```

## 3-3. 제외 적용 범위

예산 관리 계산에서 제외합니다.

```text
exclude_from_income = true
→ 총 수입 계산에서 제외

exclude_from_expense = true
→ 총 지출 계산에서 제외

exclude_from_budget = true
→ 예산 대비 실제 계산에서 제외
```

단, 거래내역 원본에서는 사라지면 안 됩니다.

거래내역 화면에서는 다음처럼 표시하세요.

```text
예산 제외
수입 제외
지출 제외
```

## 3-4. 제외 처리 UI

제외 시 확인 모달을 띄우세요.

필드:

```text
제외 유형
제외 사유
메모
```

예:

```text
이 거래를 지출 집계에서 제외하시겠습니까?
원본 거래내역은 유지되며, 예산 관리 집계에서만 제외됩니다.
```

모든 제외 처리는 되돌릴 수 있어야 합니다.

```text
[제외 해제]
```

---

# 4. 증빙 문서 타입 확장

현재 증빙 업로드 시 모든 파일을 영수증으로 보고 OCR 파싱하려는 문제가 있습니다.

활동 증빙에는 다음 문서가 올라올 수 있습니다.

```text
영수증
계좌이체 확인서
사업자등록증
통장 사본
견적서
거래명세서
청구서
기타 증빙
```

사용자가 올린 예시 이미지도 사업자등록증입니다.
이런 문서는 영수증처럼 가맹점/결제금액만 뽑는 구조로 처리하면 안 됩니다.

## 4-1. 증빙 문서 타입 추가

증빙 파일에 document_type을 추가하세요.

```text
receipt
business_registration
bankbook_copy
transfer_confirmation
invoice
quote
transaction_statement
other
unknown
```

한글 표시:

```text
receipt → 영수증
business_registration → 사업자등록증
bankbook_copy → 통장 사본
transfer_confirmation → 계좌이체 확인서
invoice → 청구서
quote → 견적서
transaction_statement → 거래명세서
other → 기타 증빙
unknown → 미분류
```

## 4-2. 업로드 시 타입 선택

증빙 업로드 UI에서 사용자가 타입을 선택할 수 있게 하세요.

옵션:

```text
자동 감지
영수증
사업자등록증
통장 사본
계좌이체 확인서
청구서
견적서
거래명세서
기타 증빙
```

기본값은 자동 감지입니다.

## 4-3. 자동 감지

OCR 또는 파일명/텍스트 기반으로 문서 타입을 추정하세요.

감지 키워드 예:

사업자등록증:

```text
사업자등록증
사업자등록번호
대표자
개업연월일
사업장소재지
업태
종목
세무서
국세청
```

통장 사본:

```text
예금주
계좌번호
은행
통장
입출금
계좌
```

계좌이체 확인서:

```text
이체확인
송금
입금계좌
출금계좌
받는분
보낸분
이체금액
거래일시
```

영수증:

```text
승인번호
카드
합계
공급가액
부가세
결제금액
영수증
```

자동 감지 결과는 확정값이 아니라 제안값입니다.
사용자가 나중에 수정할 수 있어야 합니다.

---

# 5. 증빙 파싱 필드 확장

문서 타입별로 파싱 필드를 다르게 관리하세요.

## 5-1. 공통 필드

모든 증빙 공통:

```text
document_type
title
issue_date
amount nullable
vendor_name nullable
memo
activity_report_id nullable
transaction_id nullable
file_id
confidence
raw_text
```

## 5-2. 영수증 필드

```text
vendor_name
payment_date
amount
approval_number
card_number_masked
tax_amount
supply_amount
```

## 5-3. 사업자등록증 필드

```text
business_registration_number
business_name
representative_name
business_address
business_type
business_item
opening_date
tax_office
```

## 5-4. 통장 사본 필드

```text
bank_name
account_holder
account_number_masked
account_type
```

## 5-5. 계좌이체 확인서 필드

```text
transfer_date
sender_name
receiver_name
sender_account_masked
receiver_account_masked
bank_name
transfer_amount
transaction_memo
```

필드 구조를 JSON으로 저장해도 됩니다.

예:

```text
parsed_data JSON
manual_overrides JSON
```

권장:

```text
parsed_data = OCR/AI가 추출한 원본
manual_data = 사용자가 수정한 최종값
```

화면에서는 manual_data가 있으면 manual_data를 우선 표시하세요.

---

# 6. 증빙 파싱 후에도 직접 수정 가능

현재 증빙 파싱 후 결과를 사람이 계속 수정하기 어려운 문제가 있습니다.

## 6-1. 증빙 상세/수정 화면 추가

증빙 목록에서 각 증빙을 클릭하면 상세/수정 모달을 열어야 합니다.

수정 가능 항목:

```text
문서 유형
제목
거래일/발급일
금액
업체명/상호
대표자
사업자등록번호
계좌번호
은행명
메모
연결 활동
연결 거래
```

문서 타입에 따라 필드를 다르게 표시하세요.

## 6-2. 수정 이력

가능하면 수정 이력을 남기세요.

```text
수정 전
수정 후
수정 시각
수정자 nullable
```

최소한 updated_at은 갱신하세요.

## 6-3. 수동 추가

파일 없이 수동 증빙도 추가할 수 있으면 좋습니다.

버튼:

```text
[수동 증빙 추가]
```

필드:

```text
문서 유형
제목
금액
거래일
업체명
메모
연결 활동
연결 거래
```

이 기능은 파일이 없는 경우에도 증빙 메타데이터를 남기는 용도입니다.

---

# 7. 활동 내부 증빙 업로드 버그 수정

현재 활동 상세 > 증빙 탭에서 “영수증 분석 업로드” 버튼을 눌러 파일을 업로드하면 로딩만 뜨고 실제 업로드가 안 되는 문제가 있습니다.

증상:

```text
1. 버튼 클릭 후 업로드
2. 로딩 표시만 뜸
3. 활동 증빙 목록에 추가되지 않음
4. 기존 영수증 연결 목록에도 안 보임
5. 파일함에도 안 보일 수 있음
```

## 7-1. 수정 목표

활동 내부에서 증빙 파일을 업로드하면 다음이 반드시 되어야 합니다.

```text
1. UploadedFile 생성
2. Evidence/Receipt record 생성 또는 업데이트
3. activity_report_id 연결
4. file_category = receipt 또는 evidence
5. file_role = evidence
6. 문서 타입 자동 감지 또는 사용자가 선택한 document_type 저장
7. 분석 결과가 있으면 parsed_data 저장
8. 활동 상세 증빙 탭 refetch
9. 활동 파일함 refetch
10. 전역 영수증/증빙 목록에도 표시
```

## 7-2. 버튼명 수정

기존 버튼명이 “영수증 분석 업로드”라면 너무 좁습니다.

수정 권장:

```text
증빙 분석 업로드
```

또는

```text
증빙 파일 업로드
```

문서 타입 선택:

```text
자동 감지
영수증
사업자등록증
통장 사본
계좌이체 확인서
기타 증빙
```

## 7-3. 오류 처리

업로드 실패 시 로딩만 남으면 안 됩니다.

반드시 오류 메시지를 표시하세요.

예:

```text
업로드에 실패했습니다. 서버 로그를 확인해주세요.
```

프론트에서 finally로 loading false 처리하세요.

---

# 8. 전역 증빙/영수증 화면 개선

기존 Receipts 화면이 있다면 이름은 유지하더라도 내부적으로는 다양한 증빙 타입을 다룰 수 있어야 합니다.

표시 컬럼:

```text
문서 유형
제목
업체명/상호
금액
거래일/발급일
연결 활동
연결 거래
파일
상태
작업
```

필터:

```text
전체
영수증
사업자등록증
통장 사본
계좌이체 확인서
청구서
견적서
기타
미분류
```

작업:

```text
상세/수정
활동에 연결
거래에 연결
다운로드
삭제 또는 보관
```

---

# 9. 거래내역 수동 매칭 개선

현재 거래내역 매칭에서 “이름 확인 필요” 상태가 발생했을 때, 학번으로 보내지거나 후보 매칭이 꼬여서 매칭이 안 되는 문제가 있습니다.

사용자는 이런 경우 수동으로 매칭을 확정하고 싶습니다.

현재 문제:

```text
1. 거래내역 이름과 부원 이름이 애매하면 확인 필요로 뜸
2. 수동으로 정확한 부원/PaymentRecord를 선택하고 싶음
3. 하지만 현재는 매칭이 아니라 단순 수동 납부 처리만 가능하거나
4. 학번 기준으로 잘못 보내져 매칭 확정이 실패함
```

## 9-1. 수동 거래 매칭 기능 추가

거래내역에서 확인 필요 상태일 때 다음이 가능해야 합니다.

```text
1. 거래 선택
2. 납부 유형 선택: 회비 / 활동비
3. 대상 선택:
   - 회비: 부원 또는 membership_fee PaymentRecord
   - 활동비: 활동 + 참가자 또는 activity_fee PaymentRecord
4. 금액 일치 확인
5. 수동 매칭 확정
```

## 9-2. 금액 일치 조건

수동 매칭은 금액이 정확히 일치할 때 허용합니다.

```text
transaction.deposit_amount == payment_record.required_amount - payment_record.paid_amount
```

또는 기존 정책에 따라:

```text
transaction.deposit_amount == payment_record.required_amount
```

프로젝트 현재 납부금 계산 정책과 맞춰 적용하세요.

중요:

```text
금액이 일치하면 이름/학번 매칭 confidence가 낮아도 사용자가 수동 확정 가능해야 합니다.
```

## 9-3. 금액 불일치 시

금액이 불일치하면 기본적으로 막으세요.

예:

```text
거래 금액 10,000원과 필요 금액 15,000원이 일치하지 않습니다.
수동 매칭할 수 없습니다.
부분 납부 처리 또는 수동 납부 처리 기능을 사용하세요.
```

부분 납부를 허용할 경우 명확히 별도 액션으로 분리하세요.

```text
[부분 납부로 처리]
```

## 9-4. 수동 매칭과 수동 납부 처리 분리

두 기능을 명확히 구분하세요.

수동 매칭:

```text
실제 거래내역과 PaymentRecord를 연결
matched_transaction_id 설정
payment_source = transaction_match 또는 manual_match
paid_amount 갱신
status 재계산
거래 match_status = matched
```

수동 납부 처리:

```text
거래내역 없이 paid_amount/status만 변경
matched_transaction_id 없음
payment_source = manual
```

현재 사용자가 원하는 것은 “금액이 일치하는 거래를 수동으로 매칭 확정”하는 기능입니다.

## 9-5. 수동 매칭 UI

거래내역 화면 또는 매칭 preview에서 버튼 추가:

```text
[수동 매칭]
```

모달 필드:

```text
거래 정보
납부 유형
활동 선택 nullable
대상자 검색
PaymentRecord 후보
금액 비교
확정 버튼
```

표시 예:

```text
거래 금액: 10,000원
대상 필요 금액: 10,000원
차이: 0원
수동 매칭 가능
```

확정 후:

```text
1. Transaction match_status = matched
2. PaymentRecord paid_amount 갱신
3. PaymentRecord matched_transaction_id 설정
4. status = paid 또는 partial/overpaid 재계산
5. 관련 화면 refetch
```

## 9-6. 활동비 수동 매칭

활동비의 경우 반드시 특정 활동의 activity_fee record와 연결되어야 합니다.

```text
activity_fee → /activities/{activity_id}?tab=activity-fee
```

활동비 수동 매칭 시 선택 흐름:

```text
활동 선택
→ 참가자 선택
→ 해당 activity_fee PaymentRecord 선택
→ 금액 확인
→ 수동 매칭 확정
```

## 9-7. 회비 수동 매칭

회비 수동 매칭 시 선택 흐름:

```text
부원 선택
→ 해당 period membership_fee PaymentRecord 선택
→ 금액 확인
→ 수동 매칭 확정
```

---

# 10. Quarter/Budget/Evidence/Matching 통합 연결성

이번 Task에서 다음 연결성을 확인하세요.

```text
거래내역 분기 필터
→ 예산 관리 분기 요약
→ 분기 증빙 추출
→ 제외 거래 반영
→ 증빙 문서 연결
→ 수동 매칭 결과 반영
```

예:

```text
1. 2026년 2분기 거래내역 조회
2. 특정 출금 거래를 지출 제외 처리
3. 예산 관리 2분기 총 지출에서 제외됨
4. 사업자등록증과 통장 사본을 해당 거래 증빙으로 연결
5. 2분기 증빙 ZIP에 포함됨
```

---

# 11. Backend 수정 대상

```text
backend/app/routers/transactions.py
backend/app/routers/budget.py
backend/app/routers/receipts.py
backend/app/routers/activities.py
backend/app/routers/payment_matching.py

backend/app/services/quarter_service.py
backend/app/services/budget_service.py
backend/app/services/budget_export_service.py
backend/app/services/evidence_service.py
backend/app/services/evidence_parser_service.py
backend/app/services/receipt_parser_service.py
backend/app/services/payment_matching_service.py
backend/app/services/manual_transaction_match_service.py
backend/app/services/file_storage_service.py

backend/app/models/transaction.py
backend/app/models/receipt.py
backend/app/models/uploaded_file.py
backend/app/models/payment.py
backend/app/schemas/transaction.py
backend/app/schemas/receipt.py
backend/app/schemas/evidence.py
backend/app/schemas/payment.py
```

필요하면 신규 모델/테이블:

```text
EvidenceDocument
BudgetExclusion
EvidenceEditLog
ManualTransactionMatchLog
```

---

# 12. Frontend 수정 대상

```text
frontend/app/transactions/page.tsx
frontend/app/budget/page.tsx
frontend/app/receipts/page.tsx
frontend/app/activities/[id]/page.tsx

frontend/components/evidence/*
frontend/components/transactions/*
frontend/components/budget/*
frontend/components/payments/*
frontend/lib/api.ts
```

필요하면 신규 컴포넌트:

```text
QuarterFilter.tsx
BudgetExclusionModal.tsx
EvidenceUploadPanel.tsx
EvidenceDetailEditModal.tsx
EvidenceTypeSelect.tsx
ManualTransactionMatchModal.tsx
QuarterEvidenceExportPanel.tsx
```

---

# 13. 테스트

추가 또는 보강:

```text
backend/tests/test_operating_quarter_service.py
backend/tests/test_budget_quarter_summary.py
backend/tests/test_budget_exclusion.py
backend/tests/test_evidence_document_types.py
backend/tests/test_evidence_manual_edit.py
backend/tests/test_activity_evidence_upload.py
backend/tests/test_manual_transaction_match.py
backend/tests/test_quarter_evidence_export.py
```

필수 테스트:

```text
1. 12월/1월/2월이 다음 해 1분기로 계산됨
2. 3/4/5월은 2분기, 6/7/8월은 3분기, 9/10/11월은 4분기로 계산됨
3. 예산 관리 분기 요약이 해당 분기 거래만 반영
4. 수입 제외 거래는 총 수입에서 제외
5. 지출 제외 거래는 총 지출에서 제외
6. 제외된 거래는 원본 거래내역에서는 유지
7. 사업자등록증 이미지가 receipt가 아니라 business_registration으로 분류 가능
8. 통장 사본/계좌이체 확인서 타입 저장 가능
9. 증빙 parsed_data와 manual_data가 분리되어 저장됨
10. 증빙 수정 후 manual_data가 화면에 우선 표시됨
11. 활동 내부 증빙 업로드 시 activity_report_id가 연결됨
12. 활동 내부 증빙 업로드 후 증빙 탭/파일함/전역 증빙 목록에 표시됨
13. 이름 확인 필요 거래도 금액이 정확히 일치하면 수동 매칭 가능
14. 수동 매칭은 matched_transaction_id를 설정함
15. 수동 납부 처리는 matched_transaction_id 없이 처리됨
16. 금액 불일치 수동 매칭은 기본 차단
17. activity_fee 수동 매칭은 특정 activity_id의 PaymentRecord에만 연결됨
18. membership_fee 수동 매칭은 해당 period의 PaymentRecord에 연결됨
```

---

# 14. 브라우저 검증

```text
1. 거래내역 페이지에서 2026년 2분기 필터 적용
2. 3/4/5월 거래만 보이는지 확인
3. 예산 관리에서 2분기 요약 확인
4. 특정 지출 거래를 지출 제외 처리
5. 예산 총 지출에서 제외되는지 확인
6. 제외 해제 후 다시 반영되는지 확인
7. 활동 상세 > 증빙 탭에서 사업자등록증 이미지 업로드
8. 영수증이 아니라 사업자등록증 타입으로 저장/수정 가능한지 확인
9. 업로드 후 활동 증빙 탭, 파일함, 전역 증빙 목록에 모두 보이는지 확인
10. 증빙 상세에서 사업자등록번호/상호/대표자 등 수동 수정
11. 수정 후 새로고침해도 유지되는지 확인
12. 이름 확인 필요 거래에서 수동 매칭 클릭
13. 회비 또는 활동비 PaymentRecord 선택
14. 금액 일치 시 수동 매칭 확정
15. 거래내역이 매칭됨으로 바뀌고 PaymentRecord가 paid로 반영되는지 확인
16. 금액 불일치 거래는 수동 매칭이 차단되는지 확인
17. 분기 증빙 ZIP 또는 CSV 추출이 동작하는지 확인
```

---

# 15. 완료 기준

```text
1. 거래내역과 예산 관리에서 운영 분기 기준 필터가 동작한다.
2. 12/1/2월이 다음 해 1분기로 계산된다.
3. 예산 관리에서 수입/지출/예산 제외 처리가 가능하고 되돌릴 수 있다.
4. 증빙 문서 타입이 영수증 외에도 사업자등록증, 통장 사본, 계좌이체 확인서 등을 지원한다.
5. 증빙 OCR/파싱 결과를 사람이 계속 수정할 수 있다.
6. 활동 내부 증빙 업로드가 로딩만 뜨고 실패하지 않는다.
7. 활동 내부 업로드 증빙이 활동 증빙 탭, 파일함, 전역 증빙 목록에 표시된다.
8. 이름 확인 필요 거래도 금액이 정확히 일치하면 사용자가 수동 매칭 확정할 수 있다.
9. 수동 매칭과 수동 납부 처리가 명확히 분리된다.
10. pytest 통과
11. npm run build 통과
```

---

# 16. 완료 보고 형식

```text
Task 43 완료 보고

1. 원인
- 거래내역/예산 관리에 분기 기준이 필요했던 이유:
- 증빙을 영수증으로만 처리하면 안 되는 이유:
- 활동 내부 증빙 업로드가 실패하던 이유:
- 이름 확인 필요 거래의 수동 매칭이 필요했던 이유:

2. 수정 파일
- backend:
- frontend:
- migration:
- tests:

3. 분기 관리
- 운영 분기 계산:
- 거래내역 분기 필터:
- 예산 관리 분기 요약:

4. 예산 제외 처리
- 수입 제외:
- 지출 제외:
- 예산 제외:
- 제외 해제:

5. 증빙 문서 확장
- document_type:
- 사업자등록증:
- 통장 사본:
- 계좌이체 확인서:
- 기타 증빙:

6. 증빙 수정
- parsed_data:
- manual_data:
- 상세/수정 모달:
- 수동 증빙 추가:

7. 활동 내부 증빙 업로드
- 업로드 flow:
- activity_report_id 연결:
- 파일함 반영:
- 전역 증빙 목록 반영:

8. 수동 거래 매칭
- manual transaction match:
- amount exact match:
- membership_fee:
- activity_fee:
- manual paid와 분리:

9. 검증
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task43: add quarterly finance views evidence document types and manual transaction matching
```
