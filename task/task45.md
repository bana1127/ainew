# Task 45. 활동 관련 기본 알림 규칙 및 활동 사진 누락 알림 구현

현재 프로젝트는 ClubAgent입니다.

Task 44에서 n8n 연동 기반과 사용자 설정형 알림 시스템을 구축했습니다.

이번 Task 45의 목표는 **활동 운영에 필요한 기본 알림 규칙을 실제로 적용하고, 활동 사진 누락 알림을 기본 기능으로 추가하는 것**입니다.

이번 Task는 알림 시스템 전체를 다시 만드는 작업이 아닙니다.
Task 44에서 만든 NotificationRule, NotificationDeliveryLog, n8n_service, 알림 설정 UI를 재사용해서 활동 관련 알림을 실제로 동작하게 만듭니다.

---

# 1. 핵심 목표

이번 Task에서 구현할 것:

```text
1. 활동 관련 기본 알림 규칙 자동 생성
2. 활동 사진 누락 알림 기본 추가
3. 활동 사진 증빙 타입 activity_photo 확실히 반영
4. 활동 관련 알림 규칙 수정/비활성화/삭제 가능
5. 삭제된 알림 규칙은 대상 계산과 발송에서 제외
6. 알림 대상 미리보기 지원
7. n8n Gmail 발송 연결
8. 발송 이력 저장
```

---

# 2. 기본 알림 규칙

초기 세팅 시 다음 활동 관련 알림 규칙을 기본으로 생성하세요.

## 2-1. 활동 사진 누락 알림

```text
name: 활동 사진 누락 알림
reminder_type: activity_photo_missing
target_scope: activity
enabled: true
channel: gmail
days_after: 2
repeat_interval_days: 2
max_send_count: 3
require_confirm_before_send: true
```

설명:

```text
활동일로부터 2일이 지났는데 활동 사진이 업로드되지 않은 활동을 알려줍니다.
```

대상 조건:

```text
1. ActivityReport.deleted_at IS NULL
2. activity_date 존재
3. today >= activity_date + days_after
4. 해당 activity_id에 document_type = activity_photo 증빙이 없음
5. max_send_count를 넘지 않음
6. repeat_interval_days 이내 중복 발송 아님
```

링크:

```text
/activities/{activity_id}?tab=evidence
```

---

## 2-2. 활동 전날 알림

```text
name: 활동 전날 알림
reminder_type: activity_upcoming
target_scope: activity
enabled: true
channel: gmail
days_before: 1
repeat_interval_days: null
max_send_count: 1
require_confirm_before_send: true
```

설명:

```text
활동 하루 전에 운영진에게 활동 일정을 알려줍니다.
```

대상 조건:

```text
1. ActivityReport.deleted_at IS NULL
2. activity_date 존재
3. activity_date = today + 1일
4. 활동 상태가 cancelled/deleted가 아님
5. 같은 활동에 대해 이미 발송한 이력이 없음
```

링크:

```text
/activities/{activity_id}
```

---

## 2-3. 활동 보고서 미작성 알림

```text
name: 활동 보고서 미작성 알림
reminder_type: activity_report_missing
target_scope: activity
enabled: true
channel: gmail
days_after: 2
repeat_interval_days: 2
max_send_count: 3
require_confirm_before_send: true
```

설명:

```text
활동일로부터 2일이 지났는데 보고서 본문 또는 HWPX가 준비되지 않은 활동을 알려줍니다.
```

대상 조건:

```text
1. ActivityReport.deleted_at IS NULL
2. activity_date 존재
3. today >= activity_date + days_after
4. final_content가 비어 있거나 보고서/HWPX 생성 상태가 미완료
5. max_send_count를 넘지 않음
6. repeat_interval_days 이내 중복 발송 아님
```

링크:

```text
/activities/{activity_id}?tab=report
```

---

## 2-4. 활동 증빙 누락 알림

```text
name: 활동 증빙 누락 알림
reminder_type: activity_evidence_missing
target_scope: activity
enabled: true
channel: gmail
days_after: 2
repeat_interval_days: 2
max_send_count: 3
require_confirm_before_send: true
```

설명:

```text
활동일로부터 2일이 지났는데 증빙 문서가 없는 활동을 알려줍니다.
```

대상 조건:

```text
1. ActivityReport.deleted_at IS NULL
2. activity_date 존재
3. today >= activity_date + days_after
4. 해당 activity_id에 연결된 evidence 문서가 없음
5. max_send_count를 넘지 않음
6. repeat_interval_days 이내 중복 발송 아님
```

링크:

```text
/activities/{activity_id}?tab=evidence
```

