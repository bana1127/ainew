# ClubAgent

ClubAgent는 동아리 운영 자동화를 위한 기반 프로젝트입니다. Task 1에서는 실제 업무 기능을 구현하지 않고, 이후 Task 2에서 DB 모델과 CRUD API를 붙이기 쉬운 Next.js + FastAPI + PostgreSQL 실행 구조만 만듭니다.

## 이번 Task 구현 범위

- Next.js App Router, TypeScript, Tailwind CSS 기반 프론트엔드
- FastAPI 기반 백엔드
- `GET /api/health` API
- `/`에서 `/dashboard`로 redirect
- 관리자 대시보드 레이아웃, 좌측 사이드바, 상단 헤더, placeholder 카드
- 프론트엔드에서 백엔드 health API 호출 결과 표시
- PostgreSQL Docker Compose 서비스
- 백엔드 시작 시 `backend/uploads` 자동 생성
- Task 2를 위한 `models`, `schemas`, `services`, `agents`, `utils`, `alembic` placeholder 구조

## 이번 Task에서 구현하지 않은 것

DB 상세 모델, 실제 Alembic migration, CRUD API, AI Agent, OCR, 거래내역서 파싱, 납부 매칭, n8n, Notion, Slack/Telegram, Qdrant, pgvector 연동은 구현하지 않았습니다.

## 접속 주소

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Health API: `http://localhost:8000/api/health`
- PostgreSQL: `localhost:5433`

## 환경 변수

백엔드를 로컬에서 실행할 때 기본 DB URL:

```env
DATABASE_URL=postgresql+psycopg://clubagent:clubagent@localhost:5433/clubagent
```

Docker Compose 내부에서 backend 컨테이너가 db 컨테이너에 연결할 때 사용하는 DB URL:

```env
DATABASE_URL=postgresql+psycopg://clubagent:clubagent@db:5432/clubagent
```

## Windows PowerShell 실행 방법

Docker Desktop을 실행한 뒤 PostgreSQL을 시작합니다.

```powershell
docker compose up -d db
```

백엔드를 실행합니다.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

새 PowerShell 창에서 프론트엔드를 실행합니다.

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

## WSL 실행 방법

PostgreSQL을 시작합니다.

```bash
docker compose up -d db
```

백엔드를 실행합니다.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

새 터미널에서 프론트엔드를 실행합니다.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## 전체 Docker 실행

개발 중에는 DB만 Docker로 실행하고 backend/frontend는 로컬에서 실행하는 방식을 권장합니다. 필요하면 다음 명령으로 전체 서비스를 Docker Compose로 실행할 수 있습니다.

```bash
docker compose --profile app up --build
```

## Task 2: DB Migration

Task 2에서는 SQLAlchemy 모델, Alembic 초기 migration, seed 데이터를 추가했습니다. CRUD API와 프론트 상세 화면은 아직 구현하지 않습니다.

Windows PowerShell:

```powershell
docker compose up -d db
cd backend
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
alembic upgrade head
alembic current
alembic history
```

WSL/Linux:

```bash
docker compose up -d db
cd backend
source .venv/bin/activate
cp .env.example .env
alembic upgrade head
alembic current
alembic history
```

새 migration을 생성해야 할 때는 다음 명령을 사용합니다.

```bash
alembic revision --autogenerate -m "create initial clubagent tables"
```

## Task 2: Seed Data

초기 활동 카테고리, 기본 설정, 샘플 부원 데이터는 다음 명령으로 삽입합니다.

Windows PowerShell:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.scripts.seed
```

WSL/Linux:

```bash
cd backend
source .venv/bin/activate
python -m app.scripts.seed
```

Seed 스크립트는 여러 번 실행해도 다음 기준으로 중복 삽입하지 않습니다.

- `activity_categories`: `name`
- `app_settings`: `key`
- `members`: `student_id`

Task 2 완료 후 `http://localhost:8000/api/health`에서 다음 형태의 응답을 확인할 수 있습니다.

```json
{
  "status": "ok",
  "app": "ClubAgent",
  "database": "available",
  "tables": {
    "members": 5,
    "activity_categories": 9
  }
}
```

## Task 3: API Verification

Task 3 adds basic CRUD APIs, dashboard summary data, file upload metadata, notification read APIs, and frontend list pages.

Dashboard and list API checks:

Windows PowerShell:

```powershell
curl.exe http://localhost:8000/api/health
curl.exe http://localhost:8000/api/dashboard/summary
curl.exe http://localhost:8000/api/members
curl.exe http://localhost:8000/api/activity-categories
curl.exe http://localhost:8000/api/reference-reports
curl.exe http://localhost:8000/api/activity-reports
curl.exe http://localhost:8000/api/receipts
curl.exe http://localhost:8000/api/transactions
curl.exe http://localhost:8000/api/payment-records
curl.exe http://localhost:8000/api/notifications
curl.exe http://localhost:8000/api/settings
```

WSL/Linux:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/dashboard/summary
curl http://localhost:8000/api/members
curl http://localhost:8000/api/activity-categories
curl http://localhost:8000/api/reference-reports
curl http://localhost:8000/api/activity-reports
curl http://localhost:8000/api/receipts
curl http://localhost:8000/api/transactions
curl http://localhost:8000/api/payment-records
curl http://localhost:8000/api/notifications
curl http://localhost:8000/api/settings
```

Create example:

```powershell
curl.exe -X POST http://localhost:8000/api/notifications `
  -H "Content-Type: application/json" `
  -d "{\"type\":\"system\",\"title\":\"Local check\",\"message\":\"API is working\",\"severity\":\"info\"}"
```

