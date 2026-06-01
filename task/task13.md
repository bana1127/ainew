# Task 13. 활동 보고서 카드형 UX, 통합 테스트, 외부 배포 준비

## 목표

ClubAgent의 핵심 기능을 실제 사용과 데모에 적합한 형태로 정리한다.

이번 Task의 목표는 다음이다.

```text
활동 보고서를 카드형으로 보기 쉽게 정리
→ 보고서를 클릭하면 바로 상세 확인
→ 복사, 다운로드, 보관 처리 가능
→ 전체 기능 흐름 통합 테스트
→ 로컬/외부 배포 API 연결 구조 정리
→ agent.banawy.store 외부 도메인 배포 준비
```

이번 Task는 기능을 새로 크게 늘리는 작업이 아니라, 지금까지 만든 기능을 실제 사용과 발표 데모에 맞게 정리하는 작업이다.

---

## 전제 조건

Task 1~12가 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

* 전역 AppShell
* 브랜드 로고 적용
* Dashboard
* AI 작업실 `/assistant`
* Members
* Activities
* Reports
* References
* Receipts
* Transactions
* Payments
* Notifications
* Settings
* 활동 보고서 생성 Agent
* 영수증 분석 Agent
* 거래내역서 파서
* 납부 매칭 기능
* Assistant 결과 카드 및 확인 후 반영 UX

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. 활동 보고서 카드형 목록 UI 구현
2. 활동 보고서 상세 모달 또는 Drawer 구현
3. 보고서 본문 복사 기능
4. 보고서 Markdown/Text 다운로드 기능
5. 보고서 보관/목록 제외 기능 정리
6. Reports/Activities 페이지 관계 정리
7. 통합 테스트용 샘플 데이터 정리
8. 주요 기능 시나리오 점검
9. 프론트 API base URL 구조 정리
10. 로컬 개발용 `/api → localhost:8001` 연결 정리
11. 외부 배포용 `agent.banawy.store` 연결 준비
12. README에 실행/배포/데모 절차 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* 새로운 Agent 기능
* LLM 기반 Intent Classifier
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* 로그인/권한 시스템
* DB 스키마 대규모 변경
* 기존 거래내역서 파서 재구현
* 기존 영수증 분석 로직 재구현
* 기존 납부 매칭 알고리즘 재구현

필요한 위치에는 TODO 주석만 남긴다.

---

# Part A. 활동 보고서 카드형 UX 구현

## 1. 현재 문제

활동 보고서가 목록 또는 폼 중심으로 되어 있으면, 실제 사용자가 작성된 보고서를 빠르게 훑어보기 어렵다.

원하는 방향:

```text
보고서가 카드처럼 정리됨
→ 제목, 날짜, 카테고리, 상태가 한눈에 보임
→ 클릭하면 상세 내용 확인
→ 바로 복사 가능
→ 외부 제출용으로 Markdown/Text 다운로드 가능
→ 필요 없으면 보관 처리
```

---

## 2. 적용 페이지

우선 다음 페이지를 보강한다.

```text
frontend/app/reports/page.tsx
frontend/app/activities/page.tsx
```

권장 구조:

```text
/reports
→ 활동 보고서 작성/AI 생성/초안 관리 중심

/activities
→ 생성된 활동 보고서 카드형 갤러리 및 관리 중심
```

다만 기존 구조가 반대라면, 현재 프로젝트 구조에 맞춰 자연스럽게 정리한다.

---

## 3. 활동 보고서 카드 그리드

활동 보고서 목록을 카드형 그리드로 표시한다.

카드 표시 항목:

```text
- 보고서 제목
- 활동 카테고리
- 활동일
- 장소
- 상태 badge
- 참석자 수
- 본문 미리보기 2~3줄
- 생성일 또는 수정일
```

카드 스타일:

```text
- 2~3열 그리드
- 흰색 카드
- 얇은 border
- 부드러운 shadow
- rounded-2xl
- hover 시 살짝 떠오르는 느낌
- 과한 색상 사용 금지
```

