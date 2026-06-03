# Task 39. 플로팅 운영 챗봇 구축

현재 프로젝트는 ClubAgent입니다.

Task 38에서 FINANCE > 예산 관리 페이지를 구축했습니다.

이번 Task 39의 목표는 **사이트 오른쪽 아래에 플로팅 운영 챗봇을 추가하고, 현재 ClubAgent에 저장된 부원/활동/회비/활동비/거래내역/예산/증빙/문서 정보를 기반으로 질문에 답변할 수 있게 만드는 것**입니다.

이번 챗봇은 단순 RAG 챗봇이 아닙니다.

숫자, 상태, 집계 질문은 반드시 DB 기반으로 답변하고, 문서/영수증/보고서 내용 질문은 RAG 또는 텍스트 검색으로 보조합니다.

---

# 1. 현재 문제

현재 ClubAgent에는 부원, 활동, 회비, 활동비, 거래내역, 예산, 영수증, 파일함, HWPX, 감사자료 패키지 기능이 들어가 있습니다.

하지만 사용자가 다음과 같은 질문을 했을 때 바로 답해주는 기능이 없습니다.

```text
총 부원 몇 명이야?
활동 몇 개 했어?
이번 학기 회비 미납 몇 명이야?
활동비 미납 있는 활동 알려줘.
시향 활동에 몇 명 참여했어?
증빙 빠진 활동 있어?
이번 학기 총 수입 얼마야?
지출 제일 큰 활동이 뭐야?
위퍼퓸 활동 감사자료 준비됐어?
```

따라서 사용자가 각 페이지를 직접 찾아다니지 않아도, 오른쪽 아래 플로팅 챗봇에서 현재 사이트 데이터를 질문하고 답변받을 수 있어야 합니다.

---

# 2. 핵심 목표

공통 layout에 플로팅 챗봇을 추가합니다.

```text
오른쪽 아래 Floating Button
→ 클릭
→ Chat Panel 열림
→ 질문 입력
→ DB/RAG 기반 답변
→ 관련 페이지 링크 제공
```

챗봇은 이번 Task에서 **조회 전용**입니다.

데이터를 직접 수정하면 안 됩니다.

허용:

```text
조회
요약
집계
검색
관련 링크 제공
확인 필요 안내
```

금지:

```text
납부 완료 처리
거래 매칭 반영
예산 수정
파일 삭제
활동 삭제
부원 삭제
DB 변경
```

데이터 변경이 필요한 요청은 기존 AI 작업실 또는 해당 화면의 preview/confirm 기능으로 안내하세요.

예:

```text
이 작업은 데이터 변경이 필요합니다. 회비 화면에서 확인 후 반영해주세요.
```

---

# 3. 핵심 원칙

## 3-1. 숫자/상태 질문은 DB 기반으로 답변

다음 질문은 RAG로 추측하지 말고, 반드시 DB query 또는 기존 service/API를 통해 계산하세요.

```text
총 부원 수
임원 수
일반 부원 수
활동 수
활동별 참여자 수
회비 미납 수
활동비 미납 수
총 수입
총 지출
현재 잔액
예산 대비 실제 금액
증빙 누락 활동
보고서 미작성 활동
감사자료 준비 상태
```

## 3-2. 문서/영수증/보고서 내용 질문은 검색 기반으로 답변

다음 질문은 문서 텍스트, 보고서 본문, 영수증 OCR/분석 결과, UploadedFile extracted_text를 검색해서 답변할 수 있습니다.

```text
이 활동 보고서 내용 요약해줘.
영수증에서 가맹점 뭐였어?
위퍼퓸 활동 내용 뭐였어?
제출자료에 빠진 문서 있어?
이 활동 증빙 내용 요약해줘.
```

이번 Task에서 완전한 벡터DB는 필수는 아닙니다.
우선 DB text search 기반으로 구현하고, 이후 Qdrant/pgvector로 확장 가능하도록 service interface를 분리하세요.

---

# 4. UI 요구사항

## 4-1. Floating Button

모든 주요 페이지 오른쪽 아래에 플로팅 버튼을 표시합니다.

위치:

```text
fixed bottom-6 right-6
```

표시 예:

```text
운영 챗봇
```

