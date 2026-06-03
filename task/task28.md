# Task 28. AI 자연어 명령 처리 엔진 안정화

현재 프로젝트는 ClubAgent입니다.

지금까지 부원 관리, 회비 관리, 활동 관리, 활동비, 거래내역, 영수증, HWPX 생성 기능을 구현했습니다.

하지만 현재 가장 큰 문제는 **AI가 사용자의 자연어 명령을 현재 정책에 맞게 정확히 처리하지 못한다는 점**입니다.

예시 문제:

```text
사용자 입력:
전체 회비 완납 처리해줘

현재 잘못된 동작:
- 거래내역 매칭으로 이동
- 기준 금액 30,000원 사용
- payment_matching preview 표시
- 실제 회비 완납 처리 preview가 생성되지 않음

기대 동작:
- bulk_membership_fee_mark_paid intent로 분류
- 각 PaymentRecord.required_amount 기준으로 완납 preview 생성
- 신규 15,000원, 기존 10,000원, 임원 0원 반영
- 확인 후 반영 구조 유지
```

이번 Task의 목표는 기능 추가가 아니라, **AI 명령 라우팅과 실행 정책을 현재 시스템 구조에 맞게 재정비**하는 것입니다.

---

# 1. 현재 정책

AI는 다음 정책을 반드시 따라야 합니다.

## Human-in-the-loop

```text
AI는 바로 DB에 반영하지 않는다.
AI는 분석과 preview를 생성한다.
사용자가 확인 후 반영을 눌러야 실제 DB가 변경된다.
```

기본값:

```text
auto_apply = false
requires_confirmation = true
```

## 회비와 활동비 분리

```text
membership_fee = 학기별 부원 회비
activity_fee = 특정 활동 참가자 활동비
```

회비:

```text
기준: member_id + period/current_term + payment_type=membership_fee

신규 부원: 15,000원
기존 부원: 10,000원
임원: 0원
```

활동비:

```text
기준: activity_report_id + member_id + payment_type=activity_fee

금액은 활동마다 다름.
활동 상세 내부에서 처리하는 것이 원칙.
```

거래내역:

```text
Transactions는 전체 통장 원장이다.
회비 매칭은 회비 화면에서 처리한다.
활동비 매칭은 특정 활동 내부에서 처리한다.
```

---

# 2. AI Intent Router 재정비

다음 intent를 명확히 분리하세요.

```text
bulk_membership_fee_mark_paid
membership_fee_generate_preview
membership_fee_transaction_match
manual_membership_fee_update

activity_fee_generate_preview
activity_fee_transaction_match_for_activity
manual_activity_fee_update

activity_participant_import_preview
member_roster_import_preview
activity_report_generate
hwpx_generate
unknown_needs_clarification
```

---

# 3. 자연어 명령 분류 규칙

## A. 회비 일괄 완납

다음 표현은 반드시 `bulk_membership_fee_mark_paid`로 분류합니다.

```text
전체 회비 완납 처리해줘
멤버들 전부 회비 완납 처리해줘
현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘
이번 학기 회비 전부 납부 완료로 바꿔줘
부원들 회비 다 냈다고 처리해줘
```

절대 다음으로 보내면 안 됩니다.

```text
payment_matching
activity_fee_update
membership_fee_generate_preview
manual_payment_update
```

처리 방식:

```text
1. 현재 period/current_term 확인
2. membership_fee PaymentRecord 조회
3. record별 required_amount 기준 preview 생성
4. required_amount=0이면 exempt
5. 확인 후 반영 시 paid_amount=required_amount
6. activity_fee는 절대 건드리지 않음
```

## B. 회비 거래내역 매칭

다음 표현은 `membership_fee_transaction_match`입니다.

```text
거래내역에서 회비 납부 확인해줘
통장내역 회비랑 매칭해줘
이 거래내역으로 회비 매칭해줘
회비 입금 내역 확인해줘
```

필수 조건:

```text
거래내역 파일 또는 저장된 거래내역이 있어야 함.
입금액은 PaymentRecord.required_amount와 exact match일 때만 자동 매칭 후보.
```

## C. 활동비 일괄/개별 처리

활동 상세 내부에서 다음 표현은 activity_fee입니다.

```text
참가자들 활동비 완납 처리해줘
현재 활동 활동비 납부 완료로 바꿔줘
박민서가 활동비 25000원 냈어
이 활동 거래내역으로 활동비 매칭해줘
```

