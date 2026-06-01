# Task 9. 고급 디자인 시스템 및 전역 레이아웃 정리

## 목표

ClubAgent의 전체 UI를 기능 테스트용 관리자 화면에서 벗어나, 실제 서비스처럼 보이는 고급스럽고 절제된 디자인으로 정리한다.

이번 Task의 핵심은 다음이다.

```text
모든 페이지에 일관된 전역 레이아웃 적용
→ 사이드바/헤더 누락 문제 해결
→ 디자인 토큰 정리
→ 카드/버튼/테이블/배지 스타일 통일
→ 대시보드 1차 재구성
→ 주요 페이지의 간격과 정보 배치 개선
```

이번 Task는 기능 추가가 아니라, **기존 기능을 더 잘 보이고 더 편하게 쓰도록 만드는 UI/UX 정리 작업**이다.

---

## 전제 조건

Task 1~8이 완료되어 있어야 한다.

현재 구현된 주요 기능:

* 부원 관리
* 활동 카테고리 관리
* 레퍼런스 관리
* 활동 보고서 생성
* 거래내역서 업로드 및 파싱
* 납부 매칭 및 미납자 판별
* 영수증 분석 및 감사 규정 체크
* 대시보드
* 사이드바/헤더 일부 구현

---

## 현재 문제

현재 화면은 기능 테스트용으로는 동작하지만, 다음 문제가 있다.

```text
1. 대시보드가 실사용용으로 부족함
2. 일부 페이지에서 사이드바/헤더가 누락됨
3. 페이지마다 레이아웃과 간격이 다름
4. 버튼, 카드, 테이블, badge 스타일이 통일되지 않음
5. 전체 디자인이 너무 기본 관리자 템플릿 느낌임
6. 원래 의도한 “AI 동아리 운영 비서”의 고급스러운 느낌이 약함
7. 정보가 너무 떨어져 있거나, 반대로 정리되지 않은 상태로 보임
```

---

## 디자인 방향

이번 Task의 디자인 방향은 다음이다.

```text
고급스럽지만 과하지 않게
깔끔하지만 밋밋하지 않게
향수 브랜드를 떠올리게 하는 절제된 감성
관리자 도구가 아니라 AI 비서 서비스처럼 보이게
```

---

## 디자인 키워드

```text
Luxury minimal
Warm ivory
Deep charcoal
Soft lavender accent
Muted gold point
Subtle shadow
Thin border
Large spacing
Rounded cards
Calm dashboard
```

---

## 디자인 토큰

가능하면 Tailwind 설정 또는 CSS 변수로 다음 색상 토큰을 정리한다.

### 색상

```text
background: #F8F5EF
surface: #FFFFFF
surface-soft: #FFFCF7
text-main: #1F1F24
text-muted: #77716A
border-soft: #E8E1D8
primary: #7C6CF2
primary-soft: #EEEAFE
accent: #C8A96A
success: #3F7D58
success-soft: #EAF5EE
warning: #B9822B
warning-soft: #FFF3D9
danger: #B94A48
danger-soft: #FCE9E8
```

### 형태

```text
card radius: 20px 또는 rounded-2xl
button radius: 14px 또는 rounded-xl
card shadow: 아주 약한 soft shadow
border: 1px solid border-soft
main padding: 넓게, 데스크톱 기준 24~32px
```

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. 전역 AppShell 정리
2. 모든 주요 페이지에 사이드바/헤더 적용
3. 디자인 토큰 정리
4. 공통 UI 컴포넌트 스타일 통일
5. Dashboard 재구성 1차
6. 주요 페이지 레이아웃 정리
7. 상태 badge 스타일 정리
8. Loading / Error / Empty state 통일
9. 테이블 스타일 개선
10. 버튼/입력창 스타일 개선
11. README에 디자인 구조 설명 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* Command Center 통합 입력 화면
* Intent Router
* 새로운 Agent 기능
* OpenAI 호출 로직 변경
* 거래내역서 파서 수정
* 납부 매칭 로직 수정
* 영수증 분석 로직 수정
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* 로그인/권한 시스템
* 대규모 DB 스키마 변경

필요한 위치에는 TODO 주석만 남긴다.

---

## 전역 레이아웃 요구사항

### 1. 모든 페이지에 AppShell 적용

다음 페이지들이 모두 동일한 레이아웃 안에서 보여야 한다.

```text
/dashboard
/members
/activities
/reports
/references
/receipts
/transactions
/payments
/notifications
/settings
```

각 페이지에서 사이드바와 헤더가 누락되면 안 된다.

---

### 2. AppShell 구조

권장 구조:

```text
AppShell
├── Sidebar
├── MainArea
│   ├── Header
│   └── PageContent
```

### Sidebar

사이드바에는 다음 메뉴를 유지한다.

```text
Dashboard
Assistant 또는 Workspace는 아직 구현하지 않음
Members
Activities
Reports
References
Receipts
Transactions
Payments
Notifications
Settings
```

단, Assistant 메뉴는 Task 10에서 구현 예정이므로 이번 Task에서는 메뉴만 추가하고 페이지는 준비 중 상태로 둬도 된다.