---

# 3. 기본 규칙 생성 방식

앱 초기화 또는 migration/seed에서 기본 규칙을 생성하세요.

권장 방식:

```text
backend/app/services/notification_seed_service.py
```

함수 예시:

```python
ensure_default_notification_rules()
```

동작:

```text
1. 같은 reminder_type과 name의 기본 규칙이 이미 있으면 중복 생성하지 않음
2. 없으면 기본 규칙 생성
3. 사용자가 수정한 기존 규칙은 덮어쓰지 않음
4. soft delete된 규칙은 자동 복구하지 않음
```

중요:

```text
기본 규칙은 최초 1회 생성만 합니다.
사용자가 삭제한 규칙을 서버 재시작 때 다시 만들면 안 됩니다.
```

삭제된 기본 규칙을 다시 만들고 싶을 경우에는 별도 버튼으로 처리하세요.

```text
[기본 알림 규칙 다시 생성]
```

---

# 4. 알림 규칙 삭제 기능

알림 규칙은 사용자가 삭제할 수 있어야 합니다.

삭제 정책:

```text
soft delete 권장
deleted_at 설정
enabled = false 처리
```

삭제 후 동작:

```text
1. 알림 규칙 목록 기본 조회에서 제외
2. 알림 대상 계산에서 제외
3. /api/notifications/due 대상에서 제외
4. 즉시 발송 불가
5. 발송 이력은 유지
```

UI:

```text
알림 규칙 목록
- 수정
- 비활성화
- 삭제
```

삭제 확인 모달 문구:

```text
이 알림 규칙을 삭제하시겠습니까?
삭제 후에는 자동 알림 대상 계산에서 제외됩니다.
기존 발송 이력은 유지됩니다.
```

삭제 API 예:

```http
DELETE /api/notifications/rules/{rule_id}
```

복구 기능은 이번 Task에서 필수는 아닙니다.

---

# 5. 활동 사진 증빙 타입 반영

증빙 document_type에 `activity_photo`가 반드시 포함되어야 합니다.

```text
activity_photo → 활동 사진
```

활동 사진은 금액이 없어도 정상 증빙입니다.

정책:

```text
document_type = activity_photo
amount = null 허용
status = valid 또는 uploaded
```

금액이 없다는 이유로 확인 필요로 처리하지 마세요.

활동 상세 > 증빙 탭의 문서 유형 선택 옵션에도 추가하세요.

```text
활동 사진
```

전역 증빙 목록 필터에도 추가하세요.

```text
활동 사진
```

활동 사진 업로드 시 저장:

```text
UploadedFile.activity_report_id = 현재 활동 ID
UploadedFile.file_category = evidence
UploadedFile.file_role = evidence
Receipt/EvidenceDocument.document_type = activity_photo
Receipt/EvidenceDocument.activity_report_id = 현재 활동 ID
```

---

# 6. 활동 사진 누락 대상 계산

NotificationRule의 `activity_photo_missing` 유형을 처리하세요.

권장 함수:

```python
get_activity_photo_missing_targets(rule)
```

계산 기준:

```text
1. rule.enabled = true
2. rule.deleted_at IS NULL
3. ActivityReport.deleted_at IS NULL
4. activity_date 존재
5. today >= activity_date + rule.days_after
6. 해당 activity_id에 activity_photo 증빙 없음
7. max_send_count 초과 아님
8. repeat_interval_days 이내 같은 대상에게 같은 알림 발송 이력 없음
```

응답 예시:

```json
{
  "target_type": "activity",
  "target_id": "...",
  "recipient_email": "club@example.com",
  "recipient_name": "운영진",
  "subject": "[ClubAgent] 활동 사진 업로드 필요: 위퍼퓸 교내조향활동",
  "body": "위퍼퓸 교내조향활동의 활동 사진이 아직 업로드되지 않았습니다.",
  "target_url": "/activities/{id}?tab=evidence",
  "reason": "활동일 후 2일 경과, 활동 사진 없음"
}
```

---

# 7. 메일 제목/본문 템플릿

NotificationRule에 저장된 템플릿을 사용하세요.

기본 제목:

```text
[ClubAgent] 활동 사진 업로드 필요: {{activity_title}}
```

기본 본문:

```text
{{activity_title}} 활동의 활동 사진이 아직 업로드되지 않았습니다.

활동일: {{activity_date}}
기준: 활동 종료 후 {{days_after}}일 경과
필요 작업: 활동 상세 > 증빙 탭에서 활동 사진을 업로드해주세요.

바로가기:
{{target_url}}
```

템플릿 변수:

```text
{{activity_title}}
{{activity_date}}
{{location}}
{{days_after}}
{{target_url}}
```

---

# 8. 알림 설정 UI 수정

알림 설정 화면에서 활동 관련 기본 규칙이 보여야 합니다.

표시 컬럼:

```text
알림 이름
유형
사용 여부
기준
반복
최대 발송 횟수
발송 전 확인
최근 발송
작업
```

작업:

```text
미리보기
즉시 발송
수정
비활성화
삭제
```

활동 사진 누락 알림 수정 UI에서 다음을 바꿀 수 있어야 합니다.

```text
사용 여부
활동일 기준 며칠 후 알림
반복 간격
최대 발송 횟수
발송 시간
발송 전 확인 여부
메일 제목
메일 본문
```

---

# 9. 대상자 미리보기

활동 사진 누락 알림에서 미리보기를 누르면 현재 대상 활동이 보여야 합니다.

예:

```text
활동 사진 누락 대상 2건

1. 위퍼퓸 교내조향활동
- 활동일: 2026-06-03
- 기준: 활동 후 2일 경과
- 활동 사진: 없음
- 링크: /activities/{id}?tab=evidence

2. 시향 활동
- 활동일: 2026-06-04
- 기준: 활동 후 2일 경과
- 활동 사진: 없음
- 링크: /activities/{id}?tab=evidence
```

활동 사진을 업로드한 뒤 다시 미리보기를 누르면 해당 활동은 대상에서 빠져야 합니다.

---

# 10. 즉시 발송

활동 사진 누락 알림에서 즉시 발송을 누르면 다음 흐름으로 동작하세요.

```text
1. 대상 계산
2. 발송 전 확인 모달
3. n8n Webhook 호출
4. NotificationDeliveryLog 저장
5. 성공/실패 결과 표시
```

n8n payload 예:

```json
{
  "event_type": "notification_email",
  "source": "clubagent",
  "payload": {
    "reminder_type": "activity_photo_missing",
    "recipient_email": "club@example.com",
    "recipient_name": "운영진",
    "subject": "[ClubAgent] 활동 사진 업로드 필요: 위퍼퓸 교내조향활동",
    "body": "위퍼퓸 교내조향활동의 활동 사진이 아직 업로드되지 않았습니다.",
    "target_url": "https://agent.example.com/activities/{id}?tab=evidence"
  }
}
```

---

# 11. 활동 체크리스트 반영

활동 상세 체크리스트에 다음 항목을 추가하세요.

```text
활동 사진 업로드
```

상태 기준:

```text
document_type = activity_photo 증빙이 1개 이상 있으면 완료
```

활동일 전에는 경고로 표시하지 않아도 됩니다.

활동일 + 설정일수 이후 activity_photo가 없으면 처리 필요로 표시하세요.

---

# 12. Dashboard / Budget / Chatbot 반영

활동 사진 누락은 처리 필요 항목으로 표시될 수 있어야 합니다.

Dashboard 또는 예산 관리:

```text
활동 사진 누락 2건
```

링크:

```text
/activities/{activity_id}?tab=evidence
```

챗봇 질문 대응:

```text
활동 사진 안 올린 활동 있어?
사진 증빙 빠진 활동 알려줘.
위퍼퓸 활동 사진 올라왔어?
```

답변 예:

```text
활동 사진이 누락된 활동은 1개입니다.

1. 위퍼퓸 교내조향활동
- 활동일: 2026-06-03
- 기준: 활동 후 2일 경과
- 증빙 탭: /activities/{id}?tab=evidence
```

---

# 13. 삭제 관련 주의사항

이번 Task에서 삭제 가능해야 하는 것은 “알림 규칙”입니다.

삭제 대상:

```text
NotificationRule
```

삭제 정책:

```text
soft delete
deleted_at 설정
enabled = false
```

삭제하면 안 되는 것:

```text
NotificationDeliveryLog
발송 이력
증빙 파일
활동
```

알림 규칙 삭제 후에도 과거 발송 이력은 남아 있어야 합니다.

---

# 14. Backend 수정 대상

```text
backend/app/models/notification.py
backend/app/models/receipt.py
backend/app/models/uploaded_file.py

backend/app/schemas/notification.py
backend/app/schemas/receipt.py

backend/app/routers/notifications.py
backend/app/routers/receipts.py
backend/app/routers/activities.py

backend/app/services/notification_service.py
backend/app/services/notification_target_service.py
backend/app/services/notification_seed_service.py
backend/app/services/n8n_service.py
backend/app/services/evidence_service.py

backend/alembic/versions/*
```

---

# 15. Frontend 수정 대상

