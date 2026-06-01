# Task 4. 관리 UI 1차 구현 — 부원, 활동 카테고리, 레퍼런스, 활동 보고서

## 목표

Task 3에서 구현한 CRUD API와 프론트 목록 페이지를 기반으로, 실제 사용자가 자체 웹페이지에서 핵심 데이터를 등록/수정/삭제할 수 있는 관리 UI를 구현한다.

이번 Task의 핵심은 ClubAgent의 기본 운영 데이터인 다음 4가지를 자체 웹페이지에서 관리 가능하게 만드는 것이다.

1. 부원 명부
2. 활동 카테고리
3. 레퍼런스 활동 보고서
4. 활동 보고서

이번 Task가 완료되면 AI 기능 없이도 다음 흐름이 가능해야 한다.

```text
부원 등록
→ 활동 카테고리 등록
→ 기존 활동 보고서 레퍼런스 등록
→ 활동 보고서 수동 작성
→ 활동 참여자 연결
→ 대시보드/목록에서 확인
```

---

## 전제 조건

Task 1, Task 2, Task 3이 완료되어 있어야 한다.

Task 3 완료 기준:

* 주요 CRUD API 구현 완료
* Dashboard Summary API 구현 완료
* File Upload API 구현 완료
* Frontend 주요 목록 페이지 구현 완료
* seed 데이터가 프론트에서 확인 가능

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

1. 공통 Form UI 컴포넌트
2. 부원 관리 CRUD UI
3. 활동 카테고리 관리 CRUD UI
4. 레퍼런스 보고서 CRUD UI
5. 활동 보고서 CRUD UI
6. 활동 보고서 작성 시 카테고리 선택
7. 활동 보고서 작성 시 참여자 선택
8. 활동 보고서 작성 시 레퍼런스 선택
9. 활동 참여자 연결 기능
10. 기본 검색/필터 UI
11. 사용자 확인용 confirm/delete 처리
12. README에 화면 사용 방법 추가

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

* OpenAI API 호출
* 활동 보고서 AI 생성
* 이미지 분석
* 영수증 OCR
* 거래내역서 xls/xlsx 파싱
* 납부자/미납자 자동 매칭
* n8n workflow
* Notion 연동
* Slack/Telegram 연동
* Qdrant 또는 pgvector 연동
* 로그인/권한 시스템
* 고급 디자인 시스템
* 복잡한 drag-and-drop 파일 관리
* 감사 규정 자동 판정

필요한 위치에는 TODO 주석만 남긴다.

---

## Backend 구현 요구사항

Task 3에서 대부분의 CRUD API가 구현되어 있다면 기존 API를 최대한 활용한다.

다만 활동 참여자 연결을 위해 필요한 API가 없다면 이번 Task에서 최소한의 API를 추가한다.

---

### 1. Activity Participants API 추가

파일 예시:

```text
backend/app/routers/activity_participants.py
```

또는 기존 `activity_reports.py`에 포함해도 된다.

필수 API:

```http
GET /api/activity-reports/{report_id}/participants
PUT /api/activity-reports/{report_id}/participants
```

### GET participants

특정 활동 보고서의 참여자 목록을 반환한다.

응답 예시:

```json
[
  {
    "id": "participant-id",
    "activity_report_id": "report-id",
    "member_id": "member-id",
    "role": "participant",
    "member": {
      "id": "member-id",
      "name": "김가온",
      "student_id": "20260001"
    }
  }
]
```

복잡한 nested response가 어렵다면 최소한 아래 형태도 가능하다.

```json
[
  {
    "id": "participant-id",
    "activity_report_id": "report-id",
    "member_id": "member-id",
    "role": "participant"
  }
]
```

### PUT participants

특정 활동 보고서의 참여자 목록을 한 번에 갱신한다.

요청 예시:

```json
{
  "participants": [
    {
      "member_id": "member-id-1",
      "role": "participant"
    },
    {
      "member_id": "member-id-2",
      "role": "leader"
    }
  ]
}
```

