# Task 2. DB 스키마, Alembic 마이그레이션, Seed 데이터 구현

## 목표

Task 1에서 만든 ClubAgent 프로젝트 뼈대 위에 실제 서비스 데이터 구조를 구현한다.

이번 Task의 목표는 다음이다.

* SQLAlchemy 모델 구현
* Alembic 마이그레이션 설정
* PostgreSQL 테이블 생성
* 초기 seed 데이터 삽입
* DB 연결 검증
* 이후 CRUD API와 Agent 기능을 붙이기 쉬운 DB 기반 마련

이번 Task에서는 프론트엔드 화면 구현, CRUD API, AI Agent, OCR, 거래내역서 파싱, n8n, Notion, Slack 연동은 구현하지 않는다.

---

## 전제 조건

Task 1이 완료되어 있어야 한다.

Task 1 완료 기준:

* `backend/` 기본 FastAPI 구조 존재
* `frontend/` 기본 Next.js 구조 존재
* `docker-compose.yml` 존재
* PostgreSQL Docker 컨테이너 실행 가능
* `/api/health` API 존재
* `.env.example` 존재
* README에 실행 방법 작성 완료

---

## 이번 Task 구현 범위

이번 Task에서는 아래만 구현한다.

1. SQLAlchemy 모델 작성
2. Alembic 초기화 및 설정
3. 첫 번째 마이그레이션 생성
4. PostgreSQL 테이블 생성 가능하게 구성
5. seed 스크립트 작성
6. 초기 활동 카테고리, 샘플 부원, 기본 설정 데이터 삽입
7. DB 연결 확인용 간단한 API 또는 health 응답 보강
8. README에 마이그레이션 및 seed 실행 방법 추가

---

## 구현하지 말 것

이번 Task에서는 아래 기능을 구현하지 않는다.

* members CRUD API
* activity CRUD API
* receipts CRUD API
* transactions CRUD API
* payment records CRUD API
* notifications CRUD API
* 프론트엔드 상세 페이지 구현
* OpenAI API 호출
* 활동 보고서 생성 Agent
* 영수증 OCR
* 거래내역서 xls/xlsx 파싱
* 납부자/미납자 자동 매칭
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant 또는 pgvector 연동

필요한 위치에는 TODO 주석만 남긴다.

---

## DB 설계 원칙

### 공통 원칙

* 기본 키는 UUID 사용
* `created_at`, `updated_at`은 가능한 모든 주요 테이블에 포함
* 시간 필드는 timezone-aware datetime 사용
* PostgreSQL JSONB 또는 SQLAlchemy JSON 타입 사용
* FK 관계를 명확히 설정
* 나중에 CRUD API를 붙이기 쉽게 relationship 설정
* 삭제가 자주 일어날 데이터는 실제 삭제보다 status 기반 soft delete를 고려
* 금액은 float이 아니라 integer로 저장
* 문자열 상태값은 우선 string으로 관리하고, enum은 나중에 확장 가능하도록 둔다

---

## 구현할 테이블

### 1. members

부원 명부 테이블이다.

컬럼:

* id: UUID, primary key
* name: string, required
* student_id: string, nullable
* department: string, nullable
* phone: string, nullable
* email: string, nullable
* status: string, default `"active"`
* memo: text, nullable
* created_at: datetime
* updated_at: datetime

인덱스 권장:

* name
* student_id
* status

---

### 2. activity_categories

활동 카테고리 테이블이다.

컬럼:

* id: UUID, primary key
* name: string, required, unique
* description: text, nullable
* required_fields_json: JSON, nullable
* report_template: text, nullable
* created_at: datetime
* updated_at: datetime

초기 카테고리는 seed로 삽입한다.

---

### 3. reference_reports

기존 활동 보고서 레퍼런스 테이블이다.

컬럼:

* id: UUID, primary key
* category_id: FK activity_categories.id, nullable
* title: string, required
* content: text, required
* tags: JSON, nullable
* created_at: datetime
* updated_at: datetime

