# Task 34. 영수증·증빙·파일함 정리 및 활동별 감사 준비 기반 구축

현재 프로젝트는 ClubAgent입니다.

Task 33까지 진행하면서 전체 데모 흐름과 AI 자연어 명령 안정화를 진행했습니다.

이번 Task 34의 목표는 **활동별 파일/증빙/영수증 관리 흐름을 정리하고, 이후 감사 자료 패키지 생성을 위한 기반을 만드는 것**입니다.

현재 문제:

```text
1. 영수증 업로드, 분석, 증빙 연결, 파일함 표시가 서로 완전히 일관되지 않음
2. 활동 상세 내부에서 어떤 파일이 증빙인지, 보고서인지, 원본 명단인지 구분이 어려움
3. 영수증 분석 결과가 활동 증빙/파일함에 자동으로 잘 연결되지 않는 경우가 있음
4. 파일 삭제/다운로드/미리보기/연결 해제가 일관되지 않음
5. 감사 제출용으로 활동별 필수 자료가 모두 모였는지 확인하기 어려움
```

---

# 핵심 목표

활동 상세 파일/증빙 구조를 다음처럼 정리합니다.

```text
활동 상세
- 증빙
  - 영수증
  - 사진
  - 계좌이체 증빙
  - 기타 증빙

- 파일함
  - 원본 파일
  - 참가자 명단
  - 영수증 파일
  - 생성된 HWPX
  - 기타 첨부

- 감사 체크
  - 활동 보고서 있음
  - 참여자 명단 있음
  - 증빙 파일 있음
  - 활동비/지출 내역 연결됨
```

---

# Part A. 파일 분류 체계 정리

UploadedFile 또는 관련 모델의 파일 분류를 명확히 하세요.

권장 필드:

```text
file_category
- participant_roster
- receipt
- evidence_photo
- activity_report
- generated_document
- bank_statement
- other

file_role
- source
- evidence
- generated
- attachment
```

활동과 연결된 파일은 반드시 다음 정보를 가져야 합니다.

```text
activity_report_id 또는 activity_id
related_entity_type
related_entity_id
file_category
file_role
```

---

# Part B. 활동 상세 파일함 정리

활동 상세 > 파일함 탭에서 파일을 다음 기준으로 구분해서 보여주세요.

```text
1. 원본 파일
   - 참가자 명단
   - 신청서/응답 파일
   - 업로드한 원본 엑셀

2. 증빙 파일
   - 영수증 이미지
   - 활동 사진
   - 이체 증빙

3. 생성 문서
   - HWPX 활동 내역서
   - 향후 PDF 변환 파일

4. 기타 파일
```

각 파일 row에는 다음을 표시하세요.

```text
파일명
분류
역할
업로드 일시
연결된 기능
미리보기
다운로드
삭제
연결 해제
```

삭제는 바로 삭제하지 말고 확인 모달을 띄우세요.

---

# Part C. 영수증 분석과 활동 증빙 연결

영수증 업로드/분석 후 활동과 연결되는 흐름을 안정화하세요.

흐름:

```text
활동 상세 > 증빙 탭
→ 영수증 업로드
→ OCR/분석
→ 분석 결과 preview
→ 사용자가 확인
→ Receipt 생성/갱신
→ UploadedFile을 해당 활동 파일함에 연결
→ 증빙 목록에 표시
```

전역 영수증 화면에서 업로드한 경우:

```text
1. 활동 미연결 상태로 저장
2. 사용자가 활동에 연결 가능
3. 연결 시 Receipt와 UploadedFile 모두 activity_id가 갱신되어야 함
```

---

# Part D. 증빙 탭 UI 정리

활동 상세 > 증빙 탭을 다음 구조로 정리하세요.

```text
1. 증빙 요약
   - 영수증 수
   - 활동 사진 수
   - 미확인 증빙 수
   - 연결된 지출 금액

2. 증빙 업로드
   - 영수증 업로드
   - 사진 업로드
   - 기타 증빙 업로드

3. 증빙 목록
   - 미리보기
   - 분석 결과
   - 연결된 지출/활동비
   - 다운로드
   - 삭제
```

증빙 목록 컬럼:

```text
파일
유형
금액
날짜
가맹점/내용
분석 상태
연결 상태
작업
```

---

# Part E. 미리보기/다운로드/삭제 일관화

파일 종류별로 최소한 다음 동작이 가능해야 합니다.

```text
이미지 파일
→ 인라인 미리보기

PDF
→ 다운로드 또는 브라우저 preview 가능하면 preview

HWPX
→ 다운로드

Excel/CSV
→ 다운로드, 가능하면 간단한 preview

기타
→ 다운로드
```

삭제 정책:

```text
1. 실제 파일 삭제 또는 soft delete 중 하나로 일관화
2. DB record와 물리 파일 처리 방식 명확화
3. 삭제 후 파일함/증빙 목록 refetch
4. 연결 해제는 파일 삭제와 구분
```

연결 해제:

```text
파일은 유지
activity_id 연결만 제거
증빙 목록에서는 사라짐
전역 파일함 또는 미연결 파일 목록에서는 확인 가능
```

---