---

### Header

Header에는 다음 정보를 표시한다.

```text
현재 페이지 제목
간단한 설명
오른쪽에 상태 표시 또는 빠른 액션 영역
```

예시:

```text
Dashboard
오늘 처리해야 할 운영 업무를 확인하세요.
```

---

## 페이지별 디자인 정리

## 1. Dashboard 개선

현재 대시보드는 단순 통계 중심이라 실사용성이 낮다.

이번 Task에서는 대시보드를 다음 구조로 재구성한다.

### Dashboard 구성

```text
1. Hero 영역
- ClubAgent 운영 센터
- “동아리 운영에 필요한 문서, 예산, 납부 상태를 한 곳에서 확인하세요.”
- 빠른 액션 버튼 3개
  - 활동 보고서 만들기
  - 영수증 분석하기
  - 거래내역서 반영하기

2. 오늘 확인할 일
- 확인 필요 영수증
- 미납자
- 미분류 거래내역
- 작성 중 활동 보고서

3. 운영 요약 카드
- 전체 부원 수
- 이번 달 활동 보고서 수
- 총 영수증 수
- 확인 필요 증빙 수
- 거래내역 수
- 미납 건수
- 총 입금액
- 총 출금액

4. 최근 처리 내역
- 최근 활동 보고서
- 최근 영수증
- 최근 거래내역
- 최근 알림

5. 다음 단계 안내
- Command Center는 Task 10에서 구현 예정
```

Dashboard API가 아직 최근 처리 내역을 충분히 제공하지 않는다면, 현재 가능한 API만 사용하고 부족한 부분은 placeholder 또는 empty state로 둔다.

---

## 2. Members 페이지

목표:

```text
부원 관리 페이지가 표 중심으로 깔끔하게 보이도록 정리
```

개선 사항:

```text
- 상단 페이지 헤더 정리
- 검색/필터 영역을 카드 안에 배치
- 부원 추가 버튼을 우측 상단에 배치
- 테이블 간격 정리
- 상태 badge 적용
- active/inactive/graduated/paused 색상 정리
```

---

## 3. Reports / Activities 페이지

목표:

```text
활동 보고서 생성과 목록 관리가 자연스럽게 보이도록 정리
```

개선 사항:

```text
- 활동 보고서 작성 영역을 카드로 구성
- AI 초안 생성 결과를 별도 preview 카드로 표시
- 보고서 상태 badge 통일
- draft/generated/confirmed/archived 색상 정리
```

---

## 4. Receipts 페이지

목표:

```text
영수증 분석 기능이 서비스 핵심 기능처럼 보이도록 정리
```

개선 사항:

```text
- 업로드 영역을 고급스러운 card/dropzone 형태로 정리
- 분석 결과 카드를 보기 좋게 배치
- 증빙 상태 badge 정리
- need_check는 눈에 띄지만 과하지 않게 표시
- 저장된 영수증 목록 테이블 정리
```

---

## 5. Transactions 페이지

목표:

```text
거래내역서 업로드와 파싱 결과가 명확하게 보이도록 정리
```

개선 사항:

```text
- 파일 업로드 영역 정리
- 미리보기/가져오기 버튼 배치 개선
- 파싱 결과 요약 카드 정리
- 거래내역 테이블 정리
- 금액은 우측 정렬
- 입금/출금은 badge 또는 색상으로 구분
```

---

## 6. Payments 페이지

목표:

```text
납부 상태를 빠르게 확인할 수 있게 정리
```

개선 사항:

```text
- 납부 매칭 설정 영역 카드화
- 매칭 미리보기/적용 버튼 강조
- 납부 완료/미납/확인 필요 카드 표시
- 미납자 테이블을 눈에 잘 띄게 정리
- 확인 필요 거래는 warning 스타일 적용
```

---

## 7. Settings 페이지

목표:

```text
설정 페이지가 기능 설정과 안내를 명확히 보여주도록 정리
```

개선 사항:

```text
- OpenAI mock mode 안내 카드
- 활동 카테고리 관리 영역 정리
- 설정값 목록 정리
```

---

## 공통 UI 컴포넌트 요구사항

기존 컴포넌트를 보강하거나 새로 정리한다.

```text
frontend/components/ui/
  Button.tsx
  Card.tsx
  Badge.tsx
  Input.tsx
  Textarea.tsx
  Select.tsx
  Table.tsx
  EmptyState.tsx
  LoadingState.tsx
  ErrorState.tsx
  SectionHeader.tsx
  PageHeader.tsx
  StatusBadge.tsx
```

이미 비슷한 파일이 있다면 중복 생성하지 말고 재사용/확장한다.

---

## StatusBadge 규칙

상태값별 badge 스타일을 통일한다.

### 공통 상태

```text
active → success
inactive → muted
draft → muted
generated → primary
confirmed → success
archived → muted
pending → muted
valid → success
need_check → warning
invalid → danger
unmatched → muted
matched → success
excluded → muted
paid → success
partial → warning
unpaid → danger
```

---

## 테이블 스타일 요구사항

모든 주요 테이블은 다음 스타일을 따르도록 한다.