File upload check:

Windows PowerShell:

```powershell
curl.exe -X POST http://localhost:8000/api/files/upload -F "file=@sample.txt" -F "file_type=other"
```

WSL/Linux:

```bash
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@sample.txt" \
  -F "file_type=other"
```

Frontend pages:

- `http://localhost:3000/dashboard`
- `http://localhost:3000/members`
- `http://localhost:3000/activities`
- `http://localhost:3000/references`
- `http://localhost:3000/receipts`
- `http://localhost:3000/transactions`
- `http://localhost:3000/payments`
- `http://localhost:3000/notifications`
- `http://localhost:3000/settings`

## 문제 해결

- `docker` 명령을 찾을 수 없으면 Docker Desktop 설치와 PATH 설정, WSL2 integration을 확인하세요.
- `/api/health`에서 `"database": "unavailable"`이 나오면 `docker compose up -d db`로 DB 컨테이너가 실행 중인지 확인하세요.
- PowerShell에서 venv 활성화가 막히면 같은 터미널에서 `Set-ExecutionPolicy -Scope Process RemoteSigned`를 실행한 뒤 다시 시도하세요.
- 프론트엔드가 백엔드에 연결하지 못하면 `frontend/.env.local`에 `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`이 있는지 확인하세요.
- 실제 `.env`와 `.env.local`은 Git에 포함하지 않습니다. `.env.example`을 복사해서 사용하세요.

## Task 4: 관리 UI 1차 구현

Task 4에서는 부원, 활동 카테고리, 레퍼런스 보고서, 활동 보고서의 CRUD 관리 UI를 추가했습니다.

### 부원 등록/수정/비활성화

브라우저에서 `http://localhost:3000/members` 접속

- **추가**: 우상단 "부원 추가" 버튼 클릭 → 이름, 학번, 학과, 전화번호, 이메일, 상태, 메모 입력 → 저장
- **수정**: 목록에서 "수정" 버튼 클릭 → 내용 수정 → 저장
- **비활성화**: 목록에서 "비활성화" 버튼 클릭 → 확인창에서 "비활성화" 클릭 (실제 삭제가 아니라 status=inactive 처리)
- **검색**: 상단 검색창에 이름 / 학번 / 학과 입력
- **필터**: 상태 드롭다운으로 활동중 / 비활성 / 졸업 / 휴면 필터

### 활동 카테고리 등록/수정/삭제

브라우저에서 `http://localhost:3000/settings` 접속

- **추가**: 우상단 "카테고리 추가" 버튼 클릭 → 카테고리명, 설명, 필수 입력값(쉼표 구분), 보고서 템플릿 입력 → 저장
- **수정**: 목록에서 "수정" 버튼 클릭 → 내용 수정 → 저장
- **삭제**: 목록에서 "삭제" 버튼 클릭 → 확인창에서 "삭제" 클릭
- 필수 입력값은 "활동명, 활동 일시, 장소" 형태로 쉼표 구분 입력 시 `{"fields": ["활동명", "활동 일시", "장소"]}`로 저장됩니다.

### 레퍼런스 보고서 등록/수정/삭제

브라우저에서 `http://localhost:3000/references` 접속

- **추가**: 우상단 "레퍼런스 추가" 버튼 클릭 → 카테고리, 제목, 내용, 태그(쉼표 구분) 입력 → 저장
- **수정**: 목록에서 "수정" 버튼 클릭 → 내용 수정 → 저장
- **삭제**: 목록에서 "삭제" 버튼 클릭 → 확인창에서 "삭제" 클릭
- **내용 미리보기**: 목록에서 눈 아이콘 버튼 클릭
- **필터**: 카테고리 드롭다운, 상단 검색창

### 활동 보고서 수동 작성

브라우저에서 `http://localhost:3000/reports` 접속 (또는 사이드바 "Reports" 클릭)

1. 카테고리 선택
2. 레퍼런스 보고서 참고 선택 (참고용, 저장되지 않음)
3. 제목, 활동일, 장소 입력
4. 입력 메모 작성 (AI 생성 시 사용될 데이터 — AI 기능은 향후 Task에서 구현)
5. 최종 내용 직접 작성
6. 참여자 선택 (활동 중인 부원 목록에서 체크박스로 선택)
7. 대표자 선택 (선택사항)
8. "보고서 저장" 클릭 → 저장 후 /activities로 이동

### 활동 보고서 수정/보관

브라우저에서 `http://localhost:3000/activities` 접속

- **수정**: 목록에서 "수정" 버튼 클릭 → 내용 수정 → 저장
- **보관**: 목록에서 "보관" 버튼 클릭 → 확인창에서 "보관" 클릭 (status=archived 처리)
- **필터**: 카테고리, 상태, 검색어 필터

### 활동 참여자 연결

새 보고서 작성 시 하단 "참여자 선택" 섹션에서 체크박스로 선택.
보고서 저장 후 `PUT /api/activity-reports/{id}/participants` API로 자동 저장됩니다.

API로 직접 조회/수정:

```powershell
# 참여자 조회
curl.exe http://localhost:8000/api/activity-reports/{report_id}/participants

# 참여자 수정
curl.exe -X PUT http://localhost:8000/api/activity-reports/{report_id}/participants `
  -H "Content-Type: application/json" `
  -d "{\"participants\": [{\"member_id\": \"...\"}, {\"member_id\": \"...\", \"role\": \"leader\"}]}"
```

### AI 기능 안내

Task 4에서는 AI 생성 기능을 구현하지 않았습니다.
다음 기능은 향후 Task에서 구현할 예정입니다.

- 활동 보고서 AI 자동 생성 (OpenAI API)
- 영수증 OCR 분석
- 거래내역서 파싱 및 납부 매칭
- n8n workflow 자동화
- Notion / Slack 연동

## Task 5: 거래내역서 업로드 및 파서

### 거래내역서 업로드 사용 방법

1. `/transactions` 페이지 접속
2. "파일 선택" 클릭 후 .xls, .xlsx, .csv 파일 선택
3. "미리보기" 클릭하여 파싱 결과 확인 (DB 저장 없음)
4. 파싱 결과 요약 및 거래 행 테이블 확인
5. "가져오기" 클릭하여 bank_transactions 테이블에 저장
6. 저장된 거래내역 테이블에서 확인

### 미리보기 vs 가져오기

| | 미리보기 | 가져오기 |
|---|---|---|
| 파일 저장 | ✅ uploaded_files | ✅ uploaded_files |
| DB 저장 | ❌ 저장 안 함 | ✅ bank_transactions |
| 중복 방지 | - | ✅ 중복 스킵 |

### 지원 파일 형식

- `.xlsx` — openpyxl 엔진
- `.xls` — xlrd 엔진 (실패 시 HTML fallback)
- `.csv` — utf-8-sig, cp949, utf-8 순서로 인코딩 시도

### 파서 동작 방식

1. 파일을 header 없이 DataFrame으로 읽음
2. 모든 행을 스캔하여 "거래일시" 셀이 있는 행을 헤더로 사용
3. 컬럼명 alias 매핑 (은행별 컬럼명 차이 지원)
4. 합계/빈 행/날짜 파싱 불가 행 스킵
5. 금액 문자열 → int, 날짜 문자열 → datetime 정규화
6. 중복 판단: transaction_datetime + memo + withdraw_amount + deposit_amount + balance

### API 테스트 예시

#### WSL / Linux

```bash
# 미리보기 (DB 저장 없음)
curl -X POST http://localhost:8000/api/transactions/parse-preview \
  -F "file=@sample_bank_statement.xlsx"

# 가져오기 (DB 저장)
curl -X POST http://localhost:8000/api/transactions/import \
  -F "file=@sample_bank_statement.xlsx"

# 저장된 거래내역 조회
curl "http://localhost:8000/api/transactions"

# 필터 조회
curl "http://localhost:8000/api/transactions?match_status=unmatched&q=홍길동&start_date=2026-01-01"
```

#### Windows PowerShell

```powershell
# 미리보기
curl.exe -X POST http://localhost:8000/api/transactions/parse-preview -F "file=@sample_bank_statement.xlsx"

# 가져오기
curl.exe -X POST http://localhost:8000/api/transactions/import -F "file=@sample_bank_statement.xlsx"
```

### 이번 Task에서 구현하지 않은 기능

- 부원 명부 기반 자동 매칭 (Task 6에서 구현 예정)
- 납부자/미납자 판별 (Task 6에서 구현 예정)
- 회비/활동비 자동 분류 (Task 6에서 구현 예정)
- OpenAI API, OCR, n8n, Notion, Slack, Qdrant/pgvector 연동

## Task 6. 납부 매칭 및 미납자 판별

### 납부 매칭 사용 방법

1. `/transactions`에서 거래내역서를 업로드하고 가져오기
2. `/payments`로 이동
3. 납부 기간(예: 2026-1)과 기준 금액(예: 30000) 입력
4. **매칭 미리보기** 클릭 → DB 변경 없이 결과 확인
5. 결과 검토 후 **매칭 적용** 클릭 → payment_records 생성/갱신
6. 확인 필요 거래는 수동으로 부원 선택 후 **확정** 또는 **제외** 처리
7. 미납자 목록 확인

### 미리보기 vs 매칭 적용

| 항목 | 미리보기 | 매칭 적용 |
|------|----------|----------|
| DB 변경 | 없음 | bank_transactions, payment_records 갱신 |
| 반복 실행 | 안전 | 중복 생성 없이 갱신 |
| 목적 | 결과 확인 | 납부 상태 확정 |

### 확인 필요 거래 수동 매칭

1. 확인 필요 거래 테이블에서 해당 행 클릭
2. 부원 선택 드롭다운에서 부원 이름 선택
3. 납부 유형 선택
4. **확정** 클릭 → `PATCH /api/payments/transactions/{id}/confirm`

### 제외 거래 처리

확인 필요 거래에서 **제외** 클릭 시 `match_status = "excluded"`로 표시.
이자/환불 거래는 자동으로 제외 분류됩니다.

### 납부 매칭 알고리즘

1. **학번 매칭**: memo에 학번이 포함되면 즉시 매칭 (score=1.0)
2. **이름 완전 포함 매칭**: 부원명이 memo에 포함 (score=1.0)
3. **정규화 이름 매칭**: 공백/특수문자 제거 후 포함 (score=0.95)
4. **유사도 매칭**: difflib.SequenceMatcher 기준 score ≥ 0.8 (기본값)