처리 방식:

```text
activity_id가 있으면 현재 활동의 activity_fee만 처리한다.
membership_fee는 절대 수정하지 않는다.
```

## D. 전역 AI에서 활동비 명령이 들어온 경우

전역 AI 작업실에서 사용자가 다음처럼 말하면 활동 선택이 필요합니다.

```text
활동비 매칭해줘
활동비 완납 처리해줘
참가자들 활동비 처리해줘
```

이 경우 바로 실행하지 말고 확인 요청을 반환하세요.

```text
어떤 활동의 활동비를 처리할까요?
기존 활동을 선택하거나 활동명을 입력해주세요.
```

## E. 개별 납부 처리

다음은 manual update입니다.

```text
박민서 회비 냈어
박민서 회비 15000원 입금했어
박민서가 활동비 25000원 냈어
```

분류:

```text
이름 + 회비 + 냈어/입금/납부
→ manual_membership_fee_update

이름 + 활동비 + 냈어/입금/납부
→ manual_activity_fee_update

이름만 있고 회비/활동비가 없으면 확인 요청
```

---

# 4. 잘못된 fallback 제거

프로젝트 전체에서 다음 흔적을 제거하세요.

```text
30000
30,000
기준 금액 30,000원
default membership amount
default required amount
참여자 기준 활동비 10000원
```

단, 테스트 fixture나 과거 migration에서 의미 없는 값으로 남는 것은 제외할 수 있지만, AI 결과/프리뷰/실제 실행 로직에 노출되면 실패입니다.

검색 대상:

```text
backend/app/agents/intent_router.py
backend/app/agents/assistant_orchestrator.py
backend/app/services/payment_matching_service.py
backend/app/services/payment_manual_update_service.py
backend/app/services/assistant_action_service.py
backend/app/services/membership_fee_generation_service.py
backend/app/services/activity_fee_generation_service.py
frontend/components/assistant/AssistantResultCard.tsx
frontend/app/payments/page.tsx
frontend/app/activities/[id]/page.tsx
frontend/lib/api.ts
```

---

# 5. AI Command Policy Registry 추가

AI 자연어 명령이 계속 흩어지므로 정책을 한 곳에 모으세요.

권장 파일:

```text
backend/app/agents/command_policy_registry.py
```

여기에는 다음을 정의하세요.

```python
COMMAND_POLICIES = {
    "bulk_membership_fee_mark_paid": {
        "domain": "membership_fee",
        "scope": "global_or_term",
        "requires_confirmation": True,
        "forbidden_domains": ["activity_fee"],
    },
    "activity_fee_transaction_match_for_activity": {
        "domain": "activity_fee",
        "scope": "activity",
        "requires_activity_id": True,
        "requires_confirmation": True,
        "forbidden_domains": ["membership_fee"],
    },
}
```

Intent Router와 Orchestrator는 이 registry를 참조해서 실행해야 합니다.

---

# 6. AI 실행 전 Validation 추가

실행 전에 다음을 검증하세요.

```text
1. intent가 명확한가?
2. payment_type이 명확한가?
3. scope가 명확한가?
4. activity_id가 필요한 작업인데 activity_id가 있는가?
5. 회비 작업이 activity_fee를 건드리지 않는가?
6. 활동비 작업이 membership_fee를 건드리지 않는가?
7. confirm 없이 DB 변경하지 않는가?
```

불명확하면 실행하지 말고 질문하세요.

예:

```text
회비와 활동비 중 어떤 납부를 처리할까요?
```

또는:

```text
어떤 활동의 활동비를 처리할까요?
```

---

# 7. 결과 카드 개선

AI 결과 카드에는 반드시 다음이 표시되어야 합니다.

```text
작업 유형
도메인: 회비 / 활동비 / 거래내역 / 문서
범위: 전체 학기 / 특정 활동 / 특정 부원
현재 학기 또는 activity_id
변경 예정 수
확인 후 반영 버튼
취소 버튼
```

잘못된 카드 제목:

```text
납부 매칭 미리보기
```

회비 완납 처리에서는 다음처럼 표시해야 합니다.

```text
회비 일괄 완납 처리 미리보기
```

활동비 매칭에서는 다음처럼 표시해야 합니다.

```text
활동비 거래내역 매칭 미리보기
```

회비 거래내역 매칭에서는 다음처럼 표시해야 합니다.

