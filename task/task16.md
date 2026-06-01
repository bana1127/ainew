# Task 16. 활동 중심 운영 구조 개편 및 사이드바 재정리

## 목표

ClubAgent의 구조를 기능별 관리 화면 중심에서 실제 동아리 운영 흐름에 맞는 **활동 중심 운영 구조**로 개편한다.

기존에는 기능이 다음처럼 흩어져 있었다.

```text
Reports → 활동 보고서
Payments → 회비/납부 관리
Receipts → 영수증/증빙
Members → 부원 관리
Activities → 활동 관련 일부 기능
```

하지만 실제 운영에서는 “활동”이 먼저 존재하고, 그 활동 안에서 여러 업무가 발생한다.

```text
활동 생성
→ 참여자 등록
→ 사진/자료 업로드
→ 활동 보고서 작성
→ 활동비 필요 시 납부 대상 생성
→ 활동비 납부 여부 확인
→ 영수증/증빙 연결
→ 최종 정리
```

이번 Task의 목표는 다음이다.

```text
1. 사용자 화면에서 Mock/Test/Local Dev 등 개발용 표시 제거
2. Sidebar를 활동 중심 구조로 재정리
3. Activities를 운영의 중심 페이지로 개편
4. 활동 상세 페이지를 Activity Control Center로 구현
5. 활동 안에서 보고서, 참여자, 활동비, 영수증, 첨부 자료를 관리
6. Payments는 회비/활동비 전체 현황 페이지로 정리
7. Members 상세에서 개인별 활동/납부 이력을 확인
```

---

## 전제 조건

Task 1~15가 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

```text
- 전역 AppShell
- 모바일 UX 대응
- Dashboard
- AI 작업실
- Members
- Activities
- Reports
- Receipts
- Transactions
- Payments
- Notifications
- Settings
- 활동 보고서 카드형 UX
- 영수증 분석 및 삭제
- 회비 납부 매칭 및 직접 수정
- 실제 OpenAI 모드
- 자동 점검 API
```

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

```text
1. Mock/Test/Local Dev 등 개발용 UI 표시 제거
2. Sidebar 메뉴 구조를 활동 중심으로 재정리
3. Activities 페이지를 “활동 목록 + 활동 만들기” 중심으로 개편
4. 활동 상세 페이지 /activities/[id] 구현
5. 활동 상세 안에 다음 탭 또는 섹션 구현
   - 개요
   - 참여 회원
   - 활동 보고서
   - 활동비
   - 영수증/증빙
   - 사진/첨부 자료
   - 처리 체크리스트
6. 활동비 생성 및 납부 현황 관리
7. Payments 페이지를 회비/활동비 전체 현황 페이지로 정리
8. Reports 페이지는 전체 보고서 모아보기/검색/내보내기 보조 페이지로 정리
9. Receipts 페이지는 전체 영수증 관리 + 활동별 연결 상태 표시
10. Members 상세 페이지에서 참여 활동/회비/활동비 이력 확인
11. Dashboard와 Notifications에 활동 처리 상태 최소 반영
12. 모바일에서도 활동 상세/활동비/부원 상세이 깨지지 않게 유지
```

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

```text
- 새로운 Agent 기능
- LLM 기반 Intent Classifier
- Notion 연동
- Slack/Telegram 연동
- 로그인/권한 시스템
- QR 결제 기능
- 실제 PG/은행 API 연동
- 자동 문자/카카오톡 발송
- 기존 영수증 분석 Agent 재작성
- 기존 거래내역서 파서 재작성
- 기존 납부 매칭 알고리즘 대규모 재작성
```

필요한 위치에는 TODO 주석만 남긴다.

---

# Part A. 개발용 표시 제거

## 1. 제거 대상

사용자 화면에서 다음 문구가 보이지 않게 한다.

```text
Mock Mode
Local Dev
테스트 데이터
테스트 분석 결과
Task 예정
Command Center 구현 예정
개발용
placeholder
```

