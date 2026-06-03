# Task 20. HWPX 기반 제출 문서 생성 및 편집 지원

## 목표

ClubAgent의 활동 중심 운영 구조에 **HWPX 기반 제출 문서 생성 기능**을 추가한다.

Task 19까지는 활동별 파일함, 문서 미리보기, 파일 다운로드, 제출용 파일 지정, 월별 ZIP 생성 기반을 구현했다.
이번 Task 20에서는 실제 제출 문서 템플릿을 활용해 활동 데이터를 자동으로 채운 제출용 문서를 생성한다.

이번 Task의 목표는 다음이다.

```text
1. HWPX 템플릿 업로드 및 관리
2. HWPX 템플릿에서 치환 필드 추출
3. 활동 데이터와 템플릿 필드 매핑
4. AI 활동 보고서 초안 또는 사람이 수정한 본문을 템플릿에 삽입
5. 참여자, 활동비, 영수증, 피드백 정보를 문서에 반영
6. 생성된 HWPX 문서를 활동 파일함에 저장
7. 생성 문서를 제출용 파일로 지정
8. Activities 상세에서 보고서 작성 → 문서 생성 → 다운로드 흐름 구현
```

---

## 전제 조건

Task 1~19가 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

```text
- Activities 중심 운영 구조
- /activities/{id} 활동 상세 컨트롤 센터
- 활동 보고서 초안 생성/수정
- 활동 참여자 관리
- 활동비 납부 관리
- 영수증/증빙 관리
- Google Form 신청서/활동지 Import
- 활동별 파일함
- 파일 업로드/미리보기/다운로드/삭제
- 제출용 파일 지정
- 월별 제출 패키지 preview/ZIP 생성
```

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

```text
1. HWPX 템플릿 업로드
2. HWPX 템플릿 목록 조회
3. HWPX 템플릿 필드 추출
4. 템플릿 필드와 활동 데이터 자동 매핑
5. 매핑 미리보기
6. 사람이 보고서 본문 수정
7. HWPX 문서 생성
8. 생성 문서를 활동 파일함에 저장
9. 생성 문서를 제출용 파일로 지정
10. 생성 문서 다운로드
11. 활동 상세 보고서 탭과 파일함 탭 연동
12. Reports 페이지에서 생성 문서 확인
13. README 또는 DEMO 문서 업데이트
```

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

```text
- HWP 바이너리 완전 편집
- 웹 기반 완전한 한글 WYSIWYG 편집기
- HWPX 문서의 모든 레이아웃 완전 보존 보장
- PDF 변환 서버 구현
- Google Drive API 연동
- Notion 연동
- Slack/Telegram 연동
- 로그인/권한 시스템
- 환불/오납 정산 관리
- 실제 외부 전자결재/제출 API 연동
```

이번 Task의 목표는 **HWPX 템플릿 기반 자동 치환 문서 생성**까지이다.
HWP 파일은 원본 저장/다운로드만 지원하고, 자동 편집 대상은 HWPX로 제한한다.

---

# Part A. HWPX 처리 기본 방향

## 1. HWPX 우선 지원

HWPX는 XML 기반 문서 포맷이므로 템플릿 치환 방식으로 접근한다.

권장 처리 방식:

```text
1. HWPX 파일 업로드
2. HWPX를 zip으로 열기
3. 내부 XML 파일에서 템플릿 필드 검색
4. {{필드명}} 형태의 placeholder 추출
5. 활동 데이터로 placeholder 치환
6. 다시 HWPX zip으로 패키징
7. 생성 파일 저장
```

---

## 2. 템플릿 필드 규칙

이번 Task에서 지원할 placeholder 규칙은 다음으로 제한한다.

```text
{{활동명}}
{{활동일}}
{{활동장소}}
{{활동분류}}
{{활동상태}}
{{활동목적}}
{{활동내용}}
{{활동결과}}
{{향후계획}}
{{참여자명단}}
{{참여자수}}
{{활동비금액}}
{{활동비납부현황}}
{{영수증목록}}
{{증빙상태}}
{{피드백요약}}
{{작성일}}
{{동아리명}}
```

