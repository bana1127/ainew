현재 프로젝트는 ClubAgent입니다.

Task 46. 운영 챗봇 상세 조회 성능 개선

목표는 오른쪽 하단 ClubAgent 운영 챗봇이 실제 DB/API 데이터를 기반으로 활동, 부원, 회비, 활동비, 예산, 증빙, 일정 상태를 더 정확하고 상세하게 답변하도록 개선하는 것입니다.

현재 문제:

1. 활동 목록 화면에는 활동이 보이는데 챗봇은 “활동은 총 0개입니다”라고 잘못 답변합니다.
2. 챗봇 답변이 너무 짧고 구체적인 정보가 부족합니다.
3. 활동명, 활동일, 장소, 참여자 수, 활동비 납부 상태, 증빙 상태, 보고서 상태, 체크리스트 상태 등을 충분히 제공하지 않습니다.
4. 질문 의도에 따라 필요한 세부 API를 추가 조회하지 않고 단순 summary만 반환하는 것으로 보입니다.
5. 챗봇이 현재 페이지의 컨텍스트를 잘 활용하지 못합니다.

핵심 수정 목표:

1. 챗봇의 데이터 소스를 실제 backend API/DB 기준으로 통일
2. 활동 개수 오류 수정
3. 질문 의도별 상세 조회 라우팅 추가
4. 답변에 구체적인 수치, 목록, 상태, 바로가기 링크 포함
5. 현재 페이지 컨텍스트 활용
6. 데이터가 0건일 때도 “왜 0건인지” 가능한 사유 제공

────────────────────────

1. 활동 개수 오류 수정
   ────────────────────────

현재 Activities 화면에는 활동 카드가 존재하는데 챗봇이 “활동은 총 0개”라고 답하는 문제가 있습니다.

먼저 다음을 점검하세요.

* 챗봇이 호출하는 활동 조회 API
* Activities 페이지가 호출하는 활동 조회 API
* 두 API의 필터 차이
* status 필터 차이
* planned/생성됨 상태가 count에서 제외되는지 여부
* deleted/cancelled만 제외해야 하는데 planned까지 제외하는지 여부
* pagination limit 때문에 일부만 보는지 여부
* tenant/club_id/user_id 조건이 다른지 여부

수정 기준:

* “활동 몇 개 있어?” 질문은 삭제된 활동을 제외한 전체 활동 수를 기준으로 답해야 합니다.
* 기본적으로 planned, ongoing, completed, draft 상태는 포함합니다.
* cancelled/deleted 상태는 기본 count에서 제외하되, 사용자가 “취소된 활동 포함”이라고 물으면 포함합니다.

예상 답변:
“현재 등록된 활동은 총 1개입니다.

1. 교내 조향 활동

* 활동일: 2026-05-20
* 장소: A401호
* 상태: 생성됨
* 참여자: 20명
* 보고서: 생성됨
* 활동비: 20명 중 20명 납부
* 영수증/증빙: 2건

활동 목록에서 확인할 수 있습니다.”

────────────────────────
2. 챗봇 전용 운영 조회 서비스 추가
────────────────────────

챗봇이 여러 페이지의 데이터를 안정적으로 조회할 수 있도록 전용 service를 만드세요.

권장 파일:
backend/app/services/ops_chatbot_query_service.py

기능:

* get_activity_overview()
* get_activity_detail_summary(activity_id or activity_name)
* get_member_overview()
* get_membership_fee_overview(term)
* get_activity_fee_overview(activity_id)
* get_budget_overview(quarter)
* get_evidence_overview(activity_id or quarter)
* get_calendar_overview(month)
* get_todo_overview()
* search_entities(query)

주의:
챗봇이 프론트 화면 상태만 보고 답하면 안 됩니다.
반드시 backend DB/API 기준으로 조회하세요.

────────────────────────
3. 질문 의도 분류 개선
────────────────────────

챗봇 질문을 다음 intent로 분류하세요.

활동 관련:

* activity_count
* activity_list
* activity_detail
* activity_participants
* activity_fee_status
* activity_evidence_status
* activity_report_status
* activity_photo_status
* activity_checklist_status

부원 관련:

* member_count
* executive_list
* member_search
* member_status

회비 관련:

* membership_fee_summary
* unpaid_members
* paid_members
* exempt_members

활동비 관련:

* activity_fee_summary
* activity_fee_unpaid
* activity_fee_paid

예산/거래 관련:

* budget_summary
* income_expense_summary
* transaction_search
* quarter_summary

증빙 관련:

* evidence_missing
* receipt_list
* activity_photo_missing
* business_registration_status
* bankbook_copy_status

일정 관련:

* calendar_month
* upcoming_events
* today_events
* week_events

처리 필요 항목:

* todo_summary
* missing_report
* missing_evidence
* missing_activity_photo
* unpaid_fee

────────────────────────
4. 활동 관련 답변 상세화
────────────────────────

사용자 질문 예:
“활동 몇 개 있어?”
“각각 어떤 활동이야?”
“교내 조향 활동 정보 알려줘”
“교내 조향 활동 참여자 몇 명이야?”
“이 활동 활동비 다 냈어?”
“활동 사진 올라왔어?”
“증빙 빠진 활동 있어?”

