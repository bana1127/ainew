# Task 27. 활동 참가자 Import 구조 수정

## 현재 프로젝트

현재 프로젝트는 ClubAgent입니다.

Task 26에서 부원 명단 관리 구조를 전역 Members와 분리했습니다.
이제 Task 27에서는 활동별 신청서/참가자 명단 import 구조를 수정합니다.

이번 Task의 핵심 목표는 다음입니다.

```text
활동 신청서/참가자 명단 업로드
→ 기존 부원 명단과 대조
→ 기존 부원은 활동 참가자로 연결
→ 미등록자는 바로 부원으로 만들지 않고 후보로 표시
→ 사용자가 확인 후 반영
```

---

# 현재 문제

현재 활동 참가자 import에는 다음 문제가 있습니다.

```text
1. 활동 참가자 파일을 올리면 전역 Members에 자동 추가될 수 있음
2. 정식 부원이 아닌 사람도 부원으로 들어감
3. 부원 명단과 활동 참가자 명단이 섞임
4. 미등록 참가자를 어떻게 처리할지 선택할 수 없음
5. 같은 파일을 다시 올리면 참가자가 중복될 가능성이 있음
6. 기존 부원과 매칭 결과를 사용자가 확인하기 어려움
```

---

# 핵심 정책

Task 27 이후 활동 참가자 import는 다음 정책을 따라야 합니다.

```text
1. 활동 참가자 import는 Members를 자동 생성하지 않는다.
2. 활동 참가자 import는 기존 Members와 대조한다.
3. 기존 부원과 매칭되면 ActivityParticipant 연결 후보로 표시한다.
4. 기존 부원과 매칭되지 않으면 unregistered_candidate로 표시한다.
5. 미등록 후보는 바로 부원이 되지 않는다.
6. 사용자가 확인 후 반영을 눌러야 ActivityParticipant가 생성된다.
7. 미등록 후보는 사용자가 선택해야 한다.
   - 기존 부원으로 연결
   - 새 부원으로 등록
   - 외부인으로 유지
   - 무시
8. 같은 활동에 같은 member가 중복 참가자로 들어가면 안 된다.
```

---

# 이번 Task에서 구현할 것

```text
1. 활동별 참가자/신청서 import preview 구현
2. 기존 부원 매칭 로직 구현
3. 미등록 참가자 후보 처리
4. 외부인 참가자 처리
5. 확인 후 반영 구조 적용
6. 같은 활동 내 참가자 중복 방지
7. 같은 파일 재업로드 시 중복 방지
8. 활동 상세 참여자 탭에서 import 결과 확인 UI 구현
9. AI 작업실/활동 내부 AI에서 참가자 import 시에도 동일 구조 적용
```

---

# 이번 Task에서 구현하지 말 것

```text
- 전역 부원 명단 import 기능
- 거래내역 매칭 구조 수정
- HWPX 생성 수정
- 활동 내부 AI scope guard 전체 재설계
- 로그인/권한 시스템
- 외부 SaaS 연동
```

전역 부원 명단 import는 Task 26 범위입니다.
이번 Task 27은 활동별 참가자 import만 다룹니다.

---

# Part A. 활동 참가자 Import Preview API

## API 설계

다음 API를 구현하거나 기존 API를 보강하세요.

```http
POST /api/activities/{activity_id}/participants/import/preview
POST /api/activities/{activity_id}/participants/import/confirm
POST /api/activities/{activity_id}/participants/import/cancel
```

Task 25의 Proposed Action 구조가 있다면 confirm/cancel은 공통 API를 사용해도 됩니다.

```http
POST /api/assistant/actions/{action_id}/confirm
POST /api/assistant/actions/{action_id}/cancel
```

## Preview 동작

Preview 단계에서는 DB를 변경하지 마세요.

동작 순서:

```text
1. 파일 업로드
2. 엑셀/CSV 컬럼 분석
3. 이름/학번/전화번호/학과 추출
4. 기존 Members와 매칭
5. row별 처리 예정 action 생성
6. proposed_action 저장
7. preview 결과 반환
```

응답 예시:

```json
{
  "requires_confirmation": true,
  "auto_apply": false,
  "activity_id": "...",
  "summary": {
    "total_rows": 19,
    "matched_members": 17,
    "unregistered_candidates": 2,
    "duplicate_candidates": 0,
    "invalid_rows": 0,
    "already_participants": 1,
    "will_create_participants": 16
  },
  "rows": [
    {
      "row_index": 2,
      "name": "박민서",
      "student_id": "2025170011",
      "department": "컴퓨터공학부",
      "phone": "010-1234-5678",
      "match_status": "matched_member",
      "matched_member_id": "...",
      "participant_status": "will_create",
      "action": "link_existing_member",
      "reason": "student_id matched"
    },
    {
      "row_index": 5,
      "name": "홍길동",
      "student_id": "2025123456",
      "phone": "010-0000-0000",
      "match_status": "unregistered_candidate",
      "action": "needs_user_selection",
      "available_actions": [
        "link_existing_member",
        "create_new_member",
        "mark_external",
        "ignore"
      ],
      "reason": "no matching member"
    }
  ],
  "confirm_payload": {
    "action_id": "..."
  }
}
```

---

# Part B. 컬럼 인식

활동 참가자 파일은 Google Form 응답, 명단, 신청서 등 다양한 형태일 수 있습니다.

다음 컬럼명을 normalize + contains 방식으로 인식하세요.

## 이름

```text
이름
성명
성함
이름을 입력해주세요
성함을 입력해주세요
```

## 학번

