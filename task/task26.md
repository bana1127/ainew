# Task 26. 부원 명단 관리 구조 재설계

## 현재 프로젝트

현재 프로젝트는 ClubAgent입니다.

Task 1~25까지 진행하면서 활동 관리, AI 작업실, 활동 참가자 import, 부원 관리, 납부 관리, HWPX 생성, Human-in-the-loop 확인 구조가 일부 구현되었습니다.

이번 Task 26의 목표는 **부원 명단 관리 구조를 안정화**하는 것입니다.

현재 가장 큰 문제는 다음입니다.

```text
활동 신청서/참가자 명단 파일을 업로드하면
그 안에 있는 사람들이 전역 Members에 자동 추가됨
→ 정식 부원이 아닌 사람도 부원으로 들어감
→ 같은 사람이 중복 추가됨
→ 잘못 읽힌 이름/학번/전화번호가 부원 목록을 오염시킴
```

이번 Task에서는 전역 부원 명단과 활동 참가자 데이터를 명확히 분리합니다.

---

# 핵심 정책

앞으로 부원 데이터는 다음 정책을 따라야 합니다.

```text
1. Members는 전역 부원 명단이다.
2. ActivityParticipants는 활동별 참가자 기록이다.
3. 활동 참가자 파일을 업로드했다고 Members를 자동 생성하면 안 된다.
4. Members는 부원 관리 전용 업로드/수동 추가/확인 후 반영을 통해서만 생성된다.
5. 활동 참가자 import는 기존 Members와 대조해서 연결만 한다.
6. 기존 Members에 없는 사람은 바로 부원으로 만들지 말고 “미등록 참가자 후보”로 남긴다.
```

즉, 이번 Task 26 이후에는 다음이 보장되어야 합니다.

```text
부원 명단 업로드
→ Members 생성/수정 가능

활동 참가자 명단 업로드
→ Members 자동 생성 금지
→ 기존 Members와 대조
→ ActivityParticipant로 연결
→ 미등록자는 후보로 표시
```

---

# 이번 Task에서 구현할 것

```text
1. 부원 명단 전용 업로드 공간 추가
2. 부원 명단 import preview 구현
3. 신규/기존 업데이트/중복 후보/오류/검토 필요 분류
4. 사용자가 확인 후 반영해야 Members에 적용
5. 부원 삭제 또는 비활성화 기능 추가
6. 부원 중복 병합 기능 추가
7. student_id/phone normalize 강화
8. Members 중복 방지
9. 활동 참가자 import에서 Members 자동 생성 경로 차단
10. 기존 활동 참가자 import가 부원 명단을 오염시키지 않도록 회귀 방지 테스트 추가
```

---

# 이번 Task에서 구현하지 말 것

```text
- 활동 참가자 import 전체 재설계
- 거래내역 매칭 구조 수정
- HWPX 생성 기능 수정
- 활동 내부 AI scope guard 전체 수정
- 외부 SaaS 연동
- 로그인/권한 시스템
```

활동 참가자 import 구조는 Task 27에서 별도로 다룹니다.
이번 Task 26에서는 **Members가 오염되지 않게 막고, 부원 명단 자체를 관리할 수 있게 만드는 것**에 집중하세요.

---

# Part A. 부원 명단 전용 업로드 UI

## 위치

다음 위치 중 기존 구조에 맞는 곳에 구현하세요.

```text
frontend/app/members/page.tsx
또는
frontend/app/members/import/page.tsx
```

가능하면 Members 페이지 안에 다음 섹션을 추가하세요.

```text
부원 명단 업로드
```

## UI 요구사항

부원 명단 업로드 영역에는 다음 기능이 있어야 합니다.

```text
1. 엑셀/CSV 파일 업로드
2. 업로드 후 바로 DB 반영 금지
3. 분석 결과 preview 표시
4. 신규 부원 수 표시
5. 기존 부원 업데이트 수 표시
6. 중복 후보 수 표시
7. 오류 행 수 표시
8. 검토 필요 행 수 표시
9. “확인 후 반영” 버튼
10. “취소” 버튼
```

