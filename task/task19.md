# Task 19. 활동별 파일함, 문서 뷰어, 제출 패키지 관리

## 목표

ClubAgent의 활동 중심 운영 구조에 실제 제출 자료 관리 기능을 추가한다.

현재 Activities는 활동 생성, 참여자, 보고서, 활동비, 영수증, Google Form 응답 처리를 중심으로 구성되어 있다.
하지만 실제 동아리 운영에서는 활동별로 다양한 파일을 함께 관리해야 한다.

예시:

```text
- 활동 내역서 HWP/HWPX/PDF
- 활동 기획서 HWP/HWPX/PDF
- 활동 사진
- 영수증 이미지/PDF
- Google Form 신청서 엑셀
- Google Form 활동지/피드백 엑셀
- 첨부 자료 PDF
- 월별 제출 ZIP
```

이번 Task의 목표는 다음이다.

```text
1. 활동별 파일함 구현
2. 파일 업로드/목록/미리보기/다운로드/삭제 기능 구현
3. 파일을 활동과 연결
4. 파일 유형 자동 분류
5. PDF/Image/Excel preview 지원
6. HWP/HWPX 파일은 원본 저장 및 다운로드 우선 지원
7. 제출용 파일 지정 기능 구현
8. 월별 제출 패키지 preview 및 ZIP 생성 기반 구현
9. 활동 상세에서 파일 누락 여부 확인
```

---

## 전제 조건

Task 1~18이 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

```text
- Activities 중심 운영 구조
- /activities/{id} 활동 상세 컨트롤 센터
- 활동 참여자 관리
- 활동 보고서 작성
- 활동비 관리
- 영수증/증빙 관리
- Google Form 응답 Import
- 거래내역 회비/활동비 매칭
- 매칭 취소
- UploadedFile 또는 유사한 파일 저장 모델
```

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

```text
1. 활동별 파일함 UI
2. 활동별 파일 업로드
3. 파일 목록 조회
4. 파일 상세 조회
5. 파일 미리보기
6. 파일 다운로드
7. 파일 삭제
8. 파일 활동 연결/해제
9. 파일 유형 자동 분류
10. 제출용 파일 지정
11. 활동별 제출 준비 체크리스트
12. 월별 제출 패키지 preview
13. 월별 ZIP 생성 및 다운로드
14. README 또는 DEMO 문서 업데이트
```

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

```text
- HWP/HWPX 완전 편집기
- HWPX 템플릿 기반 자동 문서 생성
- AI가 HWPX 문서 본문을 직접 작성하는 기능
- 환불/오납 정산 관리
- Google Drive API 직접 연동
- Notion 연동
- Slack/Telegram 연동
- 로그인/권한 시스템
- 실제 외부 스토리지 S3 연동
```

HWPX 템플릿 기반 문서 생성은 다음 Task로 분리한다.

```text
Task 20. HWPX 기반 제출 문서 생성 및 편집 지원
```

환불/오납 정산 관리는 다음 Task로 분리한다.

```text
Task 21. 활동비 오납/환불 정산 관리
```

---

# Part A. 파일 관리 데이터 구조

## 1. 기존 UploadedFile 모델 확인

다음 모델을 확인한다.

```text
backend/app/models/
backend/app/models/uploaded_file.py
backend/app/models/file.py
```

기존 업로드 파일 모델이 있으면 재사용한다.

필요한 필드가 없다면 최소한의 Alembic migration으로 nullable 필드를 추가한다.

권장 필드:

```text
activity_id 또는 activity_report_id nullable
original_filename
stored_filename
storage_path
mime_type
file_ext
size_bytes
file_category
file_role
preview_status
preview_metadata_json
is_submission_file
submission_month
version
deleted_at nullable
created_at
updated_at
```

프로젝트가 activity_report_id 기반이면 `activity_report_id`를 사용한다.
Activity 모델이 있으면 `activity_id`를 사용한다.

---

## 2. file_category 표준

파일 유형 분류값은 다음을 사용한다.