확인 대상:

```text
frontend/components/layout/Header.tsx
frontend/components/layout/Sidebar.tsx
frontend/components/layout/AppShell.tsx
frontend/app/dashboard/page.tsx
frontend/app/assistant/page.tsx
frontend/app/receipts/page.tsx
frontend/app/reports/page.tsx
frontend/app/settings/page.tsx
frontend/components/assistant/*
```

## 2. 처리 기준

개발 설정 자체는 유지할 수 있다.

```text
- OPENAI_MOCK_MODE 환경변수는 유지 가능
- 내부 개발 기능은 유지 가능
- 하지만 사용자-facing UI에서는 표시하지 않음
```

Header 우측의 상태 배지는 제거하거나 실사용 문구로 바꾼다.

권장:

```text
Header 우측 상태 배지 제거
또는 “운영 중” 정도만 표시
```

---

# Part B. Sidebar 구조 재정리

## 1. 현재 문제

사이드바에 기능이 많고, 보고서/납부/영수증/활동이 같은 레벨로 보여서 실제 운영 흐름이 잘 드러나지 않는다.

이번 Task에서는 Sidebar를 **활동 중심 구조**로 정리한다.

---

## 2. 권장 Sidebar 구조

```text
MAIN
- Dashboard
- AI 작업실

OPERATIONS
- Activities
- Members

FINANCE
- Payments
- Receipts
- Transactions

DOCUMENTS
- Reports
- References

SYSTEM
- Notifications
- Settings
```

## 3. 메뉴 역할

```text
Dashboard
→ 전체 운영 상태 확인

AI 작업실
→ 파일/요청 기반 자동 처리 진입점

Activities
→ 활동 생성, 활동별 운영 컨트롤 센터

Members
→ 부원 목록 및 개인별 활동/납부 이력

Payments
→ 회비/활동비 전체 납부 현황

Receipts
→ 전체 영수증 및 증빙 관리

Transactions
→ 거래내역서 업로드/파싱/매칭

Reports
→ 전체 활동 보고서 모아보기/검색/복사/다운로드

References
→ 보고서 레퍼런스 관리

Notifications
→ 자동 점검/확인 필요 알림

Settings
→ 운영 설정
```

## 4. Sidebar UI 요구사항

```text
- Activities를 Operations 그룹의 핵심 메뉴로 배치
- Reports는 Documents 그룹으로 이동
- 회비/활동비는 Payments 안에서 탭으로 처리
- 모바일 Drawer에서도 동일한 그룹 구조 유지
- 사용자 화면에 Mock Mode 카드 표시 금지
```

---

# Part C. 활동 데이터 구조 방향

## 1. 핵심 개념

이상적인 구조는 다음이다.

```text
Activity
- id
- title
- category_id
- activity_date
- location
- description
- status
- fee_enabled
- fee_amount

ActivityParticipant
- activity_id
- member_id
- role/status

ActivityReport
- activity_id
- generated_content
- final_content
- status

Receipt
- activity_id
- amount
- store_name
- evidence_status

PaymentRecord
- member_id
- payment_type
- period
- activity_id nullable
- required_amount
- paid_amount
- status
```

하지만 현재 프로젝트에 이미 `ActivityReport` 중심 구조가 있을 가능성이 크다.

따라서 이번 Task에서는 다음 원칙을 따른다.

```text
1. 이미 Activity 모델이 있으면 Activity를 중심으로 구현
2. Activity 모델이 없고 ActivityReport만 있다면, ActivityReport를 활동 단위로 확장해서 사용
3. 대규모 DB 재설계는 피함
4. 필요한 연결 필드만 최소 migration으로 추가
```

## 2. 최소 보강 필드

필요한 경우 최소한 아래 필드를 추가한다.

```text
activity_reports.fee_enabled nullable/default false
activity_reports.fee_amount nullable
payment_records.activity_report_id nullable
receipts.activity_report_id nullable
uploaded_files.activity_report_id nullable
```