또는 아이콘 버튼으로 표시해도 됩니다.

## 4-2. Chat Panel

버튼 클릭 시 채팅 패널이 열립니다.

구성:

```text
상단: ClubAgent Assistant
본문: 메시지 목록
하단: 입력창 + 전송 버튼
```

기능:

```text
열기/닫기
메시지 입력
전송
로딩 표시
오류 표시
답변 표시
관련 링크 표시
추천 질문 표시
```

## 4-3. 추천 질문

처음 열었을 때 추천 질문을 보여주세요.

```text
총 부원 몇 명이야?
활동 몇 개 했어?
이번 학기 회비 미납 몇 명이야?
활동비 미납 있는 활동 알려줘.
증빙 빠진 활동 있어?
이번 학기 총 수입 얼마야?
```

## 4-4. 모바일 대응

모바일에서는 플로팅 패널이 화면을 과하게 가리지 않도록 처리하세요.

권장:

```text
desktop: 오른쪽 아래 작은 패널
mobile: 하단 sheet 또는 거의 전체 화면 modal
```

---

# 5. Backend API

다음 API를 추가하거나 기존 assistant router에 보강하세요.

```http
POST /api/assistant/chat
GET /api/assistant/chat/suggestions
```

## 요청 예시

```json
{
  "message": "이번 학기 회비 미납 몇 명이야?",
  "context": {
    "page": "budget",
    "activity_id": null
  }
}
```

## 응답 예시

```json
{
  "answer": "이번 학기 회비 미납자는 90명입니다.",
  "intent": "membership_fee_status",
  "data_sources": ["payment_records"],
  "links": [
    {
      "label": "회비 화면에서 보기",
      "url": "/payments"
    }
  ],
  "confidence": 0.92
}
```

응답에는 가능한 경우 아래 정보를 포함하세요.

```text
answer
intent
data_sources
links
confidence
needs_clarification
clarification_question
```

---

# 6. Query Router

챗봇 내부에서 질문 유형을 분류하세요.

지원 intent:

```text
member_count
activity_count
activity_participant_count
membership_fee_status
activity_fee_status
budget_summary
cashflow_summary
activity_settlement_status
evidence_missing
report_missing
audit_readiness
document_summary
receipt_summary
unknown
```

분류 규칙 예시:

```text
"총 부원", "부원 몇 명" → member_count
"활동 몇 개" → activity_count
"참여자 몇 명" + activity context 있음 → activity_participant_count
"회비 미납" → membership_fee_status
"활동비 미납" → activity_fee_status
"총 수입", "총 지출", "잔액" → budget_summary 또는 cashflow_summary
"증빙 빠진" → evidence_missing
"감사자료 준비" → audit_readiness
"보고서 내용", "영수증 내용" → document_summary 또는 receipt_summary
```

---

# 7. DB Query Service

다음 서비스를 추가하세요.

```text
backend/app/services/assistant_query_service.py
```

지원 함수 예시:

```python
get_member_summary()
get_activity_summary()
get_activity_participant_count(activity_name=None, activity_id=None)
get_membership_fee_summary(period=None)
get_activity_fee_summary(activity_id=None)
get_budget_summary(period=None)
get_cashflow_summary(period=None)
get_activity_settlements(period=None)
get_missing_evidence_activities()
get_report_missing_activities()
get_audit_readiness(activity_id=None)
```

Task 38에서 만든 예산 관리 service/API를 최대한 재사용하세요.

```text
GET /api/budget/summary
GET /api/budget/activity-settlements
GET /api/budget/review-items
```

같은 계산 로직을 여러 곳에 중복 구현하지 마세요.

---

# 8. RAG / 문서 검색 Service

다음 서비스를 추가하세요.

```text
backend/app/services/assistant_rag_service.py
```

1차 구현은 완전한 벡터DB가 아니어도 됩니다.

검색 대상:

```text
ActivityReport.final_content
ActivityReport.generated_content
Receipt OCR/analysis result
UploadedFile.extracted_text
AI 작업 로그
활동 보고서 본문
```

지원 함수 예시:

```python
search_activity_documents(query, activity_id=None)
search_receipt_texts(query, activity_id=None)
search_uploaded_file_texts(query, activity_id=None)
```