```text
frontend/app/notifications/page.tsx
frontend/app/activities/[id]/page.tsx
frontend/app/receipts/page.tsx
frontend/components/notifications/*
frontend/components/evidence/*
frontend/lib/api.ts
```

필요 컴포넌트:

```text
NotificationRuleList.tsx
NotificationRuleFormModal.tsx
NotificationRulePreviewModal.tsx
NotificationDeliveryLogTable.tsx
ActivityPhotoMissingPreview.tsx
```

---

# 16. 테스트

추가 또는 보강:

```text
backend/tests/test_default_notification_rules.py
backend/tests/test_notification_rule_delete.py
backend/tests/test_activity_photo_evidence.py
backend/tests/test_activity_photo_missing_notification.py
backend/tests/test_activity_checklist_photo_required.py
backend/tests/test_notification_send_now.py
```

필수 테스트:

```text
1. 기본 알림 규칙이 최초 1회 생성됨
2. 기본 규칙이 중복 생성되지 않음
3. 사용자가 수정한 규칙이 seed에 의해 덮어써지지 않음
4. 삭제된 규칙은 due 대상 계산에서 제외됨
5. 삭제된 규칙은 즉시 발송할 수 없음
6. activity_photo 증빙 저장 가능
7. activity_photo는 amount=null이어도 정상 저장 가능
8. activity_photo가 있으면 activity_photo_missing 대상에서 제외
9. activity_date + days_after가 지났고 activity_photo가 없으면 대상에 포함
10. max_send_count 초과 시 제외
11. repeat_interval_days 이내 중복 발송 제외
12. 활동 체크리스트에서 activity_photo가 있으면 완료
13. send-now 호출 시 n8n_service 호출
14. NotificationDeliveryLog가 저장됨
```

---

# 17. 브라우저 검증

```text
1. 알림 설정 페이지 접속
2. 기본 알림 규칙이 표시되는지 확인
3. 활동 사진 누락 알림이 기본 ON인지 확인
4. 활동 사진 누락 알림 수정
5. days_after 값을 2에서 1로 변경
6. 저장 후 유지되는지 확인
7. 활동 사진 누락 알림 미리보기 실행
8. 활동일이 기준일을 지난 활동 중 activity_photo 없는 활동이 표시되는지 확인
9. 해당 활동 증빙 탭에 활동 사진 업로드
10. 다시 미리보기 실행
11. 대상에서 빠지는지 확인
12. 즉시 발송 실행
13. n8n 호출 및 발송 이력 저장 확인
14. 알림 규칙 삭제
15. 삭제 후 목록에서 사라지고 due 대상에 포함되지 않는지 확인
16. 발송 이력은 유지되는지 확인
```

---

# 18. 완료 기준

```text
1. 활동 관련 기본 알림 규칙이 생성된다.
2. 활동 사진 누락 알림이 기본 ON으로 제공된다.
3. 사용자가 활동 사진 누락 기준 days_after를 수정할 수 있다.
4. 사용자가 알림 규칙을 삭제할 수 있다.
5. 삭제된 알림 규칙은 실행되지 않는다.
6. activity_photo 증빙 타입이 추가된다.
7. 활동 사진이 있으면 누락 대상에서 제외된다.
8. 활동일 + 설정일수 이후 활동 사진이 없으면 누락 대상으로 잡힌다.
9. 대상자 미리보기가 가능하다.
10. 즉시 발송 시 n8n Webhook이 호출된다.
11. 발송 이력이 저장된다.
12. 활동 체크리스트에 활동 사진 업로드 상태가 반영된다.
13. pytest 통과
14. npm run build 통과
```

---

# 19. 완료 보고 형식

```text
Task 45 완료 보고

1. 원인
- 활동 관련 기본 알림 규칙이 필요했던 이유:
- 활동 사진 누락 알림이 필요했던 이유:
- 알림 규칙 삭제가 필요했던 이유:

2. 수정 파일
- backend:
- frontend:
- migration:
- tests:

3. 기본 알림 규칙
- seed:
- 중복 방지:
- 사용자 수정 보존:

4. 활동 사진 증빙
- document_type:
- 업로드:
- 체크리스트:

5. 활동 사진 누락 알림
- days_after:
- 대상 계산:
- 미리보기:
- 즉시 발송:

6. 알림 규칙 삭제
- soft delete:
- due 제외:
- 발송 이력 유지:

7. n8n 연동
- payload:
- send-now:
- delivery log:

8. Dashboard/Budget/Chatbot 반영
- 처리 필요:
- 챗봇 답변:

9. 검증
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task45: add default activity notifications and activity photo missing reminders
```
