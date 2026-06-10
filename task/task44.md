# Task 44. n8n 연동 세팅 및 사용자 설정형 알림 시스템 기반 구축

현재 프로젝트는 ClubAgent입니다.

이번 Task 44의 목표는 **n8n을 ClubAgent에 연결하고, 사용자가 직접 알림 기준을 설정할 수 있는 알림 시스템 기반을 구축하는 것**입니다.

주의: 이번 Task에서는 회비/활동비/활동사진/증빙/일정 알림을 모두 완성하는 것이 아니라, 먼저 n8n 연동과 알림 규칙 설정 기반을 안정적으로 만드는 것이 목표입니다.

---

# 1. 현재 상황

현재 ClubAgent에는 다음 기능들이 있습니다.

```text
활동 관리
회비 관리
활동비 관리
거래내역
예산 관리
증빙 관리
캘린더
플로팅 챗봇
```

하지만 아직 다음 문제가 있습니다.

```text
1. n8n 연동이 실제로 세팅되어 있는지 불확실함
2. Gmail 리마인드 발송 구조가 없음
3. 알림 기준을 사용자가 직접 설정할 수 없음
4. 회비/활동비/증빙/활동사진/일정 알림 기준이 코드에 고정되면 나중에 수정이 어려움
5. 발송 이력과 중복 발송 방지 구조가 없음
```

따라서 먼저 n8n 연동과 알림 설정 기반을 만들어야 합니다.

---

# 2. 핵심 목표

이번 Task에서 구현할 것:

```text
1. n8n 연동 설정
2. n8n Webhook 테스트
3. Gmail 발송용 n8n workflow와 연결 가능한 구조
4. NotificationRule 모델
5. NotificationDeliveryLog 모델
6. 알림 설정 화면
7. 알림 대상 미리보기
8. 테스트 메일 발송
9. 발송 이력 저장
10. 중복 발송 방지 기반
```

---

# 3. n8n 연동 방식

n8n은 ClubAgent의 외부 자동화 실행기로 사용합니다.

기본 구조:

```text
ClubAgent
→ 알림 대상 계산
→ n8n Webhook 호출
→ n8n Gmail 노드로 메일 발송
→ n8n이 ClubAgent에 발송 결과 기록
```

n8n은 알림 기준을 직접 판단하지 않습니다.

중요 정책:

```text
알림 기준 설정 = ClubAgent DB
알림 대상 계산 = ClubAgent Backend
메일 발송 실행 = n8n
발송 결과 저장 = ClubAgent DB
```

즉, 사용자가 알림 기준을 바꾸고 싶으면 n8n workflow를 수정하는 것이 아니라 ClubAgent 화면에서 설정을 바꾸게 해야 합니다.

---

# 4. 환경변수 추가

Backend 환경변수를 추가하세요.

```text
N8N_WEBHOOK_URL=
N8N_SECRET=
N8N_ENABLED=true
FRONTEND_URL=
```

설명:

```text
N8N_WEBHOOK_URL
- n8n Webhook production URL

N8N_SECRET
- ClubAgent → n8n 호출 시 검증용 secret

N8N_ENABLED
- n8n 발송 사용 여부

FRONTEND_URL
- 메일 본문 링크 생성용
```

---

# 5. n8n Service 추가

Backend에 n8n 호출 service를 추가하세요.

권장 파일:

```text
backend/app/services/n8n_service.py
```

기능:

```text
send_n8n_event(event_type, payload)
send_notification_email(payload)
send_test_email(payload)
```

요청 header:

```text
X-ClubAgent-Secret: {N8N_SECRET}
```

payload 예시:

```json
{
  "event_type": "notification_email",
  "source": "clubagent",
  "payload": {
    "recipient_email": "test@example.com",
    "recipient_name": "홍길동",
    "subject": "[ClubAgent] 테스트 알림",
    "body": "n8n Gmail 연동 테스트입니다.",
    "target_url": "https://agent.example.com"
  }
}
```

n8n이 실패하면 backend에서 에러를 로깅하고 사용자에게 명확한 오류 메시지를 반환하세요.

---

# 6. n8n 테스트 API

n8n 연결 확인용 API를 추가하세요.

```http
POST /api/integrations/n8n/test
GET /api/integrations/n8n/status
```

## status 응답 예시

```json
{
  "enabled": true,
  "webhook_configured": true,
  "secret_configured": true,
  "last_test_status": "success",
  "last_test_at": "2026-06-06T12:00:00"
}
```

## test 요청 예시

