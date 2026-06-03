# Task 18. Google Form 활동 응답 Import 및 활동비 거래내역 매칭 개선

## 목표

ClubAgent의 활동 중심 운영 구조에 Google Form 응답 엑셀 처리와 회비/활동비 거래내역 매칭을 연결한다.

동아리 활동에서는 보통 활동 전후로 Google Form을 사용한다.

```text
활동 전
→ 신청서 응답 엑셀
→ 신청자 명단, 전화번호, 학번, 선택 옵션, 신청 시간

활동 후
→ 활동지/피드백 응답 엑셀
→ 실제 참여자, 활동 후기, 개선점, 보고서 참고 내용
```

또한 거래내역서에는 회비 입금도 있고 활동비 입금도 있을 수 있다.

따라서 이번 Task의 목표는 다음이다.

```text
1. Google Form 응답 엑셀 유형 자동 판별
2. 활동 전 신청서 엑셀을 업로드하면 부원/참여자 자동 등록
3. 활동 후 활동지 엑셀을 업로드하면 참여 완료/피드백 자동 반영
4. AI 작업실과 활동 상세에서 Google Form 엑셀 처리 가능
5. 거래내역 매칭을 회비/활동비로 분리
6. 활동비 거래내역 자동 매칭 지원
7. 잘못 매칭된 납부 기록을 취소 가능하게 구현
```

---

## 전제 조건

Task 1~17이 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

```text
- Activities 중심 운영 구조
- /activities/{id} 활동 상세 컨트롤 센터
- 활동 참여자 관리
- 활동 보고서 생성
- 활동비 activity_fee payment_records 생성
- Payments 회비/활동비 탭
- 거래내역서 업로드 및 파싱
- 회비 납부 매칭
- Activity-aware Assistant
- Members 상세 이력
```

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

```text
1. Google Form 응답 엑셀 파서 구현
2. 엑셀 유형 자동 분류
   - 활동 신청서
   - 활동 후 활동지/피드백
   - 거래내역서
   - 부원 명부
   - 알 수 없음
3. 활동 신청서 Import Preview
4. 활동 신청서 Apply
5. 부원 자동 추가/업데이트
6. 활동 참여자 자동 등록
7. 활동 참여 상태 관리
8. 활동 후 피드백 Import Preview
9. 활동 후 피드백 Apply
10. 참여자 상태를 completed/attended로 자동 갱신
11. 활동 피드백/응답 내용 저장
12. 거래내역 매칭 모드 분리
13. 회비/활동비 자동 매칭 개선
14. 활동비 거래내역 매칭 지원
15. 매칭 취소 API 및 UI 구현
16. AI 작업실에서 Google Form 엑셀 자동 처리
17. 활동 상세에서 Google Form 엑셀 업로드/적용 가능
18. DEMO/README 문서 업데이트
```

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

```text
- 새로운 LLM Agent 추가
- Google Forms API 직접 연동
- Google Drive API 직접 연동
- Notion 연동
- Slack/Telegram 연동
- 로그인/권한 시스템
- 실제 은행 API 연동
- QR/PG 결제 기능
- 복잡한 감사 회계 기능
- 기존 거래내역서 파서 대규모 재작성
- 기존 영수증 분석 Agent 대규모 재작성
```

이번 Task는 **Google Form 응답 엑셀 파일 업로드 기반 자동 처리**까지만 구현한다.

---

# Part A. Google Form 응답 엑셀 유형 자동 판별

## 1. 목표

AI 작업실 또는 활동 상세 페이지에 엑셀 파일을 업로드하면, 해당 엑셀이 어떤 종류인지 자동 판별한다.

분류 타입:

```text
activity_application_form
→ 활동 전 신청서

activity_feedback_form
→ 활동 후 활동지/피드백

bank_statement
→ 거래내역서

member_roster
→ 부원 명부

unknown_excel
→ 알 수 없음
```

---

## 2. 판별 기준

우선 LLM을 쓰지 말고, 컬럼명 기반 rule-based classifier를 사용한다.

### 활동 신청서 예시 특징

```text
신청 시간
이름
학번
전화번호
연락처
참여 가능 시간
타임
선택 옵션
향조 선택
신청 사유
```

### 활동 후 활동지/피드백 예시 특징

```text
활동 후 응답
가져온 향수
인상 깊었던 향
첫 느낌
떠오르는 이미지
개선점
후기
피드백
만족도
```

### 거래내역서 예시 특징

