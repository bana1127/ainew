# Task 37. 활동별 감사자료 패키지 생성

현재 프로젝트는 ClubAgent입니다.

Task 36까지 진행하면서 부원, 활동, 회비, 활동비, 거래내역, 증빙, 파일함, HWPX 생성, 대시보드, UI 정리를 진행했습니다.

이번 Task 37의 목표는 **활동별 제출/감사용 자료를 한 번에 확인하고 다운로드할 수 있는 패키지 생성 기능**을 구현하는 것입니다.

현재 문제:

```text
1. 활동 보고서, 참여자 명단, 영수증, 증빙 사진, 활동비 현황이 각각 흩어져 있음
2. 제출할 때 필요한 파일이 다 모였는지 확인하기 어려움
3. HWPX, 영수증, 증빙 파일을 하나씩 다운로드해야 함
4. 활동별 감사 준비 상태는 볼 수 있지만 실제 제출 패키지로 묶는 기능이 없음
5. 파일명/한글 다운로드 처리에서 문제가 생길 수 있음
```

---

# 핵심 목표

활동 상세에서 다음 기능을 제공합니다.

```text
활동 상세 > 감사자료
또는
활동 상세 > 파일함 / 감사 체크 섹션

→ 감사자료 패키지 생성 미리보기
→ 누락 항목 확인
→ 생성
→ ZIP 다운로드
```

패키지에는 해당 활동의 제출/감사에 필요한 자료를 묶습니다.

---

# Part A. 감사자료 패키지 구성

패키지에는 다음 항목을 포함합니다.

## 필수 항목

```text
1. 활동 내역서 HWPX
2. 참여자 명단
3. 영수증/증빙 파일
4. 활동비 납부 현황 요약
5. 감사 체크리스트 요약
```

## 선택 항목

```text
1. 활동 사진
2. 원본 신청서/응답 엑셀
3. 거래내역 매칭 결과
4. AI 생성 보고서 본문
5. 기타 첨부 파일
```

---

# Part B. 패키지 내부 폴더 구조

ZIP 내부 구조는 다음처럼 만드세요.

```text
{활동명}_{활동일}_감사자료/
  01_활동내역서/
    활동내역서.hwpx

  02_참여자명단/
    참여자명단.csv
    원본명단.xlsx

  03_증빙자료/
    영수증_001.jpg
    영수증_002.png
    활동사진_001.jpg

  04_정산자료/
    활동비_납부현황.csv
    거래내역_매칭결과.csv

  05_점검표/
    감사체크리스트.json
    감사체크리스트.txt
```

한글 파일명 다운로드가 깨지지 않도록 기존 파일 다운로드에서 사용한 RFC 5987 방식 또는 안전한 filename encoding을 사용하세요.

---

# Part C. 패키지 생성 Preview

패키지 생성 전에 preview를 보여주세요.

Preview에는 다음을 표시합니다.

```text
활동명
활동일
참여자 수
활동내역서 존재 여부
증빙 파일 수
영수증 수
활동비 납부 현황 존재 여부
누락 항목
경고 항목
포함 예정 파일 목록
```

예시:

```text
감사자료 패키지 생성 미리보기

활동명: 위퍼퓸 교내조향활동
활동일: 2026.06.03
참여자: 19명

포함 예정:
- 활동내역서 1개
- 참여자 명단 1개
- 영수증 2개
- 활동 사진 3개
- 활동비 납부현황 1개

주의:
- 영수증 분석 미완료 1개
- 활동비 미납 2명
```

---

# Part D. 누락/경고 처리

패키지 생성 전에 누락 항목을 명확히 표시하세요.

누락 항목 예시:

```text
활동내역서 없음
참여자 명단 없음
증빙 파일 없음
활동비 납부현황 없음
영수증 분석 미완료
활동비 미납자 존재
```

정책:

```text
1. 필수 항목이 없어도 패키지 생성 자체는 가능
2. 단, preview에서 경고를 명확히 표시
3. 생성된 체크리스트에 누락 항목을 기록
4. 사용자가 확인 후 생성
```

---

# Part E. 패키지 생성 API

다음 API를 구현하세요.

```http
GET /api/activities/{activity_id}/audit-package/preview
POST /api/activities/{activity_id}/audit-package/generate
GET /api/activities/{activity_id}/audit-package/download/{package_id}
```

또는 기존 파일 다운로드 구조에 맞게 구현해도 됩니다.

Preview 응답 예시:

```json
{
  "activity_id": "...",
  "activity_title": "위퍼퓸 교내조향활동",
  "activity_date": "2026-06-03",
  "participant_count": 19,
  "files": {
    "reports": 1,
    "rosters": 1,
    "receipts": 2,
    "evidence_photos": 3,
    "generated_documents": 1
  },
  "warnings": [
    "활동비 미납자 2명이 있습니다.",
    "분석 미완료 영수증 1개가 있습니다."
  ],
  "missing": [],
  "can_generate": true
}
```

Generate 응답 예시:

```json
{
  "ok": true,
  "package_id": "...",
  "file_id": "...",
  "download_url": "/api/files/.../download",
  "filename": "위퍼퓸_교내조향활동_2026-06-03_감사자료.zip"
}
```

---

# Part F. ZIP 생성 정책

ZIP 생성 시 다음을 지키세요.

```text
1. 실제 파일이 없는 UploadedFile은 skip하고 warning 기록
2. 한글 파일명 깨짐 방지
3. 중복 파일명은 suffix 추가
4. CSV는 UTF-8 with BOM 또는 Excel 호환 인코딩 고려
5. 생성된 ZIP도 UploadedFile로 저장
6. file_category = audit_package
7. file_role = generated
8. activity_report_id = 현재 활동
```