영문 alias도 함께 지원한다.

```text
{{activity_title}}
{{activity_date}}
{{location}}
{{category}}
{{status}}
{{purpose}}
{{content}}
{{result}}
{{next_plan}}
{{participants}}
{{participant_count}}
{{activity_fee_amount}}
{{payment_summary}}
{{receipts}}
{{evidence_status}}
{{feedback_summary}}
{{generated_date}}
{{club_name}}
```

---

## 3. 미지원 필드 처리

템플릿에 매핑할 수 없는 필드가 있으면 문서 생성을 실패시키지 않는다.

대신 다음 정책을 사용한다.

```text
- 매핑 가능한 필드는 치환
- 매핑 불가 필드는 빈 문자열 또는 "미입력"으로 치환
- 생성 결과에 missing_fields 목록 표시
```

---

# Part B. Backend 데이터 구조

## 1. DocumentTemplate 모델

새 모델 또는 기존 UploadedFile 기반 구조를 사용할 수 있다.

권장 모델:

```text
DocumentTemplate
- id
- name
- description
- template_type
- original_file_id
- file_path
- placeholder_fields_json
- is_default
- created_at
- updated_at
```

template_type 값:

```text
activity_report
activity_plan
meeting_report
mentoring_report
project_report
exchange_activity
other
```

대규모 모델 추가가 부담되면 UploadedFile에 다음 방식으로 저장해도 된다.

```text
file_category = document_template
file_role = source
preview_metadata_json.placeholder_fields = [...]
```

단, 템플릿 목록 조회와 필드 추출 API는 제공해야 한다.

---

## 2. GeneratedDocument 모델

생성된 문서도 별도 모델 또는 UploadedFile로 관리한다.

권장 방식:

```text
GeneratedDocument
- id
- activity_id 또는 activity_report_id
- template_id
- generated_file_id
- document_type
- title
- mapping_json
- missing_fields_json
- status
- created_at
```

간단히 구현하려면 UploadedFile만 사용해도 된다.

```text
file_category = activity_report
file_role = generated 또는 submission
is_submission_file = true optional
```

---

# Part C. Backend Service

## 1. HWPX Template Service

파일:

```text
backend/app/services/hwpx_template_service.py
```

주요 함수:

```python
extract_hwpx_placeholders(file_path: str) -> list[str]

build_activity_template_context(
    db: Session,
    activity_id: str,
    user_overrides: dict | None = None,
) -> dict

generate_hwpx_from_template(
    template_path: str,
    output_path: str,
    context: dict,
) -> GeneratedHwpxResult
```

---

## 2. Placeholder 추출

HWPX 내부 XML에서 다음 패턴을 찾는다.

```text
{{...}}
```

주의:

```text
- XML escape 처리
- 여러 XML 파일에 나뉘어 있을 수 있음
- paragraph나 run이 쪼개져 placeholder가 분리될 수 있음
```

이번 Task에서는 우선 단순 placeholder 추출부터 구현한다.

```text
{{활동명}}처럼 한 XML text node 안에 온전하게 존재하는 placeholder 우선 지원
```

문단 조각으로 분리된 placeholder는 TODO로 남긴다.

---

## 3. HWPX 치환

HWPX zip 내부 XML 파일을 순회하면서 placeholder를 치환한다.

주의:

```text
- 원본 템플릿 파일은 절대 수정하지 않음
- 임시 디렉터리 또는 메모리에서 복사본 생성
- 치환 후 새 HWPX 파일로 저장
- XML 특수문자는 escape 처리
```

---

## 4. 활동 데이터 context 생성

활동 기반 context는 다음 데이터를 포함한다.

```text
activity_title
activity_date
location
category
status
description

participants
participant_count

report_title
report_summary
report_content
purpose
content
result
next_plan

activity_fee_amount
payment_summary

receipts
evidence_status

feedback_summary

generated_date
club_name
```