```json
{
  "recipient_email": "test@example.com",
  "subject": "[ClubAgent] n8n 테스트 메일",
  "body": "n8n Gmail 발송 테스트입니다."
}
```

이 API는 n8n Webhook으로 테스트 payload를 보내고 결과를 저장합니다.

---

# 7. NotificationRule 모델 추가

사용자가 알림 기준을 직접 설정할 수 있도록 NotificationRule 모델을 추가하세요.

권장 모델:

```text
NotificationRule

id
name
enabled
reminder_type
target_scope
channel
send_time
days_before nullable
days_after nullable
repeat_interval_days nullable
max_send_count nullable
require_confirm_before_send
term nullable
quarter nullable
activity_id nullable
conditions JSON
template_subject
template_body
created_at
updated_at
deleted_at nullable
```

## reminder_type 예시

```text
membership_fee_due
activity_fee_due
evidence_missing
activity_photo_missing
report_missing
calendar_deadline
quarter_settlement
custom
```

## target_scope 예시

```text
term
quarter
activity
calendar_event
global
```

## channel

```text
gmail
```

## conditions JSON 예시

```json
{
  "include_statuses": ["unpaid", "partial", "need_check"],
  "exclude_executives": true,
  "exclude_cancelled": true,
  "only_after_due_date": true
}
```

---

# 8. NotificationDeliveryLog 모델 추가

발송 이력과 중복 발송 방지를 위해 로그 모델을 추가하세요.

권장 모델:

```text
NotificationDeliveryLog

id
rule_id
reminder_type
target_type
target_id
recipient_email
recipient_name
subject
body
target_url
provider
provider_message_id nullable
status
error_message nullable
sent_at nullable
created_at
```

status:

```text
pending
sent
failed
skipped
```

이 로그를 통해 다음을 처리하세요.

```text
1. 최근 N일 내 같은 대상에게 같은 알림을 보냈으면 제외
2. max_send_count 초과 시 제외
3. 실패한 메일 재시도 가능
4. 발송 이력 화면 표시
```

---

# 9. 알림 기준 설정 화면 추가

SYSTEM 또는 설정 메뉴에 알림 설정 화면을 추가하세요.

권장 위치:

```text
SYSTEM
- 알림
- 설정
```

또는 기존 알림 페이지가 있으면 확장하세요.

화면 구성:

```text
알림 설정
1. n8n 연결 상태
2. Gmail 테스트 발송
3. 알림 규칙 목록
4. 알림 규칙 생성/수정
5. 대상자 미리보기
6. 발송 이력
```

---

# 10. 알림 규칙 UI

알림 규칙 생성/수정 모달을 만드세요.

공통 필드:

```text
알림 이름
알림 유형
사용 여부
발송 채널
발송 시간
발송 전 확인 여부
반복 여부
반복 간격
최대 발송 횟수
메일 제목 템플릿
메일 본문 템플릿
```

유형별 추가 필드:

## 회비 미납 알림

```text
기준 학기
대상 상태: 미납 / 부분 납부 / 확인 필요
임원 제외 여부
마감일
마감 N일 전
마감 당일
마감 후 N일마다 반복
```

주의:

```text
회비는 학기 단위입니다.
membership_fee period는 2026-1 같은 학기 기준을 유지해야 합니다.
```

## 활동비 미납 알림

```text
기준 활동
또는 전체 활동
활동일 기준 N일 후
대상 상태: 미납 / 부분 납부 / 확인 필요
취소/제외 참가자 제외
```

주의:

```text
활동비는 활동 단위입니다.
링크는 /activities/{activity_id}?tab=activity-fee 입니다.
절대 /payments로 보내지 마세요.
```

## 증빙 누락 알림

```text
기준 분기
지출 발생 후 N일
분기 마감 N일 전
문서 유형 조건
```

주의:

```text
예산/증빙은 분기 단위입니다.
```

## 활동 사진 누락 알림

```text
활동일 기준 N일 후
기본값: 활동 후 2일
대상 활동 상태
반복 간격
최대 발송 횟수
```

조건:

```text
activity_date + days_after <= today
해당 activity_report_id에 document_type = activity_photo 증빙이 없음
```

## 일정/마감 알림

```text
일정 유형
마감 N일 전
당일 알림
지난 마감 알림
```

---

# 11. 대상자 미리보기

각 알림 규칙에서 발송 전에 대상자를 미리 볼 수 있어야 합니다.

API:

```http
POST /api/notifications/rules/{rule_id}/preview
```

응답 예시:

