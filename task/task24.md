# Task 24. HWPX 활동 내역서 실제 생성 및 템플릿 치환 구현

## 현재 프로젝트

현재 프로젝트는 ClubAgent입니다.

Task 1~23까지 진행하면서 활동 생성, 참여자 등록, 활동비 생성, 파일함, 보고서 본문 저장, HWPX 템플릿 업로드 및 생성 기능이 일부 구현되었습니다.

하지만 현재 HWPX 생성 기능은 실제 제출용 문서 내용을 바꾸지 못하고 있습니다.

현재 증상:

```text
1. 활동 상세에서 HWPX 문서 생성 버튼을 누르면 파일함에 .hwpx 파일은 생성됩니다.
2. 다운로드도 가능해졌습니다.
3. 하지만 다운로드한 HWPX를 열어보면 템플릿 내용이 그대로입니다.
4. 웹에서 작성한 보고서 본문, 활동명, 활동일, 장소, 참여자 명단 등이 문서에 반영되지 않습니다.
```

즉, 현재는 실제 HWPX 문서 생성이 아니라 **템플릿 파일 복사 수준**입니다.

이번 Task 24의 목표는 실제 제출용 HWPX 양식에 활동 데이터를 반영하여, 다운로드한 HWPX 문서 안의 내용이 실제 활동 정보로 바뀌게 하는 것입니다.

---

# 참고 템플릿 구조

사용자가 제공한 실제 제출용 HWPX 양식은 다음 구조를 가집니다.

```text
00월 [ Oui Parfum ] 동아리 활동 내역서

대표자
송현수

주관
Oui Parfum

활동 장소
종합관 앞

활동 일시
2025.00.00

활동 분류
제89조 7항 교내 활동 참여

활동 사진
네이비즘 화면이 보이도록 인증 사진 필요.

활동 내용
동아리 홍보전에 참여하여 신입생과 재학생들에게 동아리 가입을 도모하는 활동을 진행함...

상기 명시한 내용은 사실과 틀림없음을 확인합니다.
동아리 활동 내역서 조작 시 회칙에 따른 불이익을 감수하겠습니다.

Oui Parfum 회장 송현수 (인)

참여 인원 명단

이름
학과
학번
서명
비고
(외부인 명시)

이하 생략

참여인원 총 00명
```

이 양식은 `{{활동명}}` 같은 placeholder 기반 템플릿이 아닙니다.
따라서 Task 24에서는 두 가지 방식을 모두 지원해야 합니다.

```text
1. Placeholder mode
- {{활동명}}, {{활동일}}, {{활동장소}}, {{보고서본문}} 같은 명시적 placeholder 치환

2. Legacy form mode
- 기존 HWPX 양식 안에 들어 있는 예시값을 찾아 실제 활동 값으로 교체
- 예: 종합관 앞 → A401호
- 예: 2025.00.00 → 2026.06.03
- 예: 참여인원 총 00명 → 참여인원 총 19명
```

이번 사용자의 실제 템플릿은 **Legacy form mode**로 처리되어야 합니다.

---

# 목표

Task 24의 최종 목표는 다음입니다.

```text
1. HWPX 템플릿 내부 XML을 실제로 열고 수정한다.
2. 활동 데이터, 보고서 본문, 참여자 명단을 HWPX에 반영한다.
3. 템플릿 파일을 단순 복사하지 않는다.
4. 생성된 HWPX를 다시 다운로드했을 때 실제 값이 반영되어 있어야 한다.
5. 생성 문서는 활동 파일함에 저장된다.
6. 사용자는 웹에서 보고서 본문을 수정하고, 수정된 내용으로 HWPX를 재생성할 수 있다.
```

---

# 이번 Task에서 구현하지 말 것

이번 Task 24에서 다음은 구현하지 않습니다.

```text
- HWP 완전 편집기
- HWPX WYSIWYG 편집기
- 브라우저에서 한글 문서 직접 편집
- PDF 변환 서버
- Google Drive 연동
- Notion/Slack/Telegram 연동
- 전자서명 기능
```

이번 Task는 **HWPX 템플릿 치환 기반 자동 문서 생성**이 목적입니다.

---

# Part A. HWPX 생성 방식 정리