동작 방식:

1. 기존 activity_report_id의 participants 삭제
2. 요청으로 받은 participants 새로 생성
3. 중복 member_id는 제거 또는 400 처리
4. 존재하지 않는 member_id가 있으면 404 또는 400 반환

주의:

* ActivityReport가 존재하지 않으면 404
* Member가 존재하지 않으면 404 또는 400
* 같은 activity_report_id, member_id 중복 방지

---

### 2. Activity Report API 보강

기존 `activity_reports.py`가 있다면 다음 필터/정렬을 확인한다.

필수 필터:

```text
category_id
status
q
```

정렬은 간단히 최신순이면 된다.

가능하면 목록 응답에 category 이름이 같이 보이도록 보강한다.

방법은 둘 중 하나로 한다.

1. response schema에 category nested 포함
2. 프론트에서 category_id 기준으로 category 목록과 매칭

복잡해지면 2번 방식을 사용한다.

---

### 3. Reference Reports API 보강

기존 `reference_reports.py`에서 다음 기능을 확인한다.

필수 필터:

```text
category_id
q
```

목록에서 title, category_id, tags, created_at이 확인 가능해야 한다.

---

## Frontend 구현 요구사항

이번 Task의 중심은 Frontend UI이다.

---

## 공통 UI 컴포넌트

다음 공통 컴포넌트를 구현하거나 기존 컴포넌트를 확장한다.

```text
frontend/components/ui/
  Button.tsx
  Input.tsx
  Textarea.tsx
  Select.tsx
  Modal.tsx
  ConfirmDialog.tsx
  EmptyState.tsx
  LoadingState.tsx
  ErrorState.tsx
  Badge.tsx
```

이미 비슷한 컴포넌트가 있으면 새로 만들지 말고 재사용한다.

요구사항:

* 너무 복잡한 디자인은 필요 없음
* Tailwind 기반으로 깔끔한 관리자 페이지 톤 유지
* 버튼 상태: 기본, 비활성화 정도만 처리
* Modal은 생성/수정 폼에 사용 가능
* ConfirmDialog는 삭제/비활성화 확인에 사용 가능

---

## 1. Members 관리 UI

파일:

```text
frontend/app/members/page.tsx
```

### 구현 기능

* 부원 목록 조회
* 부원 검색
* 상태 필터
* 부원 추가
* 부원 수정
* 부원 비활성화
* 저장 후 목록 자동 갱신
* 에러 메시지 표시

### 목록 컬럼

```text
이름
학번
학과
전화번호
이메일
상태
메모
생성일
관리 버튼
```

### 추가/수정 폼 필드

```text
name
student_id
department
phone
email
status
memo
```

### 상태 값

```text
active
inactive
graduated
paused
```

표시는 한글로 해도 된다.

```text
active → 활동중
inactive → 비활성
graduated → 졸업
paused → 휴면
```

### 삭제 동작

실제 삭제가 아니라 API의 DELETE를 호출해서 `status = inactive`가 되게 한다.

버튼 텍스트는 "비활성화"로 표시한다.

---

## 2. Activity Categories 관리 UI

파일:

```text
frontend/app/settings/page.tsx
```

또는 별도 페이지를 만들 경우:

```text
frontend/app/settings/categories/page.tsx
```

Task 1~3의 사이드바 구조에 맞춰 자연스럽게 구현한다.

### 구현 기능

* 카테고리 목록 조회
* 카테고리 추가
* 카테고리 수정
* 카테고리 삭제
* required_fields_json 편집
* report_template 편집

### 목록 컬럼

```text
카테고리명
설명
필수 입력값
템플릿 일부 미리보기
생성일
관리 버튼
```

### 추가/수정 폼 필드

```text
name
description
required_fields_json
report_template
```

### required_fields_json 입력 방식

처음에는 복잡한 JSON 에디터를 만들 필요 없다.

다음 둘 중 쉬운 방식으로 구현한다.

