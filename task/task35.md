# Task 35. 대시보드 월간 캘린더 추가 및 화면 정리

현재 프로젝트는 ClubAgent입니다.

Task 34까지 진행하면서 부원, 회비, 활동비, 거래내역, 영수증/증빙, 파일함, HWPX 생성 흐름을 정리했습니다.

이번 Task 35의 목표는 **대시보드를 실제 운영자가 보기 편한 홈 화면으로 정리**하는 것입니다.

현재 문제:

```text
1. 대시보드에 요약 카드와 활동 현황이 있지만 전체적으로 난잡해 보임
2. 월 단위로 활동 일정을 한눈에 보기 어렵다
3. 가장 중요한 일정 정보가 먼저 보이지 않는다
4. 활동, 미납, 증빙, 보고서 상태가 흩어져 보여 우선순위 파악이 어렵다
```

이번 Task에서는 **대시보드 상단에 월간 캘린더를 추가**하고, 전체 레이아웃을 더 보기 좋게 정리합니다.

---

# 핵심 목표

대시보드 구조를 다음처럼 정리합니다.

```text
1. 월간 캘린더
2. 이번 달 주요 요약
3. 처리해야 할 일
4. 최근 활동 / 최근 파일 / 최근 AI 작업
```

가장 먼저 보여야 하는 것은 **월간 캘린더**입니다.

---

# Part A. 월간 캘린더 추가

## 위치

대시보드 최상단에 월간 캘린더를 배치하세요.

```text
Dashboard
→ Monthly Calendar
→ Summary Cards
→ To-do / Recent Activity
```

## 표시 단위

기본은 현재 월입니다.

```text
2026년 6월
```

캘린더에는 이전/다음 달 이동 버튼을 제공합니다.

```text
[이전 달] 2026년 6월 [다음 달]
```

## 캘린더 데이터

우선 내부 Activity 데이터를 기반으로 표시합니다.

대상:

```text
ActivityReport.activity_date
Activity.title
Activity.location
Activity.status
```

활동 날짜가 있는 활동은 해당 날짜 칸에 표시합니다.

표시 예시:

```text
6월 3일
- 위퍼퓸 교내조향활동
```

활동 상태에 따라 badge를 표시합니다.

```text
예정
진행
완료
보고서 필요
증빙 필요
```

---

# Part B. 캘린더 이벤트 구성

캘린더에 표시할 이벤트는 우선 다음으로 제한합니다.

```text
1. 활동 일정
2. 보고서 마감이 필요한 활동
3. 증빙이 부족한 활동
4. 회비/활동비 관련 마감이 있으면 표시
```

이번 Task에서는 복잡한 외부 캘린더 연동은 하지 않습니다.

```text
Google Calendar 연동은 이번 Task에서 구현하지 않음
외부 SaaS 연동은 후속 Task로 분리
```

---

# Part C. 캘린더 UI 요구사항

캘린더는 월간 달력 형태로 보여야 합니다.

필수 UI:

```text
1. 월 제목
2. 이전 달 / 다음 달 버튼
3. 요일 헤더
4. 날짜 칸
5. 해당 날짜의 활동 목록
6. 오늘 날짜 강조
7. 활동 클릭 시 활동 상세로 이동
```

활동이 너무 많으면 처음 2~3개만 보이고 나머지는 다음처럼 표시합니다.

```text
+3개 더보기
```

더보기를 누르면 해당 날짜의 활동 목록을 모달 또는 펼침으로 표시합니다.

---

# Part D. Dashboard Summary 정리

현재 요약 카드가 너무 많거나 흐름이 난잡하면 다음 기준으로 정리하세요.

상단 요약 카드는 4개 정도로 제한합니다.

권장 카드:

```text
이번 달 활동 수
처리 필요 활동
회비 미납
활동비 미납
```

또는 현재 구현 상태에 맞춰 다음으로 구성할 수 있습니다.

```text
전체 부원
이번 달 활동
회비 미납
증빙 필요
```

중요한 점:

```text
한 화면에 너무 많은 카드를 노출하지 않는다.
중요한 지표만 먼저 보여준다.
```

---

# Part E. 처리해야 할 일 섹션 정리

대시보드의 “오늘 처리할 일” 또는 “처리해야 할 일” 섹션을 더 명확히 정리하세요.

표시 항목:

```text
1. 회비 미납 확인
2. 활동비 미납 확인
3. 보고서 미작성 활동
4. 증빙 부족 활동
5. HWPX 미생성 활동
```

각 항목은 클릭하면 관련 화면으로 이동해야 합니다.