복수 매칭 시 need_check 처리.

### 제외 거래 자동 분류 키워드

`예금이자`, `이자`, `환불`, `네이버페이환불`, `결제취소`, `취소`, `캐시백`, `정산`

### API 테스트 예시

#### WSL/Linux

```bash
# 매칭 미리보기
curl -X POST http://localhost:8000/api/payments/match-preview \
  -H "Content-Type: application/json" \
  -d '{"period":"2026-1","payment_type":"membership_fee","required_amount":30000}'

# 매칭 적용
curl -X POST http://localhost:8000/api/payments/match-apply \
  -H "Content-Type: application/json" \
  -d '{"period":"2026-1","payment_type":"membership_fee","required_amount":30000}'

# 납부 요약
curl "http://localhost:8000/api/payments/summary?period=2026-1&payment_type=membership_fee"

# 미납자 목록
curl "http://localhost:8000/api/payments/unpaid?period=2026-1&payment_type=membership_fee"
```

#### Windows PowerShell

```powershell
# 매칭 미리보기
curl.exe -X POST http://localhost:8000/api/payments/match-preview -H "Content-Type: application/json" -d "{"period":"2026-1","payment_type":"membership_fee","required_amount":30000}"

# 매칭 적용
curl.exe -X POST http://localhost:8000/api/payments/match-apply -H "Content-Type: application/json" -d "{"period":"2026-1","payment_type":"membership_fee","required_amount":30000}"

# 납부 요약
curl.exe "http://localhost:8000/api/payments/summary?period=2026-1&payment_type=membership_fee"

# 미납자 목록
curl.exe "http://localhost:8000/api/payments/unpaid?period=2026-1&payment_type=membership_fee"
```

### 미구현 기능 (TODO)

이번 Task에서 다음 기능은 구현하지 않았습니다.

- OpenAI API 기반 이름 추론 (TODO 주석 위치: payment_matching_service.py)
- 실제 알림 발송 (Slack/Telegram)
- 제외 사유 DB 저장 (reason 필드 없음, 응답에만 포함)
- n8n 워크플로우 연동
- Qdrant/pgvector 연동

## Task 7. 활동 보고서 AI 생성 Agent

### OpenAI 환경변수 설정

`backend/.env` 파일에 다음을 설정합니다:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MOCK_MODE=true
```

| 변수 | 설명 | 기본값 |
|------|------|--------|
| OPENAI_API_KEY | 실제 OpenAI API 키 | 없음 |
| OPENAI_MODEL | 사용할 모델명 | gpt-4.1-mini |
| OPENAI_MOCK_MODE | true이면 실제 API 호출 안 함 | true |

### Mock mode 테스트

기본값은 `OPENAI_MOCK_MODE=true`이므로 API 키 없이도 활동 보고서 초안 생성 기능을 테스트할 수 있습니다.

`/reports` 페이지에서 카테고리와 제목을 입력하고 **AI 초안 생성** 버튼을 클릭하면 mock 보고서가 즉시 생성됩니다.

### 실제 OpenAI API 사용

1. `backend/.env`에 `OPENAI_API_KEY=sk-...` 입력
2. `OPENAI_MOCK_MODE=false`로 변경
3. 백엔드 재시작 (`uvicorn app.main:app --reload`)
4. `/reports` 페이지에서 AI 초안 생성 실행

### /reports 페이지 사용 방법

1. 카테고리 선택 (필수)
2. 제목 입력 (필수)
3. 활동일, 장소, 참여자, 입력 메모 입력 (선택)
4. 레퍼런스 보고서 선택 (AI 참고용)
5. **AI 초안 생성** 클릭 → 생성된 초안 미리보기
6. **초안을 최종 내용에 적용** 클릭 → 최종 내용 textarea에 자동 입력
7. 내용 수정 후 **보고서 저장** 클릭

### API 테스트 예시

#### WSL/Linux

```bash
curl -X POST http://localhost:8000/api/agents/activity-report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "카테고리-UUID",
    "title": "5월 AI 스터디",
    "activity_date": "2026-05-30",
    "location": "동아리방",
    "input_text": "PBL-C 개발 방향 회의와 역할 분담 진행",
    "participant_ids": [],
    "file_ids": [],
    "save_to_db": true
  }'
```

#### Windows PowerShell

```powershell
curl.exe -X POST http://localhost:8000/api/agents/activity-report/generate `
  -H "Content-Type: application/json" `
  -d "{\"category_id\":\"카테고리-UUID\",\"title\":\"5월 AI 스터디\",\"activity_date\":\"2026-05-30\",\"location\":\"동아리방\",\"input_text\":\"PBL-C 개발 방향 논의\",\"participant_ids\":[],\"file_ids\":[],\"save_to_db\":true}"
```

### Agent 구조

```text
POST /api/agents/activity-report/generate
  → ActivityReportOrchestrator
    → FileParserAgent (파일 메타데이터 조회)
    → PostAgent (LLMService 호출 → 보고서 초안 생성)
    → PublisherAgent (activity_reports.generated_content 저장)
  → ActivityReportGenerateResponse 반환
```

### 미구현 기능 (TODO)

이번 Task에서 다음 기능은 구현하지 않았습니다.