```text
- 카드 안에 테이블 배치
- 헤더는 muted background
- 행 hover 효과
- 금액은 오른쪽 정렬
- 날짜는 작은 muted text
- 액션 버튼은 과하지 않게
- 빈 데이터는 EmptyState 표시
```

---

## 버튼 스타일 요구사항

버튼 variant를 정리한다.

```text
primary
secondary
ghost
outline
danger
```

사용 예시:

```text
주요 실행: primary
보조 이동: secondary 또는 outline
삭제/비활성화: danger
테이블 행 액션: ghost
```

---

## Loading/Error/Empty State

모든 페이지에서 다음을 통일한다.

```text
LoadingState:
- 부드러운 skeleton 또는 간단한 loading card

ErrorState:
- 에러 메시지
- 다시 시도 버튼이 가능하면 포함

EmptyState:
- 제목
- 설명
- 필요한 경우 액션 버튼
```

---

## 반응형 기준

이번 Task는 데스크톱 우선이다.

다만 최소한 다음은 깨지지 않게 한다.

```text
- 1280px 이상: 최적
- 1024px 이상: 사용 가능
- 모바일은 필수 아님
```

---

## Frontend 파일 수정 예상

주요 수정 파일:

```text
frontend/app/layout.tsx
frontend/components/layout/AppShell.tsx
frontend/components/layout/Sidebar.tsx
frontend/components/layout/Header.tsx
frontend/components/ui/*
frontend/app/dashboard/page.tsx
frontend/app/members/page.tsx
frontend/app/activities/page.tsx
frontend/app/reports/page.tsx
frontend/app/references/page.tsx
frontend/app/receipts/page.tsx
frontend/app/transactions/page.tsx
frontend/app/payments/page.tsx
frontend/app/notifications/page.tsx
frontend/app/settings/page.tsx
frontend/app/globals.css
frontend/tailwind.config.ts 또는 tailwind.config.js
```

파일명은 현재 프로젝트 구조에 맞춘다.

---

## Backend 수정 범위

이번 Task에서 Backend 로직은 원칙적으로 수정하지 않는다.

단, Dashboard에서 필요한 수치가 부족하거나 `pending_receipts` 계산이 잘못되어 있으면 최소한으로 보강할 수 있다.

허용되는 Backend 수정:

```text
- dashboard summary 계산 보강
- 최근 항목 조회 API가 이미 있으면 활용
- 없으면 이번 Task에서는 무리하게 추가하지 않음
```

---

## README 업데이트

README에 다음 내용을 추가한다.

```text
- 디자인 시스템 개요
- 주요 색상 토큰
- 공통 레이아웃 구조
- Task 9에서 기능 로직은 변경하지 않았다는 설명
- 다음 Task 10에서 Command Center를 구현할 예정이라는 설명
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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
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
http://localhost:3000/dashboard
http://localhost:3000/members
http://localhost:3000/activities
http://localhost:3000/reports
http://localhost:3000/references
http://localhost:3000/receipts
http://localhost:3000/transactions
http://localhost:3000/payments
http://localhost:3000/notifications
http://localhost:3000/settings
```

모든 페이지에서 다음을 확인한다.

```text
- 사이드바가 보이는지
- 헤더가 보이는지
- 전체 배경과 카드 스타일이 통일되었는지
- 테이블 스타일이 깨지지 않는지
- 페이지 간 간격이 일관적인지
- 기능 버튼이 여전히 동작하는지
```

---

## 완료 기준

Task 9는 다음을 모두 만족해야 완료로 본다.

1. 모든 주요 페이지에 사이드바와 헤더가 일관되게 적용되어 있다.
2. 전역 디자인 톤이 고급스럽고 절제된 방향으로 정리되어 있다.
3. Dashboard가 실사용형 운영 화면에 가깝게 재구성되어 있다.
4. 카드, 버튼, 테이블, badge 스타일이 통일되어 있다.
5. Loading/Error/Empty state가 주요 페이지에서 통일되어 있다.
6. Receipts, Transactions, Payments 페이지의 핵심 기능 UI가 보기 좋게 정리되어 있다.
7. 기존 기능 로직이 깨지지 않는다.
8. frontend build가 성공한다.
9. backend compile/test가 기존과 동일하게 통과한다.
10. README에 디자인 시스템 설명이 추가되어 있다.
11. 이번 Task에서 Command Center, Intent Router, n8n, Notion, Slack 기능은 구현되지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 9 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 디자인 시스템 변경 사항
- 색상:
- 공통 컴포넌트:
- 레이아웃:

3. 전역 레이아웃 적용 결과
- 사이드바/헤더 적용 페이지:
- 수정한 누락 페이지:

4. Dashboard 개선 내용
- ...

5. 주요 페이지 개선 내용
- Members:
- Activities/Reports:
- References:
- Receipts:
- Transactions:
- Payments:
- Notifications:
- Settings:

6. 실행 검증 결과
- backend compile/test:
- frontend build:
- 주요 URL 확인:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

9. 다음 Task에서 해야 할 일
- Task 10: Command Center 통합 입력 화면 구현
```
