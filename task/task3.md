# Task 3. 기본 CRUD API, Dashboard API, 프론트 데이터 연결 구현

## 목표

Task 2에서 구현한 DB 모델과 seed 데이터를 실제 백엔드 API로 사용할 수 있게 만든다.

이번 Task의 목표는 다음이다.

* FastAPI Router 구조 확장
* 주요 테이블 기본 CRUD API 구현
* Dashboard Summary API 구현
* 파일 업로드 API 구현
* Notification 읽음 처리 API 구현
* Frontend API client 정리
* Dashboard 페이지를 실제 API 데이터와 연결
* 각 메뉴 페이지에서 최소 목록 조회가 가능하도록 구현

이번 Task는 “AI 기능 구현”이 아니라, **자체 웹서비스의 데이터 입출력 기반을 완성하는 단계**이다.

---

## 전제 조건

Task 1, Task 2가 완료되어 있어야 한다.

Task 1 완료 기준:

* FastAPI 기본 구조 존재
* Next.js 기본 구조 존재
* Docker Compose PostgreSQL 구성 완료
* `/api/health` 구현 완료

Task 2 완료 기준:

* SQLAlchemy 모델 구현 완료
* Alembic migration 구현 완료
* PostgreSQL 테이블 생성 가능
* Seed 데이터 삽입 가능
* `/api/health`에서 DB 상태와 일부 count 확인 가능

---

## 이번 Task 구현 범위

이번 Task에서는 다음만 구현한다.

1. 주요 테이블 CRUD API
2. Dashboard Summary API
3. File Upload API
4. Notification read/read-all API
5. Frontend `lib/api.ts` 정리
6. Dashboard 페이지 실제 데이터 연결
7. 주요 메뉴별 최소 목록 페이지 구현
8. README에 API 실행/검증 방법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* OpenAI API 호출
* 활동 보고서 생성 Agent
* 영수증 OCR
* 거래내역서 xls/xlsx 파싱
* 납부자/미납자 자동 매칭
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant 또는 pgvector 연동
* 복잡한 권한/로그인 시스템
* 고급 검색/필터 UI
* 대량 업로드 기능
* 실제 감사 규정 자동 판정

필요한 위치에는 TODO 주석만 남긴다.

---

## Backend 구현 요구사항

### 1. Router 구조

다음 Router를 구현한다.

```text
backend/app/routers/
  dashboard.py
  members.py
  activity_categories.py
  reference_reports.py
  activity_reports.py
  receipts.py
  transactions.py
  payment_records.py
  notifications.py
  settings.py
  files.py
```

`backend/app/main.py`에서 모든 router를 등록한다.

API prefix는 `/api`를 사용한다.

예시:

```text
/api/members
/api/activity-categories
/api/reference-reports
/api/activity-reports
/api/receipts
/api/transactions
/api/payment-records
/api/notifications
/api/settings
/api/files
/api/dashboard/summary
```

---

## 공통 API 규칙

### Pagination

목록 조회 API는 기본적으로 `skip`, `limit`를 지원한다.

예시:

```http
GET /api/members?skip=0&limit=50
```

기본값:

```text
skip = 0
limit = 50
```

최대 limit은 200 정도로 제한한다.

---

### Error 처리

개별 조회, 수정, 삭제 시 대상이 없으면 404를 반환한다.

예시:

```json
{
  "detail": "Member not found"
}
```

---

### 응답 Schema

Task 2에서 만든 Pydantic Schema를 적극 활용한다.

Read schema는 반드시 다음 설정을 포함해야 한다.

```python
model_config = ConfigDict(from_attributes=True)
```

---

## API 상세 요구사항

### 1. Dashboard API

파일:

```text
backend/app/routers/dashboard.py
```

API:

```http
GET /api/dashboard/summary
```

응답 예시:

```json
{
  "total_members": 5,
  "active_members": 5,
  "total_activity_categories": 9,
  "total_reference_reports": 0,
  "total_activity_reports": 0,
  "draft_reports": 0,
  "total_receipts": 0,
  "pending_receipts": 0,
  "total_transactions": 0,
  "total_deposit_amount": 0,
  "total_withdraw_amount": 0,
  "total_payment_records": 0,
  "unpaid_count": 0,
  "unread_notifications": 0
}
```

