# Task 23. 활동 상세 UX 정리, 증빙/파일함/HWPX 템플릿 통합 안정화

## 목표

ClubAgent의 활동 상세 화면과 관련 기능을 실제 운영 흐름에 맞게 정리한다.

Task 16~22를 통해 활동 중심 구조, AI 작업실, Google Form Import, 파일함, HWPX 문서 생성, 활동비 정산까지 기능이 많이 추가되었다.
하지만 현재 활동 상세 화면은 기능이 누적되면서 다소 난잡해졌고, 일부 기능은 연결이 완전하지 않다.

현재 확인된 문제는 다음이다.

```text
1. 영수증 분석을 위해 업로드한 이미지가 활동 증빙/파일함에 함께 표시되지 않음
2. 영수증 분석 결과와 원본 이미지 파일의 연결이 약함
3. HWPX 템플릿 업로드 이후 삭제/수정/기본값 지정 같은 관리 기능이 부족함
4. HWPX 문서 작성 흐름이 사용자가 이해하기 어렵거나 동작이 분리되어 있음
5. 활동 상세 화면에 기능이 너무 많고 중복되어 난잡함
6. 파일함, 증빙, 보고서, 제출 문서의 역할이 겹쳐 보임
```

이번 Task의 목표는 다음이다.

```text
1. 영수증 업로드 파일을 활동 증빙 및 파일함에 확실히 연결
2. 영수증 이미지/PDF를 활동 상세에서 바로 미리보기 가능하게 수정
3. HWPX 템플릿 관리 기능 보강
4. HWPX 문서 생성 흐름을 활동 보고서 작성 흐름에 통합
5. 활동 상세 화면의 정보 구조를 재정리
6. 중복 버튼/중복 섹션/불필요한 placeholder 제거
7. 핵심 작업 흐름을 기준으로 UI를 단순화
8. 기존 기능은 유지하되 사용자가 어디서 무엇을 해야 하는지 명확하게 정리
```

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

```text
1. 영수증 파일과 Receipt record 연결 안정화
2. Receipt 업로드 시 UploadedFile 생성/연결 보장
3. 활동 상세의 증빙 섹션에서 영수증 이미지/PDF 미리보기
4. 활동 파일함에서 영수증 파일 표시
5. 영수증 삭제 시 Receipt와 연결 파일 상태 정리
6. HWPX 템플릿 관리 기능 추가
7. HWPX 템플릿 삭제/수정/기본값 지정/다운로드/필드 재추출
8. HWPX 문서 생성 UI 정리
9. 활동 상세 화면 탭/섹션 구조 재정리
10. 중복 기능 제거 또는 숨김 처리
11. 빈 상태/오류 상태/로딩 상태 정리
12. README 또는 DEMO 문서에 정리된 운영 흐름 반영
```

---

## 이번 Task에서 구현하지 말 것

```text
- HWP 바이너리 완전 편집기
- 브라우저 기반 완전한 한글 WYSIWYG 편집기
- PDF 변환 서버
- Google Drive API 연동
- Notion 연동
- Slack/Telegram 연동
- 로그인/권한 시스템
- 새로운 AI Agent 추가
- 새로운 정산 기능 추가
```

이번 Task는 기능 추가보다 **기존 기능 연결과 화면 정리**가 목적이다.

---

# Part A. 영수증/증빙 파일 연결 안정화

## 1. 현재 문제

영수증 분석을 위해 이미지를 업로드하면 분석 결과는 생기지만, 다음이 일관되지 않을 수 있다.

```text
- 활동 상세 증빙 탭에 원본 이미지가 보이지 않음
- 활동 파일함에 영수증 파일이 표시되지 않음
- Receipt record와 UploadedFile record가 분리되어 있음
- 삭제 시 Receipt만 삭제되고 원본 파일은 UI에 남거나, 반대로 파일만 남음
```

---

## 2. 수정 방향

영수증 업로드/분석 시 반드시 다음 구조가 성립해야 한다.