## 현재 문제

현재 HWPX 생성 기능은 다음처럼 동작하는 것으로 보입니다.

```text
템플릿 선택
→ 파일 복사
→ 파일명만 새로 지정
→ 파일함 저장
```

이 방식은 실패입니다.

올바른 방식은 다음입니다.

```text
템플릿 HWPX 선택
→ HWPX를 zip으로 열기
→ 내부 XML 파일 탐색
→ 활동 데이터로 XML 내용 치환
→ 참여자 명단 반영
→ 다시 zip으로 묶기
→ 새 HWPX 저장
→ UploadedFile로 파일함에 등록
```

HWPX는 zip 기반 구조이므로 Python의 `zipfile`을 사용할 수 있습니다.

---

# Part B. Backend 구현 대상

확인 및 수정 대상:

```text
backend/app/routers/document_templates.py
backend/app/routers/reports.py
backend/app/routers/activities.py
backend/app/services/hwpx_template_service.py
backend/app/services/file_storage_service.py
backend/app/models/document_template.py
backend/app/models/uploaded_file.py
backend/app/models/activity_report.py
backend/app/models/activity_participant.py
backend/tests/
```

필요하면 신규 서비스를 추가하세요.

권장 신규 파일:

```text
backend/app/services/hwpx_generation_service.py
```

---

# Part C. HWPX generation context 구성

HWPX 생성 시 다음 데이터를 하나의 context로 구성하세요.

```python
context = {
    "club_name": "Oui Parfum",
    "representative_name": "...",
    "activity_title": "...",
    "activity_month": "06",
    "activity_date": "2026.06.03",
    "activity_location": "A401호",
    "activity_category": "...",
    "activity_type": "...",
    "activity_content": "...",
    "report_body": "...",
    "participant_count": 19,
    "participant_list": [
        {
            "name": "박민서",
            "department": "...",
            "student_id": "...",
            "note": ""
        }
    ],
    "expense_summary": "...",
    "evidence_summary": "...",
    "feedback_summary": "..."
}
```

데이터 출처:

```text
activity_title
→ ActivityReport.title 또는 Activity.title

activity_date
→ ActivityReport.activity_date

activity_location
→ ActivityReport.location

activity_category
→ ActivityReport.category 또는 ActivityCategory.name

activity_content / report_body
→ 사용자가 웹에서 저장한 final_content 우선
→ final_content가 없으면 generated_content
→ 둘 다 없으면 activity description

participant_list
→ ActivityParticipant + Member join
→ active/deleted 제외
→ 이름, 학과, 학번, 비고

participant_count
→ participant_list 길이

representative_name
→ Settings에 있으면 settings 값
→ 없으면 "송현수" fallback 가능
```

본문 우선순위는 반드시 다음으로 통일하세요.

```text
1. 사용자가 저장한 final_content 또는 final_body
2. 사용자가 저장한 content
3. AI generated_content
4. activity.description
5. 빈 문자열
```

---

# Part D. Placeholder mode 구현

HWPX 내부 XML에서 다음 placeholder가 있으면 치환하세요.

```text
{{동아리명}}
{{대표자}}
{{활동명}}
{{활동월}}
{{활동일}}
{{활동장소}}
{{활동분류}}
{{활동내용}}
{{보고서본문}}
{{참여자수}}
{{참여자명단}}
{{지출요약}}
{{증빙요약}}
{{피드백요약}}
```

치환 규칙:

```text
{{활동명}} → activity_title
{{활동월}} → activity_month
{{활동일}} → activity_date
{{활동장소}} → activity_location
{{활동분류}} → activity_category
{{활동내용}} → activity_content 또는 report_body
{{보고서본문}} → report_body
{{참여자수}} → participant_count
```

주의:

HWPX XML에서는 placeholder가 여러 run으로 쪼개져 있을 수 있습니다.

예:

```xml
<hp:t>{{활</hp:t>
<hp:t>동명}}</hp:t>
```

1차 구현에서는 단순 문자열 치환을 먼저 구현해도 됩니다.
하지만 최소한 모든 `Contents/section*.xml` 파일을 대상으로 replace해야 합니다.

---

# Part E. Legacy form mode 구현