계산 기준:

* total_members: 전체 members count
* active_members: status가 `"active"`인 members count
* total_activity_categories: activity_categories count
* total_reference_reports: reference_reports count
* total_activity_reports: activity_reports count
* draft_reports: activity_reports.status == `"draft"`
* total_receipts: receipts count
* pending_receipts: receipts.evidence_status == `"pending"` 또는 need_check == true
* total_transactions: bank_transactions count
* total_deposit_amount: bank_transactions.deposit_amount 합계
* total_withdraw_amount: bank_transactions.withdraw_amount 합계
* total_payment_records: payment_records count
* unpaid_count: payment_records.status == `"unpaid"`
* unread_notifications: notifications.is_read == false

---

### 2. Members API

파일:

```text
backend/app/routers/members.py
```

API:

```http
GET /api/members
POST /api/members
GET /api/members/{member_id}
PATCH /api/members/{member_id}
DELETE /api/members/{member_id}
```

요구사항:

* `GET /api/members`는 `skip`, `limit`, `status`, `q`를 지원한다.
* `q`는 이름, 학번, 학과 검색에 사용한다.
* `DELETE`는 실제 삭제하지 않고 `status = "inactive"`로 변경한다.
* 중복 student_id가 있으면 400을 반환한다.

---

### 3. Activity Categories API

파일:

```text
backend/app/routers/activity_categories.py
```

API:

```http
GET /api/activity-categories
POST /api/activity-categories
GET /api/activity-categories/{category_id}
PATCH /api/activity-categories/{category_id}
DELETE /api/activity-categories/{category_id}
```

요구사항:

* name은 unique로 관리한다.
* 중복 name 생성 시 400을 반환한다.
* 카테고리 삭제 시 실제 삭제해도 되지만, 참조 중인 데이터가 있으면 DB 오류가 나지 않도록 예외 처리한다.

---

### 4. Reference Reports API

파일:

```text
backend/app/routers/reference_reports.py
```

API:

```http
GET /api/reference-reports
POST /api/reference-reports
GET /api/reference-reports/{reference_id}
PATCH /api/reference-reports/{reference_id}
DELETE /api/reference-reports/{reference_id}
```

요구사항:

* `category_id` 필터 지원
* `q` 검색 지원
* title, content 기준 검색
* category_id가 존재하지 않으면 400 또는 404 반환

---

### 5. Activity Reports API

파일:

```text
backend/app/routers/activity_reports.py
```

API:

```http
GET /api/activity-reports
POST /api/activity-reports
GET /api/activity-reports/{report_id}
PATCH /api/activity-reports/{report_id}
DELETE /api/activity-reports/{report_id}
```

요구사항:

* `category_id`, `status`, `q` 필터 지원
* DELETE는 실제 삭제 대신 `status = "archived"`로 변경한다.
* 생성 시 참석자 연결은 이번 Task에서는 필수 구현하지 않아도 된다.
* 참석자 연결은 TODO 주석으로 남긴다.

---

### 6. Receipts API

파일:

```text
backend/app/routers/receipts.py
```

API:

```http
GET /api/receipts
POST /api/receipts
GET /api/receipts/{receipt_id}
PATCH /api/receipts/{receipt_id}
DELETE /api/receipts/{receipt_id}
```

요구사항:

* `activity_report_id`, `evidence_status`, `need_check` 필터 지원
* amount는 integer로 처리
* 이번 Task에서는 OCR 분석을 하지 않는다.
* OCR 분석은 TODO 주석만 남긴다.

---

### 7. Bank Transactions API

파일:

```text
backend/app/routers/transactions.py
```

API:

```http
GET /api/transactions
POST /api/transactions
GET /api/transactions/{transaction_id}
PATCH /api/transactions/{transaction_id}
DELETE /api/transactions/{transaction_id}
```

요구사항:

* `match_status`, `payment_type`, `matched_member_id` 필터 지원
* 입금/출금 금액은 integer로 처리
* 이번 Task에서는 xls/xlsx 파싱을 구현하지 않는다.
* 거래내역서 파싱은 TODO 주석만 남긴다.

---

### 8. Payment Records API

파일:

```text
backend/app/routers/payment_records.py
```

API:

```http
GET /api/payment-records
POST /api/payment-records
GET /api/payment-records/{payment_id}
PATCH /api/payment-records/{payment_id}
DELETE /api/payment-records/{payment_id}
```

요구사항:

* `member_id`, `period`, `status`, `payment_type` 필터 지원
* member_id가 존재하지 않으면 400 또는 404 반환
* transaction_id가 존재하지 않으면 400 또는 404 반환

---

### 9. Notifications API

파일:

```text
backend/app/routers/notifications.py
```

API:

```http
GET /api/notifications
POST /api/notifications
GET /api/notifications/{notification_id}
PATCH /api/notifications/{notification_id}
PATCH /api/notifications/{notification_id}/read
PATCH /api/notifications/read-all
DELETE /api/notifications/{notification_id}
```

요구사항:

* `is_read`, `type`, `severity` 필터 지원
* read API는 `is_read = true`로 변경
* read-all API는 모든 알림을 읽음 처리

---

### 10. Settings API

파일:

```text
backend/app/routers/settings.py
```

API:

```http
GET /api/settings
POST /api/settings
GET /api/settings/{key}
PATCH /api/settings/{key}
DELETE /api/settings/{key}
```

요구사항:

* key는 unique
* value는 JSON
* 기본 회비 금액, 납부 기간 등을 저장하는 용도로 사용

---

### 11. Files API

파일:

```text
backend/app/routers/files.py
```

API:

```http
POST /api/files/upload
GET /api/files
GET /api/files/{file_id}
DELETE /api/files/{file_id}
```

요구사항:

* 업로드 파일은 `backend/uploads` 또는 설정된 `UPLOAD_DIR`에 저장한다.
* 저장 파일명은 UUID 기반으로 충돌을 방지한다.
* original_filename, stored_path, mime_type, file_type을 uploaded_files 테이블에 저장한다.
* Windows 경로 하드코딩 금지
* pathlib.Path 사용
* 이번 Task에서는 파일 내용 분석은 하지 않는다.

---

## Frontend 구현 요구사항

### 1. API Client 정리

파일:

```text
frontend/lib/api.ts
```

요구사항:

* `NEXT_PUBLIC_API_BASE_URL` 사용
* 공통 `apiFetch` 함수 구현
* 에러 처리 최소 구현
* 주요 API 함수 구현

필수 함수 예시:

```ts
getDashboardSummary()
getMembers()
getActivityCategories()
getReferenceReports()
getActivityReports()
getReceipts()
getTransactions()
getPaymentRecords()
getNotifications()
getSettings()
```

POST/PATCH/DELETE 함수는 기본적인 형태만 구현해도 된다.

---

### 2. Dashboard 실제 데이터 연결

파일:

```text
frontend/app/dashboard/page.tsx
```

요구사항:

* `/api/dashboard/summary` 호출
* 실제 통계 카드 표시
* 로딩 상태 표시
* 에러 상태 표시
* 기존 placeholder 카드 중 일부는 실제 count 카드로 변경

표시할 카드:

* 전체 부원 수
* 활동중 부원 수
* 활동 카테고리 수
* 활동 보고서 수
* 작성중 보고서 수
* 영수증 수
* 확인 필요 영수증 수
* 거래내역 수
* 총 입금액
* 총 출금액
* 미납 건수
* 읽지 않은 알림 수

---

### 3. 주요 메뉴별 최소 목록 페이지 구현

이번 Task에서는 복잡한 CRUD UI를 만들지 않는다.

다만 다음 페이지에서 실제 API 목록 조회는 가능해야 한다.