이미 유사한 필드가 있으면 새로 만들지 말고 재사용한다.

---

# Part D. Activities 페이지 개편

## 1. 목표

`/activities`를 활동 운영의 중심 페이지로 만든다.

기존 Reports 중심 UX를 다음처럼 바꾼다.

```text
활동 보고서 목록
→ 활동 목록 + 활동 만들기 + 활동별 처리 상태 확인
```

## 2. Activities 페이지 구성

```text
상단:
- 활동 관리
- 활동을 만들고, 참여자/보고서/활동비/증빙을 한 곳에서 관리하세요.
- 새 활동 만들기 버튼

본문:
- 활동 카드 그리드
- 검색/상태/카테고리 필터
```

## 3. 활동 카드 표시 항목

```text
활동명
활동일
장소
카테고리
참여 인원
보고서 상태
활동비 상태
영수증/증빙 상태
처리 상태
```

예시:

```text
5월 AI 스터디
활동일: 2026-05-30
참여자: 8명
보고서: 작성 완료
활동비: 6/8 납부
영수증: 2건 연결
상태: 확인 필요
[활동 관리]
```

## 4. 새 활동 만들기

새 활동 생성 UI를 추가한다.

필드:

```text
활동명
카테고리
활동일
장소
설명
참여자 선택
활동 상태
```

활동 상태:

```text
planned → 예정
in_progress → 진행 중
done → 완료
archived → 보관
```

저장 후 `/activities/{id}`로 이동한다.

---

# Part E. 활동 상세 페이지 구현

## 1. URL

다음 페이지를 추가한다.

```text
/activities/[id]
```

파일 예시:

```text
frontend/app/activities/[id]/page.tsx
```

## 2. 활동 상세 페이지 역할

활동 상세 페이지는 Activity Control Center이다.

구성:

```text
1. 활동 기본 정보
2. 처리 체크리스트
3. 참여 회원
4. 활동 보고서
5. 활동비
6. 영수증/증빙
7. 사진/첨부 자료
```

탭 UI 또는 섹션 UI로 구현한다.

권장:

```text
상단 요약 카드
하단 탭:
- 개요
- 참여자
- 보고서
- 활동비
- 증빙
- 첨부
```

---

## 3. 활동 기본 정보

표시:

```text
활동명
활동일
장소
카테고리
설명
상태
```

수정 가능하면 좋지만, 최소 구현은 표시 중심으로 한다.

---

## 4. 처리 체크리스트

활동에 필요한 작업 상태를 보여준다.

항목:

```text
참여자 등록
보고서 작성
활동비 설정
활동비 납부 완료
영수증 연결
증빙 확인
첨부 자료 등록
```

예시:

```text
참여자 8명 등록 완료
보고서 작성 완료
활동비 납부 6/8 완료
영수증 2건 연결
증빙 확인 필요 1건
```

---

## 5. 참여 회원

활동 참여자를 관리한다.

기능:

```text
참여자 추가
참여자 제거
참여자 명단 확인
```

참여자 표시:

```text
이름
학번
학과
참여 상태
비고
```

참여자 명단은 활동 보고서 참석자와 활동비 대상자에 연결된다.

---

## 6. 활동 보고서

기존 활동 보고서 기능은 활동 상세 내부 기능으로 배치한다.

기능:

```text
AI 보고서 초안 생성
보고서 수정
본문 복사
Markdown 다운로드
Text 다운로드
보고서 확정
```

본문 우선순위:

```text
final_content
generated_content
input_text
```

Reports 페이지는 전체 보고서 모아보기 역할로 남긴다.

---

## 7. 활동비

활동비가 필요한 활동에서 비용을 설정하고 납부 상태를 확인한다.

기능:

```text
활동비 사용 여부
1인당 금액
납부 기간
대상 참여자 확인
활동비 납부 대상 생성
활동비 납부 현황
미납자 목록
직접 수정
```