Preview 예시:

```text
부원 명단 분석 결과

전체 행: 28명
신규 부원: 3명
기존 부원 업데이트: 21명
중복 후보: 2명
오류 행: 2명

[확인 후 반영] [취소]
```

행별 미리보기에는 다음이 보여야 합니다.

```text
이름
학번
학과
전화번호
이메일
상태
처리 예정 작업
검토 사유
```

---

# Part B. 부원 명단 import backend

## API 설계

다음 API를 구현하세요.

```http
POST /api/members/import/preview
POST /api/members/import/confirm
POST /api/members/import/cancel
```

또는 Task 25의 Proposed Action 구조가 이미 구현되어 있다면 다음 흐름을 사용하세요.

```text
POST /api/members/import/preview
→ assistant_action_proposals 생성
→ POST /api/assistant/actions/{action_id}/confirm
```

## Preview 동작

`POST /api/members/import/preview`는 엑셀/CSV를 분석하되 DB를 변경하지 않습니다.

응답 예시:

```json
{
  "requires_confirmation": true,
  "auto_apply": false,
  "summary": {
    "total_rows": 28,
    "new_members": 3,
    "updates": 21,
    "duplicate_candidates": 2,
    "invalid_rows": 2,
    "needs_review": 4
  },
  "rows": [
    {
      "row_index": 2,
      "name": "박민서",
      "student_id": "2025170011",
      "department": "컴퓨터공학부",
      "phone": "010-1234-5678",
      "action": "update_existing",
      "matched_member_id": "...",
      "reason": "student_id matched"
    }
  ],
  "confirm_payload": {
    "action_id": "..."
  }
}
```

## Confirm 동작

확인 후 반영을 누른 경우에만 Members를 생성/수정하세요.

동작:

```text
1. action_id 조회
2. pending 상태 확인
3. preview payload 기준으로만 반영
4. 신규 부원 생성
5. 기존 부원 정보 보강
6. 중복 후보/오류 행은 자동 반영하지 않음
7. 결과 로그 저장
```

---

# Part C. 컬럼 인식

부원 명단 엑셀은 다양한 컬럼명을 가질 수 있습니다.

다음 컬럼을 normalize + contains 방식으로 인식하세요.

## 이름

```text
이름
성명
이름을 입력해주세요
성함
```

## 학번

```text
학번
학번을 입력해주세요
2.학번
2. 학번
학번(끝까지)
```

## 학과

```text
학과
학부
전공
소속
학과/학부
```

## 전화번호

```text
전화번호
연락처
휴대폰
휴대폰 번호
전화번호를 입력해주세요
```

## 이메일

```text
이메일
메일
email
e-mail
```

---

# Part D. 값 normalize

## student_id normalize

다음 값을 같은 학번으로 인식해야 합니다.

```text
2025170011
2025170011.0
" 2025170011 "
"2025-170011"
```

정규화 결과:

```text
2025170011
```

규칙:

```python
def normalize_student_id(value):
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits or None
```

## phone normalize

다음 값을 같은 번호로 인식해야 합니다.

```text
01012345678
010-1234-5678
1012345678
10-1234-5678
```

규칙:

```text
1. 숫자만 추출
2. 10자리이고 10으로 시작하면 앞에 0 추가
3. 11자리면 010-1234-5678 형식으로 저장
```

---

# Part E. 부원 upsert 기준

부원 매칭 우선순위는 다음과 같습니다.

```text
1. student_id 정확 일치
2. phone 정확 일치
3. name + department 일치
4. name 단독 일치
```

단, `name 단독 일치`는 위험하므로 다음처럼 처리하세요.

```text
이름 단독으로 정확히 1명만 매칭되면 needs_review 또는 update_candidate
이름이 여러 명이면 duplicate_candidate
자동 update는 student_id 또는 phone이 일치할 때만 권장
```

기존 부원 업데이트 정책:

```text
1. 기존 값이 비어 있고 새 값이 있으면 보강
2. 기존 값과 새 값이 다르면 바로 덮어쓰지 말고 diff 표시
3. 사용자가 확인한 경우에만 덮어쓰기
4. student_id는 핵심 식별자이므로 자동 덮어쓰기 금지
```