```json
{
  "rule_id": "...",
  "count": 3,
  "items": [
    {
      "target_type": "activity",
      "target_id": "...",
      "recipient_email": "club@example.com",
      "recipient_name": "운영진",
      "subject": "[ClubAgent] 활동 사진 업로드 필요",
      "body": "위퍼퓸 교내조향활동의 활동 사진이 아직 업로드되지 않았습니다.",
      "target_url": "/activities/...?...evidence",
      "reason": "활동일 후 2일 경과, activity_photo 없음"
    }
  ]
}
```

---

# 12. 즉시 발송 / 테스트 발송

알림 규칙별로 다음 버튼을 제공하세요.

```text
[대상자 미리보기]
[테스트 메일 보내기]
[즉시 발송]
```

즉시 발송은 다음 흐름으로 처리하세요.

```text
1. 대상자 계산
2. 발송 전 확인 모달
3. n8n Webhook 호출
4. NotificationDeliveryLog 저장
5. 발송 결과 표시
```

발송 전 확인 모달에는 대상자 수와 메일 제목/본문 미리보기를 보여주세요.

---

# 13. n8n Workflow 요구사항

n8n 쪽 workflow는 최소 2개를 기준으로 문서화하세요.

## Workflow A. Webhook 즉시 발송

```text
Webhook Trigger
→ Secret 검증
→ Gmail Send
→ HTTP Request로 ClubAgent 발송 결과 기록
→ Respond to Webhook
```

## Workflow B. Schedule 자동 발송

```text
Schedule Trigger
→ HTTP Request: GET /api/notifications/due
→ Split In Batches
→ Gmail Send
→ HTTP Request: POST /api/notifications/log
```

이번 Task에서는 n8n workflow 파일 자체를 자동 생성하지 않아도 됩니다.
대신 README 또는 docs에 n8n 세팅 방법을 남기세요.

문서 위치 권장:

```text
docs/n8n-notification-setup.md
```

포함 내용:

```text
1. n8n Webhook 생성
2. Gmail Credential 연결
3. X-ClubAgent-Secret 검증
4. Gmail Send 노드 구성
5. ClubAgent log API 호출
6. 환경변수 설정
7. 테스트 방법
```

---

# 14. 알림 대상 계산 Service

Backend에 알림 대상 계산 service를 만드세요.

권장 파일:

```text
backend/app/services/notification_service.py
```

함수 예시:

```python
preview_rule(rule_id)
get_due_notifications()
send_rule_now(rule_id)
log_delivery_result(payload)
```

알림 유형별 대상 계산 함수:

```python
get_membership_fee_due_targets(rule)
get_activity_fee_due_targets(rule)
get_evidence_missing_targets(rule)
get_activity_photo_missing_targets(rule)
get_report_missing_targets(rule)
get_calendar_deadline_targets(rule)
```

---

# 15. 활동 사진 누락 알림 기준

활동 사진은 증빙 document_type에 추가합니다.

```text
document_type = activity_photo
label = 활동 사진
```

활동 사진 누락 조건:

```text
1. ActivityReport.deleted_at IS NULL
2. activity_date 존재
3. today >= activity_date + rule.days_after
4. 해당 activity_id에 document_type = activity_photo 증빙 없음
5. 이미 max_send_count 이상 발송하지 않음
6. repeat_interval_days 이내 중복 발송 아님
```

기본 설정:

```text
활동 사진 누락 알림
enabled = true
days_after = 2
repeat_interval_days = 2
max_send_count = 3
require_confirm_before_send = true
```

메일 링크:

```text
/activities/{activity_id}?tab=evidence
```

---

# 16. 학기/분기/활동 기준 분리

반드시 기준 단위를 분리하세요.

```text
회비 알림 = 학기 기준
활동비 알림 = 활동 기준
증빙/예산 알림 = 분기 기준
활동 사진 알림 = 활동일 기준
일정 알림 = calendar event 기준
```

절대 하면 안 되는 것:

```text
1. 회비를 분기 기준으로 계산
2. membership_fee period를 2026-Q2로 변경
3. 활동비를 /payments로 연결
4. 증빙 누락을 학기 기준으로만 계산
```

---

# 17. Backend 수정 대상

```text
backend/app/models/notification.py
backend/app/models/receipt.py
backend/app/models/uploaded_file.py

backend/app/schemas/notification.py

backend/app/routers/notifications.py
backend/app/routers/integrations.py
backend/app/routers/receipts.py
backend/app/routers/activities.py

backend/app/services/n8n_service.py
backend/app/services/notification_service.py
backend/app/services/notification_target_service.py
backend/app/services/term_service.py
backend/app/services/quarter_service.py
backend/app/services/evidence_service.py

backend/alembic/versions/*
```