# Part F. 활동 감사 체크리스트

활동 상세에 간단한 감사 준비 상태를 표시하세요.

체크 항목:

```text
활동 기본 정보 입력됨
참여자 명단 있음
활동 보고서 본문 있음
HWPX 생성됨
증빙 파일 있음
영수증 분석 완료
활동비 납부 현황 생성됨
활동비/지출 금액 확인 필요 없음
```

UI 예시:

```text
감사 준비 상태
[완료] 활동 기본 정보
[완료] 참여자 명단
[완료] 활동 보고서
[주의] 증빙 영수증 없음
[완료] HWPX 문서 생성
```

이 기능은 감사 패키지 생성의 기반입니다.
이번 Task에서는 패키지 zip 생성까지는 하지 않아도 됩니다.

---

# Part G. AI 연동

활동 내부 AI에서 다음 요청을 처리할 수 있게 하세요.

```text
이 영수증 현재 활동 증빙으로 연결해줘
이 사진 증빙으로 넣어줘
증빙 빠진 거 확인해줘
감사 준비 상태 확인해줘
파일함 정리해줘
```

동작 원칙:

```text
activity_detail에서 실행되면 현재 activity_id 기준
전역 AI에서 활동 연결이 필요한 경우 활동 선택 요청
삭제/연결 해제/분류 변경은 preview 후 confirm
```

---

# Part H. Backend 수정 대상

확인 대상:

```text
backend/app/routers/files.py
backend/app/routers/receipts.py
backend/app/routers/activities.py
backend/app/services/file_storage_service.py
backend/app/services/receipt_analysis_service.py
backend/app/services/assistant_action_service.py
backend/app/agents/assistant_orchestrator.py
backend/app/models/uploaded_file.py
backend/app/models/receipt.py
```

필요하면 신규 서비스:

```text
backend/app/services/activity_evidence_service.py
backend/app/services/activity_audit_check_service.py
```

---

# Part I. Frontend 수정 대상

확인 대상:

```text
frontend/app/activities/[id]/page.tsx
frontend/app/receipts/page.tsx
frontend/lib/api.ts
frontend/components/assistant/AssistantResultCard.tsx
```

가능하면 컴포넌트 분리:

```text
ActivityEvidenceTab
ActivityFileVaultTab
ActivityAuditChecklist
FilePreviewCard
ReceiptEvidenceList
```

---

# Part J. 테스트

추가 또는 보강:

```text
backend/tests/test_activity_evidence_linking.py
backend/tests/test_activity_file_vault.py
backend/tests/test_receipt_activity_linking.py
backend/tests/test_activity_audit_checklist.py
```

필수 테스트:

```text
1. 활동 상세에서 영수증 업로드 후 Receipt와 UploadedFile이 activity_id로 연결됨
2. 전역 영수증을 활동에 연결하면 Receipt와 UploadedFile 모두 갱신됨
3. 연결 해제 시 파일은 남고 활동 파일함에서는 사라짐
4. 파일 삭제 시 목록에서 사라지고 다운로드 불가
5. 활동 파일함이 category/role 기준으로 파일을 구분함
6. 감사 체크리스트가 참여자/보고서/증빙/HWPX 상태를 올바르게 계산함
7. AI가 activity_id 없이 증빙 연결을 요청하면 활동 선택을 요구함
```

---

# Part K. 브라우저 검증

```text
1. 활동 생성
2. 참가자 명단 업로드
3. 활동 보고서 작성
4. HWPX 생성
5. 영수증 이미지 업로드
6. 분석 결과 확인
7. 활동 증빙으로 연결
8. 파일함에서 영수증/명단/HWPX가 분류되어 보이는지 확인
9. 증빙 탭에서 영수증 미리보기 확인
10. 연결 해제
11. 다시 연결
12. 삭제
13. 감사 체크리스트 상태 확인
```

---

# 완료 기준

```text
1. 활동별 파일함이 원본/증빙/생성 문서를 구분해서 보여준다.
2. 영수증 분석 결과가 활동 증빙과 파일함에 일관되게 연결된다.
3. 전역 영수증을 활동에 연결/해제할 수 있다.
4. 파일 미리보기/다운로드/삭제/연결 해제가 일관되게 동작한다.
5. 활동 감사 체크리스트가 표시된다.
6. AI가 증빙/파일함 관련 요청을 현재 activity_id 기준으로 처리한다.
7. pytest 통과
8. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 34 완료 보고

1. 원인
- 영수증/증빙/파일함이 섞인 이유:
- 활동 감사 상태를 확인하기 어려웠던 이유:

2. 수정한 파일
- backend:
- frontend:
- migration:
- tests:

3. 파일 분류
- file_category:
- file_role:
- activity linkage:

4. 증빙/영수증
- upload:
- analysis:
- link:
- unlink:
- delete:

5. 파일함
- source:
- evidence:
- generated:
- preview/download/delete:

6. 감사 체크리스트
- 항목:
- 계산 기준:
- UI:

7. AI 연동
- 증빙 연결:
- 파일함 정리:
- 감사 상태 확인:

8. 검증
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task34: organize activity evidence files and audit readiness
```