```text
거래일시
입금
출금
잔액
적요
입금자
거래내용
```

### 부원 명부 예시 특징

```text
이름
학번
학과
전화번호
이메일
상태
기수
```

---

## 3. 구현 파일

권장 파일:

```text
backend/app/services/excel_form_classifier.py
backend/app/services/google_form_import_service.py
```

주요 함수:

```python
classify_excel_form(headers: list[str], filename: str | None = None) -> FormClassificationResult
```

결과 예시:

```json
{
  "form_type": "activity_application_form",
  "confidence": 0.91,
  "matched_columns": ["이름", "학번", "전화번호", "신청 시간"],
  "reason": "신청자 정보와 선택 옵션 컬럼이 확인되었습니다."
}
```

---

# Part B. Google Form Import Preview / Apply API

## 1. Preview API

파일을 바로 DB에 반영하지 말고 먼저 Preview를 제공한다.

권장 API:

```http
POST /api/activity-form-imports/preview
```

multipart form fields:

```text
file
activity_id optional
form_stage optional: auto | before | after
activity_mode optional: auto | link_existing | create_new | none
```

동작:

```text
1. 엑셀 파일 읽기
2. 헤더 추출
3. form_type 자동 판별
4. activity_id가 있으면 해당 활동에 연결
5. activity_id가 없으면 Activity Resolver로 활동 후보 검색
6. 행별 이름/학번/전화번호/응답 내용 추출
7. 기존 부원 매칭 결과 생성
8. 신규 부원 후보 생성
9. 기존 참여자 매칭 결과 생성
10. DB에 반영하지 않고 preview 반환
```

응답 예시:

```json
{
  "import_id": "temp-import-id",
  "form_type": "activity_application_form",
  "confidence": 0.91,
  "activity_context": {
    "mode": "linked",
    "activity_id": "activity-id",
    "activity_title": "교내 조향 활동"
  },
  "summary": {
    "total_rows": 25,
    "matched_members": 18,
    "new_member_candidates": 7,
    "existing_participants": 2,
    "new_participants": 23
  },
  "rows": [
    {
      "row_index": 2,
      "name": "김가온",
      "student_id": "20260001",
      "phone": "010-0000-0000",
      "member_match_status": "matched",
      "participant_action": "create",
      "participant_status": "applied",
      "raw_response": {}
    }
  ],
  "requires_confirmation": true
}
```

---

## 2. Apply API

Preview 결과를 사용자가 확인한 뒤 DB에 반영한다.

권장 API:

```http
POST /api/activity-form-imports/apply
```

요청 예시:

```json
{
  "import_id": "temp-import-id",
  "activity_id": "activity-id",
  "form_type": "activity_application_form",
  "rows": []
}
```

구현이 복잡하면 import_id 캐시 대신 preview 결과를 프론트에서 다시 전송해도 된다.

동작:

```text
1. activity_id 확인
2. row별 member upsert
3. activity_participant upsert
4. form_type에 따라 participant status 갱신
5. raw_response_json 저장
6. import log 저장
7. 결과 반환
```

응답 예시:

```json
{
  "ok": true,
  "activity_id": "activity-id",
  "form_type": "activity_application_form",
  "created_members": 7,
  "updated_members": 18,
  "created_participants": 23,
  "updated_participants": 2,
  "saved_feedbacks": 0
}
```

---

# Part C. 부원 자동 추가/업데이트 규칙

## 1. 매칭 우선순위

Google Form 응답의 부원 매칭 기준:

```text
1순위: student_id 정확 일치
2순위: phone 정확 일치
3순위: name + department 유사 일치
4순위: name 단독 일치
```

중복 위험이 있으면 자동 확정하지 말고 `needs_review`로 표시한다.

---

## 2. 신규 부원 생성

기존 부원이 없으면 신규 부원을 생성한다.

생성 필드:

```text
name
student_id
department nullable
phone nullable
email nullable
status = active 또는 pending
source = google_form optional
```

프로젝트에 `source` 필드가 없으면 추가하지 말고 TODO만 남긴다.

---

## 3. 기존 부원 업데이트

기존 부원이 있으면 누락된 필드만 보강한다.

예:

```text
기존 phone이 비어 있고 Google Form 응답에 phone이 있으면 업데이트
기존 department가 비어 있고 응답에 department가 있으면 업데이트
```

기존 값을 무조건 덮어쓰지 않는다.

---

# Part D. 활동 참여자 상태 관리