---

# Part F. 부원 삭제/비활성화

Members 페이지에 부원 삭제 또는 비활성화 기능을 추가하세요.

권장 정책:

```text
hard delete 금지
status = inactive 또는 deleted_at 사용
```

UI 요구사항:

```text
1. 부원 row에 비활성화 버튼
2. 확인 confirm 표시
3. 비활성화된 부원은 기본 목록에서 숨김
4. 필터로 비활성 부원 보기 가능
5. 비활성 부원 복구 가능하면 좋음
```

Confirm 문구:

```text
이 부원을 비활성화하시겠습니까?
기존 활동 참여 기록과 납부 기록은 보존되지만, 기본 부원 목록에서는 숨겨집니다.
```

---

# Part G. 중복 부원 병합

중복 부원 정리 기능을 추가하세요.

## Backend

권장 API:

```http
GET /api/members/duplicates
POST /api/members/merge
```

중복 후보 기준:

```text
1. 같은 student_id
2. 같은 phone
3. 같은 name + department
4. 유사한 name + 같은 student_id 일부
```

## 병합 동작

```text
1. primary_member_id 선택
2. duplicate_member_id 선택
3. activity_participants.member_id를 primary로 이동
4. payment_records.member_id를 primary로 이동
5. payment_adjustment_logs에 member_id가 있으면 primary로 이동
6. duplicate member는 inactive 처리
7. duplicate member의 student_id/phone은 unique 충돌 방지를 위해 null 또는 metadata로 이동
```

주의:

activity_participants 이동 시 같은 활동에 같은 primary member가 이미 있으면 중복 participant를 만들면 안 됩니다.

---

# Part H. 활동 파일 업로드에서 Members 자동 생성 차단

이번 Task에서 가장 중요합니다.

현재 활동 신청서/명단 파일을 올리면 Members에 자동 생성되는 경로가 있다면 차단하세요.

확인 대상:

```text
backend/app/services/google_form_import_service.py
backend/app/agents/assistant_orchestrator.py
backend/app/routers/activity_form_imports.py
backend/app/services/member_service.py
```

수정 요구:

```text
1. 활동 참가자 import에서는 create_member 자동 실행 금지
2. 기존 Members에서 match만 수행
3. match 실패한 row는 unregistered_participant_candidate로 분류
4. 바로 Members에 insert하지 않음
5. 사용자가 명시적으로 “새 부원으로 등록”을 선택한 경우에만 Members 생성
6. 이 경우에도 Task 25 Proposed Action confirm을 거쳐야 함
```

기존 코드에 `create_missing_members=True` 같은 옵션이 있으면 기본값을 false로 바꾸세요.

```python
create_missing_members = False
```

---

# Part I. 미등록 참가자 후보 구조

활동 import에서 기존 부원과 매칭되지 않는 사람은 다음 구조로 반환하세요.

```json
{
  "row_index": 5,
  "name": "홍길동",
  "student_id": "2025123456",
  "phone": "010-0000-0000",
  "status": "unregistered_candidate",
  "available_actions": [
    "link_existing_member",
    "create_new_member",
    "mark_external",
    "ignore"
  ]
}
```

이번 Task에서는 DB 모델까지 만들기 어렵다면 preview response에만 포함해도 됩니다.
다만 ActivityParticipant에 바로 반영하면 안 됩니다.

---

# Part J. Human-in-the-loop 적용

부원 관련 모든 변경은 확인 후 반영 구조를 따라야 합니다.

적용 대상:

```text
1. 부원 명단 import confirm
2. 부원 비활성화
3. 부원 병합
4. 활동 import 중 새 부원 등록
5. 중복 후보 병합
```

`auto_apply=true`가 들어와도 부원 관련 작업에서는 무시하세요.

```python
auto_apply = False
requires_confirmation = True
```

---

# Part K. 테스트

다음 테스트를 추가하세요.

```text
backend/tests/test_member_import_preview.py
backend/tests/test_member_dedupe_merge.py
backend/tests/test_activity_import_does_not_create_members.py
```

