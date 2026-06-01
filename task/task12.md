# Task 12. 브랜드 로고 적용, 사이드바 간소화, 실사용형 Dashboard 재정리

## 목표

ClubAgent의 UI가 기능적으로는 동작하지만, 현재 화면은 메뉴와 카드가 많아 다소 정신없고 관리자 도구처럼 보인다.

이번 Task의 목표는 다음이다.

```text
AINEW/img/oui-parfum.png 로고를 ClubAgent 브랜드에 적용
→ 사이드바 메뉴 구조를 단순화
→ Dashboard를 실사용형 운영 화면으로 재정리
→ 전체 화면의 정보 밀도와 시각적 노이즈를 줄임
→ 고급스럽고 절제된 브랜드 톤 강화
```

이번 Task는 새로운 기능 개발이 아니라, 현재 구현된 기능을 더 직관적이고 고급스럽게 보이도록 정리하는 작업이다.

---

## 전제 조건

Task 1~11이 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

* 전역 AppShell
* Sidebar/Header
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
* Assistant 결과 카드 및 Human-in-the-loop UX

---

## 현재 문제

현재 UI에서 느껴지는 문제는 다음과 같다.

```text
1. 사이드바 메뉴가 너무 많아 보인다.
2. 모든 메뉴가 같은 중요도로 보여서 시선이 분산된다.
3. Dashboard 카드가 많고 정보가 흩어져 보인다.
4. 고급스러운 톤은 일부 적용되었지만 브랜드 중심성이 약하다.
5. ClubAgent만의 로고/브랜드 아이덴티티가 부족하다.
6. AI 작업실이 핵심인데 Dashboard와 사이드바에서 충분히 중심으로 보이지 않는다.
```

---

## 디자인 방향

기존 Task 9의 luxury minimal 디자인 방향을 유지하되, 이번에는 업로드된 로고의 분위기를 반영한다.

사용할 로고:

```text
AINEW/img/oui-parfum.png
```

브랜드 톤:

```text
Ivory background
Black typography
Muted gold accent
Soft lavender secondary accent
Thin border
Rounded card
Less clutter
More editorial layout
```

핵심 키워드:

```text
고급스럽게
절제되게
정돈되게
기능보다 흐름이 먼저 보이게
AI 작업실이 중심처럼 보이게
```

---

# Part A. 로고 적용

## 1. 로고 파일 처리

현재 프로젝트 루트 기준 로고 위치:

```text
img/oui-parfum.png
```

이 파일을 프론트에서 사용할 수 있도록 다음 위치로 복사한다.

```text
frontend/public/brand/oui-parfum.png
```

주의:

```text
- 원본 img/oui-parfum.png는 삭제하지 않는다.
- public/brand 폴더가 없으면 생성한다.
- 로고 파일명을 변경하지 않아도 된다.
- Next.js Image 또는 일반 img 태그로 사용한다.
```

---

## 2. 로고 사용 위치

### Sidebar 상단

기존 `CA` 박스 대신 로고를 사용한다.

권장 형태:

```text
작은 원형 로고 + ClubAgent 텍스트
```

사이즈:

```text
logo: 40px ~ 48px
텍스트: ClubAgent
서브텍스트: AI club operating assistant
```

텍스트가 너무 많으면 서브텍스트는 생략한다.

---

### Dashboard Hero

Dashboard Hero 영역에 로고를 작게 넣는다.

예시:

```text
[로고]
ClubAgent 운영 센터
문서, 예산, 납부 상태를 한 곳에서 정리하세요.
```

로고가 너무 크게 보이면 안 된다.

권장:

```text
64px ~ 80px
```

---

### AI 작업실 Hero

`/assistant` 상단에도 로고를 작게 적용한다.

예시:

```text
[로고]
ClubAgent Assistant
파일을 올리거나 요청을 입력하면 적절한 작업을 실행합니다.
```

---