```text
학번
학번을 입력해주세요
2.학번
2. 학번
학번(끝까지)
끝까지 적어주세요
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

## 신청 상태/참여 상태 후보

```text
참여 여부
참석 여부
신청 여부
활동 후 제출
피드백
```

---

# Part C. 값 Normalize

## student_id normalize

다음 값은 같은 학번으로 인식해야 합니다.

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

## phone normalize

다음 값은 같은 전화번호로 인식해야 합니다.

```text
01012345678
010-1234-5678
1012345678
10-1234-5678
```

10자리이고 `10`으로 시작하면 앞에 `0`을 붙이세요.

예:

```text
1056279620 → 01056279620 → 010-5627-9620
```

---

# Part D. 기존 부원 매칭 기준

활동 참가자 import는 Members를 자동 생성하지 않습니다.
기존 부원과 매칭만 수행합니다.

매칭 우선순위:

```text
1. student_id 정확 일치
2. phone 정확 일치
3. name + department 일치
4. name 단독 일치
```

단, name 단독 일치는 자동 연결하지 말고 검토 필요로 두세요.

정책:

```text
student_id 일치 → matched_member
phone 일치 → matched_member
name + department 일치 → matched_member 또는 needs_review
name만 일치 → needs_review
동명이인 → duplicate_candidate
매칭 없음 → unregistered_candidate
```

---

# Part E. 미등록 참가자 후보 처리

기존 Members에 없는 row는 바로 부원으로 만들지 않습니다.

Preview row는 다음 구조를 가져야 합니다.

```json
{
  "row_index": 5,
  "name": "홍길동",
  "student_id": "2025123456",
  "phone": "010-0000-0000",
  "match_status": "unregistered_candidate",
  "available_actions": [
    "link_existing_member",
    "create_new_member",
    "mark_external",
    "ignore"
  ]
}
```

사용자는 각 미등록 후보에 대해 선택할 수 있어야 합니다.

```text
1. 기존 부원으로 연결
2. 새 부원으로 등록
3. 외부인으로 유지
4. 무시
```

이번 Task에서 UI가 복잡하다면 최소한 다음을 구현하세요.

```text
- 미등록 후보 목록 표시
- 기본값은 반영 제외
- 사용자가 확인한 기존 부원만 연결
- 새 부원 생성은 별도 명시 확인 후만 가능
```

---

# Part F. Confirm 반영

Confirm 시에만 ActivityParticipant를 생성/수정합니다.

동작:

```text
1. action_id 조회
2. pending 상태 확인
3. preview rows 기준으로 처리
4. matched_member row는 ActivityParticipant 생성 또는 업데이트
5. already_participant row는 중복 생성하지 않고 상태/metadata만 업데이트
6. ignored row는 건너뜀
7. external row는 외부 참가자로 저장
8. create_new_member 선택 row만 Members 생성 후 participant 연결
9. 결과 로그 저장
```

응답 예시:

```json
{
  "ok": true,
  "activity_id": "...",
  "result": {
    "created_participants": 16,
    "updated_participants": 1,
    "external_participants": 1,
    "ignored_rows": 1,
    "created_members": 1
  }
}
```

---

# Part G. ActivityParticipant 모델/저장 정책

ActivityParticipant는 다음 개념을 지원해야 합니다.

```text
member_id: 기존 부원 연결 시 사용
external_name: 외부인일 때 사용
external_affiliation: 외부인 소속
external_student_id: 외부인 학번 또는 식별값
status: applied / confirmed / completed / cancelled
source_file_id
raw_response
```

이미 모델이 있다면 기존 필드에 맞춰 구현하세요.

중복 방지 기준:

```text
activity_id 또는 activity_report_id + member_id
```

외부인 중복 방지 기준:

```text
activity_id 또는 activity_report_id + external_name + external_student_id
```

---

# Part H. 같은 파일 재업로드 방지

같은 파일을 다시 업로드해도 참가자가 중복 생성되면 안 됩니다.

요구사항:

```text
1. 같은 활동에 같은 member는 1명만 participant로 존재
2. 같은 파일을 다시 import하면 updated_participants로 처리
3. duplicate row가 있으면 preview에서 표시
4. confirm 후에도 중복 row 생성 금지
```

---

# Part I. 파일함 연결

활동 참가자 import에 사용한 원본 파일은 해당 활동 파일함에 저장되어야 합니다.

저장 정보:

```text
file_category = activity_participant_import
file_role = source
activity_id 또는 activity_report_id = 현재 활동
```

Preview만 하고 cancel한 경우에도 원본 파일을 남길지 여부는 정책을 정하세요.

권장:

```text
preview 단계 파일은 temporary 또는 pending
confirm 후 activity file vault에 source로 확정
cancel하면 임시 파일로 남기거나 정리
```

---

# Part J. Frontend UI

활동 상세 참여자 탭에 import UI를 추가 또는 정리하세요.

## 기본 흐름

```text
1. 참가자 명단/신청서 업로드
2. 분석 버튼
3. Preview 결과 표시
4. row별 상태 확인
5. 미등록 후보 처리 선택
6. 확인 후 반영
7. 참여자 목록 refetch
```

## Preview Summary

```text
전체 행: 19명
기존 부원 연결: 17명
미등록 후보: 2명
이미 참가자: 1명
오류 행: 0명
반영 예정: 16명
```

## Row 표시

```text
이름
학번
학과
전화번호
매칭 상태
처리 예정
검토 사유
선택 작업
```

상태 badge:

```text
기존 부원 연결
미등록 후보
중복 후보
이미 참가자
오류
외부인
무시
```

---

# Part K. AI 작업실/활동 내부 AI와 연결

AI 작업실 또는 활동 내부 AI에서 사용자가 다음처럼 요청할 수 있습니다.

```text
이 명단 등록해줘
이 신청서 참여자로 넣어줘
이 파일로 참가자 추가해줘
```

이 경우에도 바로 반영하지 마세요.

AI는 다음 결과를 반환해야 합니다.

```text
명단 파일을 분석했습니다.
기존 부원 연결 17명, 미등록 후보 2명입니다.
확인 후 반영하시겠습니까?
```

즉, AI 작업도 동일한 import preview/proposed_action 구조를 사용해야 합니다.

자동 apply 금지:

```text
auto_apply = false
requires_confirmation = true
```

---

# Part L. 테스트

다음 테스트를 추가하세요.

```text
backend/tests/test_activity_participant_import_preview.py
backend/tests/test_activity_participant_import_confirm.py
backend/tests/test_activity_participant_import_no_member_autocreate.py
backend/tests/test_activity_participant_import_duplicates.py
```

## 테스트 1. 기존 부원 연결 Preview

```text
기존 Members:
박민서 / 2025170011

파일:
박민서 / 2025170011

기대:
preview: matched_member
Members count 변화 없음
ActivityParticipant 생성 없음
```

## 테스트 2. Confirm 후 참가자 생성

```text
preview 후 confirm

