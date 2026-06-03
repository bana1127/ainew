# Task 41. 활동 일정 캘린더 추가 및 참가자-활동비 상태 동기화 수정

현재 프로젝트는 ClubAgent입니다.

Task 40까지 예산 관리, 회비, 활동비, HWPX, 상태 일관성 정리를 진행했습니다.

이번 Task 41의 목표는 두 가지입니다.

```text
1. 활동 일정이 캘린더에 제대로 표시되고 관리되도록 구현
2. 활동 참가자 제거/취소 시 활동비 요약, 납부 현황, 체크리스트가 현재 참가자 기준으로 정확히 동기화되도록 수정
```

---

# 1. 현재 오류

활동 상세 > 활동비 탭에서 참가자를 제거하면 해당 인원의 activity_fee record가 `취소` 상태로 바뀌기는 합니다.

하지만 화면에서는 다음 문제가 남아 있습니다.

```text
1. 활동비 요약의 참가자 수가 여전히 제거 전 인원으로 표시됨
2. 납부 현황 테이블 제목이 취소자를 포함한 22명으로 표시됨
3. 체크리스트의 활동비 납부 완료가 20/22처럼 취소자를 포함해서 계산됨
4. 실제 현재 참가자는 20명인데 활동비 모수는 22명으로 계산됨
5. 취소된 사람도 기본 납부 현황 테이블에 계속 표시됨
6. 활동비 총 예정 금액도 현재 참가자가 아니라 전체 activity_fee record 기준으로 계산될 수 있음
```

예상 동작은 다음입니다.

```text
현재 참가자 20명
취소된 참가자 2명

활동비 요약:
참가자 20명
납부 완료 20명
미납 0명
총 예정 200,000원
총 납부 200,000원

체크리스트:
활동비 납부 완료 20/20

납부 현황 기본 테이블:
현재 참가자 20명만 표시

취소된 기록:
기본 숨김
[취소/제외 기록 보기] 버튼으로만 표시
```

---

# 2. 활동비 상태 계산 기준 재정의

activity_fee 납부 현황의 기본 기준은 반드시 **현재 활동 참가자**입니다.

## 현재 참가자에 포함할 상태

```text
confirmed
applied
completed
attended
participant
active
```

프로젝트에서 실제로 쓰는 participant status enum에 맞춰 적용하세요.

## 현재 참가자에서 제외할 상태

```text
removed
cancelled
excluded
deleted
inactive
```

---

# 3. activity_fee record 표시 정책

활동 상세 > 활동비 탭의 기본 납부 현황에는 다음 record만 표시하세요.

```text
1. 현재 활동에 active participant로 연결된 member
2. payment_type = activity_fee
3. 해당 activity_id에 연결된 record
4. status가 cancelled/excluded가 아닌 record
```

기본 납부 현황에서 제외할 record:

```text
1. 참가자에서 제거된 사람
2. participant status가 removed/cancelled/excluded인 사람
3. activity_fee status가 cancelled/excluded인 record
```

단, 이력 보존을 위해 record를 물리 삭제하지는 마세요.

별도 버튼을 추가하세요.

```text
[취소/제외 기록 보기]
```

이 버튼을 누르면 취소/제외된 activity_fee record를 별도 섹션 또는 접힌 목록으로 보여주세요.

---

# 4. 활동비 요약 계산 수정

활동비 요약은 현재 참가자 기준으로 계산해야 합니다.

계산 대상:

```text
현재 active participant에 연결된 activity_fee record
```

제외 대상:

```text
cancelled/excluded/removed participant
cancelled/excluded activity_fee record
```

요약 필드:

```text
참가자 수
납부 완료
미납
부분 납부
초과 납부
환불 필요
총 예정
총 납부
```

계산 예:

```text
현재 참가자 20명
1인당 활동비 10,000원
20명 전원 10,000원 납부

참가자 수 = 20
납부 완료 = 20
미납 = 0
총 예정 = 200,000원
총 납부 = 200,000원
```

취소된 2명의 record가 남아 있어도 기본 요약에는 포함하지 마세요.

---

# 5. 체크리스트 계산 수정

활동 상세 상단 체크리스트의 활동비 항목도 현재 참가자 기준으로 계산하세요.

현재 잘못된 예:

```text
활동비 납부 완료 20/22
```

수정 후:

```text
활동비 납부 완료 20/20
```

조건:

```text
현재 참가자 20명 중 20명이 paid이면 완료
```

취소/제외 participant는 denominator에 들어가면 안 됩니다.

---

# 6. 참가자 제거/재추가 동작

## 참가자 제거 시

참가자 제거 API 호출 시 다음을 수행하세요.

```text
1. ActivityParticipant status를 removed/cancelled로 변경
2. 해당 activity_id + member_id의 activity_fee record 조회
3. paid_amount = 0이면 status = cancelled 또는 excluded
4. paid_amount > 0이면 status = cancelled, refund_status = refund_needed
5. 기본 활동비 납부 현황에서는 제외
6. 활동비 요약/체크리스트/예산관리/Dashboard 재계산
```