## 3. 로고 스타일 주의

로고 자체가 원형이고 흰 배경이 있으므로 다음을 지킨다.

```text
- 과한 그림자 금지
- 배경 카드와 겹칠 때 흰 원형이 자연스럽게 보이도록 처리
- border는 아주 옅게
- 로고 주변 여백 충분히 확보
```

---

# Part B. 사이드바 간소화

## 목표

현재 사이드바는 메뉴가 많아 보이고, 모든 메뉴가 같은 중요도로 보여서 정신없게 느껴진다.

이번 Task에서는 메뉴를 삭제하지 않고, 정보 구조를 정리한다.

---

## 1. 메뉴 그룹화

현재 메뉴를 다음 그룹으로 정리한다.

```text
Primary
- Dashboard
- AI 작업실

Operations
- Activities
- Reports
- References

Finance
- Receipts
- Transactions
- Payments

People
- Members

System
- Notifications
- Settings
```

UI 표시 방식은 다음 중 하나로 구현한다.

### 권장 방식 A: 그룹 라벨 표시

```text
MAIN
Dashboard
AI 작업실

OPERATIONS
Activities
Reports
References

FINANCE
Receipts
Transactions
Payments

PEOPLE
Members

SYSTEM
Notifications
Settings
```

단, 그룹 라벨은 매우 작고 연하게 표시한다.

---

### 선택 방식 B: 접을 수 있는 그룹

가능하면 Finance / Operations / System은 접을 수 있게 만든다.

단, 이번 Task에서 복잡해지면 접기 기능은 구현하지 않아도 된다.

우선순위는 다음이다.

```text
1순위: 그룹 라벨로 시각 정리
2순위: active 상태 명확화
3순위: 접기 기능은 가능하면 구현
```

---

## 2. 메뉴 시각 노이즈 줄이기

사이드바 스타일을 다음처럼 조정한다.

```text
- 아이콘 크기 약간 축소
- 메뉴 간격 약간 축소
- active 배경은 연한 ivory/lavender
- active 텍스트는 deep charcoal 또는 primary
- 그룹 라벨은 작고 muted
- 하단 Mock Mode 카드는 더 작고 차분하게
```

현재처럼 모든 요소가 강하게 보이지 않게 한다.

---

## 3. Sidebar 하단 정리

현재 Mock Mode 카드가 눈에 잘 띄므로 더 차분하게 만든다.

표시 예시:

```text
Mock Mode
테스트 데이터로 실행 중
```

스타일:

```text
작은 카드
연한 gold 배경
작은 텍스트
아이콘 최소화
```

---

# Part C. Dashboard 재정리

## 목표

Dashboard를 단순 통계 카드 나열이 아니라, 실제 운영자가 오늘 해야 할 일을 빠르게 보는 화면으로 재정리한다.

---

## 현재 Dashboard 문제

현재 Dashboard는 다음 정보가 모두 비슷한 강도로 보여서 정신없다.

```text
- Hero
- 오늘 확인할 일
- 운영 요약
- 다음 단계 안내
- 여러 숫자 카드
```

이번 Task에서는 다음처럼 시각적 우선순위를 명확히 한다.

---

## 1. Dashboard 새 구조

Dashboard는 다음 4개 영역으로 재구성한다.

```text
1. Brand Hero + AI 작업실 CTA
2. 오늘 처리할 일
3. 핵심 운영 요약
4. 최근 흐름 / 다음 단계 안내
```

---

## 2. Brand Hero + AI 작업실 CTA

Hero는 현재보다 더 단순하고 브랜드 중심으로 만든다.

구성:

```text
왼쪽:
- 작은 로고
- ClubAgent 운영 센터
- 동아리 운영에 필요한 문서, 예산, 납부 상태를 한 곳에서 확인하세요.

오른쪽:
- AI 작업실로 이동 버튼
- 오늘 처리할 일 보기 버튼
```