```text
activity_report
activity_plan
receipt
photo
google_form_application
google_form_feedback
bank_statement
attachment
submission_package
other
```

---

## 3. file_role 표준

파일의 제출/운영상 역할은 다음을 사용한다.

```text
source
evidence
report
plan
attachment
submission
generated
```

예시:

```text
활동 내역서 PDF → file_category=activity_report, file_role=submission
활동 기획서 PDF → file_category=activity_plan, file_role=submission
영수증 이미지 → file_category=receipt, file_role=evidence
Google Form 신청서 → file_category=google_form_application, file_role=source
활동 사진 → file_category=photo, file_role=evidence
```

---

## 4. 파일 삭제 정책

이번 Task에서는 실제 파일 삭제가 아니라 soft delete를 우선한다.

```text
deleted_at 값이 있으면 일반 목록에서 제외
실제 파일은 디스크에 유지
관리자가 필요하면 나중에 hard delete 구현
```

단, UI에서는 사용자가 삭제된 것처럼 보여야 한다.

---

# Part B. 파일 유형 자동 분류

## 1. 파일명/확장자 기반 분류

업로드 시 파일명을 보고 file_category를 자동 추정한다.

예시 규칙:

```text
파일명에 "내역서" 포함 → activity_report
파일명에 "기획서" 포함 → activity_plan
파일명에 "영수증" 포함 → receipt
파일명에 "응답" 또는 "Google Form" 포함 → google_form_application 또는 google_form_feedback 후보
파일명에 "거래" 또는 "입출금" 포함 → bank_statement
이미지 확장자 → photo 또는 receipt 후보
zip 확장자 → submission_package
```

Google Form 엑셀은 Task 18의 classifier를 재사용한다.

```text
activity_application_form → google_form_application
activity_feedback_form → google_form_feedback
bank_statement → bank_statement
```

---

## 2. 구현 파일

권장 파일:

```text
backend/app/services/file_classification_service.py
backend/app/services/file_storage_service.py
backend/app/services/file_preview_service.py
```

주요 함수:

```python
classify_uploaded_file(filename: str, mime_type: str | None, headers: list[str] | None = None) -> FileClassificationResult
save_uploaded_file(...)
build_file_preview(...)
```

---

# Part C. Backend API

## 1. 활동별 파일 목록

```http
GET /api/activities/{activity_id}/files
```

Query:

```text
category optional
role optional
include_deleted optional default false
```

응답 예시:

```json
[
  {
    "id": "file-id",
    "activity_id": "activity-id",
    "original_filename": "Oui Parfum_20250911_멘토링활동.pdf",
    "mime_type": "application/pdf",
    "file_ext": "pdf",
    "size_bytes": 123456,
    "file_category": "activity_report",
    "file_role": "submission",
    "is_submission_file": true,
    "preview_available": true,
    "created_at": "..."
  }
]
```

---

## 2. 활동별 파일 업로드

```http
POST /api/activities/{activity_id}/files
```

multipart form:

```text
file
file_category optional
file_role optional
is_submission_file optional
submission_month optional
```

동작:

```text
1. 활동 존재 여부 확인
2. 파일 저장
3. 파일 유형 자동 분류
4. uploaded_files row 생성
5. preview metadata 생성 가능한 경우 생성
6. 결과 반환
```

---

## 3. 파일 상세 조회

```http
GET /api/files/{file_id}
```

응답:

```json
{
  "id": "file-id",
  "activity_id": "activity-id",
  "original_filename": "file.pdf",
  "mime_type": "application/pdf",
  "file_category": "activity_report",
  "file_role": "submission",
  "preview_metadata": {},
  "download_url": "/api/files/file-id/download"
}
```

---

## 4. 파일 미리보기

```http
GET /api/files/{file_id}/preview
```

파일 유형별 동작:

```text
PDF
→ inline response 또는 preview_url 반환

Image
→ inline response 또는 preview_url 반환

Excel
→ sheet 목록, 첫 30행 preview JSON 반환

HWP/HWPX
→ 이번 Task에서는 metadata와 다운로드 안내 반환
→ 가능하면 파일명/크기/확장자만 표시
→ HWPX 텍스트 추출이 쉽게 가능하면 optional로 preview_text 제공

ZIP
→ 내부 파일 목록 반환
```

Excel preview 응답 예시:

```json
{
  "type": "excel",
  "sheets": [
    {
      "name": "Form Responses 1",
      "headers": ["타임스탬프", "이름", "학번"],
      "rows": [
        ["2026.05.01", "김가온", "20260001"]
      ]
    }
  ]
}
```

ZIP preview 응답 예시:

```json
{
  "type": "zip",
  "files": [
    {
      "filename": "Oui Parfum_20250911_멘토링활동.pdf",
      "size_bytes": 123456
    }
  ]
}
```

---

## 5. 파일 다운로드

```http
GET /api/files/{file_id}/download
```

동작:

```text
- 원본 파일 다운로드
- Content-Disposition attachment
- original_filename 유지
```

---

## 6. 파일 삭제

```http
DELETE /api/files/{file_id}
```

동작:

```text
- soft delete
- deleted_at 설정
- 실제 파일은 삭제하지 않음
```

응답:

```json
{
  "ok": true,
  "deleted_id": "file-id"
}
```

---

## 7. 파일 활동 연결/해제

```http
PATCH /api/files/{file_id}/activity
```

요청:

```json
{
  "activity_id": "activity-id 또는 null"
}
```

동작:

```text
- activity_id가 있으면 해당 활동에 연결
- null이면 활동 연결 해제
```

---

## 8. 제출용 파일 지정

```http
PATCH /api/files/{file_id}/submission
```

요청:

```json
{
  "is_submission_file": true,
  "submission_month": "2026-09",
  "file_category": "activity_report",
  "file_role": "submission"
}
```

---

# Part D. 제출 패키지 관리 API

## 1. 월별 제출 패키지 Preview

```http
GET /api/submission-packages/preview
```

Query:

```text
month=2026-09
```

응답 예시:

```json
{
  "month": "2026-09",
  "activities": [
    {
      "activity_id": "activity-id",
      "title": "9월 멘토링 활동",
      "activity_date": "2026-09-11",
      "submission_files": [
        {
          "id": "file-id",
          "filename": "Oui Parfum_20260911_멘토링활동.pdf",
          "category": "activity_report"
        }
      ],
      "missing_items": ["activity_plan", "receipt"]
    }
  ],
  "summary": {
    "activity_count": 5,
    "submission_file_count": 12,
    "missing_count": 3
  }
}
```

---

## 2. 월별 제출 ZIP 생성

```http
POST /api/submission-packages/generate
```

요청:

```json
{
  "month": "2026-09",
  "include_categories": [
    "activity_report",
    "activity_plan",
    "receipt",
    "attachment"
  ]
}
```

동작:

```text
1. 해당 월의 submission file 수집
2. 파일명을 제출용 규칙으로 정리
3. ZIP 생성
4. generated file로 저장
5. 다운로드 URL 반환
```

응답:

```json
{
  "ok": true,
  "package_file_id": "file-id",
  "download_url": "/api/files/file-id/download"
}
```

---

## 3. 파일명 규칙

가능하면 제출 파일명을 다음 형식으로 정리한다.

```text
동아리명_YYYYMMDD_활동분류_활동명.ext
```

예시:

```text
Oui Parfum_20260911_멘토링활동.pdf
Oui Parfum_20260912_회의.pdf
Oui Parfum_20261029_외부단체연합활동_내향인.pdf
```

동아리명은 설정값으로 둔다.

```env
CLUB_NAME=Oui Parfum
```

또는 settings에서 관리한다.
없으면 기본값 `ClubAgent`를 사용한다.

---

# Part E. Frontend 활동 상세 파일함

## 1. 활동 상세 파일함 탭 추가