## 테스트 1. 부원 명단 전용 import

```text
입력:
부원 명단 엑셀 3명

기대:
preview에서는 DB 변경 없음
confirm 후 Members 3명 생성
```

## 테스트 2. 기존 부원 업데이트

```text
기존:
박민서 / 2025170011 / phone 없음

업로드:
박민서 / 2025170011 / phone 있음

기대:
preview: update_existing
confirm 후 phone 보강
```

## 테스트 3. 활동 참가자 import는 Members 생성 금지

```text
기존 Members 0명

활동 참가자 파일:
박민서 / 2025170011

기대:
Members 여전히 0명
unregistered_candidate 반환
ActivityParticipant 자동 생성 안 됨
```

## 테스트 4. 기존 부원 연결

```text
기존 Members:
박민서 / 2025170011

활동 참가자 파일:
박민서 / 2025170011

기대:
Member 생성 없음
ActivityParticipant는 기존 member_id로 연결 후보 생성
confirm 후 ActivityParticipant 생성
```

## 테스트 5. 중복 병합

```text
Member A: 이주현 / 2022130026
Member B: 이주현 / 2022130026

병합 후:
A 유지
B inactive
B.student_id null
participants/payment_records는 A로 이동
```

---

# Part L. Frontend 검증 시나리오

## 시나리오 1. 부원 명단 업로드

```text
1. Members 페이지 접속
2. 부원 명단 엑셀 업로드
3. preview 확인
4. 신규/업데이트/중복/오류 분류 확인
5. 확인 후 반영
6. Members 목록에 반영 확인
```

## 시나리오 2. 활동 참가자 업로드

```text
1. 기존 Members 24명 준비
2. 활동 상세에서 참가자 명단 업로드
3. 기존 부원은 연결 후보로 표시
4. Members에 없는 사람은 미등록 후보로 표시
5. 이들이 바로 Members에 추가되지 않는지 확인
```

## 시나리오 3. 부원 삭제/비활성화

```text
1. Members 목록에서 부원 비활성화
2. 기본 목록에서 사라짐
3. 활동 참여 기록은 유지
4. 비활성 필터에서 확인 가능
```

---

# 완료 기준

Task 26은 다음을 모두 만족해야 완료입니다.

```text
1. 부원 명단은 전용 업로드 공간에서만 생성/수정된다.
2. 부원 명단 업로드는 preview 후 confirm 구조를 따른다.
3. 활동 참가자 파일 업로드로 Members가 자동 생성되지 않는다.
4. 기존 부원은 student_id/phone 기준으로 정확히 매칭된다.
5. 미등록 참가자는 candidate로 남고 바로 부원이 되지 않는다.
6. 부원 삭제 또는 비활성화가 가능하다.
7. 중복 부원 병합이 가능하다.
8. student_id/phone normalize가 안정적으로 동작한다.
9. 같은 student_id의 중복 Members가 생기지 않는다.
10. 활동 참가자 import 회귀 테스트에서 Members가 오염되지 않는다.
11. pytest 통과
12. npm run build 통과
```

---

# 작업 완료 보고 형식

```text
Task 26 완료 보고

1. 원인
- 부원 명단 오염 원인:
- 활동 참가자 import와 Members 생성이 섞인 이유:

2. 수정한 파일
- backend:
- frontend:
- migration:
- tests:

3. 부원 명단 전용 import
- preview:
- confirm:
- row classification:
- normalize:

4. 부원 삭제/비활성화
- API:
- UI:
- 기존 기록 보존:

5. 중복 병합
- duplicate detection:
- merge:
- participant/payment record 이동:
- unique 보호:

6. 활동 import에서 Members 자동 생성 차단
- create_missing_members:
- unregistered candidates:
- Human-in-the-loop:

7. 검증
- pytest:
- npm run build:
- browser:
  - 부원 명단 업로드:
  - 활동 참가자 업로드:
  - 중복 병합:
  - 비활성화:

권장 커밋 메시지:
task26: separate member roster management from activity participants
```