기대:
ActivityParticipant 생성
member_id = 기존 박민서
Members count 변화 없음
```

## 테스트 3. 미등록 후보

```text
기존 Members 없음

파일:
홍길동 / 2025123456

기대:
preview: unregistered_candidate
Members count 변화 없음
ActivityParticipant 생성 없음
```

## 테스트 4. 미등록 후보를 외부인으로 반영

```text
unregistered_candidate row를 mark_external로 선택 후 confirm

기대:
Members count 변화 없음
ActivityParticipant external_name=홍길동 생성
```

## 테스트 5. 같은 파일 재업로드

```text
같은 활동에 같은 파일 두 번 import

기대:
ActivityParticipant 중복 생성 없음
두 번째 confirm은 updated_participants로 처리
```

## 테스트 6. create_new_member는 명시 선택 시에만

```text
unregistered_candidate row를 create_new_member로 선택

기대:
confirm 후에만 Member 생성
preview 단계에서는 생성 안 됨
```

---

# Part M. 브라우저 검증 시나리오

## 시나리오 1. 기존 부원 연결

```text
1. Members에 박민서가 있음
2. 활동 상세 > 참여자 탭
3. 참가자 명단 업로드
4. preview에서 박민서가 기존 부원 연결로 표시됨
5. confirm
6. 참여자 목록에 박민서 추가
7. Members 수는 증가하지 않음
```

## 시나리오 2. 미등록 후보

```text
1. Members에 없는 홍길동이 포함된 파일 업로드
2. preview에서 미등록 후보로 표시
3. confirm 전에는 Members와 Participants 모두 변화 없음
4. 외부인으로 유지 선택
5. confirm
6. ActivityParticipant에는 external로 추가
7. Members에는 추가되지 않음
```

## 시나리오 3. 같은 파일 재업로드

```text
1. 같은 파일을 한 번 더 업로드
2. preview에서 이미 참가자로 표시
3. confirm해도 참여자 수가 2배로 늘어나지 않음
```

---

# 완료 기준

Task 27은 다음을 모두 만족해야 완료입니다.

```text
1. 활동 참가자 import는 preview 후 confirm 구조를 따른다.
2. preview 단계에서는 Members와 ActivityParticipants가 변경되지 않는다.
3. 기존 Members와 student_id/phone 기준으로 매칭된다.
4. 매칭된 부원은 confirm 후 ActivityParticipant로 연결된다.
5. 매칭되지 않은 사람은 unregistered_candidate로 남는다.
6. 미등록 후보는 바로 Member가 되지 않는다.
7. 외부인으로 유지할 수 있다.
8. create_new_member는 사용자가 명시 선택한 경우에만 가능하다.
9. 같은 활동에 같은 member가 중복 participant로 생성되지 않는다.
10. 같은 파일 재업로드 시 중복 생성되지 않는다.
11. AI 작업실/활동 내부 AI도 바로 반영하지 않고 preview/proposed_action을 반환한다.
12. 원본 파일은 활동 파일함에 source로 연결된다.
13. pytest 통과
14. npm run build 통과
```

---

# 작업 완료 보고 형식

```text
Task 27 완료 보고

1. 원인
- 기존 활동 참가자 import 문제:
- Members 자동 생성 문제:
- 중복 participant 문제:

2. 수정한 파일
- backend:
- frontend:
- migration:
- tests:

3. Import Preview
- API:
- row classification:
- summary:
- proposed_action:

4. Matching
- student_id:
- phone:
- name+department:
- unregistered_candidate:

5. Confirm
- matched member:
- external participant:
- create_new_member:
- ignored rows:

6. 중복 방지
- same member/activity:
- same file reimport:
- constraints/upsert:

7. AI 연동
- assistant preview:
- auto_apply 차단:
- confirm flow:

8. 파일함 연동
- source file:
- category:
- role:

9. 검증
- pytest:
- npm run build:
- browser:
  - 기존 부원 연결:
  - 미등록 후보:
  - 외부인 유지:
  - 같은 파일 재업로드:

권장 커밋 메시지:
task27: implement confirmed activity participant imports
```