상태 badge:

```text
draft → 초안
generated → 생성됨
confirmed → 확정
archived → 보관
```

---

## 4. 카드 클릭 시 상세 모달/Drawer

카드를 클릭하면 보고서 상세를 바로 확인할 수 있어야 한다.

구현 방식은 둘 중 하나를 선택한다.

```text
1순위: 오른쪽 Drawer
2순위: 중앙 Modal
```

상세 화면 표시 항목:

```text
- 제목
- 카테고리
- 활동일
- 장소
- 상태
- 참석자
- input_text
- generated_content
- final_content
- 생성일
- 수정일
```

본문 우선순위:

```text
final_content가 있으면 final_content 표시
없으면 generated_content 표시
없으면 input_text 표시
```

---

## 5. 보고서 액션 버튼

상세 모달/Drawer에는 다음 버튼을 제공한다.

```text
- 본문 복사
- Markdown 다운로드
- Text 다운로드
- 수정하러 가기
- 보관 처리
- 닫기
```

### 본문 복사

브라우저 Clipboard API를 사용한다.

```ts
navigator.clipboard.writeText(content)
```

성공 시 짧은 안내 문구를 표시한다.

예시:

```text
보고서 본문을 클립보드에 복사했습니다.
```

---

### Markdown 다운로드

보고서를 `.md` 파일로 다운로드한다.

파일명 예시:

```text
activity-report-2026-05-30-ai-study.md
```

Markdown 형식 예시:

```markdown
# 5월 AI 스터디 활동 보고서

- 활동일: 2026-05-30
- 장소: 동아리방
- 카테고리: 정기 모임 / 스터디
- 상태: 생성됨

## 본문

...
```

---

### Text 다운로드

보고서를 `.txt` 파일로 다운로드한다.

파일명 예시:

```text
activity-report-2026-05-30-ai-study.txt
```

---

### 보관 처리

보관 버튼은 기존 activity_reports DELETE 또는 PATCH API를 사용한다.

동작:

```text
status = archived
```

실제 삭제하지 않는다.

보관 후:

```text
- 카드 목록에서 즉시 제거하거나
- 상태 필터가 archived가 아닐 때 숨김 처리
```

---

## 6. 필터 및 검색

카드형 페이지에는 최소 필터를 제공한다.

```text
검색어
카테고리
상태
활동일 범위
```

기본 상태 필터:

```text
archived 제외
```

옵션:

```text
전체
초안
생성됨
확정
보관
```

---

## 7. Empty State

보고서가 없을 때는 다음처럼 보여준다.

```text
아직 활동 보고서가 없습니다.
AI 작업실에서 활동 설명이나 사진을 올려 보고서 초안을 만들어보세요.

[AI 작업실로 이동]
```

---

# Part B. 통합 테스트 및 샘플 데이터 정리

## 1. 샘플 데이터 목적

데모와 테스트를 위해 기본 데이터가 어느 정도 있어야 한다.

이번 Task에서는 seed 또는 별도 demo seed 스크립트를 추가할 수 있다.

권장 파일:

```text
backend/app/scripts/seed_demo.py
```

또는 기존 seed.py에 `--demo` 옵션을 추가한다.

복잡하면 별도 `seed_demo.py`를 만든다.

---

## 2. 데모 데이터 구성

데모 데이터는 실제 개인정보처럼 보이지 않는 샘플만 사용한다.

데모 부원:

```text
김가온
이도윤
박서연
최하준
정민서
윤지호
한서아
강도현
오하린
문시우
```

데모 활동 보고서:

```text
- 5월 AI 스터디
- 신입 부원 OT
- PBL-C 개발 회의
- 교내 공모전 준비 회의
```

데모 레퍼런스 보고서:

```text
- 정기 스터디 보고서 예시
- 프로젝트 회의 보고서 예시
- 신입 부원 OT 보고서 예시
```