```text
Receipt
- id
- activity_id 또는 activity_report_id
- uploaded_file_id
- store_name
- total_amount
- receipt_date
- evidence_status

UploadedFile
- id
- activity_id 또는 activity_report_id
- original_filename
- file_category = receipt
- file_role = evidence
- mime_type
- storage_path
```

프로젝트가 `activity_report_id` 기반이면 해당 필드명을 사용한다.

---

## 3. Backend 수정

확인 대상:

```text
backend/app/routers/receipts.py
backend/app/routers/assistant.py
backend/app/agents/assistant_orchestrator.py
backend/app/services/receipt_analysis_service.py
backend/app/services/file_storage_service.py
backend/app/models/receipt.py
backend/app/models/uploaded_file.py
```

필수 동작:

```text
1. 영수증 업로드 시 UploadedFile 생성
2. Receipt 생성 시 uploaded_file_id 연결
3. activity_id가 있으면 Receipt와 UploadedFile 모두 같은 activity_id 연결
4. Assistant에서 영수증 분석 시에도 동일하게 처리
5. 활동 상세 증빙 조회 API에서 receipt + file 정보를 함께 반환
```

응답 예시:

```json
{
  "id": "receipt-id",
  "activity_id": "activity-id",
  "uploaded_file_id": "file-id",
  "original_filename": "receipt.jpg",
  "preview_url": "/api/files/file-id/preview",
  "download_url": "/api/files/file-id/download",
  "store_name": "편의점",
  "total_amount": 28000,
  "evidence_status": "confirmed"
}
```

---

## 4. Frontend 수정