답변에는 가능한 경우 다음을 포함하세요.

활동 목록 답변 필드:

* 활동명
* 활동일
* 장소
* 상태
* 카테고리
* 참여자 수
* 활동비 납부 상태
* 보고서 상태
* 증빙 건수
* 활동 사진 여부
* 바로가기 링크

활동 상세 답변 필드:

* 활동명
* 활동일
* 장소
* 상태
* 참여자 수
* 활동비 필요 금액
* 총 예상 수입
* 총 납부 금액
* 미납자 수
* 보고서 작성 여부
* HWPX 생성 여부
* 증빙 수
* 활동 사진 업로드 여부
* 처리 필요 항목
* 바로가기 링크

답변 예:
“교내 조향 활동은 현재 생성됨 상태입니다.

* 활동일: 2026-05-20
* 장소: A401호
* 참여자: 20명
* 보고서: 생성됨
* 활동비: 20명 중 20명 납부 완료
* 증빙: 영수증 2건
* 활동 사진: 아직 확인 필요
* 처리 필요: 활동 사진 업로드 여부 확인

바로가기: 활동 상세”

────────────────────────
5. 현재 페이지 컨텍스트 활용
────────────────────────

챗봇이 현재 사용자가 보고 있는 페이지를 알고 있으면 답변이 더 좋아집니다.

Frontend에서 챗봇 요청 payload에 다음 context를 포함하세요.

{
"current_page": "activities",
"current_activity_id": "...",
"current_tab": "activity_fee",
"visible_filters": {...}
}

예:
활동 상세 페이지에서 “이 활동 미납자 누구야?”라고 하면 현재 activity_id 기준으로 답해야 합니다.

활동 목록 페이지에서 “각각 어떤 활동이야?”라고 하면 전체 활동 목록 기준으로 답해야 합니다.

────────────────────────
6. 답변이 너무 짧지 않게 개선
────────────────────────

챗봇 답변은 최소한 다음 기준을 지키세요.

단순 개수 질문:

* 개수만 말하지 말고 상위 목록도 함께 제공

예:
나쁜 답변:
“활동은 총 1개입니다.”

좋은 답변:
“현재 등록된 활동은 총 1개입니다.

1. 교내 조향 활동

* 활동일: 2026-05-20
* 장소: A401호
* 상태: 생성됨
* 참여자: 20명
* 활동비: 20/20 납부
* 증빙: 2건

활동 목록에서 확인할 수 있습니다.”

상세 질문:

* 관련 상태와 부족한 항목까지 같이 제공

예:
“위퍼퓸 활동 사진 올라왔어?”
답변:
“위퍼퓸 교내조향활동에는 아직 활동 사진으로 분류된 증빙이 없습니다.

* 활동일: 2026-06-03
* 기준: 활동 후 2일 경과
* 현재 증빙: 영수증 2건
* 활동 사진: 없음
* 필요 작업: 증빙 탭에서 문서 유형 ‘활동 사진’으로 업로드

바로가기: 증빙 탭”

────────────────────────
7. 0건 답변 개선
────────────────────────

대상이 0건일 때 단순히 “없습니다”만 말하지 마세요.

가능한 사유를 함께 제공하세요.

예:
“활동 사진 누락 대상은 0건입니다.

가능한 이유:

* 활동일 기준 2일이 지난 활동이 없습니다.
* 모든 활동에 활동 사진이 업로드되어 있습니다.
* 해당 알림 규칙이 비활성화되어 있습니다.
* 최근 발송 이력 때문에 반복 제한에 걸렸을 수 있습니다.”

활동 개수 0건일 때도:

* 현재 필터 기준인지
* 전체 기준인지
* 취소/삭제 제외 기준인지
  명확히 말하세요.

────────────────────────
8. 링크 제공
────────────────────────

답변에는 관련 페이지 링크를 포함하세요.

링크 예:

* 활동 목록: /activities
* 활동 상세: /activities/{activity_id}
* 활동비 탭: /activities/{activity_id}?tab=activity-fee
* 증빙 탭: /activities/{activity_id}?tab=evidence
* 보고서 탭: /activities/{activity_id}?tab=report
* 회비: /payments
* 예산 관리: /budget
* 거래내역: /transactions
* 알림 설정: /notifications

프론트 챗봇 UI에서는 링크를 버튼 형태로 표시하세요.

────────────────────────
9. Frontend 챗봇 UI 개선
────────────────────────

현재 챗봇 카드가 너무 단순합니다.

개선:

* 답변 내 주요 수치를 카드 형태로 표시
* 목록 답변은 3~5개까지 표시 후 “더 보기”
* 관련 링크 버튼 표시
* 현재 페이지 기준 질문이면 “현재 화면 기준” 표시
* 전체 DB 기준이면 “전체 기준” 표시
* 로딩 중에는 “데이터 조회 중” 표시

예:
질문: “활동 몇 개 있어?”

답변 카드:

* 전체 활동: 1개
* 예정/생성됨: 1개
* 완료: 0개
* 처리 필요: 1개