- 영수증 OCR (Task 8에서 구현 예정)
- 감사 규정 체크
- n8n 워크플로우 연동
- Notion 연동
- Slack/Telegram 연동
- Qdrant/pgvector 벡터 검색
- 이미지 내용 정밀 분석 (TODO 주석: file_parser_agent.py)

## Task 8. 영수증 OCR 및 감사 규정 체크 Agent

### 영수증 분석 사용 방법

1. `/receipts` 페이지 접속
2. 영수증 이미지 선택 (jpg, png, pdf 등)
3. 연결할 활동 보고서가 있으면 선택
4. 결제 방식을 알면 수동 선택, 모르면 `unknown` 유지
5. 지출 분류 입력 (선택)
6. **영수증 분석** 클릭
7. 분석 결과 카드에서 증빙 상태 확인
8. 확인 필요 항목은 사유와 필요 증빙 목록 확인

### 증빙 상태 기준

| 상태 | 설명 | 결제 방식 예시 |
|------|------|--------------|
| valid (적합) | 감사 규정에 적합 | card, online_card |
| need_check (확인 필요) | 추가 서류 필요 | transfer_student, transfer_company, recurring_payment |
| invalid (부적합) | 불가 처리 방식 | cash_withdrawal, personal_card_reimbursement |
| pending (대기) | 미분석 상태 | - |

### Mock mode 설명

`OPENAI_MOCK_MODE=true`(기본값)이면 API 키 없이도 mock 분석 결과로 기능을 테스트할 수 있습니다.

파일명에 힌트가 있으면 mock 결과에 반영됩니다:
- `receipt_card_50700.jpg` → payment_method=card, amount=50700
- `transfer_student_30000.png` → payment_method=transfer_student, amount=30000
- `online_12000.png` → payment_method=online_card, amount=12000

### 실제 OpenAI API 테스트

1. `backend/.env`에 `OPENAI_API_KEY=sk-...` 입력
2. `OPENAI_MOCK_MODE=false`로 변경
3. (선택) `OPENAI_VISION_MODEL=gpt-4o` 설정 (기본: OPENAI_MODEL 사용)
4. 백엔드 재시작
5. `/receipts`에서 영수증 분석 실행

### API 테스트 예시

#### WSL/Linux

```bash
# 파일 업로드 분석
curl -X POST http://localhost:8000/api/agents/receipt/analyze \
  -F "file=@sample_receipt.jpg" \
  -F "save_to_db=true" \
  -F "manual_payment_method=card" \
  -F "manual_category=간식비"

# 기분석 파일 재분석
curl -X POST http://localhost:8000/api/agents/receipt/analyze-file \
  -H "Content-Type: application/json" \
  -d '{"file_id":"파일-UUID","save_to_db":true,"manual_payment_method":"card"}'

# 영수증 목록 조회
curl "http://localhost:8000/api/receipts?evidence_status=need_check"
```

#### Windows PowerShell

```powershell
curl.exe -X POST http://localhost:8000/api/agents/receipt/analyze `
  -F "file=@sample_receipt.jpg" `
  -F "save_to_db=true" `
  -F "manual_payment_method=card" `
  -F "manual_category=간식비"
```

### 감사 규정 수정

`backend/app/data/audit_rules.json` 파일을 직접 수정하여 규정을 변경할 수 있습니다.

### 미구현 기능 (TODO)

- 예산 잔액 계산 (Budget Agent 최소 구현만 완료, Task 9+ 예정)
- 실제 외부 OCR SaaS 연동
- n8n 워크플로우 연동
- Notion 연동
- Slack/Telegram 연동
- Qdrant/pgvector 연동

## Task 9. 고급 디자인 시스템 및 전역 레이아웃 정리

Task 9에서는 기능 로직을 변경하지 않고 전체 UI를 고급스럽고 절제된 디자인으로 정리했습니다.

### 디자인 시스템 개요

디자인 키워드: **Luxury minimal** — 향수 브랜드를 연상시키는 절제된 감성, warm ivory 배경, deep charcoal 텍스트, soft lavender accent.

### 주요 색상 토큰

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--background` | `#F8F5EF` | 전체 배경 (warm ivory) |
| `--surface` | `#FFFFFF` | 카드 배경 |
| `--surface-soft` | `#FFFCF7` | 테이블 호버, 연한 카드 |
| `--text-main` | `#1F1F24` | 주요 텍스트 |
| `--text-muted` | `#77716A` | 보조 텍스트, 라벨 |
| `--border-soft` | `#E8E1D8` | 카드/테이블 테두리 |
| `--primary` | `#7C6CF2` | 주요 액션, 활성 메뉴 |
| `--primary-soft` | `#EEEAFE` | primary 배경 |
| `--accent` | `#C8A96A` | muted gold 포인트 |
| `--success` | `#3F7D58` | 성공/납부완료/적합 |
| `--warning` | `#B9822B` | 확인필요/경고 |
| `--danger` | `#B94A48` | 오류/미납/부적합 |

Tailwind config에도 동일 토큰이 정의되어 있으며, `tailwind.config.ts`에서 `pine`(→primary), `coral`(→danger), `amber`(→accent), `mist`(→background), `line`(→border-soft)로 기존 코드와의 호환성을 유지합니다.

### 공통 레이아웃 구조