```text
/frontend/app/members/page.tsx
/frontend/app/activities/page.tsx
/frontend/app/references/page.tsx
/frontend/app/receipts/page.tsx
/frontend/app/transactions/page.tsx
/frontend/app/payments/page.tsx
/frontend/app/notifications/page.tsx
/frontend/app/settings/page.tsx
```

각 페이지 요구사항:

* 페이지 제목
* 간단한 설명
* API에서 목록 조회
* 간단한 테이블 또는 카드 목록 표시
* 로딩 상태
* 에러 상태
* 데이터가 없을 때 empty state 표시

이번 Task에서는 상세한 등록/수정 폼은 필수 구현하지 않는다.
등록/수정 UI는 Task 4 이후에서 구현한다.

---

## Backend 파일 구조 예상

```text
backend/app/
  routers/
    dashboard.py
    members.py
    activity_categories.py
    reference_reports.py
    activity_reports.py
    receipts.py
    transactions.py
    payment_records.py
    notifications.py
    settings.py
    files.py
```

필요하다면 다음 service 파일을 추가할 수 있다.

```text
backend/app/services/
  file_storage.py
```

---

## Frontend 파일 구조 예상

```text
frontend/app/
  dashboard/page.tsx
  members/page.tsx
  activities/page.tsx
  references/page.tsx
  receipts/page.tsx
  transactions/page.tsx
  payments/page.tsx
  notifications/page.tsx
  settings/page.tsx

frontend/lib/
  api.ts
```

공통 UI가 필요하면 다음을 추가할 수 있다.

```text
frontend/components/ui/
  DataTable.tsx
  EmptyState.tsx
  LoadingState.tsx
  ErrorState.tsx
```

---

## README 업데이트

README에 다음 내용을 추가한다.

### API 검증 예시

```bash
curl http://localhost:8000/api/dashboard/summary
curl http://localhost:8000/api/members
curl http://localhost:8000/api/activity-categories
```

### 파일 업로드 테스트 예시

WSL/Linux:

```bash
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@sample.txt" \
  -F "file_type=other"
```

Windows PowerShell에서는 curl alias 문제가 있을 수 있으므로 다음을 안내한다.

```powershell
curl.exe -X POST http://localhost:8000/api/files/upload -F "file=@sample.txt" -F "file_type=other"
```

---

## 실행 검증

가능하면 다음을 실행해 검증한다.

```bash
docker compose up -d db
cd backend
alembic upgrade head
python -m app.scripts.seed
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
http://localhost:8000/api/health
http://localhost:8000/api/dashboard/summary
http://localhost:8000/api/members
http://localhost:8000/api/activity-categories
http://localhost:3000/dashboard
http://localhost:3000/members
```

---

## 완료 기준

Task 3는 다음을 모두 만족해야 완료로 본다.

1. 주요 테이블 CRUD API가 구현되어 있다.
2. `/api/dashboard/summary`가 실제 DB count와 합계를 반환한다.
3. 파일 업로드 API가 동작하고 uploaded_files 테이블에 메타데이터가 저장된다.
4. notifications 읽음 처리 API가 동작한다.
5. 프론트 `lib/api.ts`에서 백엔드 API 호출 함수가 정리되어 있다.
6. `/dashboard` 페이지가 실제 summary 데이터를 표시한다.
7. 주요 메뉴 페이지에서 최소 목록 조회가 가능하다.
8. seed 데이터 기준으로 members와 activity_categories 목록이 프론트에서 보인다.
9. README에 API 검증 방법이 추가되어 있다.
10. 이번 Task에서 AI, OCR, 거래내역서 파싱, 납부 매칭, n8n, Notion, Slack 기능은 구현되지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 3 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 구현된 Backend API
- ...

3. 구현된 Frontend 페이지
- ...

4. Dashboard Summary 결과
- ...

5. 파일 업로드 API 상태
- ...

6. 실행 검증 결과
- docker compose up -d db:
- alembic upgrade head:
- python -m app.scripts.seed:
- backend compile/test:
- frontend build:
- 주요 URL 확인:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

9. 다음 Task에서 해야 할 일
- Task 4: 부원/활동 카테고리/레퍼런스/보고서 CRUD UI 구현
```
