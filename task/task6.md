# Task 6. 부원 명부 기반 납부 매칭 및 미납자 판별 구현

## 목표

Task 5에서 저장된 은행 거래내역과 Task 2~4에서 관리 중인 부원 명부를 비교하여, 회비 또는 활동비 납부 여부를 자동으로 판별하는 기능을 구현한다.

이번 Task의 핵심 흐름은 다음이다.

```text
거래내역 입금 행 조회
→ 적요에서 이름 후보 추출
→ 부원 명부와 매칭
→ 금액 기준으로 회비/활동비/기타 분류
→ payment_records 생성/갱신
→ 납부자/미납자/확인필요자 출력
→ 자체 웹페이지에서 결과 확인 및 수동 보정
```

이번 Task가 완료되면 거래내역서를 업로드한 뒤 `/payments` 화면에서 다음을 확인할 수 있어야 한다.

```text
납부 완료자
미납자
부분 납부자
확인 필요 입금
제외된 입금
```

---

## 전제 조건

Task 1~5가 완료되어 있어야 한다.

Task 5 완료 기준:

* 거래내역서 업로드 가능
* `.xls`, `.xlsx`, `.csv` 파싱 가능
* `bank_transactions` 테이블에 거래내역 저장 가능
* `/transactions` 페이지에서 거래내역 확인 가능

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. 납부 매칭 서비스 구현
2. 적요에서 이름 후보 추출
3. 부원 명부와 이름 매칭
4. 입금액 기준 회비/활동비/기타 분류
5. 매칭 미리보기 API
6. 매칭 적용 API
7. 미납자 자동 생성
8. 확인 필요 거래 분류
9. 수동 매칭/확정 API
10. `/payments` 페이지 보강
11. README에 납부 매칭 사용 방법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* 거래내역서 파서 재구현
* OpenAI API 호출
* LLM 기반 이름 추론
* 영수증 OCR
* 활동 보고서 AI 생성
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant 또는 pgvector 연동
* 로그인/권한 시스템
* 복잡한 회계 감사 자동화
* 실제 알림 발송

필요한 위치에는 TODO 주석만 남긴다.

---

## 핵심 개념

### 1. bank_transactions

Task 5에서 저장된 은행 거래내역이다.

이번 Task에서는 다음 필드를 주로 사용한다.

```text
transaction_datetime
transaction_type
memo
withdraw_amount
deposit_amount
balance
matched_member_id
payment_type
match_status
```

### 2. members

부원 명부이다.

이번 Task에서는 `status = active`인 부원을 기본 납부 대상자로 본다.

### 3. payment_records

부원별 납부 상태를 저장한다.

이번 Task에서 자동 생성/갱신한다.

```text
member_id
period
payment_type
required_amount
paid_amount
status
transaction_id
```

---

## 납부 매칭 기준

### 기본 설정값

`app_settings`에서 다음 값을 읽어 사용한다.

```text
membership_fee_amount
default_payment_period
transaction_matching_threshold
```

기본 fallback 값:

```text
membership_fee_amount = 30000
default_payment_period = "2026-1"
transaction_matching_threshold = 0.8
```

추가로 필요하면 이번 Task에서 다음 설정을 추가할 수 있다.

```text
activity_fee_amounts
```

예시:

```json
{
  "amounts": [10000, 20000, 30000, 49000]
}
```

단, DB 스키마를 크게 바꾸지 말고 기존 app_settings 테이블을 활용한다.

---

## 입금 행 필터링

매칭 대상 거래는 기본적으로 다음 조건을 만족해야 한다.

```text
deposit_amount > 0
```

다음 거래는 납부 매칭 대상에서 제외한다.

```text
예금이자
이자
환불
네이버페이환불
결제취소
취소
캐시백
정산
```

제외 거래는 `match_status = "excluded"`로 표시할 수 있다.

제외 거래의 `payment_type` 예시:

```text
interest
refund
other
```

---

## 적요 전처리 규칙

거래내역의 `memo`는 은행/간편송금 앱에 따라 여러 형태가 섞일 수 있다.

예시:

```text
메모아 홍길동
토스 김가온
김가온 회비
카카오페이 이도윤
홍대 박서연
메모아이예은
최하준 3월 회비
네이버페이환불
예금이자
```

전처리 규칙:

1. 앞뒤 공백 제거
2. 괄호 안 긴 설명 제거
3. 특수문자 제거 또는 공백화
4. `토스`, `카카오페이`, `메모아`, `메모`, `입금`, `회비`, `활동비` 등 불필요 키워드 제거
5. 한글 이름 후보 추출
6. 부원명 완전일치 우선
7. 실패 시 유사도 매칭
8. 여러 명이 동시에 매칭되면 확인 필요 처리

---

## 이름 매칭 방식

### 1순위: 학번 매칭

memo에 member.student_id가 포함되어 있으면 해당 부원으로 매칭한다.

### 2순위: 이름 완전 포함 매칭

member.name이 memo에 그대로 포함되어 있으면 매칭한다.

예시:

```text
memo = "토스 김가온"
member.name = "김가온"
→ matched
```

### 3순위: 정규화 이름 매칭

공백 제거, 특수문자 제거 후 비교한다.

예시:

```text
memo = "메모아이예은"
member.name = "이예은"
→ matched
```

### 4순위: 유사도 매칭

완전 일치가 실패하면 Python 표준 라이브러리 `difflib.SequenceMatcher`를 사용하여 유사도 점수를 계산한다.

기준 점수는 `transaction_matching_threshold`를 사용한다.

기본값:

```text
0.8
```

주의:

* 외부 라이브러리 rapidfuzz는 이번 Task에서 필수 사용하지 않는다.
* 필요하면 도입할 수 있지만 의존성은 최소화한다.
* 유사도 기준을 넘는 후보가 여러 명이면 `need_check` 처리한다.

---

## match_status 정의

`bank_transactions.match_status`는 다음 값을 사용한다.

```text
unmatched
matched
need_check
excluded
```

의미:

```text
unmatched   → 아직 매칭되지 않음
matched     → 부원과 납부 유형이 확정됨
need_check  → 이름 또는 금액이 애매해서 수동 확인 필요
excluded    → 이자/환불 등 납부 대상이 아님
```

---

## payment_type 정의

`bank_transactions.payment_type`, `payment_records.payment_type`은 다음 값을 사용한다.

```text
membership_fee
activity_fee
refund
interest
other
```

금액 기준:

```text
membership_fee_amount와 같으면 membership_fee
activity_fee_amounts에 포함되면 activity_fee
제외 키워드가 있으면 refund 또는 interest
그 외 입금은 other 또는 need_check
```

처음에는 membership_fee 중심으로 구현하고, activity_fee는 확장 가능한 구조로 남긴다.

---

## payment_records.status 정의

```text
unpaid
paid
partial
need_check
exempt
```

판정 기준:

```text
paid       → paid_amount >= required_amount
partial    → 0 < paid_amount < required_amount
unpaid     → paid_amount == 0
need_check → 입금자 또는 금액이 애매함
exempt     → 납부 면제, 이번 Task에서는 수동 상태로만 사용
```

---

## Backend 구현 요구사항

### 1. 납부 매칭 서비스 구현

파일:

```text
backend/app/services/payment_matching_service.py
```

주요 함수 예시:

```python
def preview_payment_matching(
    db: Session,
    period: str,
    payment_type: str = "membership_fee",
    required_amount: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> PaymentMatchingPreview:
    ...

def apply_payment_matching(
    db: Session,
    period: str,
    payment_type: str = "membership_fee",
    required_amount: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> PaymentMatchingResult:
    ...
```

내부 함수는 작게 분리한다.

권장 함수:

```python
normalize_memo()
extract_name_candidates()
classify_transaction()
match_member_from_memo()
is_excluded_transaction()
calculate_match_score()
```

---

## 2. 매칭 결과 구조

Pydantic schema 또는 dataclass로 다음 구조를 사용한다.