```text
AppShell
├── Sidebar (w-64, fixed)
│   ├── 로고 영역
│   ├── 메뉴 (Dashboard ~ Settings)
│   ├── Coming Soon (Assistant — Task 10 예정)
│   └── Mock Mode 안내 카드
└── MainArea (pl-64)
    ├── Header (sticky, 현재 페이지 제목/설명)
    └── main (px-6 py-8)
        └── 페이지 콘텐츠
```

모든 페이지(`/dashboard`, `/members`, `/activities`, `/reports`, `/references`, `/receipts`, `/transactions`, `/payments`, `/notifications`, `/settings`)에 AppShell이 적용되어 있습니다.

### 공통 UI 컴포넌트

| 컴포넌트 | 위치 | 설명 |
|---------|------|------|
| `Button` | `components/ui/Button.tsx` | primary / secondary / ghost / outline / danger variant |
| `Card` | `components/ui/Card.tsx` | rounded-2xl 카드, soft shadow |
| `Badge` | `components/ui/Badge.tsx` | default / success / warning / danger / primary |
| `StatusBadge` | `components/ui/StatusBadge.tsx` | 상태값 자동 색상 매핑 |
| `EmptyState` | `components/ui/EmptyState.tsx` | 빈 데이터 상태 표시 |
| `LoadingState` | `components/ui/LoadingState.tsx` | 로딩 스피너 |
| `ErrorState` | `components/ui/ErrorState.tsx` | 에러 메시지 + 재시도 버튼 |
| `PageHeader` | `components/ui/PageHeader.tsx` | 페이지 제목/설명/우측 액션 |
| `SectionHeader` | `components/ui/SectionHeader.tsx` | 섹션 제목/설명/우측 액션 |
| `StatCard` | `components/ui/StatCard.tsx` | 통계 수치 카드 |

### StatusBadge 상태 매핑

```text
active / confirmed / valid / matched / paid  → success (초록)
generated                                    → primary (라벤더)
need_check / partial                         → warning (황금)
invalid / unpaid                             → danger (빨강)
inactive / draft / archived / pending / unmatched / excluded / graduated / paused → muted (회색)
```

### 기능 로직 변경 없음

Task 9는 UI/UX 정리 작업으로, 다음 기능 로직은 일체 변경하지 않았습니다.

- OpenAI 호출 로직
- 영수증 분석 Agent
- 거래내역서 파서
- 납부 매칭 알고리즘
- DB 스키마 / Alembic migration
- 백엔드 API 엔드포인트

### 다음 Task 10 예정

Task 10에서 **Payment API 404 수정 및 Command Center** 구현 예정.

## Task 10. Payment API 경로 수정 및 Assistant Command Center 구현

### Part A. Payment API 404 수정

#### 원인

`frontend/lib/api.ts`에서 Payment 관련 함수들이 `/api/payments/payment-matching/*` 경로를 호출하고 있었으나, 백엔드 라우터는 `/api/payments/*` prefix로 등록되어 있었습니다.

#### 수정한 프론트엔드 경로

| 이전 (오류) | 수정 후 |
|------------|---------|
| `/api/payments/payment-matching/summary` | `/api/payments/summary` |
| `/api/payments/payment-matching/unpaid` | `/api/payments/unpaid` |
| `/api/payments/payment-matching/match-preview` | `/api/payments/match-preview` |
| `/api/payments/payment-matching/match-apply` | `/api/payments/match-apply` |
| `/api/payments/payment-matching/transactions/{id}/confirm` | `/api/payments/transactions/{id}/confirm` |
| `/api/payments/payment-matching/transactions/{id}/exclude` | `/api/payments/transactions/{id}/exclude` |

#### 표준 Payment API 경로

```text
GET  /api/payments/summary?period=2026-1&payment_type=membership_fee
GET  /api/payments/unpaid?period=2026-1&payment_type=membership_fee
POST /api/payments/match-preview
POST /api/payments/match-apply
PATCH /api/payments/transactions/{transaction_id}/confirm
PATCH /api/payments/transactions/{transaction_id}/exclude
```

backward-compatibility를 위해 다음 alias도 지원합니다 (hidden, not in docs):
- `GET /api/payments/payment-matching/summary`
- `GET /api/payments/payment-matching/unpaid`

---

### Part B. Command Center (AI 작업실)

#### URL

```text
http://localhost:3000/assistant
```

#### 사용 방법

1. 사이드바에서 **AI 작업실** 클릭
2. 파일 첨부 (영수증 이미지, 거래내역서 Excel/CSV, 활동 자료 등)
3. 자연어로 요청 입력하거나 예시 요청 chip 클릭
4. 처리 유형을 **자동 감지** 또는 수동 선택
5. 납부 기간/유형/기준 금액 설정 (납부 관련 요청 시)
6. **실행** 버튼 클릭
7. 결과 카드에서 내용 확인 후 **확인 후 반영** 클릭

#### 자동 감지 규칙 (규칙 기반, LLM 미사용)

```text
1. 사용자가 수동 선택한 경우 → 해당 intent 사용 (confidence 1.0)
2. .xls/.xlsx/.csv 파일 + 은행/거래 키워드 → bank_statement_import (0.85)
3. .xls/.xlsx/.csv 파일만 → bank_statement_import (0.75)
4. 회비/납부/미납 키워드 → payment_matching (0.80)
5. 거래내역/입금/출금/계좌/은행 키워드 → bank_statement_import (0.70)
6. 이미지 파일 + 영수증/결제/지출/증빙 키워드 → receipt_analysis (0.85)
7. 활동보고서/보고서/활동 사진/초안 키워드 → activity_report_generate (0.75)
8. 이미지 파일만 → receipt_analysis (0.45)
9. 매칭 실패 → unknown
```