1. Textarea에 JSON 문자열 입력
2. 쉼표로 구분된 필드명을 입력받고 내부에서 JSON 배열로 변환

가능하면 2번을 추천한다.

예시 입력:

```text
활동명, 활동 일시, 활동 장소, 참석자, 활동 목적, 주요 내용, 활동 결과
```

저장 값 예시:

```json
{
  "fields": [
    "활동명",
    "활동 일시",
    "활동 장소",
    "참석자",
    "활동 목적",
    "주요 내용",
    "활동 결과"
  ]
}
```

---

## 3. Reference Reports 관리 UI

파일:

```text
frontend/app/references/page.tsx
```

### 구현 기능

* 레퍼런스 보고서 목록 조회
* 카테고리 필터
* 검색
* 레퍼런스 추가
* 레퍼런스 수정
* 레퍼런스 삭제
* 상세 내용 미리보기

### 목록 컬럼

```text
제목
카테고리
태그
내용 미리보기
생성일
관리 버튼
```

### 추가/수정 폼 필드

```text
category_id
title
content
tags
```

### tags 입력 방식

쉼표로 구분된 문자열을 입력받고 JSON 배열로 변환한다.

예시:

```text
스터디, 정기모임, AI
```

저장 값 예시:

```json
["스터디", "정기모임", "AI"]
```

---

## 4. Activity Reports 관리 UI

파일:

```text
frontend/app/activities/page.tsx
```

또는 실제 작성 페이지를 따로 둘 경우:

```text
frontend/app/reports/page.tsx
```

기존 사이드바 구조에 맞춰 다음처럼 역할을 나눈다.

```text
/activities → 활동 보고서 목록
/reports → 활동 보고서 작성/수정 중심
```

이번 Task에서는 최소한 `/activities`에서 목록/수정/보관이 가능하고, `/reports`에서 새 보고서를 작성할 수 있으면 된다.

---

### /activities 구현 기능

* 활동 보고서 목록 조회
* 카테고리 필터
* 상태 필터
* 검색
* 활동 보고서 수정
* 활동 보고서 보관 처리
* final_content 또는 generated_content 미리보기

### 목록 컬럼

```text
제목
카테고리
활동일
장소
상태
내용 미리보기
생성일
관리 버튼
```

### 상태 값

```text
draft
generated
confirmed
archived
```

표시는 한글로 해도 된다.

```text
draft → 초안
generated → 생성됨
confirmed → 확정
archived → 보관
```

삭제 버튼 대신 "보관" 버튼으로 표시한다.

---

### /reports 구현 기능

* 새 활동 보고서 작성
* 카테고리 선택
* 레퍼런스 선택
* 활동명 입력
* 활동일 입력
* 장소 입력
* 입력 메모 작성
* 최종 내용 직접 작성
* 참여자 선택
* 저장
* 저장 후 `/activities` 또는 해당 목록으로 이동

### 작성 폼 필드

```text
category_id
reference_report_id
title
activity_date
location
input_text
final_content
status
participants
```

주의:

* `reference_report_id`는 DB 모델에 없어도 된다.
* 선택한 reference report의 content를 보고서 작성 화면에 참고용으로 보여주면 된다.
* 실제 activity_reports 테이블에는 reference_report_id를 저장하지 않아도 된다.
* 필요하면 input_text에 "참고 레퍼런스: ..." 형태로 일부 포함해도 된다.
* 더 좋은 방식이 가능하면 TODO로 남긴다.

---

## 5. 참여자 선택 UI

활동 보고서 작성/수정 시 부원 목록을 불러와 참여자를 선택할 수 있어야 한다.

### 최소 구현 방식

* members 목록을 checkbox로 표시
* 선택된 member_id 배열을 저장
* 저장 후 `/api/activity-reports/{report_id}/participants` PUT 호출

### Role 처리

처음에는 기본 role을 `participant`로 저장한다.

가능하면 대표자 1명을 `leader`로 선택할 수 있게 한다.

간단한 방식:

```text
참여자 checkbox
대표자 select
```