## 1. 참여 상태 표준

ActivityParticipant 또는 기존 참여자 구조에 다음 status를 사용한다.

```text
applied
→ 신청

confirmed
→ 확정

attended
→ 참석

completed
→ 활동 완료

cancelled
→ 취소

no_show
→ 불참
```

기존 status 필드가 없으면 최소 migration으로 nullable/default 값을 추가한다.

이미 status가 있으면 재사용한다.

---

## 2. 활동 전 신청서 적용 규칙

`activity_application_form` 적용 시:

```text
- member upsert
- activity participant upsert
- participant.status = applied
- 신청 시간, 선택 옵션, 타임, 응답 내용은 metadata/raw_response_json에 저장
```

---

## 3. 활동 후 피드백 적용 규칙

`activity_feedback_form` 적용 시:

```text
- member upsert 또는 기존 부원 매칭
- activity participant가 있으면 status = completed
- activity participant가 없으면 새로 생성하고 status = completed
- feedback 내용 저장
- raw_response_json 저장
```

활동 후 응답은 보고서 생성 자료로 활용될 수 있어야 한다.

---

# Part E. 활동 피드백 저장

## 1. 저장 방식

가능하면 별도 모델을 추가한다.

권장 모델:

```text
ActivityFeedback
- id
- activity_id 또는 activity_report_id
- member_id nullable
- response_type
- summary_text nullable
- raw_response_json
- submitted_at nullable
- created_at
```

대규모 migration이 부담되면 `ActivityParticipant.metadata` 또는 `raw_response_json` 필드를 사용한다.

---

## 2. 보고서 생성 연동

활동 보고서 생성 시 해당 활동의 feedback summary 또는 raw_response 일부를 입력 context에 포함한다.

예:

```text
- 참여자 후기
- 인상 깊었던 점
- 개선점
- 활동 결과 요약
```

---

# Part F. AI 작업실 연동

## 1. Assistant FileParser 보강

AI 작업실에 엑셀 파일을 올리면 다음 흐름을 탄다.

```text
1. 파일 확장자 xlsx/xls/csv 확인
2. 헤더 분석
3. form_type 분류
4. 거래내역서면 기존 거래내역 파서 실행
5. 활동 신청서/피드백이면 Google Form Import Preview 실행
6. 부원 명부면 기존 부원 명부 import 또는 TODO
7. 알 수 없으면 사용자에게 선택 요청
```

---

## 2. Assistant 결과 카드

Google Form Import Preview 결과는 AI 작업실에서 카드로 보여준다.

표시 항목:

```text
파일 유형
연결된 활동 또는 후보 활동
전체 응답 수
기존 부원 매칭 수
신규 부원 후보 수
참여자 생성/갱신 예정 수
적용 버튼
```

버튼:

```text
이 활동에 적용
다른 활동 선택
새 활동 생성 후 적용
취소
```

---

# Part G. 활동 상세 페이지 연동

## 1. 활동 상세에 Google Form Import 섹션 추가

`/activities/{id}` 안에 다음 섹션을 추가한다.

```text
신청/활동지 Import
```

기능:

```text
- 활동 전 신청서 엑셀 업로드
- 활동 후 활동지/피드백 엑셀 업로드
- Preview 확인
- Apply
```

활동 상세에서 업로드할 경우 `activity_id`는 자동으로 전달한다.

---

## 2. 참여자 목록 반영

Import Apply 후 참여자 목록이 갱신되어야 한다.

```text
신청서 Apply
→ 참여자 상태 applied

활동지 Apply
→ 참여자 상태 completed
→ 피드백 저장
```

---

# Part H. 거래내역 회비/활동비 매칭 개선

## 1. 현재 문제

현재 거래내역 매칭은 회비 중심으로 동작한다.

하지만 거래내역에는 다음이 모두 섞일 수 있다.

```text
회비 입금
활동비 입금
기타 입금
환불
지출
확인 필요
```

따라서 매칭 모드를 분리해야 한다.

---

## 2. 매칭 모드

거래내역 매칭 UI/API에서 다음 모드를 지원한다.

```text
auto
membership_fee
activity_fee
selected_activity_fee
none
```

의미:

```text
auto
→ 회비/활동비 후보를 모두 보고 점수 기반 추천

membership_fee
→ 회비 record만 대상으로 매칭

activity_fee
→ 전체 활동비 record 대상으로 매칭

selected_activity_fee
→ 선택한 활동의 activity_fee record만 대상으로 매칭

none
→ 매칭하지 않음
```