데이터 소스:

```text
Activity 또는 ActivityReport
ActivityParticipant
ActivityFeedback
PaymentRecord
Receipt
Generated report content
Settings 또는 env CLUB_NAME
```

---

## 5. 보고서 본문 우선순위

문서에 들어갈 본문은 다음 우선순위를 사용한다.

```text
1. 사용자가 문서 생성 화면에서 직접 수정한 final_content
2. Activity report final_content
3. Activity report generated_content
4. AI가 새로 생성한 report draft
5. 빈 문자열
```

---

# Part D. Backend API

## 1. 템플릿 업로드

```http
POST /api/document-templates
```

multipart form:

```text
file
name optional
description optional
template_type optional
is_default optional
```

조건:

```text
- .hwpx 파일만 자동 치환 템플릿으로 허용
- .hwp 파일은 템플릿으로 업로드 가능하더라도 자동 치환은 unsupported 처리
```

응답:

```json
{
  "id": "template-id",
  "name": "교내 활동 참여 템플릿",
  "template_type": "activity_report",
  "placeholder_fields": ["활동명", "활동일", "참여자명단"]
}
```

---

## 2. 템플릿 목록

```http
GET /api/document-templates
```

Query:

```text
template_type optional
```

---

## 3. 템플릿 상세/필드 조회

```http
GET /api/document-templates/{template_id}
GET /api/document-templates/{template_id}/fields
```

---

## 4. 활동 기반 문서 생성 Preview

```http
POST /api/activities/{activity_id}/documents/preview
```

요청:

```json
{
  "template_id": "template-id",
  "overrides": {
    "활동내용": "사용자가 수정한 활동 내용",
    "향후계획": "다음 활동 계획"
  }
}
```

응답:

```json
{
  "activity_id": "activity-id",
  "template_id": "template-id",
  "mapped_fields": {
    "활동명": "5월 AI 스터디",
    "활동일": "2026-05-30",
    "참여자명단": "김가온, 이도윤"
  },
  "missing_fields": ["향후계획"],
  "content_preview": {
    "title": "5월 AI 스터디 활동 내역서",
    "summary": "...",
    "body": "..."
  }
}
```

---

## 5. 활동 기반 HWPX 문서 생성

```http
POST /api/activities/{activity_id}/documents/generate
```

요청:

```json
{
  "template_id": "template-id",
  "document_title": "Oui Parfum_20260530_정기스터디",
  "overrides": {
    "활동내용": "최종 수정된 본문"
  },
  "mark_as_submission": true,
  "submission_month": "2026-05"
}
```

동작:

```text
1. 활동 조회
2. 템플릿 조회
3. context 생성
4. overrides 병합
5. HWPX 생성
6. UploadedFile 또는 GeneratedDocument로 저장
7. 활동 파일함에 연결
8. mark_as_submission=true이면 제출용 파일로 지정
9. 다운로드 URL 반환
```

응답:

```json
{
  "ok": true,
  "generated_file_id": "file-id",
  "download_url": "/api/files/file-id/download",
  "missing_fields": [],
  "activity_id": "activity-id"
}
```

---

## 6. 생성 문서 목록

```http
GET /api/activities/{activity_id}/documents
```

응답:

```json
[
  {
    "id": "generated-doc-id",
    "file_id": "file-id",
    "template_name": "교내 활동 참여 템플릿",
    "title": "Oui Parfum_20260530_정기스터디.hwpx",
    "created_at": "...",
    "download_url": "/api/files/file-id/download"
  }
]
```

---

# Part E. Frontend Activities 문서 생성 UI

## 1. 활동 상세 보고서 탭 보강

