# Task 5. 거래내역서 업로드 및 파서 구현

## 목표

ClubAgent에서 은행 거래내역서 파일을 업로드하면, 거래 행을 자동으로 파싱하여 `bank_transactions` 테이블에 저장하는 기능을 구현한다.

이번 Task의 핵심은 다음이다.

```text
거래내역서 파일 업로드
→ 파일 형식 확인
→ 거래 테이블 헤더 자동 탐색
→ 거래일시/구분/적요/출금액/입금액/잔액/거래점 추출
→ 금액/날짜 정규화
→ bank_transactions 테이블 저장
→ 자체 웹페이지에서 거래내역 확인
```

이번 Task에서는 납부자 자동 매칭, 미납자 판별, 회비/활동비 자동 분류는 구현하지 않는다.
그 기능은 Task 6에서 구현한다.

---

## 전제 조건

Task 1~4가 완료되어 있어야 한다.

Task 1:

* FastAPI / Next.js / PostgreSQL / Docker Compose 기본 구조 완료

Task 2:

* SQLAlchemy 모델, Alembic, seed 데이터 완료
* `bank_transactions`, `uploaded_files` 테이블 존재

Task 3:

* 기본 CRUD API 구현 완료
* 파일 업로드 API 구현 완료
* 거래내역 목록 페이지 최소 구현 완료

Task 4:

* 기본 관리 UI 구현 완료

---

## 이번 Task 구현 범위

이번 Task에서는 다음만 구현한다.

1. 거래내역서 파일 업로드 UI
2. 거래내역서 파서 구현
3. xls/xlsx/csv 파일 처리
4. 은행 거래내역 헤더 행 자동 탐색
5. 거래 행 정규화
6. 파싱 결과 미리보기 API
7. 파싱 결과 DB 저장 API
8. 저장된 거래내역 목록 표시
9. 파싱 실패/확인 필요 행 처리
10. README에 거래내역서 업로드 사용 방법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* 부원 명부 기반 자동 매칭
* 납부자/미납자 판별
* 회비/활동비 자동 분류
* 동명이인 처리
* 유사도 매칭
* OpenAI API 호출
* Agent 실행 로직
* 영수증 OCR
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant/pgvector 연동

필요한 위치에는 TODO 주석만 남긴다.

---

## 참고 거래내역서 구조

거래내역서에는 상단에 계좌 정보가 있고, 실제 거래 테이블은 중간부터 시작할 수 있다.

예상 구조:

```text
거래내역조회

계좌번호 | 예금종류 | 조회기간
잔액 | 인출가능금액

거래일시 | 구분 | 적요 | 출금액 | 입금액 | 잔액 | 거래점
2026.02.25 13:10:01 | 입금 | 메모아 홍길동 | 0 | 30000 | 500000 | ...
...
합계 | ... | ... | ...
```

실제 파서는 헤더 행 번호를 고정하면 안 된다.
반드시 `"거래일시"` 셀이 있는 행을 찾아서 그 행을 헤더로 사용해야 한다.

---

## 거래내역 표준 컬럼

파싱 결과는 아래 표준 컬럼으로 정규화한다.

```text
transaction_datetime
transaction_type
memo
withdraw_amount
deposit_amount
balance
branch
raw_json
```

원본 컬럼과 매핑:

```text
거래일시 → transaction_datetime
구분 → transaction_type
적요 → memo
출금액 → withdraw_amount
입금액 → deposit_amount
잔액 → balance
거래점 → branch
원본 row 전체 → raw_json
```

---

## 파일 형식 지원

다음 파일을 지원한다.

```text
.xls
.xlsx
.csv
```

권장 Python 패키지:

```text
pandas
openpyxl
xlrd
```

주의:

* `.xlsx`는 `openpyxl` 사용
* `.xls`는 `xlrd` 사용
* 일부 은행 `.xls` 파일은 실제 Excel 바이너리가 아니라 HTML 테이블일 수 있다.
* 따라서 `.xls` 파싱 실패 시 `pandas.read_html()` fallback을 시도한다.
* `.csv`는 encoding 문제를 고려해 `utf-8-sig`, `cp949` 순서로 시도한다.

