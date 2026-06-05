Task 42 완료 보고

1. 원인
- 기존 Dashboard 캘린더는 날짜 클릭 시 ActivityReport 생성 모달만 열어 일반 회의/마감/메모성 일정을 활동과 분리해 저장할 수 없었다.
- 일반 일정이 ActivityReport로 들어가면 활동 수, 활동비, 보고서, 증빙, 정산 집계에 섞일 위험이 있었다.
- 플로팅 챗봇은 일부 단순 카운트만 처리해 운영 데이터 요약 질문을 충분히 답하지 못했다.

2. 수정 파일
- backend: models/calendar.py, schemas/calendar.py, routers/calendar.py, services/calendar_event_service.py, services/assistant_activity_insight_service.py
- backend 변경: main.py, models/__init__.py, schemas/assistant.py, services/assistant_query_service.py
- frontend 변경: components/dashboard/DashboardCalendar.tsx, components/assistant/AssistantChatPanel.tsx, lib/api.ts
- migration: backend/alembic/versions/20260604_0016_task42_calendar_events.py
- tests: test_calendar_general_events.py, test_assistant_activity_insights.py 및 기존 플로팅 챗봇 테스트 보정

3. 모델/API
- CalendarEvent 모델 추가: title, event_type, event_date, start/end_time, location, description, status, activity_report_id, is_all_day, deleted_at.
- API 추가:
  - GET /api/calendar/events
  - POST /api/calendar/events
  - PATCH /api/calendar/events/{event_id}
  - DELETE /api/calendar/events/{event_id}
- GET은 ActivityReport 기반 activity event와 CalendarEvent 기반 general/deadline/meeting event를 합쳐 반환한다.

4. UI
- Dashboard 캘린더 날짜 클릭 시 선택 모달 표시:
  - 활동 만들기
  - 일반 일정 추가
  - 취소
- 일반 일정 생성/수정/삭제 모달 추가.
- activity event는 활동 상세로 이동하고, general/deadline/meeting event는 수정 모달을 연다.

5. 집계 분리
- 일반 일정은 ActivityReport를 생성하지 않는다.
- 전체 활동 수, 활동비, 참가자, 보고서, 증빙, 감사자료 패키지, 활동별 정산 집계에 포함되지 않는다.

6. 챗봇 연동 준비
- activity_overview, activity_detail_insight, activity_fee_insight, membership_fee_insight, calendar_schedule, budget_insight, evidence_summary, report_summary, transaction_review intent 추가.
- 활동비 링크는 /activities/{id}?tab=activity-fee, 회비 링크는 /payments 유지.
- 프론트 플로팅 챗봇은 last_activity_id context를 넘겨 후속 질문을 지원한다.

7. 검증
- alembic upgrade head 통과.
- python -m compileall backend\app 통과.
- 대상 pytest 27개 통과.
- frontend npm run build 통과.
- 전체 pytest는 전역 Python 환경에서 psycopg/fastapi 누락 및 기존 테스트 스텁 수집 이슈로 실패했다.

8. 권장 커밋 메시지
- task42: add general calendar events separate from activities
- task42: expand assistant with activity insights and calendar-aware answers