```python
class TransactionMatchItem:
    transaction_id: UUID
    transaction_datetime: datetime | None
    memo: str | None
    deposit_amount: int
    matched_member_id: UUID | None
    matched_member_name: str | None
    payment_type: str | None
    match_status: str
    score: float | None
    reason: str | None

class PaymentMatchingPreview:
    period: str
    payment_type: str
    required_amount: int
    total_active_members: int
    total_deposit_transactions: int
    matched_count: int
    need_check_count: int
    excluded_count: int
    unpaid_count: int
    matched_items: list[TransactionMatchItem]
    need_check_items: list[TransactionMatchItem]
    excluded_items: list[TransactionMatchItem]
    unpaid_members: list[MemberSummary]

class PaymentMatchingResult(PaymentMatchingPreview):
    created_payment_records: int
    updated_payment_records: int
    updated_transactions: int
```

프로젝트 기존 schema 스타일에 맞춰도 된다.

---

## 3. Matching API 구현

파일:

```text
backend/app/routers/payment_matching.py
```

또는 기존 `payment_records.py` / `payments.py` 구조가 있다면 자연스럽게 병합한다.

### Preview API

```http
POST /api/payments/match-preview
```

요청 예시:

```json
{
  "period": "2026-1",
  "payment_type": "membership_fee",
  "required_amount": 30000,
  "start_date": "2026-03-01",
  "end_date": "2026-03-31"
}
```

응답:

```json
{
  "period": "2026-1",
  "payment_type": "membership_fee",
  "required_amount": 30000,
  "total_active_members": 5,
  "total_deposit_transactions": 4,
  "matched_count": 3,
  "need_check_count": 1,
  "excluded_count": 0,
  "unpaid_count": 2,
  "matched_items": [],
  "need_check_items": [],
  "excluded_items": [],
  "unpaid_members": []
}
```

주의:

* Preview는 DB의 `payment_records`를 변경하지 않는다.
* 단순히 결과만 반환한다.

---

### Apply API

```http
POST /api/payments/match-apply
```

기능:

1. 매칭 preview 수행
2. `bank_transactions`의 matched_member_id, payment_type, match_status 갱신
3. `payment_records` 생성 또는 갱신
4. 미납 부원에 대해서도 `status = unpaid` record 생성
5. 결과 반환

중요:

* 같은 `member_id + period + payment_type` 조합이 이미 있으면 새로 만들지 않고 갱신한다.
* 같은 transaction이 이미 연결된 payment_record가 있으면 중복 생성하지 않는다.
* 여러 번 실행해도 중복 payment_records가 생기면 안 된다.

---

### Manual Confirm API

```http
PATCH /api/payments/transactions/{transaction_id}/confirm
```

요청 예시:

```json
{
  "member_id": "member-id",
  "period": "2026-1",
  "payment_type": "membership_fee",
  "required_amount": 30000,
  "status": "paid"
}
```

기능:

* 특정 거래를 특정 부원과 수동 연결
* bank_transactions 업데이트
* payment_records 생성 또는 갱신

---

### Mark Excluded API

```http
PATCH /api/payments/transactions/{transaction_id}/exclude
```

요청 예시:

```json
{
  "payment_type": "refund",
  "reason": "환불 입금으로 납부 대상 제외"
}
```

기능:

* 특정 거래를 납부 매칭 대상에서 제외
* bank_transactions.match_status = "excluded"
* bank_transactions.payment_type 갱신

reason 저장 필드가 없으면 응답에만 포함하고, 추후 확장 TODO를 남긴다.

---

### Summary API

```http
GET /api/payments/summary?period=2026-1&payment_type=membership_fee
```

응답 예시:

```json
{
  "period": "2026-1",
  "payment_type": "membership_fee",
  "required_amount": 30000,
  "total_members": 5,
  "paid_count": 3,
  "partial_count": 0,
  "unpaid_count": 2,
  "need_check_count": 1,
  "total_required_amount": 150000,
  "total_paid_amount": 90000
}
```

---

### Unpaid API

```http
GET /api/payments/unpaid?period=2026-1&payment_type=membership_fee
```

응답:

```json
[
  {
    "member_id": "member-id",
    "name": "김가온",
    "student_id": "20260001",
    "required_amount": 30000,
    "paid_amount": 0,
    "status": "unpaid"
  }
]
```