---

## 3. Backend API 보강

기존 매칭 API가 있다면 다음 필드를 추가한다.

```json
{
  "period": "2026-1",
  "payment_type": "membership_fee",
  "match_mode": "auto",
  "activity_id": null
}
```

활동비 매칭 시:

```json
{
  "match_mode": "selected_activity_fee",
  "payment_type": "activity_fee",
  "activity_id": "activity-id"
}
```

---

## 4. 활동비 매칭 기준

activity_fee 매칭 기준:

```text
1. 선택된 활동의 activity_fee payment_records를 우선 대상으로 사용
2. 입금자명/적요에 참여자 이름이 포함되면 높은 점수
3. 학번이 포함되면 매우 높은 점수
4. 금액이 required_amount와 같으면 높은 점수
5. activity title 일부가 적요에 있으면 가산점
6. 이미 paid/exempt인 record는 기본 제외
7. 후보가 여러 명이면 need_check로 표시
```

---

## 5. 회비 매칭 기준 유지

membership_fee 매칭은 기존 기준을 유지한다.

```text
member_id + period + payment_type 기준
금액 = 회비 기준 금액
이름/학번/입금자명/적요 기반 매칭
```

---

# Part I. 매칭 취소 기능

## 1. 목표

잘못 매칭된 거래내역과 납부 기록을 취소할 수 있어야 한다.

---

## 2. Backend API

둘 중 하나 이상 구현한다.

권장 1:

```http
POST /api/payment-records/{payment_record_id}/unmatch
```

권장 2:

```http
POST /api/transactions/{transaction_id}/unmatch
```

가능하면 둘 다 구현한다.

---

## 3. 취소 동작

payment_record 기준 취소:

```text
1. payment_record 조회
2. 연결된 transaction_id 확인
3. payment_record.transaction_id = null
4. payment_record.paid_amount = 0 또는 남은 수동 납부액 기준 재계산
5. payment_record.status 재계산
   - paid_amount == 0 → unpaid
   - 0 < paid_amount < required_amount → partial
   - paid_amount >= required_amount → paid
6. transaction.match_status = unmatched
7. transaction.matched_payment_record_id = null
8. 필요하면 note에 unmatch 기록
```

거래내역 기준 취소:

```text
1. transaction 조회
2. 연결된 payment_record 조회
3. 위와 동일하게 연결 해제
```

---

## 4. Frontend UI

다음 위치에 매칭 취소 버튼을 추가한다.

```text
Payments > 회비 납부 기록
Payments > 활동비 납부 기록
Transactions > 매칭된 거래내역
Activity detail > 활동비 납부 현황
```

버튼 문구:

```text
매칭 취소
```

confirm 문구:

```text
이 거래내역 매칭을 취소하시겠습니까?
납부 상태가 미납 또는 부분 납부로 되돌아갈 수 있습니다.
```

성공 후:

```text
- payment_records 새로고침
- transactions 새로고침
- summary 새로고침
- activity detail 새로고침
```

---

# Part J. Transactions 페이지 개선

## 1. 거래내역 매칭 UI 보강

Transactions 또는 Payments 페이지에서 거래내역 매칭 시 다음 옵션을 제공한다.

```text
매칭 대상
- 자동 판단
- 회비
- 활동비
- 선택한 활동의 활동비
```

선택한 활동의 활동비인 경우 activity select 표시.

---

## 2. 매칭 Preview

거래내역을 바로 적용하지 말고 preview를 보여준다.

Preview row 표시:

```text
거래일
입금자/적요
금액
추천 매칭 대상
매칭 유형: 회비/활동비
활동명
부원명
신뢰도
상태
```

사용자가 확인 후 Apply.

---

# Part K. 문서화

README 또는 DEMO 문서에 다음 내용을 추가한다.

