# Task 15. 모바일 UX 지원 및 데모 안정화

## 목표

ClubAgent를 데스크톱뿐 아니라 모바일 브라우저에서도 최대한 자연스럽게 사용할 수 있도록 UI/UX를 개선한다.

이번 Task의 핵심은 다음이다.

```text
모바일 접속 시 화면 깨짐 방지
→ Sidebar를 모바일용 Drawer/Bottom Navigation으로 전환
→ Dashboard, AI 작업실, Reports, Receipts, Payments 주요 화면 모바일 최적화
→ 테이블 중심 화면을 모바일 카드형으로 보완
→ 영수증 촬영/업로드 UX 개선
→ 외부 도메인 agent.banawy.store에서 모바일 테스트 가능 상태로 정리
```

이번 Task는 새로운 Agent 기능을 추가하는 작업이 아니라, 현재 구현된 기능을 실제 사용 환경과 발표 데모에서 안정적으로 보여주기 위한 반응형 UI 정리 작업이다.

---

## 전제 조건

Task 1~14가 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

* 전역 AppShell
* 브랜드 로고 적용
* Dashboard
* AI 작업실 `/assistant`
* 활동 보고서 카드형 UX
* 영수증 분석 및 삭제
* 거래내역서 파서
* 납부 매칭 및 직접 수정
* 실제 OpenAI 모드
* 자동 점검 API
* Notifications
* 외부 도메인 `agent.banawy.store`
* 프론트 `/api` proxy 구조

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. 모바일 전역 레이아웃 개선
2. 모바일 Sidebar Drawer 또는 Bottom Navigation 구현
3. Header 모바일 대응
4. Dashboard 모바일 레이아웃 정리
5. AI 작업실 모바일 UX 개선
6. 영수증 모바일 업로드/촬영 UX 개선
7. 활동 보고서 카드/상세 모달 모바일 대응
8. Payments 모바일 카드형 보기 보완
9. Transactions/Receipts 테이블 모바일 대응
10. 모바일 터치 타깃, 폰트 크기, 여백 정리
11. 모바일에서 외부 도메인 접속 테스트 체크리스트 작성
12. README 또는 DEMO.md에 모바일 테스트 방법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* 새로운 Agent 기능
* LLM 기반 Intent Classifier
* Notion 연동
* Slack/Telegram 연동
* 로그인/권한 시스템
* n8n workflow 추가
* DB 스키마 대규모 변경
* 기존 영수증 분석 로직 재작성
* 기존 납부 매칭 알고리즘 재작성
* 기존 거래내역서 파서 재작성

필요한 위치에는 TODO 주석만 남긴다.

---

# Part A. 전역 모바일 레이아웃

## 1. Breakpoint 기준

반응형 기준은 다음으로 잡는다.

```text
mobile: 0px ~ 767px
tablet: 768px ~ 1023px
desktop: 1024px 이상
```

Tailwind 기준으로는 다음을 사용한다.

```text
default = mobile
md = tablet
lg = desktop
```

---

## 2. AppShell 모바일 구조

현재 데스크톱 AppShell은 다음 구조일 가능성이 높다.

```text
Sidebar + MainContent
```

모바일에서는 Sidebar를 고정으로 두면 화면이 너무 좁아진다.

모바일 구조는 다음 중 하나로 구현한다.

### 권장 방식

```text
Mobile Header
+ Menu Button
+ Full-screen 또는 slide-in Drawer Sidebar
+ MainContent full width
```

### 선택 방식

```text
상단 Header
+ 하단 Bottom Navigation
+ More 메뉴 Drawer
```

이번 Task에서는 구현 난이도를 고려해 **Mobile Drawer Sidebar 방식**을 우선 적용한다.

---

## 3. Sidebar 모바일 요구사항

`frontend/components/layout/Sidebar.tsx` 또는 관련 AppShell 컴포넌트를 수정한다.

요구사항:

```text
- 데스크톱: 기존 Sidebar 유지
- 모바일: Sidebar 숨김
- 모바일 Header의 메뉴 버튼 클릭 시 Drawer로 Sidebar 표시
- Drawer 바깥 클릭 시 닫힘
- 메뉴 클릭 시 Drawer 닫힘
- 현재 active 메뉴 표시 유지
```

모바일 Drawer 너비:

```text
width: 280px ~ 320px
```

스타일:

```text
- ivory/surface 배경 유지
- 얇은 border
- 과한 shadow 금지
- 로고 표시 유지
```

---

## 4. Header 모바일 요구사항

`frontend/components/layout/Header.tsx` 또는 AppShell Header를 보강한다.

모바일 Header 구성:

```text
왼쪽: 메뉴 버튼
중앙 또는 왼쪽: 현재 페이지 제목
오른쪽: 간단한 상태 또는 비움
```