예:

```text
회비 미납 12명 → /payments
활동비 미납 4건 → 해당 활동 또는 활동 목록
보고서 미작성 2건 → 활동 상세
증빙 부족 1건 → 활동 상세 증빙 탭
```

---

# Part F. 최근 활동 섹션

대시보드 하단에는 최근 활동을 간단히 보여주세요.

구성:

```text
최근 활동
최근 업로드 파일
최근 AI 작업
```

너무 길면 각 섹션은 3~5개만 표시합니다.

더 필요한 경우 “전체 보기” 링크를 제공합니다.

---

# Part G. API 요구사항

대시보드용 API를 보강하세요.

기존 API가 있다면 확장하고, 없으면 다음 형태를 추가하세요.

```http
GET /api/dashboard/summary
GET /api/dashboard/calendar?month=2026-06
```

캘린더 응답 예시:

```json
{
  "month": "2026-06",
  "events": [
    {
      "id": "...",
      "type": "activity",
      "title": "위퍼퓸 교내조향활동",
      "date": "2026-06-03",
      "location": "A401",
      "status": "completed",
      "needs_report": false,
      "needs_evidence": true,
      "url": "/activities/..."
    }
  ]
}
```

summary 응답은 현재 대시보드 카드에 필요한 값만 반환하세요.

---

# Part H. Frontend 수정 대상

확인 대상:

```text
frontend/app/dashboard/page.tsx
frontend/lib/api.ts
frontend/components/*
```

가능하면 컴포넌트 분리:

```text
DashboardCalendar
DashboardSummaryCards
DashboardTodoList
DashboardRecentActivity
```

---

# Part I. Backend 수정 대상

확인 대상:

```text
backend/app/routers/dashboard.py
backend/app/routers/activities.py
backend/app/models/activity_report.py
backend/app/models/payment.py
backend/app/models/uploaded_file.py
```

필요하면 service 추가:

```text
backend/app/services/dashboard_service.py
```

---

# Part J. 모바일/작은 화면 고려

캘린더는 작은 화면에서 깨지지 않게 처리하세요.

모바일에서는 다음 중 하나로 표시합니다.

```text
1. 월간 캘린더 유지 + 가로 스크롤
2. 주간/리스트 형태로 변환
3. 날짜별 리스트로 축약
```

최소 기준:

```text
모바일에서 내용이 화면 밖으로 심하게 깨지면 안 됨
```

---

# Part K. 테스트

추가 또는 보강:

```text
backend/tests/test_dashboard_calendar.py
backend/tests/test_dashboard_summary.py
```

필수 테스트:

```text
1. activity_date가 있는 활동이 calendar event로 반환됨
2. month 파라미터에 해당하는 활동만 반환됨
3. 삭제된 활동은 calendar event에서 제외됨
4. report/evidence 필요 여부가 계산됨
5. dashboard summary가 회비/활동비/증빙/보고서 상태를 반환함
```

---

# 브라우저 검증

```text
1. Dashboard 접속
2. 월간 캘린더가 가장 먼저 보이는지 확인
3. 현재 월 활동이 날짜에 표시되는지 확인
4. 이전/다음 달 이동 확인
5. 활동 클릭 시 상세 페이지로 이동 확인
6. 요약 카드가 너무 많지 않고 정리되어 보이는지 확인
7. 처리해야 할 일 섹션에서 관련 페이지로 이동되는지 확인
8. 모바일 폭에서 캘린더가 깨지지 않는지 확인
```

---

# 완료 기준

```text
1. 대시보드 최상단에 월간 캘린더가 표시된다.
2. 활동 일정이 날짜별로 표시된다.
3. 이전/다음 달 이동이 가능하다.
4. 활동 클릭 시 상세 페이지로 이동한다.
5. 요약 카드가 보기 좋게 정리된다.
6. 처리해야 할 일 섹션이 명확하다.
7. 최근 활동/파일/AI 작업이 간단히 표시된다.
8. 모바일 화면에서 심하게 깨지지 않는다.
9. pytest 통과
10. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 35 완료 보고

1. 원인
- 대시보드가 난잡해 보였던 이유:
- 캘린더가 필요했던 이유:

2. 수정한 파일
- backend:
- frontend:
- tests:

3. 캘린더
- API:
- 월 이동:
- 이벤트 표시:
- 활동 상세 이동:

4. 대시보드 정리
- 요약 카드:
- 처리해야 할 일:
- 최근 활동:

5. 반응형
- 데스크톱:
- 모바일:

6. 검증
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task35: add dashboard calendar and simplify dashboard layout
```