사용자가 제공한 실제 템플릿처럼 placeholder가 없는 경우에는 legacy form mode를 사용하세요.

## 1. 제목 치환

기존 문구:

```text
00월 [ Oui Parfum ] 동아리 활동 내역서
```

예상 결과:

```text
06월 [ Oui Parfum ] 동아리 활동 내역서
```

치환 규칙:

```text
00월 → {activity_month}월
[ Oui Parfum ] → club_name 유지
```

## 2. 활동 장소 치환

기존 예시값:

```text
종합관 앞
```

실제 값:

```text
A401호
```

## 3. 활동 일시 치환

기존 예시값:

```text
2025.00.00
```

실제 값:

```text
2026.06.03
```

## 4. 활동 분류 치환

기존 예시값:

```text
제89조 7항 교내 활동 참여
```

실제 값:

```text
activity_category 또는 activity_type
```

카테고리가 없으면 기존 값 유지.

## 5. 활동 내용 치환

기존 예시 본문:

```text
동아리 홍보전에 참여하여 신입생과 재학생들에게 동아리 가입을 도모하는 활동을 진행함...
```

실제 값:

```text
report_body 또는 activity_content
```

주의:

활동 내용은 여러 문단으로 들어갈 수 있어야 합니다.
처음에는 줄바꿈을 `\n`으로 유지하거나 HWPX XML의 텍스트 노드 안에 안전하게 삽입하세요.

## 6. 참여인원 총 00명 치환

기존 문구:

```text
참여인원 총 00명
```

실제 값:

```text
참여인원 총 19명
```

---

# Part F. 참여자 명단 생성

이번 Task에서 가능한 한 참여자 명단까지 실제로 반영하세요.

우선순위:

```text
1단계 필수:
- 참여인원 총 00명 → 실제 인원 수로 치환

2단계 필수에 가깝게 구현:
- 참여 인원 명단 표에 이름/학과/학번을 삽입

3단계 추후 가능:
- 서명란, 비고, 외부인 표시 정교화
```

## 참여자 명단 데이터

ActivityParticipant에서 현재 활동 참여자를 조회하세요.

필드:

```text
name
department
student_id
note 또는 external_flag
```

정렬:

```text
1. student_id 오름차순
2. name 오름차순
```

## HWPX 표 삽입 구현 방향

HWPX 표 구조를 완벽히 생성하기 어렵다면 1차 구현은 다음 방식 중 하나로 해도 됩니다.

### 방식 A. 텍스트 블록 삽입

`이하 생략` 위치를 찾아 그 앞 또는 그 자리에 다음 텍스트를 삽입합니다.

```text
박민서 / 컴퓨터공학부 / 2025170011 / / 
문채영 / 경영학과 / 2025440012 / /
...
```

### 방식 B. 표 행 복제

기존 표의 데이터 행 또는 `이하 생략` 행을 찾아서 `<hp:tr>`를 복제하고, 셀 텍스트를 참여자 값으로 치환합니다.

가능하면 방식 B가 좋지만, HWPX 구조가 복잡하면 Task 24에서는 방식 A로 먼저 구현해도 됩니다.

중요한 완료 기준:

```text
다운로드한 HWPX 안에 참여자 이름과 학번이 실제로 들어가 있어야 합니다.
```

---

# Part G. XML 치환 범위

HWPX 내부에서 다음 파일들을 대상으로 치환하세요.

```text
Contents/section*.xml
Contents/header*.xml
Contents/footer*.xml
```

최소 필수:

```text
Contents/section*.xml
```

파일이 없으면 건너뛰세요.

모든 XML 수정 시:

```text
1. UTF-8로 decode
2. XML escape 처리
3. 치환
4. UTF-8로 encode
5. zip에 다시 기록
```

반드시 XML 특수문자를 escape하세요.

예:

```text
& → &amp;
< → &lt;
> → &gt;
```

---

# Part H. 생성 전 Preview 추가

Frontend에서 HWPX 생성 전 매핑 Preview를 보여주세요.

