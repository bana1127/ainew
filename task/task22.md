# Task 22. 활동 관리 핵심 흐름 긴급 안정화

## 목표

ClubAgent의 활동 관리 핵심 흐름을 실제 사용 가능하게 안정화한다.

현재 확인된 문제는 다음과 같다.

```text
1. 활동 삭제 기능이 없음
2. AI 작업실에서 명단 파일을 올리고 새 활동 생성을 요청해도 참여자 연동이 안 됨
3. AI 작업실에서 업로드한 파일이 활동 파일함에 연결되지 않음
4. Activity-aware Assistant, Google Form Import, File Vault가 실제 실행 흐름에서 연결되지 않음
```

이번 Task의 목표는 다음이다.

```text
AI 작업실에서 명단/신청서 파일 업로드
→ 새 활동 생성
→ 파일을 활동 파일함에 저장
→ 부원 자동 추가/업데이트
→ 활동 참여자 자동 등록
→ 활동 상세에서 참여자와 파일 확인 가능
```

---

## 구현 범위

이번 Task에서는 다음을 구현한다.

```text
1. 활동 삭제 기능 추가
2. 활동 삭제는 soft delete로 처리
3. 삭제된 활동은 기본 목록에서 제외
4. AI 작업실에서 새 활동 생성 요청 처리 보강
5. AI 작업실 업로드 파일을 activity file vault에 저장
6. 명단/신청서/Google Form 엑셀 파일을 활동 참여자로 자동 반영
7. 새 활동 생성 후 import apply까지 자동 실행 또는 사용자 확인 후 실행
8. Assistant 결과 카드에 생성된 활동, 추가된 참여자, 연결된 파일 표시
9. 활동 상세에서 즉시 참여자 목록과 파일함 확인 가능
10. 관련 API 500 방어 및 통합 검증
```

---

## 이번 Task에서 구현하지 말 것

```text
- 새로운 Agent 기능
- Notion/Slack/Telegram 연동
- 로그인/권한 시스템
- HWPX 추가 기능
- 환불/오납 신규 기능
- Google Forms API 직접 연동
```

이번 Task는 기존 기능의 연결 오류를 해결하는 안정화 작업이다.

---

# Part A. 활동 삭제 기능

## 1. Backend 삭제 API

다음 API를 구현한다.

```http
DELETE /api/activities/{activity_id}
```

동작:

```text
1. activity_id 존재 확인
2. 실제 DB row hard delete 금지
3. deleted_at 또는 status=archived/deleted 방식으로 soft delete
4. 연결된 files, participants, payment_records, receipts는 삭제하지 않음
5. 일반 활동 목록에서는 삭제된 활동 제외
6. 활동 상세 접근 시 삭제된 활동이면 404 또는 deleted 상태 안내
```

권장 필드:

```text
deleted_at nullable
```

이미 status가 있다면 `archived` 또는 `deleted`를 사용할 수 있지만, 가능하면 deleted_at을 추가한다.

---

## 2. Frontend 삭제 UI

수정 대상:

```text
frontend/app/activities/page.tsx
frontend/app/activities/[id]/page.tsx
```

요구사항:

```text
- 활동 카드에 삭제 버튼 추가
- 활동 상세 상단에 삭제 버튼 추가
- 삭제 전 confirm 표시
- 삭제 후 /activities로 이동
- 삭제된 활동은 목록에서 사라짐
```

confirm 문구:

```text
이 활동을 삭제하시겠습니까?
참여자, 파일, 납부 기록은 복구를 위해 보관되지만 활동 목록에서는 보이지 않습니다.
```

---

# Part B. AI 작업실 새 활동 생성 + 명단 파일 연동

## 1. 현재 문제

AI 작업실에서 사용자가 다음처럼 요청할 수 있다.

```text
이 명단 파일로 새 활동 만들어줘
이 신청서 파일로 활동 생성하고 참여자 등록해줘
이 엑셀 보고 새 활동 만들고 부원 추가해줘
```

현재는 이 흐름이 끝까지 이어지지 않는다.