요구사항:

```text
- 높이 56px ~ 64px
- sticky top 가능
- 배경 blur 또는 surface 배경
- iOS safe-area 고려
- 제목이 길면 줄임 처리
```

---

## 5. 전역 CSS 보강

`frontend/app/globals.css`를 확인하고 모바일 overflow 문제를 줄인다.

필수 확인:

```text
html, body {
  overflow-x: hidden;
}

* {
  box-sizing: border-box;
}
```

주의:

```text
- 전체 페이지에서 가로 스크롤이 생기지 않도록 한다.
- 테이블이 필요한 경우 테이블 내부 컨테이너만 horizontal scroll을 허용한다.
```

---

# Part B. Dashboard 모바일 UX

## 목표

모바일에서 Dashboard가 너무 긴 카드 목록처럼 보이지 않도록 우선순위를 정리한다.

---

## 모바일 Dashboard 구조

모바일에서는 다음 순서로 표시한다.

```text
1. Brand Hero
2. AI 작업실 CTA
3. 오늘 처리할 일
4. 핵심 운영 요약
5. 최근 흐름 또는 추천 작업
```

---

## 요구사항

`frontend/app/dashboard/page.tsx`를 보강한다.

```text
- Hero는 모바일에서 세로 배치
- 로고는 너무 크게 보이지 않게 48px ~ 64px
- CTA 버튼은 세로 1열
- 오늘 처리할 일 카드는 1열 또는 2열
- 운영 요약 카드는 2열 권장
- 카드 padding은 모바일에서 줄임
```

예시 Tailwind 방향:

```text
grid-cols-1 md:grid-cols-2 lg:grid-cols-4
p-4 md:p-6 lg:p-8
text-2xl md:text-3xl
```

---

# Part C. AI 작업실 모바일 UX

## 목표

모바일에서 `/assistant`는 가장 중요한 진입점이므로, 입력 흐름이 편해야 한다.

---

## 개선 요구사항

`frontend/app/assistant/page.tsx`를 수정한다.

모바일 입력 흐름:

```text
1. 간단한 안내
2. 파일 업로드
3. 요청 입력
4. 예시 요청 chip
5. 처리 옵션 접기/펼치기
6. 실행 버튼
7. 결과 카드
```

---

## 파일 업로드 모바일 개선

파일 업로드 input은 모바일에서 다음을 지원한다.

```text
- 이미지 파일 선택
- 카메라 촬영 가능
- 다중 파일 선택 가능
```

input 예시:

```html
<input type="file" accept="image/*,.pdf,.xls,.xlsx,.csv" multiple />
```

영수증 중심 입력에는 가능하면 별도 input 또는 안내 문구를 둔다.

```text
영수증은 휴대폰 카메라로 촬영한 이미지도 업로드할 수 있습니다.
```

가능하면 `capture="environment"`는 선택적으로만 사용한다. 강제 촬영이 되면 파일 선택이 불편할 수 있다.

---

## 요청 textarea 모바일 개선

요구사항:

```text
- 최소 높이 120px
- 모바일 키보드가 올라와도 버튼이 가려지지 않도록 여백 확보
- 예시 chip은 가로 스크롤 가능하게 처리
- 실행 버튼은 full width
```

---

## 결과 카드 모바일 개선

Assistant 결과 카드는 모바일에서 다음처럼 보인다.

```text
- 1열 카드
- summary grid는 1~2열
- Agent flow pill은 줄바꿈 허용
- 상세 페이지 이동 버튼은 full width 또는 2열
- 확인 후 반영 버튼은 가장 아래에 명확히 표시
```

---

# Part D. 활동 보고서 모바일 UX

## 목표

활동 보고서 카드형 목록과 상세 확인이 모바일에서도 편해야 한다.

---

## Reports/Activities 카드 그리드

수정 대상:

```text
frontend/app/activities/page.tsx
frontend/app/reports/page.tsx
frontend/components/reports/*
```

요구사항:

```text
- 모바일: 1열 카드
- 태블릿: 2열 카드
- 데스크톱: 3열 카드
- 카드 내부 미리보기 텍스트는 2~3줄 제한
- 버튼은 하단에 정렬
```

---

## 상세 모달/Drawer 모바일 대응

현재 Drawer 또는 Modal이 있다면 모바일에서는 full-screen에 가깝게 표시한다.

요구사항:

```text
- 모바일에서는 width 100%
- 높이는 90vh 이상 또는 full height
- 본문 영역은 스크롤 가능
- 하단 액션 버튼은 sticky bottom 가능
- 복사/다운로드/보관 버튼이 너무 좁지 않게 배치
```

---

# Part E. Receipts 모바일 UX

## 목표

휴대폰으로 영수증을 촬영하거나 업로드하고 분석 결과를 확인하기 편해야 한다.