수정 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/app/receipts/page.tsx
frontend/components/files/*
frontend/lib/api.ts
```

활동 상세의 증빙 섹션에서 다음을 보여준다.

```text
- 영수증 이미지/PDF 미리보기
- 분석 결과
- 금액
- 날짜
- 가맹점
- 증빙 상태
- 다운로드
- 삭제
```

영수증 파일은 파일함에도 표시되어야 한다.

```text
file_category = receipt
file_role = evidence
```

---

# Part B. HWPX 템플릿 관리 기능 보강

## 1. 현재 문제

HWPX 템플릿 업로드/문서 생성은 가능하더라도 실제 운영에서는 다음 기능이 필요하다.

```text
- 잘못 올린 템플릿 삭제
- 템플릿 이름/설명/유형 수정
- 기본 템플릿 지정
- 템플릿 원본 다운로드
- 템플릿 필드 재추출
- 삭제된 템플릿은 문서 생성 선택지에서 제외
```

---

## 2. Backend API 추가/보강

다음 API를 구현한다.

```http
PATCH /api/document-templates/{template_id}
DELETE /api/document-templates/{template_id}
GET /api/document-templates/{template_id}/download
POST /api/document-templates/{template_id}/refresh-fields
```

수정 가능 필드:

```text
name
description
template_type
is_default
```

삭제 정책:

```text
- hard delete 금지
- deleted_at 설정
- 기본 목록에서 제외
- 기존 생성 문서 이력에는 영향 없음
```

기본 템플릿 정책:

```text
is_default=true로 설정하면 같은 template_type의 다른 템플릿은 is_default=false
```

---

## 3. Frontend 템플릿 관리 UI

위치:

```text
활동 상세 > 보고서/문서 섹션
또는 Settings/Reports > 템플릿 관리
```

최소 UI:

```text
- 템플릿 목록
- 템플릿명
- 템플릿 유형
- 추출된 필드 수
- 기본 템플릿 여부
- 업로드 일시
- 수정
- 기본값 지정
- 필드 재추출
- 원본 다운로드
- 삭제
```

삭제 confirm 문구:

```text
이 템플릿을 삭제하시겠습니까?
기존에 생성된 문서에는 영향이 없지만, 앞으로 문서 생성 목록에서는 보이지 않습니다.
```

---

# Part C. HWPX 문서 작성 흐름 정리

## 1. 기본 방향

이번 Task에서 HWP/HWPX 완전 편집기는 구현하지 않는다.

문서 작성 흐름은 다음으로 정리한다.

```text
1. 활동 정보/참여자/영수증/피드백/활동비 데이터를 불러옴
2. AI 보고서 초안 또는 기존 보고서 본문을 표시
3. 사람이 화면에서 본문 수정
4. HWPX 템플릿 선택
5. 필드 매핑 Preview 확인
6. HWPX 생성
7. 활동 파일함에 저장
8. 제출용 파일로 지정
```

---

## 2. UI 정리

활동 상세의 보고서/문서 섹션은 다음 순서로 배치한다.

```text
보고서 본문
→ AI 초안 불러오기
→ 사람이 본문 수정
→ HWPX 템플릿 선택
→ 필드 매핑 확인
→ 문서 생성
→ 생성 문서 다운로드/파일함 보기
```

문서 생성과 템플릿 관리를 한 화면에 모두 노출하면 복잡해지므로, 템플릿 관리는 접힘 영역 또는 별도 관리 버튼으로 둔다.

---

# Part D. Activities 상세 화면 정보 구조 정리

## 1. 현재 문제

활동 상세 화면에 기능이 많아져 사용자가 어디서 무엇을 해야 하는지 헷갈릴 수 있다.

현재 기능:

```text
- 개요
- 참여자
- Google Form Import
- AI 실행
- 보고서
- HWPX 문서
- 활동비
- 영수증
- 파일함
- 제출 패키지
- 정산
```

이 기능들을 같은 레벨로 모두 노출하면 화면이 난잡해진다.

---

## 2. 권장 탭 구조

활동 상세 페이지를 다음 5개 탭으로 정리한다.

```text
1. 개요
2. 참여자
3. 자료/증빙
4. 보고/문서
5. 정산
```

각 탭의 역할:

```text
개요
- 활동 기본 정보
- 처리 체크리스트
- 빠른 작업

참여자
- 참여자 목록
- 신청서/명단 Import
- 활동 후 피드백 Import
- 참여 상태 관리

자료/증빙
- 영수증
- 사진
- 첨부 파일
- 파일함
- 미리보기/다운로드/삭제

보고/문서
- AI 보고서 초안
- 본문 수정
- HWPX 템플릿 선택
- 문서 생성
- 생성 문서

정산
- 활동비 설정
- 납부 현황
- 거래내역 매칭
- 오납/환불
- 매칭 취소
```

---

## 3. 중복 제거 원칙

다음 기준으로 중복을 정리한다.

```text
1. 영수증은 자료/증빙 탭에서 관리
2. 영수증 파일은 파일함에도 보이되, 별도 중복 업로드 UI는 최소화
3. HWPX 문서 생성은 보고/문서 탭에서 관리
4. 생성된 문서는 파일함에는 결과 파일로만 표시
5. AI 작업은 개요의 빠른 작업 또는 보고/문서 탭에서만 노출
6. 활동비/환불/오납은 정산 탭에만 모음
7. Google Form 신청서/활동지는 참여자 탭에 모음
```

---

## 4. UI 정리 작업

다음 작업을 수행한다.

```text
- 중복된 업로드 버튼 제거
- 중복된 AI 실행 영역 제거
- 임시 placeholder 제거
- 너무 긴 섹션은 접힘 영역으로 변경
- 고급 기능은 “상세 설정” 안으로 이동
- 각 탭 상단에 이 탭에서 할 수 있는 작업 1문장 설명 추가
- 빈 데이터일 때 다음 행동 버튼 제공
```

빈 상태 예시:

```text
참여자가 없습니다.
신청서 엑셀을 업로드하거나 직접 참여자를 추가하세요.

영수증이 없습니다.
영수증 이미지를 업로드하면 분석 결과와 원본 파일이 함께 저장됩니다.

제출 문서가 없습니다.
보고서 본문을 작성한 뒤 HWPX 템플릿으로 문서를 생성하세요.
```

---

# Part E. 통합 검증

## 확인 시나리오 1. 영수증 증빙 연결

```text
1. /activities/{id} 접속
2. 자료/증빙 탭 이동
3. 영수증 이미지 업로드
4. 분석 결과 확인
5. 원본 이미지 preview 확인
6. 파일함에도 receipt/evidence로 표시되는지 확인
```

## 확인 시나리오 2. AI 작업실 영수증 연결

```text
1. /assistant 접속
2. 활동 선택 또는 자동 감지
3. 영수증 이미지 업로드
4. 실행
5. 활동 상세 자료/증빙 탭에서 영수증과 이미지 확인
```

## 확인 시나리오 3. HWPX 템플릿 관리

```text
1. HWPX 템플릿 업로드
2. 템플릿 목록 확인
3. 이름/설명 수정
4. 기본 템플릿 지정
5. 원본 다운로드
6. 필드 재추출
7. 템플릿 삭제
8. 삭제된 템플릿이 문서 생성 목록에서 제외되는지 확인
```

## 확인 시나리오 4. HWPX 문서 생성

```text
1. 보고/문서 탭 이동
2. 보고서 본문 수정
3. 템플릿 선택
4. 필드 매핑 preview 확인
5. 문서 생성
6. 생성 문서 다운로드
7. 생성 문서가 자료/증빙 또는 파일함에 표시되는지 확인
```

## 확인 시나리오 5. 활동 상세 UI 정리

```text
1. 활동 상세 진입
2. 탭이 개요/참여자/자료·증빙/보고·문서/정산으로 정리되었는지 확인
3. 중복 업로드/중복 AI 실행/placeholder가 제거되었는지 확인
4. 모바일에서도 탭과 카드가 깨지지 않는지 확인
```

---

## 완료 기준

```text
1. 영수증 업로드 시 Receipt와 UploadedFile이 함께 생성/연결된다.
2. 활동 상세 자료/증빙 탭에서 영수증 이미지/PDF를 미리볼 수 있다.
3. 영수증 파일이 활동 파일함에도 표시된다.
4. AI 작업실에서 업로드한 영수증도 활동 증빙에 연결된다.
5. HWPX 템플릿 수정/삭제/기본값 지정/다운로드/필드 재추출이 가능하다.
6. 삭제된 템플릿은 문서 생성 선택지에서 제외된다.
7. HWPX 문서 생성 흐름이 보고/문서 탭 안에서 자연스럽게 동작한다.
8. 활동 상세 탭 구조가 개요/참여자/자료·증빙/보고·문서/정산으로 정리된다.
9. 중복된 버튼과 placeholder가 정리된다.
10. 빈 상태와 오류 상태가 사용자에게 이해되게 표시된다.
11. frontend build가 성공한다.
12. backend compile/test가 성공한다.
```

---

## 작업 완료 후 보고 형식

```text
Task 23 완료 보고

1. 생성/수정한 주요 파일
- ...

2. 영수증/증빙 연결 안정화
- Receipt와 UploadedFile 연결:
- 활동 상세 증빙 표시:
- 파일함 연동:
- 삭제 처리:

3. HWPX 템플릿 관리
- 수정:
- 삭제:
- 기본값 지정:
- 원본 다운로드:
- 필드 재추출:

4. HWPX 문서 작성 흐름
- 보고서 본문 수정:
- 템플릿 선택:
- 필드 매핑:
- 문서 생성:
- 파일함 저장:

5. 활동 상세 UI 정리
- 새 탭 구조:
- 제거한 중복 기능:
- 빈 상태:
- 모바일 대응:

6. 실행 검증 결과
- backend compile/test:
- frontend build:
- 영수증 업로드:
- AI 영수증 연결:
- 템플릿 관리:
- 문서 생성:
- UI 정리:

7. 이번 Task에서 의도적으로 구현하지 않은 기능
- HWP 완전 편집기:
- HWPX WYSIWYG:
- PDF 변환:

8. Git 상태 및 권장 커밋 메시지
- git status:
- 권장 커밋 메시지:
  task23: clean activity workspace and integrate evidence templates
```