수정 후에는 다음이 되어야 한다.

```text
1. 파일 업로드
2. Assistant가 새 활동 생성 의도 파악
3. 활동 생성
4. 업로드 파일을 새 활동 파일함에 저장
5. 엑셀 유형 판별
6. 명단/신청서면 member upsert
7. activity participant upsert
8. 결과 카드에 생성 결과 표시
```

---

## 2. Assistant intent 보강

Intent Router에서 다음 요청을 인식한다.

```text
activity_create_with_roster
activity_create_with_application_form
activity_create_with_file
```

키워드 예시:

```text
새 활동 만들어줘
활동 생성해줘
명단 추가해줘
참여자 등록해줘
신청자 등록해줘
이 파일로 활동 만들어줘
```

---

## 3. 새 활동 생성 규칙

활동명은 다음 우선순위로 정한다.

```text
1. 사용자 메시지에서 명시된 활동명
2. 파일명에서 추정한 활동명
3. "새 활동"
```

예시:

```text
파일명: 26-1 위퍼퓸 교내조향활동 모집.xlsx
→ 활동명 후보: 교내조향활동

메시지: 이 명단으로 5월 공유시향 활동 만들어줘
→ 활동명: 5월 공유시향 활동
```

활동일은 다음 우선순위로 정한다.

```text
1. 사용자 메시지에서 날짜 추출
2. 엑셀 응답의 timestamp 또는 제출 시점
3. 오늘 날짜
```

---

# Part C. 파일함 연결

## 1. Assistant 업로드 파일 저장 보강

AI 작업실에서 업로드된 모든 파일은 임시 파일로만 쓰고 사라지면 안 된다.

activity_id가 결정되면 반드시 파일함에 저장한다.

저장 정보:

```text
activity_id 또는 activity_report_id
original_filename
stored_filename
mime_type
file_ext
size_bytes
file_category
file_role
```

분류 규칙:

```text
명단/신청서 엑셀 → google_form_application 또는 member_roster
활동지/피드백 엑셀 → google_form_feedback
이미지 → photo 또는 receipt 후보
PDF/HWP/HWPX → attachment 또는 activity_report 후보
```

---

## 2. 활동 상세 파일함 반영

Assistant 실행 후 `/activities/{id}`의 파일함 탭에서 업로드 파일이 보여야 한다.

필수 확인:

```text
- 파일명 표시
- 파일 유형 표시
- 다운로드 가능
- Excel preview 가능하면 표시
```

---

# Part D. 명단/신청서 자동 참여자 등록

## 1. Excel 유형 판별

Task 18의 classifier를 재사용한다.

지원 유형:

```text
activity_application_form
activity_feedback_form
member_roster
unknown_excel
```

명단 파일은 `member_roster` 또는 `activity_application_form`으로 처리한다.

---

## 2. member upsert

매칭 우선순위:

```text
1. student_id 정확 일치
2. phone 정확 일치
3. name + department 일치
4. name 단독 일치
```

기존 부원이 있으면 누락된 정보만 보강한다.
없으면 신규 부원을 생성한다.

---

## 3. activity participant upsert

새 활동 생성 후 명단 row마다 참여자를 등록한다.

상태 규칙:

```text
activity_application_form → applied
member_roster → confirmed
activity_feedback_form → completed
```

참여자 row에는 raw_response_json 또는 metadata를 저장한다.

---

## 4. Preview와 자동 Apply 기준

AI 작업실에서 사용자가 명확히 “새 활동 만들고 등록해줘”라고 요청한 경우:

```text
- 새 활동 생성
- import preview
- 자동 apply 가능
```

다만 중복 위험이 있으면 requires_confirmation=true로 반환한다.

중복 위험 기준:

```text
- 같은 이름이 여러 명 존재
- 학번 없음
- 전화번호 없음
- 활동 후보가 여러 개
```

---

# Part E. Assistant 결과 카드

AI 작업실 결과 카드에 다음 정보를 표시한다.