---

## Receipts 페이지 요구사항

수정 대상:

```text
frontend/app/receipts/page.tsx
```

요구사항:

```text
- 업로드 영역은 모바일에서 full width
- 분석 버튼 full width
- 결제 방식 select와 카테고리 input은 1열
- 분석 결과 카드는 모바일에서 1열
- 필요 증빙/판단 사유는 접히지 않고 잘 보이게 표시
- 저장된 영수증 목록은 모바일에서 테이블 대신 카드형 또는 row stack 형태로 표시
- 삭제 버튼은 각 카드 하단에 배치
```

---

## 모바일 영수증 목록 카드

테이블 대신 모바일에서는 다음 형태로 보여준다.

```text
[가맹점] [금액]
날짜
결제 방식 / 카테고리
증빙 상태 badge
사유 일부
[수정] [삭제]
```

데스크톱에서는 기존 테이블 유지 가능.

---

# Part F. Payments 모바일 UX

## 목표

모바일에서 납부 상태 확인과 직접 수정이 가능해야 한다.

---

## Payments 페이지 요구사항

수정 대상:

```text
frontend/app/payments/page.tsx
```

요구사항:

```text
- 납부 설정 영역은 모바일 1열
- 매칭 미리보기/적용 버튼 full width
- 요약 카드는 2열 또는 1열
- 미납자 테이블은 모바일 카드형으로 표시
- 직접 수정 버튼은 각 미납자 카드 하단에 표시
- 직접 수정 모달은 모바일 full-screen 또는 bottom sheet 형태
```

---

## 미납자 모바일 카드

표시 항목:

```text
이름
학번
필요 금액
납부 금액
상태 badge
직접 수정 버튼
```

---

## 직접 수정 모달 모바일

요구사항:

```text
- 모바일 width 100%
- input/select 1열
- 저장 버튼 full width
- 닫기 버튼 명확히 표시
```

---

# Part G. Transactions 모바일 UX

## 목표

거래내역서 업로드와 파싱 결과를 모바일에서도 확인 가능하게 한다.

---

## Transactions 페이지 요구사항

수정 대상:

```text
frontend/app/transactions/page.tsx
```

요구사항:

```text
- 업로드 영역 full width
- 미리보기/가져오기 버튼 모바일 full width
- 요약 카드는 2열 또는 1열
- 거래 목록 테이블은 모바일에서 horizontal scroll 또는 카드형
```

권장:

```text
- 데스크톱: 테이블
- 모바일: 카드형 목록
```

모바일 거래 카드:

```text
거래일시
적요
입금/출금 금액
잔액
매칭상태 badge
```

---

# Part H. Notifications 모바일 UX

## 목표

자동 점검 알림을 모바일에서 빠르게 확인할 수 있게 한다.

수정 대상:

```text
frontend/app/notifications/page.tsx
```

요구사항:

```text
- 알림 목록 1열 카드
- unread/read badge
- automation badge
- 메시지 2~3줄 preview
- 관련 페이지 이동 링크
```

---

# Part I. 터치 타깃 및 접근성

## 터치 영역

모바일에서 클릭 가능한 요소는 최소 높이를 확보한다.

```text
button min-height: 44px
input/select min-height: 44px
tap target spacing 충분히 확보
```

---

## 폰트 크기

```text
본문: 최소 14px 이상
input: iOS zoom 방지를 위해 16px 권장
작은 설명 텍스트: 12px 이하 남발 금지
```

---

## 모달/Drawer 접근성

```text
- ESC 닫기 가능하면 유지
- 배경 클릭 닫기
- 닫기 버튼 명확히 표시
- 모바일에서 스크롤 잠김 처리 가능하면 적용
```

---

# Part J. 외부 모바일 테스트

## 테스트 대상

실제 휴대폰 브라우저에서 다음 URL을 확인한다.

```text
https://agent.banawy.store
https://agent.banawy.store/dashboard
https://agent.banawy.store/assistant
https://agent.banawy.store/activities
https://agent.banawy.store/receipts
https://agent.banawy.store/payments
https://agent.banawy.store/notifications
```

---

## 모바일 테스트 체크리스트

다음 문서를 추가하거나 README에 포함한다.

권장 파일:

```text
MOBILE_TEST.md
```

체크리스트:

```text
1. 외부 도메인 접속 가능
2. 로그인 없이 Dashboard 표시
3. 모바일 메뉴 열고 닫기 가능
4. AI 작업실에서 파일 선택 가능
5. 영수증 사진 업로드 가능
6. 요청 입력 후 실행 버튼 클릭 가능
7. 결과 카드가 화면 밖으로 튀어나가지 않음
8. 활동 보고서 카드 클릭 가능
9. 보고서 복사/다운로드 버튼 클릭 가능
10. 영수증 삭제 가능
11. 미납자 직접 수정 모달 사용 가능
12. 가로 스크롤이 전체 페이지에 생기지 않음
13. iPhone Safari / Android Chrome 중 최소 하나에서 확인
```

