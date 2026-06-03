# Task 36. 전체 UI 가독성 개선 및 모바일 최적화

현재 프로젝트는 ClubAgent입니다.

Task 35까지 진행하면서 대시보드 캘린더, 부원 관리, 회비, 활동비, 거래내역, 영수증/증빙, 파일함, HWPX 생성 등 주요 기능을 구현했습니다.

이번 Task 36의 목표는 **전체 화면의 가독성과 모바일 사용성을 개선하는 것**입니다.

현재 문제:

```text
1. 일부 카드/테이블에서 글씨가 아래로 밀리거나 줄바꿈이 어색함
2. 버튼이 너무 많이 노출되어 행 높이가 커지고 보기 불편함
3. 긴 파일명, 긴 활동명, 긴 설명이 레이아웃을 깨뜨림
4. 테이블 컬럼이 많아 화면이 좁을 때 보기 어려움
5. 모바일에서 사이드바, 탭, 테이블, 카드가 불편하게 보임
6. 대시보드/활동 상세/부원/회비/활동비 화면의 UI 일관성이 부족함
```

---

# 핵심 목표

이번 Task는 새 기능 추가가 아니라 UI 안정화 작업입니다.

```text
1. 글씨가 아래로 밀리거나 겹치는 문제 수정
2. 긴 텍스트 말줄임/줄바꿈/높이 정리
3. 테이블 모바일 대응
4. 버튼 과다 노출 정리
5. 카드/섹션 간격 통일
6. 전체 모바일 레이아웃 최적화
```

---

# Part A. 글씨 내려감/레이아웃 깨짐 수정

전체 화면에서 다음 문제를 찾아 수정하세요.

```text
1. 카드 제목이 줄바꿈되면서 값이 아래로 밀림
2. badge와 텍스트가 한 줄에 정렬되지 않음
3. 버튼이 줄바꿈되며 테이블 행 높이를 과도하게 키움
4. 긴 이름/파일명/활동명이 셀을 밀어냄
5. 숫자 금액/상태 badge가 세로 정렬이 안 맞음
6. 모바일에서 제목과 버튼이 겹침
```

공통 스타일 원칙:

```text
- 주요 카드: 제목, 값, 설명이 일정한 높이와 간격을 유지
- 테이블 셀: vertical-align middle
- 긴 텍스트: truncate 또는 line-clamp 적용
- 버튼 그룹: 한 줄에 너무 많으면 dropdown/menu로 이동
- badge: inline-flex, items-center 기준 정렬
```

---

# Part B. 공통 UI 규칙 정리

가능하면 공통 class 또는 reusable component로 정리하세요.

권장 컴포넌트:

```text
PageHeader
SummaryCard
StatusBadge
ActionMenu
ResponsiveTable
EmptyState
LoadingState
ErrorState
```

공통 규칙:

```text
1. 페이지 상단: 제목 + 설명 + 주요 액션
2. 요약 카드: 2~4개 우선 표시
3. 위험/보조 작업: 더보기 메뉴로 이동
4. 긴 내용: 미리보기 + 전체 보기
5. 빈 상태: 안내 문구와 다음 행동 버튼 표시
```

---

# Part C. 테이블 가독성 개선

대상 화면:

```text
Members
Payments/회비
Activities
Activity Detail > 참가자
Activity Detail > 활동비
Activity Detail > 파일함
Activity Detail > 증빙
Transactions
Receipts
Dashboard
```

수정 요구:

```text
1. 테이블이 화면 밖으로 깨지면 가로 스크롤 적용
2. 모바일에서는 중요한 컬럼만 보이게 하거나 카드형 리스트로 전환
3. 긴 파일명/활동명/이름은 truncate 처리
4. 금액 컬럼은 우측 정렬
5. 상태 컬럼은 badge로 통일
6. 작업 버튼은 [수정] + [더보기] 중심으로 정리
```