수정 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/components/documents/*
frontend/lib/api.ts
```

Preview 예시:

```text
{{활동명}} → 위퍼퓸 교내조향활동
{{활동일}} → 2026.06.03
{{활동장소}} → A401호
{{참여자수}} → 19명
{{보고서본문}} → 저장된 보고서 본문 일부
```

Legacy form mode에서는 다음처럼 표시하세요.

```text
00월 → 06월
종합관 앞 → A401호
2025.00.00 → 2026.06.03
참여인원 총 00명 → 참여인원 총 19명
활동 내용 예시문 → 저장된 보고서 본문
```

Preview 값이 비어 있으면 문서 생성 전에 경고하세요.

예:

```text
보고서 본문이 비어 있습니다. 그래도 생성하시겠습니까?
참여자가 없습니다. 참여자 명단 없이 생성됩니다.
```

---

# Part I. 생성 결과 검증 API

HWPX 생성 후 내부 텍스트를 간단히 추출해서 검증할 수 있는 helper를 추가하세요.

권장 함수:

```python
extract_hwpx_text(path: Path) -> str
```

동작:

```text
1. zipfile로 HWPX 열기
2. Contents/section*.xml 읽기
3. 태그 제거 또는 텍스트 노드 추출
4. plain text 반환
```

생성 후 검증:

```text
- activity_title 또는 activity_location이 포함되어야 함
- activity_date가 포함되어야 함
- participant_count가 포함되어야 함
- report_body 일부가 포함되어야 함
```

검증 실패 시:

```text
1. 파일은 생성하되 warning을 response에 포함
2. 또는 생성 실패 처리
```

Task 24에서는 warning 포함을 권장합니다.

---

# Part J. API 설계

기존 API가 있으면 보강하고, 없으면 다음 형태로 구현하세요.

## 1. 문서 생성 Preview

```http
GET /api/activities/{activity_id}/document-generation-preview?template_id=...
```

응답 예시:

```json
{
  "mode": "legacy_form",
  "template_id": "...",
  "mappings": [
    {
      "source": "00월",
      "target": "06월",
      "field": "activity_month"
    },
    {
      "source": "종합관 앞",
      "target": "A401호",
      "field": "activity_location"
    }
  ],
  "warnings": []
}
```

## 2. HWPX 생성

```http
POST /api/activities/{activity_id}/generate-hwpx
```

요청:

```json
{
  "template_id": "...",
  "save_to_file_vault": true,
  "mark_as_submission": false
}
```

응답:

```json
{
  "ok": true,
  "file_id": "...",
  "filename": "위퍼퓸 교내조향활동_2026-06-03.hwpx",
  "download_url": "/api/files/.../download",
  "mode": "legacy_form",
  "replaced_count": 8,
  "participant_count": 19,
  "warnings": []
}
```

---

# Part K. Frontend 요구사항

활동 상세의 보고서 또는 보고·문서 탭에서 다음 UI를 제공하세요.

```text
1. 보고서 본문 수정 영역
2. 저장 버튼
3. 템플릿 선택
4. 생성 전 Preview
5. HWPX 생성 버튼
6. 생성된 문서 목록
7. 다운로드 버튼
8. 파일함에서 보기 버튼
```

생성 완료 후:

```text
- "HWPX 문서 생성 완료" 표시
- 치환된 필드 수 표시
- 참여자 수 표시
- warning이 있으면 표시
```

예:

```text
HWPX 문서 생성 완료
- 치환 필드: 8개
- 참여자: 19명
- 파일함에 저장됨
```

---

# Part L. 테스트

테스트 파일을 추가하세요.

```text
backend/tests/test_hwpx_generation_service.py
backend/tests/test_activity_hwpx_generation_api.py
```

## 테스트 1. Legacy form mode 치환

입력:

```text
template contains:
00월 [ Oui Parfum ] 동아리 활동 내역서
종합관 앞
2025.00.00
참여인원 총 00명
```

context:

```text
activity_month = 06
location = A401호
activity_date = 2026.06.03
participant_count = 19
```

기대:

```text
생성된 HWPX 텍스트에 다음 포함:
06월 [ Oui Parfum ] 동아리 활동 내역서
A401호
2026.06.03
참여인원 총 19명
```

## 테스트 2. 보고서 본문 반영

context:

```text
report_body = "이번 활동은 교내 조향 체험을 중심으로 진행되었다."
```

기대:

```text
생성된 HWPX 텍스트에 위 문장이 포함됨
기존 예시 문장 "동아리 홍보전에 참여하여"가 그대로 남아 있으면 실패
```

## 테스트 3. 참여자 명단 반영

participants:

```text
박민서 / 컴퓨터공학부 / 2025170011
문채영 / 경영학과 / 2025440012
```

기대:

```text
생성된 HWPX 텍스트에 박민서, 2025170011, 문채영, 2025440012 포함
```

## 테스트 4. Placeholder mode

template contains:

```text
{{활동명}}
{{활동일}}
{{보고서본문}}
{{참여자수}}
```

기대:

```text
모두 context 값으로 치환
```

## 테스트 5. 원본 템플릿 그대로 복사 방지

생성된 문서에 다음이 그대로 남아 있으면 실패:

```text
2025.00.00
참여인원 총 00명
동아리 홍보전에 참여하여 신입생과 재학생들에게
```

단, 사용자가 일부러 본문에 해당 문장을 넣은 경우는 제외.

---

# Part M. 브라우저 검증 시나리오

다음 시나리오를 실제로 확인하세요.

```text
1. 활동 상세 페이지 진입
2. 참여자 19명 존재
3. 보고서 본문 입력:
   "이번 활동은 교내 조향 체험을 중심으로 진행되었으며, 참여자들이 향료를 직접 경험하는 방식으로 운영되었습니다."
4. 저장
5. HWPX 템플릿 선택:
   Oui Parfum_20250000_교내 활동 참여.hwpx
6. Preview 확인:
   - 활동일
   - 장소
   - 참여자 수
   - 보고서 본문
7. HWPX 생성
8. 파일함에서 다운로드
9. 한글 또는 HWPX 뷰어로 열기
10. 다음이 반영되었는지 확인:
   - 06월
   - A401호
   - 2026.06.03
   - 저장한 보고서 본문
   - 참여인원 총 19명
   - 참여자 이름/학번
```

---

# 완료 기준

Task 24는 다음을 모두 만족해야 완료입니다.

```text
1. HWPX 생성 시 템플릿 파일을 단순 복사하지 않는다.
2. HWPX 내부 XML을 실제로 수정한다.
3. placeholder mode를 지원한다.
4. legacy form mode를 지원한다.
5. 업로드된 실제 Oui Parfum 활동 내역서 양식에서 제목 월, 장소, 일시, 활동 내용, 참여인원 총 수가 바뀐다.
6. 보고서 탭에서 저장한 본문이 생성된 HWPX에 반영된다.
7. 참여자 이름/학과/학번이 생성된 HWPX에 반영된다.
8. 생성 전 Preview에서 어떤 값이 들어갈지 확인할 수 있다.
9. 생성된 HWPX가 파일함에 저장된다.
10. 생성된 HWPX 다운로드가 가능하다.
11. 다운로드한 HWPX가 템플릿 그대로가 아니라 실제 활동 정보로 변경되어 있다.
12. 기존 HWPX 다운로드 한글 파일명 처리는 깨지지 않는다.
13. pytest 통과
14. npm run build 통과
```

---

# 작업 완료 보고 형식

```text
Task 24 완료 보고

1. 원인
- 기존 HWPX 생성이 템플릿 그대로였던 이유:
- placeholder/legacy form 처리 문제:

2. 수정한 주요 파일
- backend:
- frontend:
- tests:

3. HWPX generation context
- activity:
- report body:
- participants:
- settings:

4. Placeholder mode
- 지원 placeholder:
- 치환 방식:
- section XML 처리:

5. Legacy form mode
- 00월:
- 종합관 앞:
- 2025.00.00:
- 활동 내용:
- 참여인원 총 00명:
- 참여자 명단:

6. Preview UI
- mappings:
- warnings:
- template mode:

7. 생성 결과
- file_id:
- replaced_count:
- participant_count:
- warnings:

8. 테스트 결과
- pytest:
- npm run build:
- generated HWPX text extraction:
- browser download:

9. 의도적으로 구현하지 않은 기능
- HWP 완전 편집기:
- HWPX WYSIWYG:
- PDF 변환:
- 이미지 삽입 고도화:

권장 커밋 메시지:
task24: generate real hwpx reports from activity templates
```