검색 결과에는 출처 정보를 포함하세요.

```json
{
  "source_type": "activity_report",
  "source_id": "...",
  "title": "위퍼퓸 교내조향활동",
  "snippet": "..."
}
```

---

# 9. Context 처리

Frontend에서 현재 페이지 정보를 context로 전달하세요.

예:

```json
{
  "context": {
    "page": "activity_detail",
    "activity_id": "..."
  }
}
```

활동 상세 페이지에서 사용자가 다음처럼 물으면 현재 activity_id 기준으로 답변해야 합니다.

```text
참여자 몇 명이야?
활동비 미납 몇 명이야?
증빙 다 있어?
감사자료 준비됐어?
```

전역 페이지에서 같은 질문이 들어오면 활동을 특정하라고 물어보세요.

예:

```text
어떤 활동을 기준으로 확인할까요?
활동명을 입력하거나 활동 상세 페이지에서 다시 질문해주세요.
```

---

# 10. 링크 정책

답변에는 관련 화면 링크를 포함하세요.

반드시 아래 정책을 지키세요.

```text
membership_fee 관련 → /payments
activity_fee 관련 → /activities/{activity_id}?tab=activity-fee
증빙 관련 → /activities/{activity_id}?tab=evidence
활동 관련 → /activities/{activity_id}
예산 관련 → /budget 또는 현재 예산 관리 페이지 경로
부원 관련 → /members
거래내역 관련 → /transactions
영수증 관련 → /receipts
```

중요:

```text
활동비 미납은 절대 /payments로 보내지 마세요.
활동비는 해당 활동 상세 > 활동비 탭으로 보내야 합니다.
```

---

# 11. 답변 예시

## 11-1. 총 부원 수

질문:

```text
총 부원 몇 명이야?
```

응답:

```text
현재 등록된 부원은 총 101명입니다.
임원은 10명, 일반 부원은 91명입니다.

부원 관리에서 보기: /members
```

## 11-2. 활동 수

질문:

```text
활동 몇 개 했어?
```

응답:

```text
등록된 활동은 총 8개입니다.
완료된 활동은 5개, 예정된 활동은 3개입니다.

활동 관리에서 보기: /activities
```

## 11-3. 특정 활동 참여자 수

질문:

```text
시향 활동에 몇 명 참여했어?
```

응답:

```text
시향 활동에는 총 12명이 참여했습니다.
신청 14명 중 완료 12명, 취소 2명입니다.

활동 상세 보기: /activities/{id}
```

활동명이 여러 개 매칭되면 후보를 보여주세요.

## 11-4. 회비 미납

질문:

```text
이번 학기 회비 미납 몇 명이야?
```

응답:

```text
이번 학기 회비 미납자는 90명입니다.
회비 화면에서 확인할 수 있습니다.

회비 화면: /payments
```

## 11-5. 활동비 미납

질문:

```text
활동비 미납 있는 활동 알려줘.
```

응답:

```text
활동비 미납이 있는 활동은 2개입니다.

1. 위퍼퓸 교내조향활동 - 미납 3명
   /activities/{id}?tab=activity-fee

2. 시향 활동 - 미납 1명
   /activities/{id}?tab=activity-fee
```

## 11-6. 증빙 누락

질문:

```text
증빙 빠진 활동 있어?
```

응답:

```text
증빙이 부족한 활동은 1개입니다.

1. 위퍼퓸 교내조향활동
   증빙 탭에서 확인: /activities/{id}?tab=evidence
```

---

# 12. 안전 정책

이번 Task에서 플로팅 챗봇은 조회 전용입니다.

사용자가 다음처럼 말해도 바로 수정하지 마세요.

```text
박민서 회비 완납 처리해줘.
이 거래 매칭해줘.
이 파일 삭제해줘.
예산 금액 바꿔줘.
```

응답 예시:

```text
이 요청은 데이터 변경이 필요한 작업입니다.
회비 화면 또는 AI 작업실에서 미리보기 후 확인 반영으로 처리해주세요.
```

필요하면 관련 화면 링크를 제공합니다.

---

# 13. Frontend 수정 대상

