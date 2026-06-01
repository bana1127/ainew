# ClubAgent 배포 가이드

## 구조 개요

```text
[브라우저]
    │
    ▼
[Next.js 프론트 :3000]
    │  /api/* 경로
    ▼
[Next.js Rewrite OR Nginx reverse proxy]
    │
    ▼
[FastAPI 백엔드 :8001]
    │
    ▼
[PostgreSQL :5432]
```

---

## 로컬 개발 구조

### API 흐름

```text
브라우저 → http://localhost:3000/api/health
  → Next.js rewrite (next.config.ts)
  → http://127.0.0.1:8001/api/health
```

### 환경변수

`frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001
```

`backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://clubagent:clubagent@localhost:5433/clubagent
BACKEND_CORS_ORIGINS=http://localhost:3000,https://agent.banawy.store
OPENAI_API_KEY=sk-...
OPENAI_MOCK_MODE=false
```

### 실행 순서

1. PostgreSQL:
```powershell
docker compose up -d db
```

2. 백엔드:
```powershell
cd backend
.venv\Scripts\activate
alembic upgrade head
python -m app.scripts.seed
python -m app.scripts.seed_demo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

3. 프론트엔드:
```powershell
cd frontend
npm install
npm run dev
```

---

## 외부 배포 — agent.banawy.store

### 구조

```text
https://agent.banawy.store/
  →  Next.js (127.0.0.1:3000)

https://agent.banawy.store/api/
  →  FastAPI (127.0.0.1:8001)
```

### Nginx 설정 예시

```nginx
server {
    listen 80;
    server_name agent.banawy.store;

    # HTTPS redirect
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name agent.banawy.store;

    ssl_certificate     /etc/letsencrypt/live/agent.banawy.store/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/agent.banawy.store/privkey.pem;

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
    }

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 프론트엔드 환경변수 (외부 배포)

`frontend/.env.production`:

```env
NEXT_PUBLIC_API_BASE_URL=
NEXT_PUBLIC_APP_URL=https://agent.banawy.store
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001
```

`NEXT_PUBLIC_API_BASE_URL`을 빈 값으로 두면 브라우저에서 `/api/*` 상대 경로를 사용하고,
Nginx가 `/api/` → `http://127.0.0.1:8001/api/`로 프록시합니다.

### 백엔드 환경변수 (외부 배포)

`backend/.env`:

```env
BACKEND_CORS_ORIGINS=https://agent.banawy.store
OPENAI_MOCK_MODE=false
OPENAI_API_KEY=sk-...
```

### 프론트 프로덕션 빌드

```bash
cd frontend
npm run build
npm start   # 또는 pm2 start npm -- start
```

---

## 로컬 vs 외부 배포 차이

| 항목 | 로컬 개발 | 외부 배포 |
|------|-----------|-----------|
| 프론트 URL | http://localhost:3000 | https://agent.banawy.store |
| 백엔드 URL | http://127.0.0.1:8001 | http://127.0.0.1:8001 (서버 내부) |
| API 경로 | Next.js rewrite | Nginx reverse proxy |
| HTTPS | 불필요 | Let's Encrypt 권장 |
| CORS origins | localhost:3000 | agent.banawy.store |

---

## TODO

- [ ] PM2 설정으로 프론트 자동 재시작
- [ ] GitHub Actions CI/CD 파이프라인 구성
- [ ] Let's Encrypt certbot 자동 갱신 설정
- [ ] 환경변수 시크릿 관리 (GitHub Secrets 또는 .env 비공개 설정)