```text
- Google Form 신청서 import 방법
- Google Form 활동지/피드백 import 방법
- 신청자 자동 등록 흐름
- 활동 완료 상태 자동 반영 흐름
- 거래내역 회비/활동비 매칭 차이
- 활동비 매칭 방법
- 매칭 취소 방법
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

## 시나리오 1. 활동 전 신청서 Import

```text
1. /activities/{id} 접속
2. 신청서 엑셀 업로드
3. form_type = activity_application_form 판별 확인
4. Preview에서 기존 부원/신규 부원 후보 확인
5. Apply
6. 참여자 목록에 status=applied로 추가되는지 확인
```

## 시나리오 2. 활동 후 활동지 Import

```text
1. /activities/{id} 접속
2. 활동 후 활동지/피드백 엑셀 업로드
3. form_type = activity_feedback_form 판별 확인
4. Preview에서 기존 참여자 매칭 확인
5. Apply
6. 참여자 status=completed로 변경되는지 확인
7. 피드백 내용이 저장되는지 확인
```

## 시나리오 3. AI 작업실에서 Google Form 엑셀 처리

```text
1. /assistant 접속
2. 활동 신청서 엑셀 업로드
3. 기존 활동 후보 또는 새 활동 생성 제안 확인
4. 활동 선택 후 Apply
5. 활동 상세에 참여자가 반영되는지 확인
```

## 시나리오 4. 회비 거래내역 매칭

```text
1. 거래내역서 업로드
2. match_mode=membership_fee 선택
3. Preview 확인
4. Apply
5. 회비 납부 상태 갱신 확인
```

## 시나리오 5. 활동비 거래내역 매칭

```text
1. 활동비 대상이 생성된 활동 준비
2. 거래내역서 업로드
3. match_mode=selected_activity_fee 선택
4. 활동 선택
5. Preview에서 참여자별 활동비 매칭 확인
6. Apply
7. 활동비 납부 상태 갱신 확인
```

## 시나리오 6. 매칭 취소

```text
1. 매칭된 납부 기록 확인
2. 매칭 취소 클릭
3. confirm 승인
4. payment_record.transaction_id가 제거되는지 확인
5. 거래내역 match_status가 unmatched로 돌아가는지 확인
6. 납부 상태가 unpaid/partial로 재계산되는지 확인
```

---

## 완료 기준

Task 18은 다음을 모두 만족해야 완료로 본다.

```text
1. Google Form 응답 엑셀 유형을 자동 판별한다.
2. 활동 신청서 엑셀을 Preview할 수 있다.
3. 활동 신청서 Apply 시 부원이 자동 추가/업데이트된다.
4. 활동 신청서 Apply 시 활동 참여자가 status=applied로 등록된다.
5. 활동 후 피드백 엑셀을 Preview할 수 있다.
6. 활동 후 피드백 Apply 시 참여자가 completed로 갱신된다.
7. 활동 피드백/응답 내용이 저장된다.
8. AI 작업실에서 Google Form 응답 엑셀을 처리할 수 있다.
9. 활동 상세에서 Google Form 응답 엑셀을 처리할 수 있다.
10. 거래내역 매칭 모드가 회비/활동비로 분리된다.
11. 활동비 거래내역 자동 매칭이 가능하다.
12. 선택한 활동의 활동비만 대상으로 거래내역을 매칭할 수 있다.
13. 매칭 Preview 후 Apply 흐름이 유지된다.
14. 매칭 취소 API가 동작한다.
15. Payments/Transactions/Activity detail에서 매칭 취소 버튼이 보인다.
16. 매칭 취소 후 payment_record와 transaction 상태가 정상 복구된다.
17. frontend build가 성공한다.
18. backend compile/test가 성공한다.
19. 이번 Task에서 Google Forms API 직접 연동, Notion, Slack, 로그인 기능은 구현하지 않았다.
```

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 18 완료 보고

1. 생성/수정한 주요 파일
- ...

2. Google Form 엑셀 분류
- classifier:
- 지원 form_type:
- 판별 기준:

3. 활동 신청서 Import
- Preview:
- Apply:
- member upsert:
- participant status:

4. 활동 후 피드백 Import
- Preview:
- Apply:
- completed 처리:
- feedback 저장:

5. AI 작업실 연동
- Excel FileParser:
- 활동 후보:
- Preview 카드:
- Apply UX:

6. 활동 상세 연동
- 신청서 업로드:
- 활동지 업로드:
- 참여자 갱신:
- 피드백 표시:

7. 거래내역 매칭 개선
- match_mode:
- membership_fee:
- activity_fee:
- selected_activity_fee:
- Preview/Apply:

8. 매칭 취소 기능
- API:
- PaymentRecord 복구:
- Transaction 복구:
- Frontend 버튼:

9. 실행 검증 결과
- alembic upgrade:
- backend compile/test:
- frontend build:
- 신청서 import:
- 활동지 import:
- 회비 매칭:
- 활동비 매칭:
- 매칭 취소:

10. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

11. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task18: import google form responses and improve payment matching
```