```text
생성된 활동
- 활동명
- 활동일
- 활동 상세 이동 버튼

참여자 등록 결과
- 전체 행 수
- 신규 부원 수
- 기존 부원 업데이트 수
- 신규 참여자 수
- 기존 참여자 수
- 검토 필요 수

파일 연결 결과
- 저장된 파일명
- 파일함 이동 버튼
```

버튼:

```text
활동 상세 보기
참여자 확인
파일함 보기
```

---

# Part F. Backend API 점검

확인/보강 대상:

```text
POST /api/assistant/execute
POST /api/activities
DELETE /api/activities/{activity_id}
POST /api/activity-form-imports/preview
POST /api/activity-form-imports/apply
POST /api/activities/{activity_id}/files
GET /api/activities/{activity_id}/files
```

Assistant가 내부에서 필요한 서비스 함수를 직접 호출해도 되고, API 흐름을 재사용해도 된다.

중요한 것은 결과적으로 다음이 성립해야 한다.

```text
Assistant 실행 결과
→ activity 생성
→ file 저장
→ member upsert
→ participant upsert
```

---

# Part G. 검증 시나리오

## 시나리오 1. 활동 삭제

```text
1. /activities 접속
2. 활동 카드 삭제 클릭
3. confirm 승인
4. 활동 목록에서 사라지는지 확인
5. DB row가 hard delete되지 않았는지 확인
```

## 시나리오 2. AI 작업실에서 명단 파일로 새 활동 생성

```text
1. /assistant 접속
2. 명단 또는 신청서 엑셀 업로드
3. "이 명단으로 새 활동 만들어줘" 입력
4. 실행
5. 새 활동 생성 확인
6. 참여자 자동 등록 확인
7. 업로드 파일이 활동 파일함에 표시되는지 확인
```

## 시나리오 3. 활동 상세 확인

```text
1. Assistant 결과에서 활동 상세 보기 클릭
2. 참여자 탭 확인
3. 파일함 탭 확인
4. 업로드 파일과 참여자 목록이 반영되어 있는지 확인
```

## 시나리오 4. 중복 위험

```text
1. 학번 없는 명단 업로드
2. 이름이 중복되는 부원 존재
3. 자동 apply 대신 확인 필요로 표시되는지 확인
```

---

## 완료 기준

```text
1. 활동 삭제 버튼이 있다.
2. 활동 삭제는 soft delete로 처리된다.
3. 삭제된 활동은 목록에서 제외된다.
4. AI 작업실에서 새 활동 생성 요청을 인식한다.
5. 명단/신청서 엑셀 업로드 시 새 활동을 만들 수 있다.
6. 업로드 파일이 생성된 활동 파일함에 저장된다.
7. 명단/신청서의 부원이 자동 추가/업데이트된다.
8. 활동 참여자가 자동 등록된다.
9. Assistant 결과 카드에 생성 활동/참여자/파일 연결 결과가 표시된다.
10. 활동 상세에서 참여자와 파일을 바로 확인할 수 있다.
11. 중복 위험 시 확인 필요로 처리된다.
12. 기존 일반 Assistant 요청은 깨지지 않는다.
13. frontend build가 성공한다.
14. backend compile/test가 성공한다.
```

---

## 작업 완료 후 보고 형식

```text
Task 22 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 활동 삭제
- Backend API:
- soft delete:
- Frontend 버튼:
- 삭제 후 목록 갱신:

3. AI 작업실 새 활동 생성
- intent:
- activity 생성:
- activity title/date 추정:
- 결과 카드:

4. 파일함 연결
- Assistant 업로드 파일 저장:
- file_category:
- 활동 파일함 표시:

5. 명단/신청서 Import 연동
- form classifier:
- member upsert:
- participant upsert:
- status 적용:
- 중복 위험 처리:

6. 실행 검증 결과
- backend compile/test:
- frontend build:
- 활동 삭제:
- AI 작업실 명단 업로드:
- 참여자 반영:
- 파일함 반영:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

8. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task22: stabilize activity creation import and deletion
```