수정 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/components/files/*
frontend/lib/api.ts
```

활동 상세에 탭 또는 섹션을 추가한다.

```text
파일함
```

표시 구성:

```text
- 파일 업로드 영역
- 파일 유형 필터
- 제출용 파일 필터
- 파일 카드/테이블
- 미리보기 패널
```

---

## 2. 파일 카드 표시

파일 카드에는 다음 정보를 표시한다.

```text
파일명
파일 유형
역할
크기
업로드 일시
제출용 여부
미리보기 버튼
다운로드 버튼
삭제 버튼
```

예시:

```text
Oui Parfum_20250911_멘토링활동.pdf
유형: 활동 내역서
역할: 제출 파일
크기: 1.2MB
[미리보기] [다운로드] [삭제]
```

---

## 3. 파일 업로드 UX

활동 상세에서 파일을 드래그하거나 선택해서 업로드할 수 있어야 한다.

허용 확장자:

```text
pdf
png
jpg
jpeg
webp
xlsx
xls
csv
hwp
hwpx
zip
```

업로드 옵션:

```text
파일 유형
파일 역할
제출용 파일 여부
제출 월
```

파일 유형은 자동 분류가 기본이고, 사용자가 수정 가능해야 한다.

---

## 4. 파일 미리보기 UI

파일 유형별 preview UI:

```text
PDF
→ iframe 또는 object로 표시

Image
→ 이미지 viewer

Excel
→ sheet/row preview table

HWP/HWPX
→ "원본 파일 다운로드 후 확인" 안내
→ 가능하면 metadata 표시

ZIP
→ 내부 파일 목록 표시
```

주의:

```text
- 미리보기 불가능한 파일 때문에 전체 화면이 깨지면 안 됨
- 실패 시 다운로드 버튼은 항상 제공
```

---

## 5. 삭제 UX

삭제 버튼 클릭 시 confirm을 띄운다.

문구:

```text
이 파일을 삭제하시겠습니까?
화면에서는 사라지지만 원본 파일은 복구를 위해 서버에 보관될 수 있습니다.
```

성공 후 파일 목록 새로고침.

---

# Part F. 전체 파일 관리 페이지 보강

가능하면 전체 파일 관리 페이지를 추가한다.

```text
/files
```

이번 Task에서 시간이 부족하면 TODO로 남긴다.

최소 요구는 활동 상세 파일함이다.

---

# Part G. Receipts / Reports / Assistant 연동

## 1. Receipts 연동

영수증 업로드 결과도 파일함에 표시되어야 한다.

```text
영수증 분석 파일
→ activity file로도 표시
→ file_category=receipt
→ file_role=evidence
```

---

## 2. Reports 연동

보고서 PDF/HWP/HWPX 파일은 파일함에서 제출용 파일로 지정할 수 있어야 한다.

```text
file_category=activity_report
file_role=submission
is_submission_file=true
```

---

## 3. Assistant 연동

AI 작업실에서 업로드한 파일도 activity_id가 있으면 활동 파일함에 연결되어야 한다.

```text
activity_id가 있는 Assistant 요청
→ uploaded_files.activity_id 또는 activity_report_id 저장
→ 활동 상세 파일함에서 표시
```

---

# Part H. Dashboard / Notifications 반영

## 1. Dashboard

Dashboard 또는 활동 상세 체크리스트에 파일 누락 상태를 반영한다.

예시:

```text
제출 파일 미등록 활동
증빙 파일 누락 활동
월별 제출 패키지 미생성
```

---

## 2. Notifications / Automation

자동 점검이 있다면 weekly-check에 다음을 포함한다.

```text
제출 파일 누락 활동 수
증빙 파일 누락 활동 수
```

기존 자동 점검 API가 불안정하면 TODO로 남기고 UI/API를 깨지 않게 한다.

---

# Part I. 문서화

README 또는 DEMO 문서에 다음 내용을 추가한다.

```text
- 활동별 파일함 사용 방법
- 파일 업로드/미리보기/다운로드/삭제 방법
- 제출용 파일 지정 방법
- 월별 제출 패키지 preview 방법
- 월별 ZIP 생성 방법
- HWP/HWPX는 이번 단계에서 원본 관리/다운로드 우선 지원한다는 점
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

## 시나리오 1. 활동별 파일 업로드

```text
1. /activities/{id} 접속
2. 파일함 탭 이동
3. PDF/Image/Excel/HWP/ZIP 파일 업로드
4. 파일 목록에 표시되는지 확인
5. 파일 유형이 자동 분류되는지 확인
```

## 시나리오 2. 파일 미리보기

```text
1. PDF 미리보기
2. 이미지 미리보기
3. Excel preview table 확인
4. ZIP 내부 목록 확인
5. HWP/HWPX는 다운로드 안내 표시 확인
```

## 시나리오 3. 다운로드/삭제

```text
1. 업로드 파일 다운로드
2. 원본 파일명이 유지되는지 확인
3. 파일 삭제
4. 목록에서 사라지는지 확인
5. 직접 파일이 없어져서 서버 오류가 나지 않는지 확인
```

## 시나리오 4. 제출용 파일 지정

```text
1. 활동 파일 중 하나를 제출용 파일로 지정
2. submission_month 설정
3. 제출용 필터에서 보이는지 확인
```

## 시나리오 5. 월별 제출 패키지 Preview

```text
1. /api/submission-packages/preview?month=2026-09 호출
2. 해당 월 활동과 제출 파일 목록 확인
3. missing_items 확인
```

## 시나리오 6. 월별 ZIP 생성

```text
1. 월별 제출 패키지 생성
2. ZIP 다운로드
3. ZIP 내부에 제출용 파일들이 포함되는지 확인
```

---

## 완료 기준

Task 19는 다음을 모두 만족해야 완료로 본다.

```text
1. 활동별 파일함 탭이 구현되어 있다.
2. 활동별 파일 업로드가 가능하다.
3. 파일이 활동과 연결되어 저장된다.
4. 파일 유형이 자동 분류된다.
5. 파일 목록에서 파일명/유형/역할/크기/업로드일을 볼 수 있다.
6. PDF 미리보기가 가능하다.
7. 이미지 미리보기가 가능하다.
8. Excel preview가 가능하다.
9. ZIP 내부 파일 목록 preview가 가능하다.
10. HWP/HWPX는 원본 다운로드 중심으로 안전하게 처리된다.
11. 파일 다운로드가 가능하다.
12. 파일 삭제가 가능하다.
13. 제출용 파일 지정이 가능하다.
14. 월별 제출 패키지 preview가 가능하다.
15. 월별 ZIP 생성 및 다운로드가 가능하다.
16. Assistant/Receipts/Reports에서 생성 또는 업로드된 파일이 활동 파일함과 연결된다.
17. frontend build가 성공한다.
18. backend compile/test가 성공한다.
19. 이번 Task에서 HWP/HWPX 완전 편집기, HWPX 템플릿 생성, 환불 정산은 구현하지 않았다.
```

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 19 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 파일 관리 데이터 구조
- 모델:
- migration:
- activity 연결:
- file_category/file_role:

3. 파일 업로드/목록/상세
- 업로드 API:
- 목록 API:
- 상세 API:

4. 파일 미리보기
- PDF:
- Image:
- Excel:
- HWP/HWPX:
- ZIP:

5. 다운로드/삭제
- 다운로드:
- soft delete:
- 삭제 후 목록 갱신:

6. 활동 상세 파일함
- 파일함 탭:
- 업로드 UI:
- 파일 카드:
- preview panel:

7. 제출 패키지
- 제출용 파일 지정:
- 월별 preview:
- ZIP 생성:
- 다운로드:

8. 연동
- Receipts:
- Reports:
- Assistant:
- Dashboard/Notifications:

9. 실행 검증 결과
- alembic upgrade:
- backend compile/test:
- frontend build:
- 파일 업로드:
- 미리보기:
- 다운로드:
- 삭제:
- 제출 패키지:

10. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

11. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task19: add activity file vault and submission packages
```