아래 목록:

1. 교내 조향 활동
   2026-05-20 / A401호 / 20명 / 활동비 20/20 납부

버튼:
[활동 목록 보기]
[상세 보기]

────────────────────────
10. Backend 수정 대상
────────────────────────

예상 수정 파일:

backend/app/services/ops_chatbot_query_service.py
backend/app/services/assistant_chat_service.py
backend/app/routers/assistant.py
backend/app/routers/activities.py
backend/app/routers/members.py
backend/app/routers/payments.py
backend/app/routers/budget.py
backend/app/routers/receipts.py
backend/app/routers/notifications.py
backend/app/schemas/assistant.py

필요 시:
backend/app/services/activity_summary_service.py
backend/app/services/member_summary_service.py
backend/app/services/finance_summary_service.py

────────────────────────
11. Frontend 수정 대상
────────────────────────

예상 수정 파일:

frontend/components/assistant/FloatingAssistant.tsx
frontend/components/assistant/AssistantChatPanel.tsx
frontend/components/assistant/AssistantResultCard.tsx
frontend/lib/api.ts
frontend/app/activities/page.tsx
frontend/app/activities/[id]/page.tsx

────────────────────────
12. 테스트
────────────────────────

추가 테스트:

backend/tests/test_ops_chatbot_activity_queries.py
backend/tests/test_ops_chatbot_activity_detail.py
backend/tests/test_ops_chatbot_context.py
backend/tests/test_ops_chatbot_zero_reason.py
backend/tests/test_ops_chatbot_finance_queries.py

필수 테스트:

1. 활동이 1개 있으면 “활동 몇 개 있어?”에 1개라고 답한다.
2. planned/생성됨 상태 활동도 활동 개수에 포함된다.
3. deleted/cancelled 활동은 기본 활동 수에서 제외된다.
4. 활동 목록 답변에 활동명, 날짜, 장소, 참여자 수가 포함된다.
5. 활동 상세 답변에 활동비/보고서/증빙/활동사진 상태가 포함된다.
6. 현재 activity_id context가 있으면 “이 활동” 질문에 해당 활동 기준으로 답한다.
7. 활동 사진이 없으면 activity_photo_missing 상태를 답변에 포함한다.
8. 대상 0건일 때 가능한 사유를 반환한다.
9. 챗봇 답변 링크가 올바른 URL을 가진다.
10. 회비/활동비/증빙/예산 질문도 각각 전용 조회 함수로 처리된다.

────────────────────────
13. 브라우저 검증
────────────────────────

검증 시나리오:

1. 활동 목록에 활동 1개가 있는 상태에서 챗봇에 질문
   질문:
   활동 몇 개 있어?

기대:
활동은 총 1개라고 답해야 함.
활동명, 날짜, 장소, 참여자 수, 활동비 상태를 함께 보여야 함.

2. 활동 상세 페이지에서 질문
   질문:
   이 활동 활동비 다 냈어?

기대:
현재 activity_id 기준으로 활동비 납부 현황을 답해야 함.

3. 활동 상세 페이지에서 질문
   질문:
   활동 사진 올라왔어?

기대:
activity_photo 증빙 여부를 기준으로 답해야 함.

4. 활동 목록 페이지에서 질문
   질문:
   증빙 빠진 활동 있어?

기대:
증빙 누락 활동 목록과 링크를 보여야 함.

5. 예산 관리 페이지에서 질문
   질문:
   이번 분기 수입 지출 알려줘.

기대:
현재 분기 기준 수입, 지출, 순증감, 제외 거래 여부를 답해야 함.

────────────────────────
14. 완료 기준
────────────────────────

1. 챗봇이 활동 개수를 실제 데이터와 맞게 답한다.
2. planned/생성됨 상태 활동을 누락하지 않는다.
3. 챗봇 답변이 단순 개수뿐 아니라 상세 목록과 상태를 포함한다.
4. 현재 페이지 context를 활용한다.
5. 활동비, 보고서, 증빙, 활동 사진 상태를 함께 설명한다.
6. 0건일 때 가능한 사유를 제공한다.
7. 링크 버튼이 제공된다.
8. pytest 통과
9. npm run build 통과

완료 보고 형식:

Task 46 완료 보고

1. 원인

* 챗봇이 활동 0개라고 잘못 답한 이유:
* 답변 정보가 부족했던 이유:

2. 수정 파일

* backend:
* frontend:
* tests:

3. 데이터 조회 개선

* activity query:
* detail query:
* finance query:
* evidence query:

4. 질문 의도 분류

* activity_count:
* activity_detail:
* activity_fee:
* evidence:
* budget:

5. 답변 상세화

* 목록 답변:
* 상세 답변:
* 0건 사유:
* 링크:

6. 현재 페이지 context

* current_page:
* current_activity_id:
* current_tab:

7. 검증

* 활동 몇 개 있어:
* 활동 상세:
* 활동 사진:
* 증빙 누락:
* 예산 질문:

권장 커밋 메시지:
task46: improve ops chatbot detailed data queries and contextual answers