데모 거래내역/영수증은 실제 파일을 만들기 어렵다면 DB seed 데이터로 최소 생성한다.

---

## 3. 데모 seed 실행 방식

실행 명령:

```bash
python -m app.scripts.seed_demo
```

요구사항:

```text
- 여러 번 실행해도 중복 생성되지 않음
- 기존 기본 seed와 충돌하지 않음
- 데모 활동 보고서가 카드형 목록에서 바로 보임
```

---

## 4. 데모 시나리오 문서

README 또는 별도 문서에 데모 흐름을 작성한다.

권장 파일:

```text
DEMO.md
```

데모 시나리오:

```text
1. Dashboard 접속
2. AI 작업실 접속
3. 활동 보고서 초안 생성
4. Activities 또는 Reports에서 카드형 보고서 확인
5. 보고서 클릭
6. 본문 복사
7. Markdown 다운로드
8. 거래내역서 업로드
9. 납부 매칭 실행
10. 영수증 분석
11. Dashboard에서 처리 상태 확인
```

---

# Part C. API 연결 구조 정리

## 1. 현재 문제

로컬 개발에서는 프론트가 백엔드 `localhost:8001`을 호출해야 한다.

외부 배포에서는 다음 도메인을 사용할 예정이다.

```text
agent.banawy.store
```

따라서 API 연결 구조를 명확히 해야 한다.

---

## 2. 권장 구조

프론트에서는 가능하면 직접 `http://localhost:8001`을 하드코딩하지 않는다.

프론트는 기본적으로 상대 경로 `/api`를 호출한다.

```text
frontend → /api/*
```

로컬 개발 시:

```text
Next.js rewrite
/api/* → http://127.0.0.1:8001/api/*
```

외부 배포 시:

```text
https://agent.banawy.store/api/*
→ reverse proxy
→ backend 127.0.0.1:8001/api/*
```

---

## 3. 프론트 환경변수 정리

`frontend/.env.example`에 다음을 정리한다.

```env
NEXT_PUBLIC_API_BASE_URL=/api
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

로컬 개발 기본값은 `/api`를 권장한다.

단, 기존 코드가 직접 `http://localhost:8001`을 쓰고 있다면 `NEXT_PUBLIC_API_BASE_URL`로 통일한다.

---

## 4. next.config.js rewrites 설정

로컬 개발에서 `/api`가 백엔드로 넘어가도록 rewrite를 설정한다.

파일:

```text
frontend/next.config.js
```

또는 프로젝트가 `.mjs`를 쓰면 해당 파일에 맞춘다.

예시:

```js
const nextConfig = {
  async rewrites() {
    const apiUrl = process.env.NEXT_API_PROXY_TARGET || "http://127.0.0.1:8001";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
```

추가 env:

```env
NEXT_API_PROXY_TARGET=http://127.0.0.1:8001
```

주의:

```text
NEXT_API_PROXY_TARGET은 서버 측 Next 설정에서 사용하는 값이므로 NEXT_PUBLIC 접두사가 필요 없다.
```

---

## 5. frontend/lib/api.ts 수정

`frontend/lib/api.ts`에서 API base를 다음 방식으로 정리한다.

```ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";
```

주의:

```text
- API_BASE_URL 끝의 slash 중복 제거
- fetch 경로가 /api/api/... 형태가 되지 않도록 처리
- 절대 URL과 상대 URL 모두 동작해야 함
```

---

## 6. 백엔드 CORS 정리

외부 도메인에서 직접 백엔드를 호출할 가능성이 있으므로 CORS 설정을 정리한다.

`backend/.env.example`에 다음을 추가 또는 정리한다.

```env
BACKEND_CORS_ORIGINS=http://localhost:3000,https://agent.banawy.store
```

`backend/app/core/config.py`와 `main.py`에서 CORS origins를 읽는 구조가 이미 있다면 유지하고, 없다면 최소 보강한다.

주의:

```text
- agent.banawy.store만 허용
- "*" 남발 금지
- 개발 환경에서만 localhost 허용
```

---

## 7. 외부 배포 reverse proxy 문서화

실제 배포 방식은 아직 확정하지 않아도 된다.

다만 README 또는 DEPLOY.md에 아래 예시를 작성한다.

권장 파일:

```text
DEPLOY.md
```

Nginx 예시:

```nginx
server {
    server_name agent.banawy.store;

    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

또는 프론트를 정적 빌드/PM2로 돌리는 방식은 TODO로 남긴다.

---

# Part D. 실행 명령 정리

루트에 실행 명령 문서가 있다면 업데이트한다.

권장 파일:

```text
실행 명령어.md
```

또는 README에 포함한다.

로컬 실행:

```powershell
cd C:\Users\wonseo\Desktop\AINEW
docker compose up -d db
```

Backend:

```powershell
cd C:\Users\wonseo\Desktop\AINEW\backend
.venv\Scripts\activate
alembic upgrade head
python -m app.scripts.seed
python -m app.scripts.seed_demo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Frontend:

```powershell
cd C:\Users\wonseo\Desktop\AINEW\frontend
npm install
npm run dev
```

---

# 실행 검증

가능하면 다음을 실행한다.

Backend:

```bash
cd backend
python -m compileall app
pytest
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

확인 URL:

```text
http://localhost:3000/dashboard
http://localhost:3000/assistant
http://localhost:3000/activities
http://localhost:3000/reports
http://localhost:3000/api/health
```

주의:

```text
/api/health가 Next rewrite를 통해 backend /api/health로 연결되어야 한다.
```

직접 백엔드 확인:

```text
http://localhost:8001/api/health
```

---

## 완료 기준

Task 13은 다음을 모두 만족해야 완료로 본다.

1. 활동 보고서가 카드형 그리드로 표시된다.
2. 활동 보고서 카드를 클릭하면 상세 모달 또는 Drawer가 열린다.
3. 상세 화면에서 보고서 본문을 복사할 수 있다.
4. 상세 화면에서 Markdown 다운로드가 가능하다.
5. 상세 화면에서 Text 다운로드가 가능하다.
6. 보고서를 보관 처리할 수 있다.
7. 보관된 보고서는 기본 목록에서 제외되거나 상태로 구분된다.
8. 데모용 seed 데이터가 추가되어 카드형 보고서를 바로 확인할 수 있다.
9. 데모 시나리오 문서가 추가되어 있다.
10. 프론트 API base URL이 `/api` 중심으로 정리되어 있다.
11. 로컬 개발에서 `/api`가 `127.0.0.1:8001` 백엔드로 rewrite된다.
12. 외부 배포 도메인 `agent.banawy.store` 기준 설정 문서가 추가되어 있다.
13. 백엔드 CORS에 `https://agent.banawy.store`가 반영되어 있다.
14. frontend build가 성공한다.
15. backend compile/test가 성공한다.
16. 이번 Task에서 새로운 Agent, n8n, Notion, Slack 기능은 구현하지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 13 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 활동 보고서 카드형 UX
- 카드 그리드:
- 상세 모달/Drawer:
- 복사:
- Markdown 다운로드:
- Text 다운로드:
- 보관 처리:

3. 데모 데이터 및 통합 테스트
- seed_demo:
- DEMO.md:
- 샘플 보고서:

4. API 연결 구조 정리
- NEXT_PUBLIC_API_BASE_URL:
- NEXT_API_PROXY_TARGET:
- next.config rewrite:
- CORS:
- 외부 도메인:

5. 외부 배포 준비
- DEPLOY.md:
- agent.banawy.store reverse proxy:
- 로컬/외부 차이:

6. 실행 검증 결과
- backend compile/test:
- frontend build:
- /api rewrite:
- 주요 URL 확인:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

9. 다음 Task에서 해야 할 일
- Task 14: n8n 자동 점검 API 및 내부 알림 자동화 구현
```