활동비 생성 규칙:

```text
payment_type = activity_fee
activity_report_id 또는 activity_id = 현재 활동
member_id = 참여자
required_amount = 입력 금액
paid_amount = 0
status = unpaid
```

중복 기준:

```text
member_id + activity_id/activity_report_id + payment_type
```

이미 paid/partial/exempt 상태인 기록은 paid_amount/status를 덮어쓰지 않는다.

---

## 8. 영수증/증빙

활동에 관련된 영수증을 연결한다.

기능:

```text
영수증 업로드
AI 영수증 분석
활동에 연결
증빙 상태 확인
영수증 삭제
```

활동 상세에서는 해당 활동과 연결된 영수증만 표시한다.

전체 영수증은 `/receipts`에서 관리한다.

---

## 9. 사진/첨부 자료

활동 자료를 업로드하고 확인한다.

기능:

```text
사진 업로드
PDF 업로드
활동 자료 업로드
업로드 파일 목록
```

첨부 자료는 보고서 생성에 활용될 수 있도록 연결 정보만 유지한다.

---

# Part F. 활동 관련 Backend API

실제 구조에 맞게 다음 API를 구현하거나 보강한다.

## 1. 활동 목록

```http
GET /api/activities
```

응답에는 카드에 필요한 요약 정보를 포함한다.

```json
{
  "id": "activity-id",
  "title": "5월 AI 스터디",
  "activity_date": "2026-05-30",
  "location": "동아리방",
  "category_name": "정기 스터디",
  "participant_count": 8,
  "report_status": "confirmed",
  "activity_fee_status": "6/8 paid",
  "receipt_count": 2,
  "need_check_count": 1,
  "status": "done"
}
```

## 2. 활동 생성

```http
POST /api/activities
```

요청:

```json
{
  "title": "5월 AI 스터디",
  "category_id": "category-id",
  "activity_date": "2026-05-30",
  "location": "동아리방",
  "description": "정기 AI 스터디",
  "participant_member_ids": ["member-id-1", "member-id-2"]
}
```

## 3. 활동 상세

```http
GET /api/activities/{activity_id}
```

응답:

```json
{
  "activity": {},
  "participants": [],
  "report": {},
  "activity_fee": {
    "enabled": true,
    "amount": 10000,
    "records": [],
    "summary": {}
  },
  "receipts": [],
  "attachments": [],
  "checklist": []
}
```

## 4. 참여자 관리

```http
POST /api/activities/{activity_id}/participants
DELETE /api/activities/{activity_id}/participants/{member_id}
```

## 5. 활동비 대상 생성

```http
POST /api/activities/{activity_id}/activity-fees/generate
```

또는 기존 Payments API를 사용한다.

```http
POST /api/payments/activity-fees/generate
```

둘 중 하나만 구현해도 된다.
권장: 활동 상세에서 쓰기 편한 `/api/activities/{id}/activity-fees/generate`를 구현하고 내부에서 payment service를 호출한다.

## 6. 활동 영수증 연결

```http
PATCH /api/receipts/{receipt_id}/activity
```

요청:

```json
{
  "activity_id": "activity-id"
}
```

또는 activity_report_id 기반이면 해당 필드명을 사용한다.

---

# Part G. Payments 페이지 역할 정리

## 1. 목표

Payments는 전체 납부 현황 페이지로 유지한다.

구조:

```text
/payments
- 회비 탭
- 활동비 탭
```

## 2. 회비 탭

기존 기능 유지.

```text
기간
기준 금액
거래내역 매칭
미납자
납부 기록
직접 수정
```

payment_type:

```text
membership_fee
```

## 3. 활동비 탭

활동 기준으로 납부 현황을 확인한다.

```text
활동 선택
활동비 납부 현황
참여자별 납부 상태
미납자
직접 수정
```

활동비 생성의 중심은 `/activities/{id}`에 둔다.
Payments에서는 전체 현황 확인과 직접 수정에 집중한다.