수정 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/components/documents/*
frontend/lib/api.ts
```

활동 상세의 보고서 탭에 다음 섹션을 추가한다.

```text
제출 문서 생성
```

구성:

```text
1. 템플릿 선택
2. 템플릿 필드 확인
3. 활동 데이터 매핑 미리보기
4. 보고서 본문 수정 textarea/editor
5. 문서 생성 버튼
6. 생성된 문서 다운로드
7. 파일함에서 보기
```

---

## 2. 템플릿 관리 UI

간단한 템플릿 업로드 UI를 제공한다.

위치:

```text
Settings 또는 Reports 또는 Activities 문서 생성 섹션
```

이번 Task에서는 활동 상세 내부에서 업로드 가능하면 충분하다.

기능:

```text
- HWPX 템플릿 업로드
- 템플릿명 입력
- 템플릿 유형 선택
- 추출된 필드 확인
```

---

## 3. 필드 매핑 미리보기

템플릿 선택 후 다음을 보여준다.

```text
필드명
자동 매핑 값
수정 가능 여부
누락 여부
```

예시:

```text
{{활동명}} → 5월 AI 스터디
{{활동일}} → 2026-05-30
{{참여자명단}} → 김가온, 이도윤, 박서연
{{향후계획}} → 미입력
```

누락 필드는 강조한다.

---

## 4. 본문 수정 영역

AI가 생성한 보고서 초안 또는 기존 보고서 본문을 사람이 수정할 수 있어야 한다.

필드:

```text
활동 목적
주요 내용
활동 결과
향후 계획
```

또는 하나의 큰 textarea:

```text
최종 보고서 본문
```

1차 구현은 큰 textarea 하나여도 된다.

---

## 5. 문서 생성 결과

문서 생성 후 표시:

```text
문서가 생성되었습니다.
[다운로드]
[파일함에서 보기]
[제출용 파일로 지정됨]
```

생성 파일은 활동 파일함에도 표시되어야 한다.

```text
file_category=activity_report
file_role=generated 또는 submission
```

---

# Part F. Reports 페이지 연동

## 1. Reports 페이지 역할

Reports는 전체 보고서 모아보기 역할이다.

Task 20 이후 Reports에는 생성된 문서도 표시할 수 있다.

표시:

```text
활동명
보고서 상태
생성 문서 수
최근 생성 문서
다운로드
활동 상세로 이동
```

---

# Part G. File Vault 연동

Task 19의 파일함과 반드시 연결한다.

문서 생성 결과는 다음처럼 저장한다.

```text
activity_id = 현재 활동
file_category = activity_report
file_role = generated 또는 submission
is_submission_file = mark_as_submission 값
submission_month = 요청 값
```

파일함에서 다음이 가능해야 한다.

```text
미리보기
다운로드
삭제
제출용 지정/해제
```

HWPX preview는 이번 Task에서 완전 구현하지 않아도 된다.
파일함에서는 HWPX를 원본 다운로드 중심으로 표시한다.

---

# Part H. Assistant 연동

## 1. AI 보고서 초안 연동

Activity-aware Assistant가 생성한 보고서 초안은 문서 생성 UI에서 사용할 수 있어야 한다.

흐름:

```text
Assistant가 활동 보고서 초안 생성
→ 활동 report generated_content 저장
→ 문서 생성 UI에서 해당 본문을 기본값으로 표시
→ 사람이 수정
→ HWPX 생성
```

---

## 2. 문서 생성 intent는 이번 Task에서 선택사항

이번 Task에서 Assistant에게 다음 요청까지 처리하게 만들 수 있으면 좋다.

```text
"이 활동 제출용 한글 문서 만들어줘"
```

하지만 필수는 아니다.

필수는 활동 상세 UI에서 문서 생성이 가능해야 한다.

---

# Part I. 문서화

README 또는 DEMO 문서에 다음 내용을 추가한다.

```text
- HWPX 템플릿 업로드 방법
- 템플릿 placeholder 작성 규칙
- 활동 데이터와 필드 매핑 방식
- 보고서 본문 수정 후 HWPX 생성 방법
- 생성 문서 다운로드 방법
- 생성 문서가 활동 파일함과 제출 패키지에 연결되는 방식
- HWP는 이번 단계에서 원본 관리/다운로드만 지원한다는 점
```

템플릿 작성 예시:

```text
{{활동명}}
{{활동일}}
{{활동장소}}
{{참여자명단}}
{{활동내용}}
{{활동결과}}
{{영수증목록}}
{{피드백요약}}
```

---

# 실행 검증

## Backend

```bash
cd backend
alembic upgrade head
python -m compileall app
pytest
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Frontend

```bash
cd frontend
npm install
npm run build
npm run dev -- -H 0.0.0.0 -p 3000
```

외부 테스트용:

```bash
npm run build
npm run start -- -H 0.0.0.0 -p 3000
```

---

# 확인 시나리오

## 시나리오 1. HWPX 템플릿 업로드

```text
1. /activities/{id} 접속
2. 보고서 탭 이동
3. HWPX 템플릿 업로드
4. placeholder 필드 추출 확인
```

## 시나리오 2. 필드 매핑 Preview

```text
1. 템플릿 선택
2. 활동 데이터 자동 매핑 확인
3. 누락 필드 확인
4. 본문 수정
```

## 시나리오 3. HWPX 문서 생성

```text
1. 문서 제목 입력
2. 제출용 파일로 지정
3. 문서 생성 클릭
4. generated_file_id와 download_url 확인
5. HWPX 파일 다운로드
```

## 시나리오 4. 파일함 연동

```text
1. 활동 상세 파일함 탭 이동
2. 생성된 HWPX 문서가 표시되는지 확인
3. 다운로드 가능 여부 확인
4. 제출용 파일로 지정되어 있는지 확인
```

## 시나리오 5. 월별 제출 패키지 연동

```text
1. 생성 문서를 submission_month와 함께 제출용 지정
2. /api/submission-packages/preview?month=YYYY-MM 확인
3. 해당 문서가 제출 패키지에 포함되는지 확인
```

---

## 완료 기준

Task 20은 다음을 모두 만족해야 완료로 본다.

```text
1. HWPX 템플릿 업로드가 가능하다.
2. HWPX 템플릿에서 placeholder 필드를 추출할 수 있다.
3. 활동 데이터 context를 생성할 수 있다.
4. 템플릿 필드와 활동 데이터를 자동 매핑할 수 있다.
5. 매핑 preview를 볼 수 있다.
6. 사람이 보고서 본문을 수정할 수 있다.
7. HWPX 문서를 생성할 수 있다.
8. 생성된 HWPX 문서를 다운로드할 수 있다.
9. 생성된 문서가 활동 파일함에 저장된다.
10. 생성된 문서를 제출용 파일로 지정할 수 있다.
11. 생성된 문서가 월별 제출 패키지 preview에 포함된다.
12. Assistant가 생성한 보고서 초안을 문서 생성 UI에서 사용할 수 있다.
13. frontend build가 성공한다.
14. backend compile/test가 성공한다.
15. 이번 Task에서 HWP 완전 편집기, HWPX 완전 WYSIWYG, PDF 변환은 구현하지 않았다.
```

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 20 완료 보고

1. 생성/수정한 주요 파일
- ...

2. HWPX 템플릿 관리
- 업로드:
- 목록:
- 필드 추출:
- 저장 구조:

3. HWPX 생성 서비스
- placeholder 추출:
- context 생성:
- 치환:
- output 저장:

4. 활동 문서 생성 UI
- 템플릿 선택:
- 필드 매핑 preview:
- 본문 수정:
- 문서 생성:
- 다운로드:

5. 파일함/제출 패키지 연동
- 파일함 저장:
- 제출용 지정:
- 월별 패키지 포함:

6. Assistant/Reports 연동
- AI 초안 사용:
- Reports 표시:

7. 실행 검증 결과
- alembic upgrade:
- backend compile/test:
- frontend build:
- 템플릿 업로드:
- 필드 추출:
- 문서 생성:
- 다운로드:
- 제출 패키지:

8. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

9. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task20: generate hwpx documents from activity templates
```
