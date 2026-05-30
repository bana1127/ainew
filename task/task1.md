# Task 1. ClubAgent 프로젝트 뼈대 및 실행 환경 구축

## 목표

ClubAgent 프로젝트의 1차 기반을 구축한다.

이번 Task의 목표는 실제 기능 구현이 아니라, 앞으로 자체 웹페이지, DB, 백엔드 API, Agent, n8n 자동화를 붙일 수 있는 기본 프로젝트 구조를 안정적으로 만드는 것이다.

이번 Task에서는 다음만 구현한다.

* Next.js 프론트엔드 기본 프로젝트
* FastAPI 백엔드 기본 프로젝트
* PostgreSQL Docker 컨테이너
* docker-compose 실행 환경
* 백엔드 health check API
* 프론트 기본 대시보드 placeholder
* 프론트에서 백엔드 health API 호출 확인
* Windows 11 + WSL2 + Docker Desktop 환경에서 실행 가능한 구조
* README 실행 방법 작성

AI 기능, Agent 기능, OCR, 거래내역서 파싱, Notion, Slack, n8n 연동은 이번 Task에서 구현하지 않는다.

---

## 개발 환경

이 프로젝트는 Windows 11 PC에서 개발한다.

기준 환경은 다음과 같다.

* Windows 11
* WSL2
* Docker Desktop
* Node.js
* Python 3.10 이상
* PostgreSQL은 Docker 컨테이너로 실행

주의사항:

* Windows 절대경로를 코드에 하드코딩하지 말 것
* 모든 경로는 상대경로 또는 pathlib.Path 기반으로 작성할 것
* backend/uploads 폴더는 앱 시작 시 없으면 자동 생성할 것
* .env.example은 제공하되 실제 .env는 gitignore에 포함할 것
* README에는 Windows PowerShell 기준 실행 방법과 WSL 기준 실행 방법을 모두 작성할 것

---

## 기술 스택

### Frontend

* Next.js App Router
* TypeScript
* Tailwind CSS
* 기본 관리자 대시보드 레이아웃

### Backend

* FastAPI
* Uvicorn
* Pydantic Settings
* SQLAlchemy 2.x
* psycopg
* Alembic은 이번 Task에서 설치만 해두고 실제 마이그레이션은 Task 2에서 진행

### Database

* PostgreSQL
* Docker Compose로 실행

---

## 프로젝트 구조

다음 구조로 프로젝트를 생성한다.

```text
clubagent/
  backend/
    app/
      main.py
      core/
        config.py
        database.py
      routers/
        health.py
      models/
        __init__.py
      schemas/
        __init__.py
      services/
        __init__.py
      agents/
        __init__.py
      utils/
        __init__.py
      data/
      uploads/
    alembic/
    requirements.txt
    .env.example
    .gitignore

  frontend/
    app/
      layout.tsx
      page.tsx
      dashboard/
        page.tsx
    components/
      layout/
        Sidebar.tsx
        Header.tsx
        AppShell.tsx
      ui/
        StatCard.tsx
    lib/
      api.ts
    package.json
    .env.example
    .gitignore

  docker-compose.yml
  .gitignore
  README.md
```

---

## Backend 구현 요구사항

### 1. FastAPI 앱 생성

`backend/app/main.py`에 FastAPI 앱을 생성한다.

필수 사항:

* CORS 설정
* `/api/health` 라우터 연결
* 앱 시작 시 `backend/app/uploads` 또는 `backend/uploads` 폴더 자동 생성
* 기본 root API는 선택사항

예시 응답:

```json
{
  "service": "ClubAgent API",
  "status": "running"
}
```

---

### 2. 환경변수 설정

`backend/app/core/config.py`를 만든다.

Pydantic Settings를 사용한다.

필수 환경변수:

```env
APP_NAME=ClubAgent
APP_ENV=development
BACKEND_CORS_ORIGINS=http://localhost:3000
DATABASE_URL=postgresql+psycopg://clubagent:clubagent@localhost:5433/clubagent
UPLOAD_DIR=uploads
```

Docker 내부에서 백엔드를 같이 실행할 때를 고려해 다음 DATABASE_URL도 README에 설명한다.

```env
DATABASE_URL=postgresql+psycopg://clubagent:clubagent@db:5432/clubagent
```

---

### 3. DB 연결 파일 생성

`backend/app/core/database.py`를 만든다.

이번 Task에서는 실제 모델과 테이블 생성은 하지 않는다.

다만 다음을 미리 구성한다.

* SQLAlchemy engine
* SessionLocal
* Base
* get_db dependency

Task 2에서 models를 추가할 수 있게 구조만 잡는다.

---

### 4. Health API 구현

`backend/app/routers/health.py`를 만든다.

필수 API:

```http
GET /api/health
```

응답 예시:

```json
{
  "status": "ok",
  "app": "ClubAgent",
  "database": "configured"
}
```

가능하면 DB 연결 확인도 포함한다.

DB 연결 확인이 실패해도 서버가 죽지 않고 다음처럼 응답하게 한다.

```json
{
  "status": "ok",
  "app": "ClubAgent",
  "database": "unavailable"
}
```

---

### 5. requirements.txt

`backend/requirements.txt`에 다음 패키지를 포함한다.

```text
fastapi
uvicorn[standard]
pydantic-settings
sqlalchemy
psycopg[binary]
alembic
python-multipart
```

---

## Frontend 구현 요구사항

### 1. Next.js 프로젝트 생성

`frontend/` 아래에 Next.js App Router 기반 프로젝트를 만든다.

필수 사용:

* TypeScript
* Tailwind CSS
* App Router

---

### 2. 기본 레이아웃 구현

관리자 대시보드 형태로 구성한다.

필수 컴포넌트:

```text
components/layout/AppShell.tsx
components/layout/Sidebar.tsx
components/layout/Header.tsx
components/ui/StatCard.tsx
```

Sidebar 메뉴는 다음을 미리 넣는다.

```text
Dashboard
Members
Activities
References
Reports
Receipts
Transactions
Payments
Notifications
Settings
```

아직 각 페이지는 구현하지 않아도 된다.
이번 Task에서는 Dashboard만 실제 페이지로 만든다.

---

### 3. 메인 페이지 redirect

`/` 접속 시 `/dashboard`로 이동하게 한다.

---

### 4. Dashboard placeholder 페이지

`/dashboard` 페이지를 만든다.

표시할 내용:

* ClubAgent 관리자 대시보드 제목
* 서비스 설명 한 줄
* 준비 중인 기능 카드

카드 예시:

```text
부원 관리
활동 보고서
영수증 정리
거래내역 분석
납부 체크
자동 알림
```

---

### 5. 백엔드 health API 호출

`frontend/lib/api.ts`를 만든다.

환경변수:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`/dashboard`에서 백엔드 `/api/health`를 호출하고 결과를 표시한다.

표시 예시:

```text
Backend API: connected
Database: configured
```

API 호출 실패 시:

```text
Backend API: disconnected
```

---

## Docker Compose 요구사항

루트에 `docker-compose.yml`을 만든다.

이번 Task에서는 최소한 PostgreSQL 컨테이너는 반드시 포함한다.

### PostgreSQL

서비스 이름:

```text
db
```

환경변수:

```env
POSTGRES_USER=clubagent
POSTGRES_PASSWORD=clubagent
POSTGRES_DB=clubagent
```

포트:

```text
5433:5432
```

5432는 Windows 로컬 PostgreSQL과 충돌할 수 있으므로 외부 포트는 5433으로 설정한다.

볼륨:

```text
postgres_data
```

---

### 선택사항: backend/frontend 컨테이너

가능하면 backend와 frontend도 docker-compose에 포함한다.

다만 개발 편의를 위해 README에는 두 가지 실행 방식을 모두 적는다.

1. DB만 Docker로 실행하고 백엔드/프론트는 로컬에서 실행
2. 전체 서비스를 Docker Compose로 실행

---

## .gitignore 요구사항

루트 `.gitignore`에 다음을 포함한다.

```text
.env
.env.*
!.env.example
__pycache__/
*.pyc
.venv/
node_modules/
.next/
dist/
build/
uploads/
postgres_data/
```

단, `uploads/.gitkeep` 파일을 두어 uploads 폴더 구조는 유지한다.

---

## README 작성 요구사항

README에는 다음 내용을 포함한다.

### 1. 프로젝트 설명

ClubAgent는 동아리 운영을 위한 자체 웹 기반 AI 운영 비서 프로젝트이다.

이번 버전은 다음 기능을 붙이기 위한 기반 구조이다.

* 자체 웹페이지
* FastAPI 백엔드
* PostgreSQL DB
* 활동 보고서 Agent
* 영수증 분석 Agent
* 거래내역서 분석 Agent
* n8n 자동화

이번 Task에서는 기반 구조만 구현한다.

---

### 2. Windows PowerShell 실행 방법

예시:

```powershell
docker compose up -d db

cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd ..\frontend
npm install
copy .env.example .env.local
npm run dev
```

---

### 3. WSL 실행 방법

예시:

```bash
docker compose up -d db

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd ../frontend
npm install
cp .env.example .env.local
npm run dev
```

---

### 4. 접속 주소

```text
Frontend: http://localhost:3000
Backend: http://localhost:8000
Health API: http://localhost:8000/api/health
PostgreSQL: localhost:5433
```

---

## 완료 기준

Task 1은 다음 조건을 모두 만족해야 완료로 본다.

1. `docker compose up -d db` 실행 시 PostgreSQL 컨테이너가 정상 실행된다.
2. `cd backend && uvicorn app.main:app --reload` 실행 시 FastAPI 서버가 정상 실행된다.
3. `http://localhost:8000/api/health` 접속 시 JSON 응답이 나온다.
4. `cd frontend && npm run dev` 실행 시 Next.js 서버가 정상 실행된다.
5. `http://localhost:3000` 접속 시 `/dashboard`로 이동한다.
6. Dashboard에서 백엔드 health API 연결 상태가 표시된다.
7. 프로젝트 전체 구조가 이후 Task 2에서 DB 모델과 CRUD API를 추가하기 쉬운 형태로 되어 있다.
8. Windows/WSL 환경에서 경로 문제가 발생하지 않도록 상대경로와 pathlib.Path를 사용한다.
9. README에 Windows PowerShell과 WSL 실행 방법이 모두 작성되어 있다.
10. 이번 Task에서는 AI, OCR, 거래내역서 파싱, Notion, Slack, n8n 기능을 구현하지 않는다.

---

## 이번 Task에서 구현하지 말 것

다음은 절대 구현하지 말고 TODO 주석만 남긴다.

* DB 모델 상세 구현
* CRUD API
* 활동 보고서 생성 AI
* 영수증 OCR
* 거래내역서 파싱
* 납부 매칭
* Notion 연동
* Slack 연동
* n8n 워크플로우
* Qdrant 또는 pgvector

---

## 기대 결과

Task 1 완료 후에는 다음 상태가 되어야 한다.

```text
프론트엔드 접속 가능
백엔드 health API 응답 가능
PostgreSQL 컨테이너 실행 가능
프론트에서 백엔드 연결 상태 확인 가능
프로젝트 폴더 구조 완성
README 실행 방법 정리
```

이 상태를 기반으로 Task 2에서 DB 모델과 Alembic 마이그레이션, 기본 시드 데이터를 구현할 예정이다.