---

# Part H. Reports 페이지 역할 정리

## 1. 목표

Reports는 더 이상 활동 운영의 중심이 아니다.

역할:

```text
전체 보고서 모아보기
검색
복사
Markdown/Text 다운로드
보관
```

활동 보고서 작성/수정의 중심은 `/activities/{id}` 내부 보고서 탭으로 이동한다.

## 2. Reports 페이지 안내 문구

Reports 페이지 상단 문구를 수정한다.

예시:

```text
전체 활동 보고서를 모아보고 복사하거나 내보낼 수 있습니다.
새 보고서는 Activities에서 활동을 만든 뒤 작성하세요.
```

---

# Part I. Members 상세 페이지

## 1. URL

```text
/members/[id]
```

## 2. Backend API

```http
GET /api/members/{member_id}/summary
```

응답:

```json
{
  "member": {},
  "activities": [],
  "membership_payments": [],
  "activity_fee_payments": [],
  "summary": {
    "activity_count": 0,
    "membership_paid_count": 0,
    "activity_fee_unpaid_count": 0,
    "need_check_count": 0
  }
}
```

## 3. Frontend 구성

```text
프로필 카드
요약 카드
참여 활동 내역
회비 납부 이력
활동비 납부 이력
확인 필요 항목
```

Members 목록에서 row/card 클릭 시 상세 페이지로 이동한다.

---

# Part J. Dashboard / Notifications 반영

## 1. Dashboard

Dashboard에 활동 중심 지표를 최소 반영한다.

예시:

```text
진행 중 활동
보고서 미작성 활동
활동비 미납
증빙 확인 필요
```

카드가 너무 많아지면 추천 작업 영역에만 표시해도 된다.

## 2. Notifications / Automation

자동 점검이 있다면 weekly-check에 다음을 포함한다.

```text
보고서 미작성 활동
활동비 미납 활동
증빙 확인 필요 활동
```

---

# Part K. 모바일 대응

Task 15 모바일 UX 기준을 유지한다.

필수 확인:

```text
- Sidebar 모바일 Drawer 정상
- Activities 카드 모바일 1열
- 활동 상세 탭 모바일 사용 가능
- 참여자/활동비/영수증 목록 모바일 카드형
- Payments 회비/활동비 탭 모바일 사용 가능
- Members 상세 모바일 카드형
- 전체 페이지 가로 스크롤 없음
```

---

# 문서화

README 또는 DEMO 문서에 다음 내용을 추가한다.