---

## Backend 구현 요구사항

### 1. 의존성 추가

`backend/requirements.txt`에 다음 패키지를 추가한다.

```text
pandas
openpyxl
xlrd
```

필요하다면 HTML 테이블 fallback을 위해 다음도 추가할 수 있다.

```text
lxml
html5lib
beautifulsoup4
```

단, 과도한 의존성은 피하고 필요한 경우에만 추가한다.

---

## 2. 파서 서비스 구현

파일:

```text
backend/app/services/bank_statement_parser.py
```

주요 함수:

```python
parse_bank_statement(file_path: Path) -> BankStatementParseResult
```

또는 프로젝트 스타일에 맞게 class로 구현해도 된다.

### 반환 구조

Pydantic schema 또는 dataclass로 다음 구조를 반환한다.

```python
class ParsedBankTransaction:
    transaction_datetime: datetime | None
    transaction_type: str | None
    memo: str | None
    withdraw_amount: int
    deposit_amount: int
    balance: int | None
    branch: str | None
    raw_json: dict
    row_index: int
    warnings: list[str]

class BankStatementParseResult:
    total_rows: int
    parsed_rows: int
    skipped_rows: int
    transactions: list[ParsedBankTransaction]
    errors: list[str]
    warnings: list[str]
```

프로젝트 기존 schema 스타일에 맞춰도 된다.

---

## 3. 헤더 자동 탐색

파서 요구사항:

1. 파일을 DataFrame으로 읽는다.
2. 모든 행을 탐색하여 `"거래일시"`가 포함된 행을 찾는다.
3. 해당 행을 header로 사용한다.
4. 그 다음 행부터 실제 거래 데이터로 본다.
5. 컬럼명 공백 제거
6. 필요한 컬럼이 없으면 명확한 에러 반환

필수 컬럼:

```text
거래일시
구분
적요
출금액
입금액
잔액
거래점
```

단, 은행 양식에 따라 일부 컬럼명이 다를 수 있으므로 아래 alias를 허용한다.

```text
거래일시: 거래일시, 거래일자, 일시, 거래일
구분: 구분, 거래구분, 입출금
적요: 적요, 내용, 거래내용, 입금자명, 보낸분/받는분
출금액: 출금액, 출금, 지급액, 지출액
입금액: 입금액, 입금, 입금액(원)
잔액: 잔액, 거래후잔액
거래점: 거래점, 취급점, 지점
```

---

## 4. 행 필터링

다음 행은 저장하지 않는다.

```text
빈 행
합계 행
소계 행
거래일시가 비어 있는 행
출금액/입금액/잔액이 모두 비어 있는 행
```

합계 행 판단 기준:

* 거래일시 또는 적요에 `"합계"`, `"합 계"`, `"총계"` 포함
* 또는 거래일시가 날짜로 파싱되지 않고, 다른 값도 요약 행처럼 보이는 경우

---

## 5. 금액 정규화

금액 문자열을 integer로 변환한다.

예시:

```text
"30,000" → 30000
"30,000원" → 30000
"" → 0
"-" → 0
"0" → 0
"(30,000)" → -30000
```

주의:

* 금액은 float이 아니라 int
* NaN은 0 또는 None으로 처리
* 출금액/입금액은 값이 없으면 0
* 잔액은 없으면 None

---

## 6. 날짜 정규화

거래일시를 datetime으로 변환한다.

지원 예시:

```text
2026.02.25 13:10:01
2026-02-25 13:10:01
2026/02/25 13:10
20260225
2026.02.25
```

시간이 없는 경우는 `00:00:00`으로 처리한다.

날짜 파싱 실패 시 해당 행은 저장하지 않고 warnings에 기록한다.

---

## 7. 중복 저장 방지

같은 거래내역서를 여러 번 업로드할 수 있으므로 중복 저장을 어느 정도 방지한다.

이번 Task에서는 완벽한 중복 검증이 아니라 다음 기준으로 중복을 판단한다.

중복 판단 기준:

```text
transaction_datetime
memo
withdraw_amount
deposit_amount
balance
```

위 값이 모두 같은 기존 row가 있으면 저장하지 않는다.

중복 row는 skipped 처리한다.

---

## 8. DB 저장 기본값

저장 시 다음 기본값을 사용한다.

```text
match_status = "unmatched"
payment_type = None
matched_member_id = None
```

Task 6에서 부원 매칭을 구현할 예정이므로 이번 Task에서는 매칭하지 않는다.

---

## 9. Backend API

### 1. Preview API

```http
POST /api/transactions/parse-preview
```

기능:

* 거래내역서 파일을 업로드한다.
* 파일을 `uploaded_files` 테이블에 저장한다.
* 파일을 실제로 파싱한다.
* DB에는 `bank_transactions`를 저장하지 않는다.
* 파싱 결과 preview를 반환한다.

요청:

```multipart
file: 업로드 파일
```

선택 필드:

```text
file_type = bank_statement
```

응답 예시:

```json
{
  "file_id": "uploaded-file-id",
  "total_rows": 30,
  "parsed_rows": 28,
  "skipped_rows": 2,
  "transactions": [
    {
      "row_index": 7,
      "transaction_datetime": "2026-02-25T13:10:01",
      "transaction_type": "입금",
      "memo": "메모아 홍길동",
      "withdraw_amount": 0,
      "deposit_amount": 30000,
      "balance": 500000,
      "branch": "스마트뱅킹",
      "warnings": []
    }
  ],
  "warnings": [],
  "errors": []
}
```

---

### 2. Import API

```http
POST /api/transactions/import
```

기능:

* 거래내역서 파일을 업로드한다.
* 파일을 `uploaded_files` 테이블에 저장한다.
* 파일을 파싱한다.
* `bank_transactions` 테이블에 저장한다.
* 중복 거래는 저장하지 않는다.
* 저장 결과를 반환한다.

요청:

```multipart
file: 업로드 파일
```

응답 예시:

```json
{
  "file_id": "uploaded-file-id",
  "total_rows": 30,
  "parsed_rows": 28,
  "inserted_rows": 25,
  "skipped_rows": 3,
  "duplicate_rows": 2,
  "errors": [],
  "warnings": []
}
```

---

### 3. 기존 Transactions API 보강

기존 API가 있다면 다음 필터를 확인/보강한다.

```http
GET /api/transactions?match_status=unmatched&payment_type=membership_fee
```

추가 필터:

```text
start_date
end_date
min_deposit
max_deposit
min_withdraw
max_withdraw
q
```

q 검색 대상:

```text
memo
transaction_type
branch
```

---

## Frontend 구현 요구사항

### 1. 거래내역 페이지 보강

파일:

```text
frontend/app/transactions/page.tsx
```

구현 기능:

1. 거래내역서 파일 업로드
2. 미리보기 버튼
3. 가져오기 버튼
4. 파싱 결과 요약 표시
5. 파싱된 거래 preview 테이블 표시
6. 저장된 거래내역 목록 표시
7. 필터 UI
8. 오류/경고 메시지 표시

---

### 2. 업로드 UI

필수 UI:

```text
파일 선택
미리보기 버튼
가져오기 버튼
```

지원 확장자 안내:

```text
지원 파일: .xls, .xlsx, .csv
```

---

### 3. 파싱 결과 요약

미리보기 또는 가져오기 후 다음 정보를 표시한다.

```text
전체 행 수
파싱 성공 행 수
저장된 행 수
스킵 행 수
중복 행 수
경고 수
오류 수
```

---

### 4. Preview 테이블

컬럼:

```text
거래일시
구분
적요
출금액
입금액
잔액
거래점
경고
```

금액은 천 단위 콤마로 표시한다.

---

### 5. 저장된 거래내역 테이블

기존 거래내역 목록 테이블을 보강한다.

컬럼:

```text
거래일시
구분
적요
출금액
입금액
잔액
거래점
매칭상태
납부유형
생성일
```

---

### 6. 필터 UI

최소 필터:

```text
검색어 q
매칭상태 match_status
납부유형 payment_type
```