관계:

* activity_categories 1:N reference_reports

---

### 4. activity_reports

AI 또는 사용자가 작성한 활동 보고서 테이블이다.

컬럼:

* id: UUID, primary key
* category_id: FK activity_categories.id, nullable
* title: string, required
* activity_date: date, nullable
* location: string, nullable
* input_text: text, nullable
* generated_content: text, nullable
* final_content: text, nullable
* status: string, default `"draft"`
* created_at: datetime
* updated_at: datetime

상태 예시:

* draft
* generated
* confirmed
* archived

관계:

* activity_categories 1:N activity_reports
* activity_reports N:M members through activity_participants

---

### 5. activity_participants

활동 보고서와 부원 참여자를 연결하는 테이블이다.

컬럼:

* id: UUID, primary key
* activity_report_id: FK activity_reports.id, required
* member_id: FK members.id, required
* role: string, nullable
* created_at: datetime

관계:

* activity_reports 1:N activity_participants
* members 1:N activity_participants

제약 조건:

* 같은 activity_report_id, member_id 조합은 중복되지 않도록 unique constraint 권장

---

### 6. uploaded_files

업로드 파일 메타데이터 테이블이다.

컬럼:

* id: UUID, primary key
* original_filename: string, required
* stored_path: string, required
* mime_type: string, nullable
* file_type: string, nullable
* related_entity_type: string, nullable
* related_entity_id: UUID, nullable
* created_at: datetime

file_type 예시:

* image
* receipt
* bank_statement
* report_attachment
* other

---

### 7. receipts

영수증 및 지출 증빙 테이블이다.

컬럼:

* id: UUID, primary key
* activity_report_id: FK activity_reports.id, nullable
* file_id: FK uploaded_files.id, nullable
* receipt_date: date, nullable
* store_name: string, nullable
* amount: integer, default 0
* payment_method: string, nullable
* category: string, nullable
* evidence_status: string, default `"pending"`
* need_check: boolean, default false
* reason: text, nullable
* created_at: datetime
* updated_at: datetime

evidence_status 예시:

* pending
* valid
* need_check
* invalid

payment_method 예시:

* card
* online_card
* transfer_student
* transfer_company
* cash
* unknown

관계:

* activity_reports 1:N receipts
* uploaded_files 1:1 또는 1:N receipts

---

### 8. bank_transactions

은행 거래내역 테이블이다.

컬럼:

* id: UUID, primary key
* transaction_datetime: datetime, nullable
* transaction_type: string, nullable
* memo: string, nullable
* withdraw_amount: integer, default 0
* deposit_amount: integer, default 0
* balance: integer, nullable
* branch: string, nullable
* raw_json: JSON, nullable
* matched_member_id: FK members.id, nullable
* payment_type: string, nullable
* match_status: string, default `"unmatched"`
* created_at: datetime
* updated_at: datetime

match_status 예시:

* unmatched
* matched
* need_check
* excluded

payment_type 예시:

* membership_fee
* activity_fee
* refund
* interest
* other

관계:

* members 1:N bank_transactions

---

### 9. payment_records

부원별 납부 기록 테이블이다.

컬럼:

* id: UUID, primary key
* member_id: FK members.id, required
* period: string, required
* payment_type: string, default `"membership_fee"`
* required_amount: integer, default 0
* paid_amount: integer, default 0
* status: string, default `"unpaid"`
* transaction_id: FK bank_transactions.id, nullable
* created_at: datetime
* updated_at: datetime

status 예시:

* unpaid
* paid
* partial
* exempt
* need_check

관계:

* members 1:N payment_records
* bank_transactions 1:1 또는 1:N payment_records

제약 조건 권장:

* member_id, period, payment_type 조합 unique constraint

---

### 10. notifications

자체 웹페이지 내부 알림 테이블이다.

컬럼:

* id: UUID, primary key
* type: string, required
* title: string, required
* message: text, required
* severity: string, default `"info"`
* is_read: boolean, default false
* related_entity_type: string, nullable
* related_entity_id: UUID, nullable
* created_at: datetime