---

# Backend 수정 범위

이번 Task는 Frontend 중심이다.

Backend는 원칙적으로 수정하지 않는다.

허용되는 Backend 수정:

```text
- 모바일 업로드에서 파일 MIME type이 누락되는 경우를 위한 방어적 처리
- CORS 또는 upload size 오류가 명확히 발생하는 경우 최소 수정
```

새로운 API는 만들지 않는다.

---

# Frontend 수정 예상 파일

```text
frontend/app/layout.tsx
frontend/app/globals.css

frontend/components/layout/AppShell.tsx
frontend/components/layout/Sidebar.tsx
frontend/components/layout/Header.tsx

frontend/app/dashboard/page.tsx
frontend/app/assistant/page.tsx
frontend/app/activities/page.tsx
frontend/app/reports/page.tsx
frontend/app/receipts/page.tsx
frontend/app/payments/page.tsx
frontend/app/transactions/page.tsx
frontend/app/notifications/page.tsx

frontend/components/assistant/*
frontend/components/ui/*
frontend/components/reports/*
```

실제 구조에 맞춰 필요한 파일만 수정한다.

---

# README / 문서 업데이트

다음 내용을 README 또는 `MOBILE_TEST.md`에 추가한다.

```text
- 모바일 지원 범위
- 모바일 메뉴 사용 방법
- 휴대폰 영수증 업로드 방법
- 모바일 테스트 체크리스트
- agent.banawy.store에서 모바일 확인하는 방법
```

---

# 실행 검증

## Frontend

```bash
cd frontend
npm install
npm run build
npm run dev -- -H 0.0.0.0 -p 3000
```

외부 테스트용:

```bash
npm run build
npm run start -- -H 0.0.0.0 -p 3000
```

## Backend

필요 시:

```bash
cd backend
python -m compileall app
pytest
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

## 확인 URL

```text
http://localhost:3000
http://localhost:3000/dashboard
http://localhost:3000/assistant
http://localhost:3000/activities
http://localhost:3000/receipts
http://localhost:3000/payments

https://agent.banawy.store
https://agent.banawy.store/dashboard
https://agent.banawy.store/assistant
https://agent.banawy.store/receipts
https://agent.banawy.store/payments
```

---

## 완료 기준

Task 15는 다음을 모두 만족해야 완료로 본다.

1. 모바일에서 Sidebar가 고정으로 화면을 차지하지 않는다.
2. 모바일 메뉴 버튼으로 Drawer를 열고 닫을 수 있다.
3. Dashboard가 모바일 1열/2열 레이아웃으로 자연스럽게 표시된다.
4. AI 작업실에서 모바일 파일 업로드와 요청 입력이 가능하다.
5. 영수증 이미지를 모바일에서 선택/촬영해 업로드할 수 있다.
6. Assistant 결과 카드가 모바일 화면 밖으로 넘치지 않는다.
7. 활동 보고서 카드 목록이 모바일 1열로 표시된다.
8. 활동 보고서 상세 모달/Drawer가 모바일에서 사용 가능하다.
9. Receipts 목록이 모바일에서 카드형 또는 stack 형태로 보기 좋게 표시된다.
10. Payments 미납자 목록이 모바일에서 카드형으로 표시된다.
11. 납부 직접 수정 모달이 모바일에서 사용 가능하다.
12. Transactions 목록이 모바일에서 깨지지 않는다.
13. Notifications가 모바일 카드형으로 표시된다.
14. 전체 페이지에서 불필요한 가로 스크롤이 발생하지 않는다.
15. 주요 버튼과 입력창의 터치 영역이 충분하다.
16. `MOBILE_TEST.md` 또는 README에 모바일 테스트 체크리스트가 추가되어 있다.
17. frontend build가 성공한다.
18. 이번 Task에서 새로운 Agent, n8n, Notion, Slack 기능은 구현하지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 15 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 전역 모바일 레이아웃
- AppShell:
- Sidebar Drawer:
- Header:

3. 페이지별 모바일 개선
- Dashboard:
- AI 작업실:
- Activities/Reports:
- Receipts:
- Payments:
- Transactions:
- Notifications:

4. 터치/접근성 개선
- 버튼:
- 입력창:
- 모달/Drawer:
- 가로 스크롤 방지:

5. 모바일 테스트 문서
- MOBILE_TEST.md:
- 테스트 체크리스트:

6. 실행 검증 결과
- frontend build:
- backend compile/test:
- localhost 확인:
- agent.banawy.store 확인:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task15: improve mobile responsive ux
```