#### auto_apply 옵션

| auto_apply | 동작 |
|-----------|------|
| false (기본) | 미리보기 결과 반환, 사용자가 확인 후 반영 |
| true | 바로 저장/적용 |

#### Human-in-the-loop

`auto_apply=false`이면 결과 카드에 **확인 후 반영** 버튼이 표시됩니다.
- `payment_matching_preview` → match-apply 실행
- `bank_statement_preview` → import 실행
- 기타 → re-run with auto_apply=true

#### LLM 기반 Intent Classifier

이번 Task에서는 LLM 기반 Intent Classifier를 구현하지 않았습니다.
규칙 기반 라우팅만 구현하였으며, LLM 기반 분류는 향후 Task에서 추가 예정입니다.

#### API 테스트 예시

```bash
# 납부 매칭 미리보기
curl -X POST http://localhost:8001/api/assistant/execute \
  -F "message=이번 달 미납자 확인해줘" \
  -F "requested_intent=payment_matching" \
  -F "period=2026-1" \
  -F "payment_type=membership_fee" \
  -F "required_amount=30000" \
  -F "auto_apply=false"

# 영수증 분석
curl -X POST http://localhost:8001/api/assistant/execute \
  -F "message=이 영수증 활동비로 정리해줘" \
  -F "files=@receipt.jpg" \
  -F "auto_apply=false"
```

#### 미구현 기능 (TODO)

- LLM 기반 Intent Classifier
- assistant_runs 실행 이력 DB 테이블
- 멀티턴 채팅
- n8n/Notion/Slack 연동

## Task 11. Assistant 결과 카드 고도화 및 Human-in-the-loop UX

### 결과 카드 종류

| result_type | 카드 컴포넌트 | 설명 |
|-------------|-------------|------|
| `receipt_analysis` | ReceiptResultCard | 날짜/가맹점/금액/증빙상태 상세 표시 |
| `bank_statement_preview` | BankStatementResultCard | 파싱 통계 + 경고/오류 목록 |
| `bank_statement_import_result` | BankStatementResultCard | 저장 결과 통계 |
| `payment_matching_preview` | PaymentMatchingResultCard | 매칭/미납 통계 + 미납자 미리보기 |
| `payment_matching_result` | PaymentMatchingResultCard | 반영 완료 통계 |
| `activity_report_draft` | ActivityReportResultCard | 제목/요약/본문 미리보기 |
| `general_message` | GeneralResultCard | 안내 메시지 |
| `error` | GeneralResultCard | 오류 메시지 + 재시도 안내 |

### preview vs applied 상태

| 상태 | 설명 | 버튼 |
|------|------|------|
| `preview` | 분석 완료, DB 미반영 | 반영하기 / 취소 |
| `applied` | DB에 반영 완료 | 결과 확인하기 (상세 페이지 이동) |
| `failed` | 오류 발생 | — |
| `cancelled` | 사용자가 취소 | — |

### 확인 후 반영 UX

1. **실행** 버튼 → `auto_apply=false`로 미리보기 결과 반환
2. 결과 카드에 **반영 버튼** 표시 (예: "납부 상태 반영", "거래내역 반영")
3. 반영 버튼 클릭 → **확인 모달** 팝업
   - "이 결과를 실제 데이터에 반영하시겠습니까?"
   - 작업 유형별 구체적 설명 표시
4. **반영하기** 클릭 → 기존 API 호출:
   - `payment_matching_preview` → `POST /api/payments/match-apply`
   - `bank_statement_preview` → `POST /api/transactions/import`
   - 기타 → `auto_apply=true`로 재실행
5. 성공 시 카드 상태 `applied`로 변경 + 상세 페이지 이동 버튼 표시

### auto_apply=false 기본 원칙

ClubAgent는 "AI가 마음대로 저장하는 서비스"가 아닙니다.
AI가 초안을 만들고 사람이 확인한 뒤 반영하는 Human-in-the-loop 원칙을 따릅니다.
`auto_apply`는 기본값이 `false`이며, 사용자가 명시적으로 체크해야 자동 반영됩니다.

### 결과 카드에서 상세 페이지 이동

각 결과 카드에는 관련 상세 페이지 이동 버튼이 표시됩니다.

| result_type | 이동 페이지 |
|-------------|----------|
| receipt_analysis | /receipts |
| bank_statement_* | /transactions |
| payment_matching_* | /payments |
| activity_report_draft | /reports |

### 실행 이력

세션 내 실행 결과는 페이지 내에 누적 표시됩니다 (newest first).
DB 저장 없이 프론트 state에만 유지됩니다.
TODO(Task 13): `assistant_runs` 테이블 추가 예정.

## Task 12. 브랜드 로고 적용, 사이드바 간소화, Dashboard 재정리

### 브랜드 로고

| 구분 | 경로 |
|------|------|
| 원본 | `img/oui-parfum.png` |
| Frontend public asset | `frontend/public/brand/oui-parfum.png` |
| URL | `/brand/oui-parfum.png` |