## 참가자 재추가 시

같은 member를 다시 활동에 추가하면 새 record를 중복 생성하지 마세요.

```text
1. 기존 cancelled/removed participant가 있으면 복구
2. 기존 cancelled/excluded activity_fee record가 있으면 복구
3. required_amount는 현재 활동비 기준으로 갱신
4. paid_amount는 기존 값을 유지
5. status는 required_amount / paid_amount 기준으로 재계산
```

---

# 7. 활동비 대상 생성/갱신 버튼 수정

활동 상세 > 활동비 탭의 버튼:

```text
활동비 대상 생성/갱신
```

동작 기준:

```text
현재 활동 참가자만 기준으로 activity_fee 대상 생성/갱신
```

구체 동작:

```text
1. 현재 active participant 목록 조회
2. active participant에게 activity_fee record가 없으면 생성
3. active participant의 기존 record는 required_amount 갱신, paid_amount 유지
4. 현재 participant가 아닌 사람의 record는 기본 목록에서 제외
5. 참가자에서 제거된 사람의 unpaid record는 cancelled/excluded 처리
6. paid_amount가 있는 제거 record는 refund_needed 처리
```

---

# 8. 예산 관리/Dashboard/챗봇 연동

다음 화면과 기능에서도 취소/제외된 참가자를 activity_fee 미납/총 예정/참가자 수에 포함하지 마세요.

```text
Dashboard
예산 관리
활동별 정산 현황
활동비 미납 요약
감사 체크리스트
감사자료 패키지 preview
Floating Chatbot
```

예:

```text
활동비 미납 있는 활동 알려줘
```

응답 시 취소된 activity_fee record는 미납으로 세면 안 됩니다.

---

# 9. 캘린더 일정 추가

이번 Task 41에서 활동 일정 캘린더 기능도 함께 구현합니다.

## 목표

활동 날짜가 있는 모든 활동은 캘린더에 표시되어야 합니다.

현재 Dashboard에 캘린더가 있다면 보강하고, 없다면 다음 위치 중 하나에 구현하세요.

```text
1. Dashboard 상단 월간 캘린더
2. 활동 관리 페이지의 캘린더 보기
3. 활동 상세에서 일정 정보 수정
```

우선순위는 다음입니다.

```text
1. Dashboard 월간 캘린더
2. 활동 관리 페이지 캘린더 보기
3. 활동 상세 일정 수정
```

---

# 10. 캘린더 표시 요구사항

캘린더에는 활동을 날짜별로 표시하세요.

활동 event 정보:

```text
활동명
활동일
장소
상태
참가자 수
보고서 상태
활동비 상태
증빙 상태
```

월간 캘린더에서 활동명은 너무 길면 줄이세요.

```text
위퍼퓸 교내조향활동
```

클릭 시:

```text
활동 상세 페이지로 이동
/activities/{activity_id}
```

활동비 문제가 있는 활동이면 badge 또는 색상/표시 문구를 추가하세요.

```text
활동비 미납
증빙 필요
보고서 미작성
```

---

# 11. 캘린더 필터

캘린더에 필터를 추가하세요.

```text
전체
예정
진행 중
완료
처리 필요
```

처리 필요 기준:

```text
보고서 미작성
활동비 미납
증빙 누락
제출용 파일 미지정
```

---

# 12. 캘린더 API

필요하면 다음 API를 추가하세요.

```http
GET /api/calendar/activities?year=2026&month=6
```

응답 예시:

```json
{
  "year": 2026,
  "month": 6,
  "items": [
    {
      "activity_id": "...",
      "title": "위퍼퓸 교내조향활동",
      "date": "2026-06-03",
      "location": "A401",
      "status": "planned",
      "participant_count": 20,
      "needs_attention": false,
      "badges": ["활동비 완료", "증빙 확인"],
      "target_url": "/activities/..."
    }
  ]
}
```

---

# 13. 활동 상세 일정 수정

활동 상세의 개요 탭 또는 상단 정보에서 활동일/장소를 수정할 수 있게 하세요.

수정 가능 항목:

```text
활동일
장소
활동명
활동 상태
```

수정 후:

```text
1. 활동 상세 refetch
2. Dashboard 캘린더 refetch
3. 활동 목록 refetch
```

---

# 14. UI 가독성

활동비/거래내역/예산관리 테이블에서 상태 배지가 세로로 쪼개지지 않게 유지하세요.

필수:

```text
badge는 whitespace-nowrap
table wrapper는 overflow-x-auto
table은 min-width 적용
작업 버튼은 한 줄 유지
```

특히 다음 텍스트는 세로로 표시되면 안 됩니다.

```text
확인 필요
매칭 취소
납부 완료
활동비 미납
```

---

# 15. 수정 대상

Backend:

```text
backend/app/routers/activities.py
backend/app/routers/dashboard.py
backend/app/routers/budget.py
backend/app/routers/calendar.py
backend/app/services/activity_participant_service.py
backend/app/services/activity_fee_service.py
backend/app/services/payment_status_service.py
backend/app/services/activity_calendar_service.py
backend/app/services/budget_service.py
backend/app/services/activity_audit_check_service.py
backend/app/schemas/activity.py
backend/app/schemas/calendar.py
```

Frontend:

```text
frontend/app/dashboard/page.tsx
frontend/app/activities/page.tsx
frontend/app/activities/[id]/page.tsx
frontend/lib/api.ts
frontend/components/calendar/*
frontend/components/activities/*
frontend/components/payments/*
```

필요하면 신규 컴포넌트:

```text
frontend/components/calendar/ActivityMonthCalendar.tsx
frontend/components/calendar/ActivityCalendarEvent.tsx
frontend/components/activities/ActivityFeeCancelledRecords.tsx
```

---

# 16. 테스트

추가 또는 보강:

```text
backend/tests/test_activity_participant_remove_fee_sync.py
backend/tests/test_activity_fee_summary_excludes_cancelled.py
backend/tests/test_activity_fee_checklist_counts.py
backend/tests/test_activity_fee_readd_participant.py
backend/tests/test_activity_calendar_api.py
backend/tests/test_dashboard_calendar.py
```

필수 테스트:

```text
1. 참가자 22명 중 2명 제거 시 현재 참가자 수는 20명
2. 제거된 participant는 activity_fee 요약에서 제외
3. 제거된 unpaid activity_fee는 미납으로 계산되지 않음
4. paid_amount가 있는 제거 record는 refund_needed 처리
5. 체크리스트 활동비 납부 완료가 20/20으로 표시
6. 납부 현황 기본 테이블에는 20명만 표시
7. 취소/제외 기록 보기에서는 취소된 2명 표시
8. 제거된 참가자 재추가 시 중복 생성 없이 복구
9. 캘린더 API가 해당 월 활동을 반환
10. 캘린더 event target_url이 활동 상세로 연결
11. 처리 필요 활동에 badge가 포함됨
```

---

# 17. 브라우저 검증

```text
1. 활동 상세 접속
2. 참가자 수와 활동비 납부 현황 수 확인
3. 참가자 1명 제거
4. 활동비 탭으로 이동
5. 납부 현황 기본 목록에서 제거된 사람이 사라졌는지 확인
6. 활동비 요약의 참가자 수가 줄었는지 확인
7. 체크리스트가 20/20처럼 현재 참가자 기준으로 바뀌는지 확인
8. [취소/제외 기록 보기]에서 제거된 사람 확인
9. 제거된 사람을 다시 추가했을 때 중복 없이 복구되는지 확인
10. Dashboard 캘린더에서 활동이 해당 날짜에 표시되는지 확인
11. 캘린더 event 클릭 시 활동 상세로 이동하는지 확인
12. 활동 상세에서 날짜/장소 수정 후 캘린더에 반영되는지 확인
```

---

# 18. 완료 기준

```text
1. 참가자 제거 후 활동비 기본 납부 현황에서 제거된 사람이 보이지 않는다.
2. 취소된 activity_fee record는 기본 미납/완납/총 예정 계산에서 제외된다.
3. 체크리스트 활동비 완료 비율이 현재 참가자 기준으로 표시된다.
4. 예산 관리/Dashboard/챗봇에서도 취소된 activity_fee가 미납으로 잡히지 않는다.
5. 취소/제외 기록은 별도 보기로 확인 가능하다.
6. 제거된 참가자를 재추가해도 중복 participant/payment record가 생기지 않는다.
7. Dashboard 또는 활동 관리에 월간 활동 캘린더가 표시된다.
8. 캘린더 event 클릭 시 활동 상세로 이동한다.
9. 활동일/장소 수정 후 캘린더가 갱신된다.
10. pytest 통과
11. npm run build 통과
```

---

# 19. 완료 보고 형식

```text
Task 41 완료 보고

1. 원인
- 참가자 제거 후 활동비 모수에 남던 이유:
- 체크리스트가 20/22로 표시되던 이유:
- 캘린더 기능이 필요했던 이유:

2. 수정 파일
- backend:
- frontend:
- tests:

3. 참가자-활동비 동기화
- 참가자 제거:
- activity_fee 취소/제외:
- 재추가 복구:
- refund_needed:

4. 활동비 요약/체크리스트
- 현재 참가자 기준:
- 취소 기록 제외:
- 취소/제외 기록 보기:

5. 연동 화면
- Activity Detail:
- Dashboard:
- Budget:
- Chatbot:
- Audit:

6. 캘린더
- API:
- Dashboard UI:
- 활동 관리 UI:
- event click:
- 일정 수정:

7. UI 가독성
- badge nowrap:
- table overflow:
- mobile:

8. 검증
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task41: add activity calendar and sync activity fees with active participants
```