가능하면 날짜 범위 필터도 추가한다.

```text
start_date
end_date
```

---

## Frontend API 함수 보강

파일:

```text
frontend/lib/api.ts
```

추가 함수:

```ts
parseTransactionPreview(file: File)
importTransactions(file: File)
getTransactions(params?: TransactionQueryParams)
```

필요하다면 타입도 추가한다.

```ts
ParsedBankTransaction
BankStatementPreviewResponse
BankStatementImportResponse
TransactionQueryParams
```

---

## 테스트 및 검증

가능하면 간단한 테스트를 추가한다.

### Backend parser unit test

파일 예시:

```text
backend/tests/test_bank_statement_parser.py
```

테스트 항목:

1. 금액 문자열 정규화
2. 날짜 문자열 정규화
3. 합계 행 제거
4. 헤더 행 탐색
5. 필수 컬럼 누락 시 에러 반환

테스트 프레임워크가 아직 없다면 pytest를 추가한다.

`backend/requirements.txt`에 추가:

```text
pytest
```

테스트 실행:

```bash
pytest
```

테스트까지 구현하기 어렵다면 최소한 파서 함수 내부를 검증 가능한 작은 함수로 분리한다.

---

## README 업데이트

README에 다음 내용을 추가한다.

### 거래내역서 업로드 사용 방법

```text
1. /transactions 페이지 접속
2. .xls, .xlsx, .csv 파일 선택
3. 미리보기 클릭
4. 파싱 결과 확인
5. 가져오기 클릭
6. 저장된 거래내역 테이블 확인
```

### API 테스트 예시

WSL/Linux:

```bash
curl -X POST http://localhost:8000/api/transactions/parse-preview \
  -F "file=@sample_bank_statement.xlsx"
```

```bash
curl -X POST http://localhost:8000/api/transactions/import \
  -F "file=@sample_bank_statement.xlsx"
```

Windows PowerShell:

```powershell
curl.exe -X POST http://localhost:8000/api/transactions/parse-preview -F "file=@sample_bank_statement.xlsx"
```

```powershell
curl.exe -X POST http://localhost:8000/api/transactions/import -F "file=@sample_bank_statement.xlsx"
```

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
http://localhost:3000/transactions
http://localhost:8000/api/transactions
```

---

## 완료 기준

Task 5는 다음을 모두 만족해야 완료로 본다.

1. 거래내역서 `.xls`, `.xlsx`, `.csv` 업로드가 가능하다.
2. `"거래일시"` 헤더 행을 자동 탐색한다.
3. 거래일시, 구분, 적요, 출금액, 입금액, 잔액, 거래점을 표준 컬럼으로 정규화한다.
4. 금액 문자열을 integer로 정규화한다.
5. 날짜 문자열을 datetime으로 정규화한다.
6. 합계/빈 행/잘못된 행을 저장하지 않는다.
7. 미리보기 API가 DB 저장 없이 파싱 결과를 반환한다.
8. 가져오기 API가 파싱 결과를 `bank_transactions`에 저장한다.
9. 중복 거래는 중복 저장하지 않는다.
10. `/transactions` 페이지에서 파일 업로드, 미리보기, 가져오기, 저장된 거래 목록 확인이 가능하다.
11. README에 거래내역서 업로드 사용 방법이 추가되어 있다.
12. 이번 Task에서 납부자/미납자 매칭은 구현하지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 5 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 구현된 Backend 기능
- ...

3. 구현된 Frontend 기능
- ...

4. 거래내역서 파서 동작 방식
- ...

5. 지원 파일 형식
- ...

6. 실행 검증 결과
- docker compose up -d db:
- alembic upgrade head:
- python -m app.scripts.seed:
- backend compile/test:
- pytest:
- frontend build:
- 주요 URL 확인:

7. 파싱 테스트 결과
- 미리보기 API:
- 가져오기 API:
- 중복 방지:
- 저장된 거래 수:

8. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

9. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

10. 다음 Task에서 해야 할 일
- Task 6: 부원 명부 기반 납부 매칭 및 미납자 판별 구현
```