로고 적용 위치:
- Sidebar 상단 (40×40px 원형)
- Dashboard Hero (64×64px 원형)
- AI 작업실 Hero (56×56px 원형)

### 사이드바 그룹 구조

```text
MAIN
  Dashboard / AI 작업실

OPERATIONS
  Activities / Reports / References

FINANCE
  Receipts / Transactions / Payments

PEOPLE
  Members

SYSTEM
  Notifications / Settings
```

그룹 라벨은 작고 muted하게 표시됩니다.

### Dashboard 구조 변경

| 영역 | 내용 |
|------|------|
| Brand Hero | 로고 + 제목 + AI 작업실 / 운영 데이터 CTA 2개 |
| 오늘 처리할 일 | 확인 필요 영수증 / 미납자 / 작성 중 보고서 / 읽지 않은 알림 |
| 운영 요약 | 전체 부원 / 활동 카테고리 / 전체 보고서 / 전체 거래내역 / 총 입금 / 총 출금 (6개) |
| 추천 작업 | AI 작업실 안내 + 이동 링크 |

개발자용 "Task 예정" 문구를 실사용자용 문구로 교체했습니다.

### AI 작업실이 핵심 진입점

AI 작업실(`/assistant`)은 ClubAgent의 핵심 진입점입니다.

- Dashboard Hero에서 **AI 작업실 열기** CTA 제공
- 사이드바 MAIN 그룹에서 Dashboard 바로 아래 배치
- 파일 업로드 → 요청 입력 → (상세 옵션) → 실행 순서로 정돈
- 상세 옵션(처리 유형/납부 기간 등)은 **접을 수 있는 영역**으로 이동하여 기본 화면 단순화
- `auto_apply` 문구: "확인 없이 바로 반영 / 기본값은 꺼짐입니다."

## Task 13. 활동 보고서 카드형 UX, 데모 데이터, 외부 배포 준비

### 활동 보고서 카드형 목록 (`/activities`)

보고서 목록이 카드 그리드 형태로 표시됩니다.

- **카드**: 제목 / 카테고리 / 활동일 / 장소 / 상태 badge / 본문 미리보기
- **카드 클릭 → 오른쪽 Drawer** 오픈
- **Drawer 액션**: 본문 복사 / `.md` 다운로드 / `.txt` 다운로드 / 수정하러 가기 / 보관 처리
- 기본값: `archived` 상태 제외 표시
- EmptyState에서 AI 작업실로 이동 안내

### 데모 데이터

```bash
cd backend
python -m app.scripts.seed_demo
```

삽입 내용: 샘플 부원 10명, 활동 보고서 4개(draft/generated/confirmed), 레퍼런스 보고서 3개

자세한 데모 시나리오는 [DEMO.md](DEMO.md) 참조.

### API 연결 구조

| 환경 | API 경로 | 연결 방식 |
|------|---------|---------|
| 로컬 개발 | `/api/*` | Next.js rewrite → `http://127.0.0.1:8001/api/*` |
| 외부 배포 | `https://agent.banawy.store/api/*` | Nginx reverse proxy → `http://127.0.0.1:8001/api/*` |

**환경변수 요약:**

```env
# frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=         # 빈값 → /api 상대 경로 사용 (rewrite 활성화)
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001

# backend/.env
BACKEND_CORS_ORIGINS=http://localhost:3000,https://agent.banawy.store
```

배포 상세는 [DEPLOY.md](DEPLOY.md) 참조.

## Task 14. 실제 AI 모드 활성화 및 자동화 점검 API

### 실제 OpenAI 모드 활성화

```env
# backend/.env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_VISION_MODEL=gpt-4.1-mini
OPENAI_MOCK_MODE=false
```

- `OPENAI_MOCK_MODE=true` (기본): 테스트용 Mock 응답
- `OPENAI_MOCK_MODE=false`: 실제 OpenAI API 호출 (영수증 OCR + 활동 보고서 생성)
- API key 미설정 시 사용자 친화적 에러 메시지 반환

### 영수증 삭제

`/receipts` 페이지 목록에서 각 행의 삭제 아이콘으로 영수증 분석 결과를 삭제할 수 있습니다.
업로드된 원본 파일(`uploaded_files`)은 삭제되지 않습니다.

### 납부 상태 직접 수정

`/payments` 페이지 미납자 목록에서 **직접 수정** 버튼으로 거래내역 매칭 없이 납부 상태를 변경할 수 있습니다.

지원 상태: `unpaid` / `paid` / `partial` / `need_check` / `exempt`

API:
```
PUT /api/payment-records/manual
```

### 자동 점검 API

n8n 또는 curl로 주기적으로 호출할 수 있는 자동 점검 엔드포인트:

```bash
POST /api/automations/weekly-check       # 주간 운영 현황
POST /api/automations/audit-check        # 감사 규정 준수 점검
POST /api/automations/quarterly-summary  # 분기 요약
```

결과는 `/notifications` 페이지에 자동 저장됩니다.

인증 (선택):
```env
AUTOMATION_API_TOKEN=my-secret-token
```
설정 시 `X-Automation-Token: my-secret-token` 헤더 필요.

### n8n 연결

자세한 n8n 설정, curl 테스트 방법, 점검 항목 설명은 [AUTOMATION.md](AUTOMATION.md) 참조.