severity 예시:

* info
* warning
* error
* success

type 예시:

* payment
* receipt
* activity
* audit
* system

---

### 11. app_settings

서비스 설정 테이블이다.

컬럼:

* id: UUID, primary key
* key: string, unique, required
* value: JSON, nullable
* description: text, nullable
* created_at: datetime
* updated_at: datetime

초기 설정 예시:

* membership_fee_amount
* default_payment_period
* audit_warning_days
* receipt_check_enabled
* transaction_matching_threshold

---

## Backend 파일 구조

다음 파일을 구현 또는 수정한다.

```text
backend/
  app/
    models/
      __init__.py
      base.py
      member.py
      activity.py
      file.py
      receipt.py
      transaction.py
      payment.py
      notification.py
      setting.py

    schemas/
      __init__.py
      common.py
      member.py
      activity.py
      file.py
      receipt.py
      transaction.py
      payment.py
      notification.py
      setting.py

    core/
      database.py

    routers/
      health.py

    data/
      seed_categories.json
      seed_settings.json

    scripts/
      seed.py

  alembic/
    env.py
    versions/

  alembic.ini
```

기존 Task 1 구조와 충돌하지 않도록 필요한 경우 기존 구조에 맞춰 자연스럽게 병합한다.

---

## SQLAlchemy 모델 요구사항

### Base

`backend/app/models/base.py` 또는 기존 `core/database.py`의 Base를 사용한다.

Task 2에서는 Alembic autogenerate가 모든 모델을 인식해야 한다.

따라서 `backend/app/models/__init__.py`에서 모든 모델을 import한다.

예시:

```python
from app.models.member import Member
from app.models.activity import ActivityCategory, ReferenceReport, ActivityReport, ActivityParticipant
from app.models.file import UploadedFile
from app.models.receipt import Receipt
from app.models.transaction import BankTransaction
from app.models.payment import PaymentRecord
from app.models.notification import Notification
from app.models.setting import AppSetting
```

---

## Alembic 요구사항

Alembic을 설정한다.

필수 조건:

1. `alembic.ini` 생성
2. `alembic/env.py`가 프로젝트의 `Base.metadata`를 참조해야 함
3. `.env`의 `DATABASE_URL`을 사용할 수 있어야 함
4. autogenerate가 모델 변경사항을 감지할 수 있어야 함
5. 첫 번째 migration 파일 생성

마이그레이션 이름 예시:

```text
create_initial_clubagent_tables
```

실행 명령 예시:

```bash
alembic revision --autogenerate -m "create initial clubagent tables"
alembic upgrade head
```

Windows PowerShell 기준 명령도 README에 적는다.

---

## Seed 데이터 요구사항

### seed_categories.json

초기 활동 카테고리를 삽입한다.

카테고리 목록:

1. 정기 모임 / 스터디
2. 프로젝트 / 개발 활동
3. 세미나 / 특강
4. 대회 / 공모전
5. 신입 부원 모집 / OT
6. 운영 회의
7. 교류 행사
8. MT / 회식 / 친목
9. 물품 구매 / 행정 처리

각 카테고리는 다음 필드를 가진다.

* name
* description
* required_fields_json
* report_template

report_template은 간단한 기본 템플릿으로 작성한다.

예시:

```text
활동명:
활동 일시:
활동 장소:
참석자:
활동 목적:
주요 내용:
활동 결과:
향후 계획:
```

---

### seed_settings.json

초기 설정값을 삽입한다.

예시:

```json
[
  {
    "key": "membership_fee_amount",
    "value": { "amount": 30000 },
    "description": "기본 회비 금액"
  },
  {
    "key": "default_payment_period",
    "value": { "period": "2026-1" },
    "description": "기본 납부 기간"
  },
  {
    "key": "audit_warning_days",
    "value": { "days": 14 },
    "description": "감사 준비 알림 기준일"
  },
  {
    "key": "transaction_matching_threshold",
    "value": { "score": 0.8 },
    "description": "거래내역 부원명 매칭 기준 점수"
  }
]
```