---

# 18. Frontend 수정 대상

```text
frontend/app/notifications/page.tsx
frontend/app/settings/page.tsx 또는 SYSTEM 알림 페이지
frontend/app/activities/[id]/page.tsx
frontend/app/receipts/page.tsx

frontend/components/notifications/*
frontend/components/evidence/*
frontend/lib/api.ts
```

신규 컴포넌트 권장:

```text
NotificationRuleList.tsx
NotificationRuleFormModal.tsx
NotificationRulePreviewModal.tsx
NotificationDeliveryLogTable.tsx
N8nConnectionStatusCard.tsx
TestEmailModal.tsx
```

---

# 19. 테스트

추가 테스트:

```text
backend/tests/test_n8n_integration.py
backend/tests/test_notification_rules.py
backend/tests/test_notification_preview.py
backend/tests/test_notification_delivery_logs.py
backend/tests/test_activity_photo_missing_notification.py
backend/tests/test_notification_term_quarter_scope.py
```

필수 테스트:

```text
1. n8n webhook URL 설정 여부를 status API가 반환
2. test API가 n8n_service를 호출
3. NotificationRule 생성/수정/삭제 가능
4. disabled rule은 due target에 포함되지 않음
5. membership_fee 알림은 학기 기준으로 대상 계산
6. activity_fee 알림은 활동 기준으로 대상 계산
7. evidence_missing 알림은 분기 기준으로 대상 계산
8. activity_photo_missing은 활동일 + days_after 기준으로 대상 계산
9. activity_photo가 있으면 누락 대상에서 제외
10. max_send_count 초과 시 발송 대상 제외
11. repeat_interval_days 이내 중복 발송 제외
12. delivery log 저장 가능
13. send_rule_now는 n8n_service를 통해 발송 요청
```

---

# 20. 브라우저 검증

```text
1. 알림 설정 페이지 접속
2. n8n 연결 상태 확인
3. 테스트 메일 발송
4. 회비 미납 알림 규칙 생성
5. 대상자 미리보기 확인
6. 활동 사진 누락 알림 규칙 생성
7. days_after = 2 설정
8. 활동일이 2일 지난 활동 중 activity_photo 없는 활동이 대상에 뜨는지 확인
9. 활동 사진 업로드 후 미리보기에서 대상에서 빠지는지 확인
10. 즉시 발송 클릭
11. n8n Webhook 호출 확인
12. Gmail 수신 확인
13. 발송 이력 저장 확인
```

---

# 21. 완료 기준

```text
1. n8n Webhook 연결 상태를 확인할 수 있다.
2. n8n 테스트 메일을 보낼 수 있다.
3. 사용자가 알림 규칙을 생성/수정/비활성화할 수 있다.
4. 알림 기준을 사용자가 직접 설정할 수 있다.
5. 회비/활동비/증빙/활동사진/일정 알림 기준이 서로 분리된다.
6. 대상자 미리보기가 가능하다.
7. 즉시 발송이 가능하다.
8. 발송 이력이 저장된다.
9. 중복 발송 방지 기준이 적용된다.
10. 활동 사진 누락 알림이 activity_date + 설정일수 기준으로 동작한다.
11. n8n Gmail 발송 workflow 세팅 문서가 있다.
12. pytest 통과
13. npm run build 통과
```

---

# 22. 완료 보고 형식

```text
Task 44 완료 보고

1. 원인
- n8n 기반 알림 설정이 필요했던 이유:
- 사용자가 알림 기준을 설정해야 하는 이유:

2. 수정 파일
- backend:
- frontend:
- migration:
- docs:
- tests:

3. n8n 연동
- env:
- n8n_service:
- status API:
- test API:
- docs:

4. NotificationRule
- 모델:
- reminder_type:
- 조건:
- 사용자 설정:

5. NotificationDeliveryLog
- 발송 이력:
- 중복 방지:
- 실패 기록:

6. 알림 설정 UI
- 규칙 목록:
- 생성/수정:
- 대상자 미리보기:
- 테스트 메일:
- 즉시 발송:

7. 활동 사진 누락 알림
- document_type=activity_photo:
- days_after:
- 대상 계산:
- 링크:

8. 기준 분리
- 회비 학기 기준:
- 활동비 활동 기준:
- 증빙/예산 분기 기준:
- 일정 calendar 기준:

9. n8n/Gmail 검증
- webhook:
- Gmail:
- delivery log:

10. 검증
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task44: add n8n notification settings and configurable gmail reminders
```