---

## 4. 기존 Payment Records API 보강

기존 `GET /api/payment-records`가 있다면 다음 필터를 확인/보강한다.

```text
period
payment_type
status
member_id
```

목록 응답에서 가능하면 member 이름이 보이도록 한다.

복잡해지면 프론트에서 members 목록과 조합해도 된다.

---

## Frontend 구현 요구사항

### 1. Payments 페이지 보강

파일:

```text
frontend/app/payments/page.tsx
```

구현 기능:

1. 납부 기간 입력
2. 납부 유형 선택
3. 기준 금액 입력
4. 날짜 범위 필터
5. 매칭 미리보기 버튼
6. 매칭 적용 버튼
7. 납부 요약 카드
8. 매칭 성공 거래 테이블
9. 확인 필요 거래 테이블
10. 제외 거래 테이블
11. 미납자 테이블
12. 수동 매칭 UI
13. 제외 처리 UI
14. 기존 payment_records 목록 표시

---

## 2. 기본 입력 UI

필드:

```text
period
payment_type
required_amount
start_date
end_date
```

기본값:

```text
period = app_settings.default_payment_period 또는 "2026-1"
payment_type = "membership_fee"
required_amount = app_settings.membership_fee_amount 또는 30000
```

---

## 3. 납부 요약 카드

표시할 값:

```text
전체 납부 대상자 수
납부 완료자 수
부분 납부자 수
미납자 수
확인 필요 거래 수
제외 거래 수
총 납부 예정 금액
총 납부 확인 금액
```

---

## 4. 매칭 성공 거래 테이블

컬럼:

```text
거래일시
적요
입금액
매칭 부원
납부 유형
매칭 점수
상태
사유
```

---

## 5. 확인 필요 거래 테이블

컬럼:

```text
거래일시
적요
입금액
추정 부원
점수
사유
수동 처리
```

수동 처리:

* 부원 선택
* 납부 유형 선택
* 확정 버튼
* 제외 버튼

---

## 6. 미납자 테이블

컬럼:

```text
이름
학번
학과
납부 기간
필요 금액
납부 금액
상태
```

---

## 7. 제외 거래 테이블

컬럼:

```text
거래일시
적요
입금액
분류
사유
```

---

## 8. Frontend API 함수 보강

파일:

```text
frontend/lib/api.ts
```

추가 함수:

```ts
previewPaymentMatching(payload)
applyPaymentMatching(payload)
confirmPaymentTransaction(transactionId, payload)
excludePaymentTransaction(transactionId, payload)
getPaymentSummary(params)
getUnpaidPayments(params)
getPaymentRecords(params)
```

필요 타입:

```ts
PaymentMatchingPreview
PaymentMatchingResult
TransactionMatchItem
PaymentSummary
UnpaidPaymentItem
PaymentMatchingPayload
```

---

## 수동 매칭 동작

확인 필요 거래에서 수동 매칭을 수행할 수 있어야 한다.

동작:

1. 확인 필요 거래 선택
2. 부원 선택
3. 납부 유형 선택
4. 기준 금액 확인
5. 확정 클릭
6. bank_transactions 업데이트
7. payment_records 업데이트
8. 목록/요약 새로고침

---

## 자동 미납자 생성 방식

`match-apply` 실행 시 active members 전체를 기준으로 해당 period/payment_type에 대한 payment_records를 생성 또는 갱신한다.

예시:

```text
전체 active members: 5명
납부 매칭 성공: 3명
미납: 2명
```

그러면 결과:

```text
3명 → status = paid
2명 → status = unpaid
```

이미 해당 period/payment_type의 payment_record가 있으면 중복 생성하지 않고 갱신한다.

---

## 중복 실행 안정성

매칭 적용 API는 여러 번 실행해도 데이터가 중복으로 쌓이면 안 된다.

필수 조건:

```text
member_id + period + payment_type 기준으로 payment_records 중복 방지
transaction_id 기준으로 이미 연결된 거래 중복 방지
```

DB unique constraint가 이미 있다면 사용한다.
없다면 코드 레벨에서 중복을 방지한다.

---

## README 업데이트