---

### 샘플 부원 데이터

seed.py에서 샘플 부원 5명을 삽입한다.

예시 이름은 임의로 작성하되, 실제 개인정보처럼 보이지 않는 샘플 데이터를 사용한다.

예시:

* 김가온
* 이도윤
* 박서연
* 최하준
* 정민서

각 샘플 부원은 다음 값을 가진다.

* name
* student_id
* department
* status = active

student_id는 예시값을 사용한다.

---

## seed.py 요구사항

`backend/app/scripts/seed.py`를 작성한다.

필수 기능:

1. DB 세션 생성
2. 활동 카테고리 seed 삽입
3. app_settings seed 삽입
4. 샘플 부원 seed 삽입
5. 이미 존재하는 데이터는 중복 삽입하지 않음
6. 실행 결과를 콘솔에 출력

실행 예시:

```bash
python -m app.scripts.seed
```

중복 삽입 방지 기준:

* activity_categories: name 기준
* app_settings: key 기준
* members: student_id 기준

---

## Pydantic Schema 요구사항

이번 Task에서 CRUD API는 구현하지 않지만, 이후 Task를 위해 기본 schema를 작성한다.

각 주요 모델에 대해 다음 schema를 준비한다.

예시:

* MemberBase
* MemberCreate
* MemberUpdate
* MemberRead

다른 모델도 유사하게 구성한다.

Pydantic v2 기준으로 작성한다.

```python
model_config = ConfigDict(from_attributes=True)
```

---

## Health API 보강

`GET /api/health` 응답에 DB 연결 상태와 테이블 개수를 간단히 포함한다.

예시 응답:

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

DB 연결 실패 시 서버는 죽지 않고 다음처럼 응답한다.

```json
{
  "status": "ok",
  "app": "ClubAgent",
  "database": "unavailable",
  "tables": {}
}
```

---

## README 업데이트

README에 다음 내용을 추가한다.

### Alembic 마이그레이션 실행

WSL/Linux:

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "create initial clubagent tables"
alembic upgrade head
```

Windows PowerShell:

```powershell
cd backend
.venv\Scripts\activate
alembic revision --autogenerate -m "create initial clubagent tables"
alembic upgrade head
```

### Seed 실행

WSL/Linux:

```bash
cd backend
source .venv/bin/activate
python -m app.scripts.seed
```

Windows PowerShell:

```powershell
cd backend
.venv\Scripts\activate
python -m app.scripts.seed
```

---

## 완료 기준

Task 2는 다음을 모두 만족해야 완료로 본다.

1. SQLAlchemy 모델이 모두 구현되어 있다.
2. Alembic이 `Base.metadata`를 정상 인식한다.
3. 첫 번째 migration으로 모든 테이블을 생성할 수 있다.
4. `alembic upgrade head` 실행 시 PostgreSQL에 테이블이 생성된다.
5. `python -m app.scripts.seed` 실행 시 초기 카테고리, 설정, 샘플 부원이 삽입된다.
6. seed 스크립트를 여러 번 실행해도 중복 삽입되지 않는다.
7. `/api/health`에서 DB 연결 상태와 일부 테이블 count를 확인할 수 있다.
8. README에 migration, seed 실행 방법이 추가되어 있다.
9. Windows/WSL 환경 모두에서 실행 가능하도록 경로 처리가 되어 있다.
10. 이번 Task에서 CRUD API, AI, OCR, 거래내역서 파싱, n8n, Notion, Slack 기능은 구현되지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 2 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 구현된 DB 모델
- ...

3. Alembic 마이그레이션 상태
- ...

4. Seed 데이터
- ...

5. 실행 방법
- ...

6. 확인해야 할 URL 또는 명령
- ...

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. 다음 Task에서 해야 할 일
- Task 3: 대시보드 API 및 기본 CRUD API/프론트 페이지 연결
```