빠른 액션 버튼은 3개에서 1~2개로 줄인다.

기존:

```text
활동 보고서 만들기
영수증 분석하기
거래내역서 반영하기
```

수정:

```text
AI 작업실 열기
운영 데이터 확인
```

세부 작업은 `/assistant` 안에서 하도록 유도한다.

---

## 3. 오늘 처리할 일

카드는 4개 유지하되, 시각적으로 더 작고 명확하게 만든다.

표시 항목:

```text
확인 필요 영수증
미납자
작성 중 보고서
읽지 않은 알림
```

각 카드에는 다음만 표시한다.

```text
숫자
라벨
짧은 설명 또는 상태
```

색상은 과하지 않게 한다.

---

## 4. 핵심 운영 요약

운영 요약 카드는 현재 8개에서 4~6개로 줄인다.

우선 표시:

```text
전체 부원
활동 카테고리
전체 보고서
전체 거래내역
총 입금액
총 출금액
```

다음 항목은 Dashboard에서 제거하거나 접힌 영역으로 보낸다.

```text
전체 영수증
활동 중 부원
```

필요하면 작은 텍스트로 Hero나 요약에 포함한다.

---

## 5. 다음 단계 안내 카드 정리

현재 “Task 10에서 Command Center 구현 예정” 같은 개발자용 문구는 실사용 화면에서는 제거한다.

대신 실사용 안내로 바꾼다.

예시:

```text
추천 작업
AI 작업실에서 영수증, 거래내역서, 활동 자료를 한 번에 올려보세요.
```

버튼:

```text
AI 작업실로 이동
```

---

# Part D. AI 작업실 화면 가독성 개선

## 목표

`/assistant`는 핵심 화면이므로 현재보다 더 집중도 있게 정리한다.

---

## 1. 중앙 카드 폭 조정

현재 입력 카드가 약간 넓고 정보가 많아 보일 수 있다.

권장:

```text
max-width: 760px ~ 840px
```

---

## 2. 입력 흐름 정리

현재 요소 순서를 유지하되, 시각적으로 묶는다.

```text
1. 파일 업로드
2. 요청 입력
3. 예시 요청
4. 처리 옵션
5. 실행
```

처리 옵션은 처음부터 너무 크게 보이지 않게 한다.

방법:

```text
- 기본 옵션만 보이기
- 상세 옵션은 접을 수 있는 영역으로 이동
```

상세 옵션:

```text
처리 유형
납부 기간
납부 유형
기준 금액
auto_apply
```

---

## 3. auto_apply 문구 개선

현재 문구:

```text
자동 반영 (auto_apply) — 체크 시 확인 없이 바로 저장됩니다. 기본값은 미체크(미리보기)입니다.
```

수정 문구:

```text
확인 없이 바로 반영
기본값은 꺼짐입니다. 먼저 미리보기 결과를 확인한 뒤 반영하는 것을 권장합니다.
```

---

# Part E. 공통 UI 정리

## 1. 버튼 개수 줄이기

주요 화면에서 한 줄에 버튼이 너무 많으면 안 된다.

원칙:

```text
- Primary 버튼은 한 영역에 하나만
- 나머지는 ghost 또는 outline
- CTA는 AI 작업실 중심으로 유도
```

---

## 2. 카드 간격 정리

현재 카드 간격이 넓어 화면이 길어질 수 있다.

조정:

```text
section gap: 28px 정도
card gap: 16px ~ 20px
card padding: 20px ~ 24px
```

---

## 3. 아이콘 사용 줄이기

아이콘은 유지하되 다음 원칙 적용.

```text
- 카드마다 큰 아이콘을 반복하지 않기
- 작은 muted icon 중심
- 상태를 색으로 과하게 강조하지 않기
```

---

# Backend 수정 범위

이번 Task는 Frontend 중심이다.

Backend는 원칙적으로 수정하지 않는다.

허용되는 수정:

```text
- Dashboard summary 값이 깨지는 경우 최소 수정
- Assistant response가 화면 표시를 위해 detail_url을 이미 제공하는 경우 그대로 사용
```

새 API는 만들지 않는다.

---

# Frontend 수정 예상 파일

```text
frontend/public/brand/oui-parfum.png

frontend/components/layout/Sidebar.tsx
frontend/components/layout/Header.tsx
frontend/components/layout/AppShell.tsx

frontend/app/dashboard/page.tsx
frontend/app/assistant/page.tsx
frontend/app/globals.css

frontend/components/ui/Button.tsx
frontend/components/ui/Card.tsx
frontend/components/ui/Badge.tsx
frontend/components/ui/StatusBadge.tsx
```

필요하면 다음 파일도 수정한다.

```text
frontend/components/assistant/*
frontend/components/ui/PageHeader.tsx
frontend/components/ui/SectionHeader.tsx
```

---

# README 업데이트

README에 다음 내용을 추가한다.

```text
- 브랜드 로고 적용 위치
- 로고 파일 경로
- 사이드바 그룹 구조
- Dashboard 정보 구조 변경
- AI 작업실이 앞으로의 핵심 진입점이라는 설명
```

---

# 실행 검증

가능하면 다음을 실행한다.

```bash
cd frontend
npm install
npm run build
npm run dev
```

Backend가 필요한 화면 확인 시:

```bash
cd backend
python -m compileall app
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

확인 URL:

```text
http://localhost:3000/dashboard
http://localhost:3000/assistant
http://localhost:3000/members
http://localhost:3000/receipts
http://localhost:3000/transactions
http://localhost:3000/payments
```

확인할 것:

```text
- 사이드바 상단에 oui-parfum 로고가 보이는지
- 사이드바 메뉴가 그룹화되어 덜 복잡해졌는지
- Dashboard가 덜 정신없고 핵심 흐름이 먼저 보이는지
- AI 작업실이 핵심 진입점처럼 보이는지
- 기존 페이지 이동이 깨지지 않는지
- frontend build가 성공하는지
```

---

## 완료 기준

Task 12는 다음을 모두 만족해야 완료로 본다.

1. `img/oui-parfum.png`가 프론트 public asset으로 복사되어 사용된다.
2. Sidebar 상단에 로고가 적용되어 있다.
3. Dashboard Hero 또는 AI 작업실 Hero에 로고가 자연스럽게 적용되어 있다.
4. Sidebar 메뉴가 그룹화되어 현재보다 덜 복잡하게 보인다.
5. Dashboard 카드 수와 시각적 노이즈가 줄었다.
6. Dashboard에서 AI 작업실로 이동하는 CTA가 명확하다.
7. 개발자용 “Task 예정” 문구가 실사용자용 문구로 바뀌었다.
8. AI 작업실 입력 흐름이 더 정돈되어 보인다.
9. auto_apply 문구가 사용자 친화적으로 수정되었다.
10. 기존 기능과 라우팅이 깨지지 않는다.
11. frontend build가 성공한다.
12. README에 브랜드/레이아웃 변경 내용이 추가되어 있다.
13. 이번 Task에서 새 Agent, n8n, Notion, Slack 기능은 구현하지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 12 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 로고 적용 내용
- 원본 경로:
- public 복사 경로:
- 적용 위치:

3. 사이드바 간소화 내용
- 그룹 구조:
- active 스타일:
- Mock Mode 카드:

4. Dashboard 재정리 내용
- Hero:
- 오늘 처리할 일:
- 운영 요약:
- 추천 작업:

5. AI 작업실 개선 내용
- 입력 카드:
- 상세 옵션:
- auto_apply 문구:

6. 실행 검증 결과
- frontend build:
- 주요 URL 확인:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

9. 다음 Task에서 해야 할 일
- Task 13: 통합 테스트, 데모 시나리오, 샘플 데이터 정리
```