README에 다음 내용을 추가한다.

### 납부 매칭 사용 방법

```text
1. /transactions에서 거래내역서를 업로드하고 가져오기
2. /payments로 이동
3. 납부 기간과 기준 금액 입력
4. 매칭 미리보기 클릭
5. 결과 확인
6. 문제가 없으면 매칭 적용 클릭
7. 확인 필요 거래는 수동 매칭 또는 제외 처리
8. 미납자 목록 확인
```

### API 테스트 예시

WSL/Linux:

```bash
curl -X POST http://localhost:8000/api/payments/match-preview \
  -H "Content-Type: application/json" \
  -d '{"period":"2026-1","payment_type":"membership_fee","required_amount":30000}'
```

```bash
curl -X POST http://localhost:8000/api/payments/match-apply \
  -H "Content-Type: application/json" \
  -d '{"period":"2026-1","payment_type":"membership_fee","required_amount":30000}'
```

Windows PowerShell:

```powershell
curl.exe -X POST http://localhost:8000/api/payments/match-preview -H "Content-Type: application/json" -d "{\"period\":\"2026-1\",\"payment_type\":\"membership_fee\",\"required_amount\":30000}"
```

```powershell
curl.exe -X POST http://localhost:8000/api/payments/match-apply -H "Content-Type: application/json" -d "{\"period\":\"2026-1\",\"payment_type\":\"membership_fee\",\"required_amount\":30000}"
```

---

## 테스트 및 검증

가능하면 테스트를 추가한다.

파일 예시:

```text
backend/tests/test_payment_matching_service.py
```

테스트 항목:

1. 예금이자 제외
2. 환불 제외
3. 이름 완전 포함 매칭
4. 공백/접두어 제거 후 이름 매칭
5. 유사도 매칭
6. 미납자 계산
7. payment_records 중복 생성 방지

pytest가 이미 있으면 사용한다.

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
http://localhost:3000/payments
http://localhost:8000/api/payments/match-preview
http://localhost:8000/api/payments/summary?period=2026-1&payment_type=membership_fee
http://localhost:8000/api/payments/unpaid?period=2026-1&payment_type=membership_fee
```

---

## 완료 기준

Task 6은 다음을 모두 만족해야 완료로 본다.

1. 거래내역 입금 행을 납부 매칭 대상으로 조회할 수 있다.
2. 예금이자/환불/취소 등 제외 거래를 분류할 수 있다.
3. 적요에서 이름 후보를 추출할 수 있다.
4. 부원 명부와 이름 매칭을 수행할 수 있다.
5. 회비 기준 금액으로 membership_fee를 판별할 수 있다.
6. 매칭 미리보기 API가 DB 변경 없이 결과를 반환한다.
7. 매칭 적용 API가 bank_transactions와 payment_records를 갱신한다.
8. active members 기준으로 미납자를 자동 생성할 수 있다.
9. 확인 필요 거래를 수동으로 매칭할 수 있다.
10. 제외 거래를 수동으로 제외 처리할 수 있다.
11. `/payments` 페이지에서 납부자/미납자/확인필요자를 확인할 수 있다.
12. 여러 번 매칭 적용을 실행해도 payment_records가 중복 생성되지 않는다.
13. README에 납부 매칭 사용 방법이 추가되어 있다.
14. 이번 Task에서 AI, OCR, n8n, Notion, Slack 기능은 구현되지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 6 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 구현된 Backend 기능
- ...

3. 구현된 Frontend 기능
- ...

4. 납부 매칭 로직
- ...

5. 수동 매칭/제외 처리 방식
- ...

6. 실행 검증 결과
- docker compose up -d db:
- alembic upgrade head:
- python -m app.scripts.seed:
- backend compile/test:
- pytest:
- frontend build:
- 주요 URL 확인:

7. 매칭 테스트 결과
- 매칭 미리보기:
- 매칭 적용:
- 미납자 생성:
- 중복 실행 방지:
- 수동 매칭:
- 제외 처리:

8. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

9. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

10. 다음 Task에서 해야 할 일
- Task 7: 활동 보고서 AI 생성 Agent 구현
```