모바일 기준:

```text
화면 폭이 좁을 때:
- 모든 컬럼을 억지로 보여주지 않음
- 핵심 정보만 카드형으로 표시
- 상세 정보는 펼치기/모달/상세 페이지에서 확인
```

---

# Part D. 모바일 최적화

모바일에서 다음이 안정적으로 동작해야 합니다.

```text
1. 사이드바 열기/닫기
2. 상단 헤더가 화면을 가리지 않음
3. 대시보드 캘린더가 깨지지 않음
4. 탭이 많으면 가로 스크롤 또는 드롭다운으로 표시
5. 테이블은 카드형 또는 가로 스크롤로 표시
6. 버튼이 화면 밖으로 나가지 않음
7. 모달이 모바일 화면 안에 맞게 표시
8. 파일 미리보기 이미지가 화면 폭에 맞게 조절됨
```

우선 모바일 breakpoint는 Tailwind 기준으로 다음을 사용하세요.

```text
sm
md
lg
```

권장 방식:

```text
desktop: table
mobile: card list
```

---

# Part E. 대시보드 정리

Task 35에서 캘린더를 추가했습니다.
이번 Task에서는 대시보드를 더 깔끔하게 보이도록 정리하세요.

수정 요구:

```text
1. 캘린더가 최상단에서 안정적으로 보이도록 유지
2. 요약 카드 높이 통일
3. 카드 제목/수치/설명 줄바꿈 정리
4. 처리해야 할 일 목록을 너무 길게 보여주지 않음
5. 최근 활동/최근 파일/최근 AI 작업은 3~5개만 표시
6. 모바일에서는 캘린더 아래에 요약 카드가 1열로 표시
```

---

# Part F. 활동 상세 화면 정리

활동 상세는 기능이 많아서 특히 정리가 필요합니다.

탭 구조:

```text
개요
AI 작업
참가자
보고서
활동비
증빙
파일함
```

수정 요구:

```text
1. 탭이 모바일에서 깨지지 않도록 가로 스크롤 처리
2. 각 탭 상단에 간단한 설명 추가
3. 너무 많은 버튼은 섹션별로 분리
4. 활동비 탭은 Task 31 구조 유지
5. 증빙/파일함 탭은 Task 34 구조 유지
6. HWPX 생성/다운로드 버튼은 명확히 표시
```

---

# Part G. AI 결과 카드 UI 개선

AI 결과 카드가 길어질 때 보기 어렵습니다.

수정 요구:

```text
1. 결과 요약 먼저 표시
2. 상세 로그/diagnostics는 접기/펼치기로 숨김
3. proposed_action row가 많으면 최대 5개만 먼저 표시
4. 전체 보기 버튼 제공
5. 확인 후 반영 / 취소 버튼은 항상 잘 보이게 배치
6. 모바일에서 버튼이 세로로 자연스럽게 쌓이게 처리
```

Diagnostics는 기본 접힘 상태로 두세요.

표시 항목:

```text
intent
domain
scope
payment_type
activity_id
action_id
service_called
```

---

# Part H. HWPX/파일 미리보기 UI 정리

파일명이나 문서명이 길어서 깨지는 경우가 많습니다.

수정 요구:

```text
1. 긴 파일명은 truncate
2. hover 또는 상세보기에서 전체 파일명 표시
3. 다운로드/미리보기/삭제 버튼을 일관된 위치에 배치
4. HWPX 파일은 다운로드 중심
5. 이미지 파일은 화면 폭에 맞춰 preview
6. 파일 카드 높이 과도하게 늘어나지 않게 조정
```

---

# Part I. 접근성/상태 표시

다음 상태를 일관되게 보여주세요.

```text
Loading
Empty
Error
Success
Confirm required
Needs review
```

각 화면에서 데이터가 없을 때 빈 테이블만 보이지 않게 하세요.

예:

```text
아직 등록된 활동이 없습니다.
새 활동을 만들거나 AI 작업실에서 활동을 생성해보세요.
```

---

# 수정 대상

Frontend 중심 작업입니다.

```text
frontend/app/dashboard/page.tsx
frontend/app/members/page.tsx
frontend/app/members/[id]/page.tsx
frontend/app/payments/page.tsx
frontend/app/activities/page.tsx
frontend/app/activities/[id]/page.tsx
frontend/app/transactions/page.tsx
frontend/app/receipts/page.tsx
frontend/components/assistant/AssistantResultCard.tsx
frontend/lib/api.ts
frontend/components/*
```

필요하면 공통 UI 컴포넌트를 추가하세요.

```text
frontend/components/ui/ResponsiveTable.tsx
frontend/components/ui/StatusBadge.tsx
frontend/components/ui/ActionMenu.tsx
frontend/components/ui/PageHeader.tsx
frontend/components/ui/SummaryCard.tsx
```

Backend는 원칙적으로 최소 수정입니다.
단, UI에서 필요한 count/summary가 부족하면 기존 summary API를 보강하세요.

---

# 테스트 및 검증

프론트 빌드는 반드시 통과해야 합니다.

```bash
cd frontend
npm run build
```

백엔드는 수정했다면 함께 검증하세요.

```bash
cd backend
python -m compileall app
pytest
```

브라우저 검증:

```text
1. Dashboard
   - 캘린더가 최상단에서 깨지지 않음
   - 요약 카드가 일정한 높이로 보임
   - 모바일 폭에서도 깨지지 않음

2. Members
   - 101명 이상 pagination/목록이 보기 좋음
   - 임원 badge가 한 줄에 잘 보임
   - 상세 페이지가 모바일에서도 읽기 좋음

3. Payments/회비
   - 테이블이 가로로 깨지지 않음
   - 금액/상태/작업 버튼 정렬이 안정적임

4. Activity Detail
   - 탭이 모바일에서 깨지지 않음
   - 활동비 탭 버튼이 난잡하지 않음
   - 증빙/파일함 미리보기와 버튼이 정리됨

5. AI Result Card
   - 긴 결과가 접힘/펼침으로 보임
   - 확인 후 반영 버튼이 잘 보임
   - diagnostics는 기본 접힘

6. Transactions
   - 긴 거래 적요가 레이아웃을 깨지 않음
   - 모바일에서 확인 가능
```

---

# 완료 기준

```text
1. 글씨가 아래로 밀리거나 겹치는 주요 문제가 해결된다.
2. 긴 텍스트가 레이아웃을 깨지 않는다.
3. 테이블은 데스크톱/모바일에서 모두 사용 가능하다.
4. 모바일에서 주요 화면이 심하게 깨지지 않는다.
5. 활동 상세 탭과 AI 결과 카드가 보기 좋게 정리된다.
6. 위험 작업 버튼은 더보기/모달로 정리된다.
7. 빈 상태/로딩/에러 상태가 일관되게 표시된다.
8. npm run build 통과
9. backend 수정 시 pytest 통과
```

---

# 완료 보고 형식

```text
Task 36 완료 보고

1. 원인
- 글씨 밀림/레이아웃 깨짐 원인:
- 모바일 불편 원인:

2. 수정한 파일
- frontend:
- backend:
- components:

3. 공통 UI 정리
- PageHeader:
- SummaryCard:
- StatusBadge:
- ResponsiveTable:
- ActionMenu:

4. 화면별 개선
- Dashboard:
- Members:
- Payments:
- Activities:
- Activity Detail:
- Transactions:
- Receipts:
- AI Result Card:

5. 모바일 최적화
- sidebar:
- tables:
- tabs:
- modals:
- file preview:

6. 검증
- npm run build:
- pytest:
- browser:
- mobile viewport:

권장 커밋 메시지:
task36: improve responsive layout and UI readability
```
