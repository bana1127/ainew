# Task 25. Human-in-the-loop 확인 우선 모드 적용

현재 프로젝트는 ClubAgent입니다.

현재 문제는 기능 자체보다 **AI 자동 반영의 신뢰도가 아직 충분하지 않다**는 점입니다.

지금까지 발견된 문제:

```text
1. 활동 명단 업로드가 부원 명단을 오염시킴
2. 활동 내부 AI가 현재 활동 범위를 벗어날 가능성이 있음
3. 특정 학생 납부 수정과 전체 활동비 수정이 혼동됨
4. 거래내역 매칭 결과를 바로 믿기 어려움
5. HWPX 생성 결과도 실제 확인 전까지 신뢰하기 어려움
```

따라서 이번 Task의 목표는 자동 반영을 강화하는 것이 아니라, **모든 AI 처리 결과를 사람에게 먼저 확인받고, 확인 후에만 DB에 반영하는 구조**로 바꾸는 것입니다.

---

# 핵심 정책

앞으로 AI 작업은 기본적으로 다음 흐름을 따릅니다.

```text
AI 분석
→ 반영 예정 결과 Preview 생성
→ 사용자 확인 요청
→ 사용자가 “반영”을 눌렀을 때만 실제 DB 수정
→ 반영 결과 기록
```

기본값은 항상 다음과 같아야 합니다.

```text
auto_apply = false
requires_confirmation = true
```

예외적으로 즉시 반영해도 되는 기능은 이번 Task에서는 만들지 않습니다.
현재는 모든 주요 작업이 확인 후 반영되어야 합니다.

---

# 적용 대상

다음 작업은 반드시 확인 후 반영해야 합니다.

```text
1. 부원 명단 추가/수정/삭제/병합
2. 활동 생성
3. 활동 참가자 추가/삭제/상태 변경
4. 활동비 생성/수정
5. 특정 학생 납부 상태 수정
6. 회비 납부 상태 수정
7. 거래내역 업로드/매칭/삭제
8. 영수증 분석 결과 반영
9. HWPX 생성 문서 제출용 지정
10. 파일 삭제
```

AI가 할 수 있는 것은 “제안”까지입니다.
실제 DB 변경은 사용자 확인 이후에만 수행합니다.

---

# Assistant 결과 구조 변경

AI 작업 결과는 다음 구조로 반환하세요.

```json
{
  "requires_confirmation": true,
  "auto_apply": false,
  "proposed_actions": [
    {
      "type": "activity_fee_update",
      "label": "활동비 금액 변경",
      "target": "위퍼퓸 교내조향활동",
      "before": "25,000원",
      "after": "30,000원",
      "risk": "medium"
    }
  ],
  "preview": {
    "summary": "참여자 19명의 활동비를 30,000원으로 변경할 예정입니다.",
    "affected_count": 19
  },
  "confirm_payload": {
    "action_id": "...",
    "expires_at": "..."
  }
}
```

---

# Frontend 결과 카드 요구사항

결과 카드에는 “바로 반영 완료”처럼 보이면 안 됩니다.

대신 다음처럼 표시하세요.

```text
AI가 다음 작업을 제안했습니다.

작업 유형: 활동비 수정
대상 활동: 위퍼퓸 교내조향활동
영향 대상: 참여자 19명
변경 내용: 활동비 25,000원 → 30,000원

[확인 후 반영] [취소]
```

반영 버튼을 누르기 전까지는 DB가 바뀌면 안 됩니다.

---

# Confirm Apply API 추가

확인 후 반영을 위한 공통 API를 추가하세요.

```http
POST /api/assistant/actions/{action_id}/confirm
```

동작:

```text
1. 저장된 proposed_action 조회
2. action_id 유효성 확인
3. 사용자 확인 요청인지 확인
4. 실제 DB 반영
5. 결과 로그 저장
6. 최신 데이터 refetch 가능하도록 response 반환
```

취소 API도 추가하세요.

```http
POST /api/assistant/actions/{action_id}/cancel
```

---

# Proposed Action 저장

AI가 제안한 작업은 DB에 저장하세요.

권장 모델:

```text
assistant_action_proposals
```

필드 예시:

```text
id
action_type
source
activity_id
payload_json
preview_json
status
confidence
risk_level
created_at
confirmed_at
cancelled_at
applied_at
```

상태값:

```text
pending
confirmed
applied
cancelled
expired
failed
```

---

# 신뢰도 데이터 축적

지금은 자동 반영하지 않지만, 나중에 신뢰도 기반 루프를 적용하기 위해 사용자의 선택 데이터를 저장해야 합니다.

기록할 것:

```text
1. AI가 제안한 작업
2. confidence
3. risk_level
4. 사용자가 반영했는지 취소했는지
5. 사용자가 수정 후 반영했는지
6. 반영 후 오류가 있었는지
7. 어떤 intent가 자주 틀리는지
```

나중에 다음 정책으로 확장할 수 있게 설계하세요.

```text
신뢰도 높음 + 위험 낮음 + 과거 성공률 높음
→ 자동 반영 후보

현재는 절대 자동 반영하지 않음
```

---

# 중요한 예시

## 1. 특정 학생 납부 수정

사용자 입력:

```text
박민서 학생이 활동비 25000원 제출했어
```

현재는 바로 반영하지 말고 다음처럼 제안합니다.

```text
박민서님의 활동비 납부 상태를 다음과 같이 변경할 예정입니다.

기존 상태: 미납
기존 납부 금액: 0원
변경 상태: 납부 완료
변경 납부 금액: 25,000원

[확인 후 반영] [취소]
```

## 2. 활동 참가자 명단 업로드

사용자 입력:

```text
이 명단 등록해줘
```

바로 부원/참가자를 만들지 말고 다음처럼 미리보기합니다.

```text
명단 파일을 분석했습니다.

기존 부원 연결: 17명
미등록 후보: 2명
중복 후보: 0명
오류 행: 0개

활동 참가자로 추가할 대상: 19명

[확인 후 반영] [취소]
```

## 3. 거래내역 매칭

```text
거래내역을 회비에 매칭해줘
```

바로 납부 상태를 바꾸지 말고:

```text
거래내역 24건을 분석했습니다.

자동 매칭 가능: 18건
확인 필요: 4건
미매칭: 2건

[확인 후 반영] [수동 검토]
```

---

# 기존 auto_apply 제거

다음 위치에서 자동 반영을 막으세요.

```text
assistant_orchestrator
payment_manual_update_service
google_form_import_service
activity_fee_generation_service
transaction_matching_service
receipt_analysis_service
```

기존에 `auto_apply=true`가 있더라도 현재는 무시하거나 강제로 false 처리하세요.

```python
auto_apply = False
requires_confirmation = True
```

---

# 완료 기준

이번 Task는 다음을 만족해야 완료입니다.

```text
1. AI 작업 결과가 바로 DB에 반영되지 않는다.
2. 모든 주요 작업은 proposed_action으로 저장된다.
3. 결과 카드에 변경 예정 내용이 표시된다.
4. 사용자가 확인 후 반영을 눌러야 실제 DB가 수정된다.
5. 취소하면 아무 데이터도 바뀌지 않는다.
6. 사용자의 확인/취소 선택이 기록된다.
7. 기존 자동 반영 경로가 막힌다.
8. 활동 내부 AI도 확인 후 반영 구조를 따른다.
9. 나중에 신뢰도 기반 자동화로 확장 가능한 로그가 남는다.
10. pytest 통과
11. npm run build 통과
```

---

# 작업 완료 보고 형식

```text
Task 25 Human-in-the-loop 확인 모드 완료 보고

1. 원인
- 자동 반영이 위험했던 이유:
- 데이터 오염 가능성:

2. 수정한 파일
- backend:
- frontend:
- migration:
- tests:

3. Proposed Action 구조
- model:
- action_type:
- payload:
- status:

4. Confirm/Cancel API
- confirm:
- cancel:
- applied log:

5. 적용 대상
- 부원:
- 활동 참가자:
- 납부:
- 거래내역:
- 영수증:
- HWPX:

6. Frontend
- preview card:
- 확인 후 반영:
- 취소:
- refetch:

7. 신뢰도 데이터 축적
- confidence:
- user decision:
- success/failure:

8. 검증
- 자동 반영 차단:
- 확인 후 반영:
- 취소:
- pytest:
- npm run build:
```