어려우면 전부 participant로 저장하고 TODO를 남긴다.

---

## 6. Frontend API 함수 보강

파일:

```text
frontend/lib/api.ts
```

기존 Task 3 함수에 다음 create/update/delete 함수를 보강한다.

필수 함수 예시:

```ts
createMember()
updateMember()
deleteMember()

createActivityCategory()
updateActivityCategory()
deleteActivityCategory()

createReferenceReport()
updateReferenceReport()
deleteReferenceReport()

createActivityReport()
updateActivityReport()
deleteActivityReport()

getActivityReportParticipants()
updateActivityReportParticipants()
```

함수 이름은 프로젝트 기존 스타일에 맞춰도 된다.

---

## 7. UX 요구사항

### 공통

* 저장 중 버튼 비활성화
* 저장 성공 후 목록 갱신
* 실패 시 에러 메시지 표시
* 삭제/비활성화/보관 전 확인창 표시
* 데이터가 없으면 EmptyState 표시
* 로딩 중 LoadingState 표시

### 레이아웃

* 데스크톱 우선
* 관리자 대시보드 톤 유지
* 너무 많은 기능보다 안정적으로 동작하는 폼 우선
* 모바일 대응은 필수 아님

---

## 8. README 업데이트

README에 Task 4 사용 방법을 추가한다.

포함할 내용:

```text
- 부원 등록 방법
- 활동 카테고리 등록 방법
- 레퍼런스 보고서 등록 방법
- 활동 보고서 수동 작성 방법
- 활동 참여자 연결 방법
- 이번 Task에서 AI 생성은 아직 구현하지 않았다는 설명
```

---

## 실행 검증

가능하면 다음을 실행해 검증한다.

```bash
docker compose up -d db
cd backend
alembic upgrade head
python -m app.scripts.seed
python -m compileall app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

새 터미널:

```bash
cd frontend
npm install
npm run build
npm run dev
```

확인 URL:

```text
http://localhost:3000/members
http://localhost:3000/settings
http://localhost:3000/references
http://localhost:3000/activities
http://localhost:3000/reports
```

API 확인:

```text
http://localhost:8000/api/members
http://localhost:8000/api/activity-categories
http://localhost:8000/api/reference-reports
http://localhost:8000/api/activity-reports
```

---

## 완료 기준

Task 4는 다음을 모두 만족해야 완료로 본다.

1. 부원 등록/수정/비활성화가 프론트에서 가능하다.
2. 활동 카테고리 등록/수정/삭제가 프론트에서 가능하다.
3. 레퍼런스 보고서 등록/수정/삭제가 프론트에서 가능하다.
4. 활동 보고서 수동 작성/수정/보관이 프론트에서 가능하다.
5. 활동 보고서 작성 시 카테고리와 레퍼런스를 선택할 수 있다.
6. 활동 보고서 작성 시 참여자를 선택하고 저장할 수 있다.
7. 주요 폼에서 저장/수정/삭제 후 목록이 갱신된다.
8. 로딩/에러/빈 데이터 상태가 최소한으로 처리되어 있다.
9. README에 사용 방법이 추가되어 있다.
10. 이번 Task에서 AI, OCR, 거래내역서 파싱, 납부 매칭, n8n, Notion, Slack 기능은 구현되지 않았다.

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 4 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 구현된 Frontend 관리 UI
- ...

3. 추가/보강된 Backend API
- ...

4. 주요 동작 확인 결과
- 부원 등록/수정/비활성화:
- 카테고리 등록/수정/삭제:
- 레퍼런스 등록/수정/삭제:
- 활동 보고서 작성/수정/보관:
- 참여자 연결:

5. 실행 검증 결과
- docker compose up -d db:
- alembic upgrade head:
- python -m app.scripts.seed:
- backend compile/test:
- frontend build:
- 주요 URL 확인:

6. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

7. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:

8. 다음 Task에서 해야 할 일
- Task 5: 거래내역서 업로드 및 파서 구현
```
