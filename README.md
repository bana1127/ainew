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

## 문제 해결

- `docker` 명령을 찾을 수 없으면 Docker Desktop 설치와 PATH 설정, WSL2 integration을 확인하세요.
- `/api/health`에서 `"database": "unavailable"`이 나오면 `docker compose up -d db`로 DB 컨테이너가 실행 중인지 확인하세요.
- PowerShell에서 venv 활성화가 막히면 같은 터미널에서 `Set-ExecutionPolicy -Scope Process RemoteSigned`를 실행한 뒤 다시 시도하세요.
- 프론트엔드가 백엔드에 연결하지 못하면 `frontend/.env.local`에 `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`이 있는지 확인하세요.
- 실제 `.env`와 `.env.local`은 Git에 포함하지 않습니다. `.env.example`을 복사해서 사용하세요.