```text
회비 거래내역 매칭 미리보기
```

---

# 8. Command Test Corpus 추가

AI 자연어 명령 테스트를 반드시 추가하세요.

권장 파일:

```text
backend/tests/test_assistant_command_intent_matrix.py
```

테스트 문장:

```text
전체 회비 완납 처리해줘
현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘
이번 학기 회비 납부 완료로 바꿔줘
거래내역에서 회비 납부 확인해줘
이 거래내역으로 회비 매칭해줘
박민서 회비 15000원 냈어
박민서가 활동비 25000원 냈어
활동비 매칭해줘
현재 활동 참가자들 활동비 완납 처리해줘
이 명단 참여자로 넣어줘
부원 명단 업로드해줘
```

각 문장이 기대 intent로 가는지 검증하세요.

예:

```text
전체 회비 완납 처리해줘
→ bulk_membership_fee_mark_paid

거래내역에서 회비 납부 확인해줘
→ membership_fee_transaction_match

박민서가 활동비 25000원 냈어
→ manual_activity_fee_update

활동비 매칭해줘
→ activity_missing_clarification 또는 activity_fee_transaction_match_for_activity
```

---

# 9. 실제 브라우저 검증 시나리오

다음 시나리오를 반드시 확인하세요.

## 시나리오 1. 회비 일괄 완납

```text
1. DB 초기화
2. 부원 명단 업로드
3. 회비 대상 생성
4. AI 작업실에 입력:
   현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘

기대:
- bulk_membership_fee_mark_paid
- 회비 일괄 완납 처리 미리보기
- 신규 15,000원
- 기존 10,000원
- 임원 0원
- 30,000원 문구 없음
- activity_fee record 변경 없음
```

## 시나리오 2. 회비 거래내역 매칭

```text
입력:
거래내역에서 회비 납부 확인해줘

기대:
- membership_fee_transaction_match
- 거래내역 기준 매칭
- 입금액 exact match만 자동 후보
```

## 시나리오 3. 활동비 전역 요청

```text
입력:
활동비 매칭해줘

기대:
- 어떤 활동인지 물어봄
- 바로 실행하지 않음
```

## 시나리오 4. 활동 내부 활동비 요청

```text
활동 상세 내부 AI 입력:
이 거래내역으로 활동비 매칭해줘

기대:
- 현재 activity_id 기준
- 해당 활동 참가자와 activity_fee record만 매칭
- membership_fee 변경 없음
```

---

# 10. 완료 기준

이번 Task는 다음을 만족해야 완료입니다.

```text
1. AI가 자연어 명령을 기대 intent로 분류한다.
2. 전체 회비 완납 요청이 payment_matching으로 가지 않는다.
3. 회비 / 활동비 / 거래내역 매칭 / 수동 납부가 분리된다.
4. activity_id가 필요한 작업은 activity_id 없이 실행되지 않는다.
5. 30,000원 같은 legacy 기준 금액이 AI 결과에 나오지 않는다.
6. 모든 위험 작업은 확인 후 반영 구조를 따른다.
7. AI 결과 카드에서 작업 도메인과 범위가 명확히 보인다.
8. 테스트 corpus로 자연어 명령 분류를 검증한다.
9. pytest 통과
10. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 28 AI 자연어 명령 처리 안정화 완료 보고

1. 원인
- 자연어 명령이 잘못 라우팅된 이유:
- legacy 금액이 남아 있던 위치:
- 회비/활동비가 섞인 원인:

2. 수정한 파일
- backend:
- frontend:
- tests:

3. Intent Router
- bulk_membership_fee_mark_paid:
- membership_fee_transaction_match:
- activity_fee_transaction_match:
- manual update:
- clarification:

4. Command Policy Registry
- domains:
- scopes:
- required context:
- forbidden domains:

5. Preview/Confirm
- Human-in-the-loop:
- action proposal:
- confirm validation:

6. Legacy 제거
- 30,000원:
- 활동비 10,000원 quick action:
- result card:

7. 테스트
- command intent matrix:
- 회비 완납:
- 회비 거래매칭:
- 활동비 요청:
- ambiguous request:

8. 브라우저 검증
- 전체 회비 완납:
- 회비 거래내역 매칭:
- 활동비 전역 요청:
- 활동 내부 활동비 요청:

권장 커밋 메시지:
task28: stabilize assistant command routing and payment domain policies
```