```text
frontend/components/assistant/FloatingAssistant.tsx
frontend/components/assistant/AssistantChatPanel.tsx
frontend/app/layout.tsx 또는 공통 shell/sidebar layout
frontend/lib/api.ts
```

모든 주요 페이지에서 플로팅 버튼이 보이게 하세요.

단, 로그인/에러 페이지가 있다면 제외해도 됩니다.

---

# 14. Backend 수정 대상

```text
backend/app/routers/assistant.py
backend/app/services/assistant_query_service.py
backend/app/services/assistant_rag_service.py
backend/app/services/budget_service.py
backend/app/services/activity_audit_check_service.py
backend/app/agents/intent_router.py
backend/app/agents/assistant_orchestrator.py
```

---

# 15. 테스트

추가 또는 보강:

```text
backend/tests/test_floating_assistant_query_router.py
backend/tests/test_floating_assistant_db_answers.py
backend/tests/test_floating_assistant_activity_context.py
backend/tests/test_floating_assistant_links.py
backend/tests/test_floating_assistant_readonly.py
```

필수 테스트:

```text
1. "총 부원 몇 명이야" → member_count
2. "활동 몇 개 했어" → activity_count
3. "시향 활동에 몇 명 참여했어" → activity_participant_count
4. "회비 미납 몇 명이야" → membership_fee_status
5. "활동비 미납 있는 활동 알려줘" → activity_fee_status
6. activity_fee 응답 링크는 /activities/{id}?tab=activity-fee
7. membership_fee 응답 링크는 /payments
8. activity_detail context에서 "참여자 몇 명이야"는 현재 activity_id 기준
9. 전역 context에서 "참여자 몇 명이야"는 clarification 반환
10. 챗봇이 confirm 없이 DB를 수정하지 않음
11. 수정 요청은 안내 메시지와 관련 링크만 반환
```

---

# 16. 브라우저 검증

```text
1. 모든 주요 페이지 오른쪽 아래에 플로팅 버튼 표시
2. 버튼 클릭 시 채팅 패널 열림
3. "총 부원 몇 명이야?" 질문
4. "활동 몇 개 했어?" 질문
5. "이번 학기 회비 미납 몇 명이야?" 질문
6. "활동비 미납 있는 활동 알려줘" 질문
7. 관련 링크 클릭 시 올바른 화면으로 이동
8. 활동 상세에서 "참여자 몇 명이야?" 질문 시 현재 활동 기준 답변
9. 전역 페이지에서 "참여자 몇 명이야?" 질문 시 활동 선택 요청
10. 모바일 화면에서 패널이 깨지지 않는지 확인
```

---

# 17. 완료 기준

```text
1. 플로팅 챗봇 버튼이 공통 layout에 추가된다.
2. 채팅 패널에서 질문/답변이 가능하다.
3. 숫자/상태 질문은 DB 기반으로 답변한다.
4. 문서/영수증/보고서 질문은 검색 service로 처리할 수 있는 구조가 있다.
5. 활동 상세 context를 인식한다.
6. 전역 context에서 모호한 활동 질문은 clarification을 반환한다.
7. 답변에 관련 링크를 제공한다.
8. activity_fee 관련 링크는 활동 상세 활동비 탭으로 이동한다.
9. membership_fee 관련 링크는 회비 화면으로 이동한다.
10. 챗봇은 이번 Task에서 DB를 직접 수정하지 않는다.
11. pytest 통과
12. npm run build 통과
```

---

# 18. 완료 보고 형식

```text
Task 39 완료 보고

1. 원인
- 플로팅 챗봇이 필요했던 이유:
- RAG만으로 부족한 이유:

2. 수정 파일
- backend:
- frontend:
- tests:

3. UI
- FloatingAssistant:
- ChatPanel:
- 추천 질문:
- 모바일 대응:

4. Query Router
- intent:
- DB query:
- RAG search:
- clarification:

5. 지원 질문
- 부원:
- 활동:
- 회비:
- 활동비:
- 예산:
- 증빙:
- 문서:

6. 링크 정책
- membership_fee:
- activity_fee:
- evidence:
- activity_detail:
- budget:

7. 안전 정책
- 조회만 허용:
- DB 수정 금지:
- 수정 요청 안내:

8. 검증
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task39: add floating operations chatbot with db-backed answers
```