```text
- 활동 중심 운영 구조 설명
- 활동 생성 방법
- 활동 상세에서 참여자/보고서/활동비/영수증 관리하는 방법
- 회비와 활동비 차이
- Payments의 역할
- Reports의 역할 변경
- Members 상세에서 개인별 이력 확인 방법
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

## 시나리오 1. 개발용 문구 제거

```text
1. Dashboard 접속
2. Header/Sidebar 확인
3. Mock Mode, Local Dev, 테스트 데이터 문구가 보이지 않는지 확인
```

## 시나리오 2. Sidebar 구조 확인

```text
1. Sidebar 확인
2. Activities가 운영 중심 메뉴로 보이는지 확인
3. Reports가 Documents 또는 보조 보고서 메뉴로 이동했는지 확인
4. 모바일 Drawer에서도 동일하게 보이는지 확인
```

## 시나리오 3. 활동 생성

```text
1. /activities 접속
2. 새 활동 만들기
3. 활동명, 날짜, 장소, 카테고리, 참여자 입력
4. 저장
5. /activities/{id}로 이동
```

## 시나리오 4. 활동 상세 컨트롤

```text
1. /activities/{id} 접속
2. 참여자 목록 확인
3. 활동 보고서 작성 또는 초안 생성
4. 활동비 금액 설정
5. 활동비 납부 대상 생성
6. 영수증 연결
7. 체크리스트 상태 확인
```

## 시나리오 5. 활동비 납부 확인

```text
1. /activities/{id} 활동비 탭에서 납부 현황 확인
2. 미납자 직접 수정
3. /payments?tab=activity_fee에서 동일 내역 확인
```

## 시나리오 6. 부원 상세

```text
1. /members 접속
2. 부원 클릭
3. /members/{id} 접속
4. 참여 활동 확인
5. 회비 납부 이력 확인
6. 활동비 납부 이력 확인
```

## 시나리오 7. 모바일 확인

```text
1. 모바일 화면 크기로 /activities 접속
2. 활동 상세 진입
3. 탭/섹션 사용 가능 여부 확인
4. 활동비/참여자/영수증 목록이 깨지지 않는지 확인
```

---

# 완료 기준

Task 16은 다음을 모두 만족해야 완료로 본다.

```text
1. 사용자 화면에서 Mock/Test/Local Dev 문구 제거
2. Sidebar가 활동 중심 구조로 재정리됨
3. /activities가 활동 목록/활동 만들기 중심으로 변경됨
4. /activities/{id} 활동 상세 컨트롤 센터 구현
5. 활동 상세에서 참여자 관리 가능
6. 활동 상세에서 활동 보고서 작성/확인 가능
7. 활동 상세에서 활동비 설정 및 대상 생성 가능
8. 활동 상세에서 활동비 납부 현황 확인 가능
9. 활동 상세에서 영수증/증빙 연결 확인 가능
10. Payments가 회비/활동비 탭으로 정리됨
11. 활동비 전체 현황을 Payments에서 확인 가능
12. Reports는 전체 보고서 모아보기 역할로 정리됨
13. /members/[id] 부원 상세 페이지 구현
14. 부원 상세에서 참여 활동 이력 확인 가능
15. 부원 상세에서 회비 납부 이력 확인 가능
16. 부원 상세에서 활동비 납부 이력 확인 가능
17. Dashboard 또는 Notifications에 활동 처리 상태 최소 반영
18. 모바일에서 Activities/활동 상세/Payments/Members 상세이 깨지지 않음
19. frontend build 성공
20. backend compile/test 성공
21. 이번 Task에서 Notion, Slack, 로그인, 신규 Agent는 구현하지 않음
```

---

# 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 16 완료 보고

1. 생성/수정한 주요 파일
- ...

2. Mock/Test 표시 제거
- 제거한 화면:
- 변경한 문구:
- 유지한 개발 설정:

3. Sidebar 재정리
- 새 그룹 구조:
- Activities 위치:
- Reports 위치:
- 모바일 Drawer 반영:

4. 활동 중심 구조 개편
- Activities 목록:
- 새 활동 만들기:
- 활동 상세 URL:
- 활동 상세 탭/섹션:

5. 활동 상세 기능
- 참여자:
- 보고서:
- 활동비:
- 영수증/증빙:
- 첨부:
- 체크리스트:

6. Payments 역할 정리
- 회비 탭:
- 활동비 탭:
- 활동비 전체 현황:
- 직접 수정:

7. Reports 역할 정리
- 전체 보고서 모아보기:
- 복사/다운로드:
- 활동 상세와의 관계:

8. Members 상세 페이지
- URL:
- 기본 정보:
- 참여 활동 이력:
- 회비 납부 이력:
- 활동비 납부 이력:

9. Backend 변경
- migration:
- API:
- activity/payment/receipt 연결:
- member summary:

10. Frontend 변경
- Activities:
- Activity detail:
- Payments:
- Reports:
- Members:
- Sidebar:
- Dashboard/Notifications:

11. 실행 검증 결과
- alembic upgrade:
- backend compile/test:
- frontend build:
- 활동 생성:
- 활동 상세:
- 활동비 생성:
- Payments 활동비:
- 부원 상세:
- 모바일 확인:

12. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

13. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task16: refactor around activity control center
```