---

# Part G. CSV 생성

패키지 안에 최소한 다음 CSV를 생성하세요.

## 참여자명단.csv

컬럼:

```text
이름
학과
학번
참가상태
외부인여부
비고
```

## 활동비_납부현황.csv

컬럼:

```text
이름
학번
필요금액
납부금액
상태
환불상태
매칭거래
비고
```

## 거래내역_매칭결과.csv

가능하면 포함합니다.

컬럼:

```text
거래일
적요
입금액
매칭대상
매칭상태
사유
```

---

# Part H. 감사 체크리스트 파일

패키지 안에 감사 체크리스트를 포함하세요.

## 감사체크리스트.txt

예시:

```text
감사 체크리스트

활동명: 위퍼퓸 교내조향활동
활동일: 2026.06.03
참여자 수: 19명

[완료] 활동 기본 정보 입력됨
[완료] 참여자 명단 있음
[완료] 활동 내역서 생성됨
[주의] 활동비 미납자 2명
[완료] 증빙 파일 있음
[주의] 영수증 분석 미완료 1개
```

## 감사체크리스트.json

같은 정보를 JSON으로도 저장하세요.

---

# Part I. Frontend UI

활동 상세에 “감사자료” 섹션 또는 버튼을 추가하세요.

권장 위치:

```text
활동 상세 > 파일함 탭
또는
활동 상세 > 감사 체크리스트 영역
```

UI:

```text
[감사자료 패키지 미리보기]
[감사자료 패키지 생성]
[다운로드]
```

Preview 카드에는 다음을 표시하세요.

```text
포함 예정 파일
누락 항목
주의 항목
생성 가능 여부
```

생성 후에는 파일함의 생성 문서/감사자료 그룹에도 표시되어야 합니다.

---

# Part J. AI 연동

활동 내부 AI에서 다음 요청을 처리하세요.

```text
감사자료 패키지 만들어줘
이 활동 제출자료 묶어줘
감사용 파일 빠진 거 확인해줘
감사 체크리스트 보여줘
```

동작:

```text
activity_detail이면 현재 activity_id 기준
전역 AI에서 활동이 없으면 활동 선택 요청
패키지 생성은 preview 후 confirm
```

---

# Part K. Backend 수정 대상

확인 대상:

```text
backend/app/routers/activities.py
backend/app/routers/files.py
backend/app/services/file_storage_service.py
backend/app/services/activity_audit_check_service.py
backend/app/services/assistant_action_service.py
backend/app/agents/assistant_orchestrator.py
backend/app/models/uploaded_file.py
```

필요하면 신규 서비스:

```text
backend/app/services/activity_audit_package_service.py
```

---

# Part L. Frontend 수정 대상

확인 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/lib/api.ts
frontend/components/assistant/AssistantResultCard.tsx
```

가능하면 컴포넌트 분리:

```text
ActivityAuditPackagePanel
AuditPackagePreviewCard
```

---

# Part M. 테스트

추가 또는 보강:

```text
backend/tests/test_activity_audit_package_preview.py
backend/tests/test_activity_audit_package_generation.py
backend/tests/test_activity_audit_package_zip_contents.py
backend/tests/test_assistant_audit_package_intent.py
```

필수 테스트:

```text
1. preview가 활동별 파일/참여자/증빙/보고서 상태를 반환
2. HWPX, 영수증, 참여자명단, 활동비현황이 ZIP에 포함됨
3. 파일이 없어도 warning 기록 후 생성 가능
4. 생성된 ZIP이 UploadedFile로 저장됨
5. ZIP 다운로드 가능
6. 한글 파일명이 깨지지 않음
7. 전역 AI에서 activity_id 없이 패키지 생성 요청 시 활동 선택 요청
8. 활동 내부 AI에서 패키지 생성 요청 시 preview 반환
```

---

# 브라우저 검증

```text
1. 활동 생성
2. 참가자 명단 업로드
3. 활동비 대상 생성
4. 영수증/증빙 업로드
5. HWPX 활동 내역서 생성
6. 감사 체크리스트 확인
7. 감사자료 패키지 preview 실행
8. 포함 파일과 경고 확인
9. 패키지 생성
10. ZIP 다운로드
11. ZIP 내부 구조 확인
12. 파일함에서 audit_package로 표시되는지 확인
```

---

# 완료 기준

```text
1. 활동별 감사자료 패키지 preview가 가능하다.
2. 누락/경고 항목이 표시된다.
3. ZIP 패키지를 생성할 수 있다.
4. HWPX, 증빙, 참여자 명단, 활동비 현황이 포함된다.
5. 생성된 ZIP이 파일함에 저장된다.
6. ZIP 다운로드가 가능하다.
7. 한글 파일명이 깨지지 않는다.
8. AI에서 감사자료 패키지 요청이 가능하다.
9. pytest 통과
10. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 37 완료 보고

1. 원인
- 감사자료가 흩어져 있던 이유:
- 제출 패키지 생성이 필요했던 이유:

2. 수정한 파일
- backend:
- frontend:
- tests:

3. Preview
- 포함 파일:
- 누락 항목:
- 경고 항목:

4. ZIP 생성
- 폴더 구조:
- CSV 생성:
- 체크리스트:
- UploadedFile 저장:
- 다운로드:

5. AI 연동
- activity_detail:
- global clarification:
- preview/confirm:

6. 검증
- ZIP 내용:
- 한글 파일명:
- 파일함 표시:
- pytest:
- npm run build:

권장 커밋 메시지:
task37: generate activity audit package zip
```
