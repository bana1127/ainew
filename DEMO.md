# ClubAgent 데모 시나리오

ClubAgent의 주요 기능을 단계별로 체험하는 가이드입니다.

---

## 로컬 실행 순서

### 1. PostgreSQL 시작

```powershell
docker compose up -d db
```

### 2. 백엔드 실행

```powershell
cd backend
.venv\Scripts\activate
alembic upgrade head
python -m app.scripts.seed
python -m app.scripts.seed_demo
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### 3. 프론트엔드 실행

새 터미널에서:

```powershell
cd frontend
npm install
npm run dev
```

### 4. 접속

```
http://localhost:3000
```

---

## 데모 시나리오

### Step 1. Dashboard 확인

1. `http://localhost:3000/dashboard` 접속
2. **오늘 처리할 일** 카드 확인
3. 운영 요약 수치 확인
4. **AI 작업실 열기** 버튼으로 진입

---

### Step 2. 활동 보고서 카드 확인

1. 사이드바 → **Activities** 클릭
2. 카드 그리드에서 "5월 AI 스터디", "신입 부원 OT" 등 확인
3. 카드 클릭 → 상세 Drawer 오픈
4. **본문 복사** 버튼으로 클립보드에 복사
5. **.md 다운로드** 또는 **.txt 다운로드** 버튼으로 파일 저장

---

### Step 3. AI 작업실에서 보고서 초안 생성

1. 사이드바 → **AI 작업실** 클릭
2. 메시지 입력: "이 사진과 메모로 활동 보고서 초안 만들어줘"
3. 처리 유형이 "자동 감지"인 상태에서 **실행**
4. 결과 카드에서 보고서 초안 확인
5. **보고서 목록 보기** 클릭 → Activities 페이지에서 확인

---

### Step 4. 거래내역서 업로드

1. 사이드바 → **Transactions** 클릭
2. Excel 또는 CSV 파일 업로드
3. **미리보기** 클릭 → 파싱 결과 확인
4. **가져오기** 클릭 → DB 저장

---

### Step 5. 납부 매칭 실행

1. 사이드바 → **Payments** 클릭
2. 납부 기간 입력 (예: `2026-1`)
3. 기준 금액 입력 (예: `30000`)
4. **미리보기** 클릭 → 매칭 결과 확인
5. **매칭 적용** 클릭 → 납부 상태 반영

또는 AI 작업실에서:
- 메시지: "이번 달 미납자 확인해줘"
- 실행 → 결과 확인 → **납부 상태 반영** 클릭

---

### Step 6. 영수증 분석

1. 사이드바 → **Receipts** 클릭
2. 영수증 이미지 업로드
3. **영수증 분석** 클릭
4. 증빙 상태 확인 (valid / need_check / invalid)

또는 AI 작업실에서:
- 영수증 이미지 파일 첨부
- 메시지: "이 영수증 활동비로 정리해줘"
- 실행 → 결과 카드 확인

---

### Step 7. Dashboard에서 처리 상태 확인

1. Dashboard로 돌아가기
2. 오늘 처리할 일 카드 수치 변화 확인
3. 운영 요약 수치 확인

---

## 데모 데이터 설명

`python -m app.scripts.seed_demo`로 삽입되는 데이터:

| 종류 | 수량 | 설명 |
|------|------|------|
| 샘플 부원 | 10명 | 가상 학번/이름 |
| 활동 보고서 | 4개 | draft/generated/confirmed 포함 |
| 레퍼런스 보고서 | 3개 | 스터디/회의/OT 예시 |

여러 번 실행해도 중복 생성되지 않습니다.

---

---

## Task 18. Google Form 응답 Import 및 활동비 매칭 (신규)

### Google Form 신청서 Import 방법

1. 활동 상세 → **명단 Import** 탭 클릭
2. `.xlsx` / `.xls` / `.csv` 파일 선택
3. 파일 유형 힌트: **자동 판별** 또는 **활동 전 신청서** 선택
4. **미리보기** 클릭 → 기존 부원 매칭 / 신규 부원 후보 확인
5. **이 활동에 적용** 클릭 → 참여자 `status=applied`로 등록됨

신청서에서 자동 처리:
- 이름/학번/전화번호로 기존 부원 매칭
- 새 부원은 자동 생성 (status=active)
- 기존 부원의 누락 필드(전화번호 등)만 보강

### Google Form 활동지/피드백 Import 방법

1. 활동 상세 → **명단 Import** 탭 클릭
2. 파일 유형 힌트: **활동 후 피드백/활동지** 선택
3. **미리보기** 확인 → **이 활동에 적용**
4. 참여자 `status=completed`로 자동 갱신
5. 피드백 내용이 `activity_feedbacks` 테이블에 저장됨

### AI 작업실에서 Google Form 엑셀 처리

1. `/assistant` 접속
2. Google Form 응답 엑셀 업로드
3. AI가 파일 헤더 분석 → form_type 자동 판별
4. **활동 신청서** 또는 **활동 후 피드백** 카드 표시
5. 연결 활동 / 신규 부원 후보 수 확인
6. **이 활동에 적용** 클릭

거래내역서 엑셀을 올리면 기존 거래내역 파서가 실행됩니다.

---

### 거래내역 회비/활동비 매칭 차이

| 구분 | 회비 | 활동비 |
|------|------|--------|
| 매칭 대상 | 전체 활성 부원 | 활동 참여자 |
| 기준 기간 | `2026-1` 형식 | `act-{id[:8]}` 형식 |
| 금액 | 설정된 회비 금액 | 활동비 설정 금액 |
| 매칭 단위 | payment_type=membership_fee | payment_type=activity_fee |

### 활동비 거래내역 매칭 방법 (selected_activity_fee)

1. **Payments** 페이지 → **회비** 탭
2. 매칭 대상 셀렉터에서 **활동비 (전체)** 선택
3. 기간, 날짜 범위 설정 후 **미리보기**
4. 매칭 결과에서 활동명/부원명/신뢰도 확인
5. **매칭 적용**

또는 활동 상세 → **활동비** 탭에서 activity_fee payment record 상태 확인 후 수동 수정 가능.

### 매칭 취소 방법

**납부 기록에서 취소:**
1. Payments > 회비/활동비 탭 → 납부 기록 테이블
2. `transaction_id`가 있는 레코드 우측 **매칭 취소** 버튼
3. 확인 → `payment_record.transaction_id = null`, `status = unpaid` 복구

**거래내역에서 취소:**
1. Transactions 페이지 → 매칭 상태 = `matched` 거래 내역
2. 우측 **매칭 취소** 버튼
3. 확인 → `transaction.match_status = unmatched` 복구

---

## Task 19. 활동별 파일함 및 제출 패키지 관리 (신규)

### 활동 파일함 사용 방법

1. `/activities/{id}` 접속
2. **파일함** 탭 클릭
3. 파일 선택 (.pdf/.png/.jpg/.jpeg/.webp/.xlsx/.xls/.csv/.hwp/.hwpx/.zip)
4. 파일 유형 선택 (자동 분류 기본)
5. 제출용 파일 여부 체크 (필요시 제출 월 입력)
6. **업로드** 클릭

자동 분류 규칙:
- 파일명에 "내역서" → activity_report (활동 내역서)
- 파일명에 "기획서" → activity_plan (활동 기획서)
- 파일명에 "영수증" → receipt (영수증/증빙)
- 이미지 확장자 → photo (사진)
- ZIP → submission_package (제출 패키지)
- Google Form 엑셀 → Task 18 classifier로 자동 분류

### 파일 미리보기

- **PDF**: iframe inline 미리보기
- **이미지**: 이미지 viewer
- **Excel/CSV**: sheet별 30행 table 미리보기
- **ZIP**: 내부 파일 목록 표시
- **HWP/HWPX**: 원본 다운로드 안내 + 파일 메타데이터 표시

미리보기 불가 파일: "원본 파일 다운로드" 버튼 항상 제공

### 파일 다운로드

- 파일 카드 → **다운로드 버튼** (원본 파일명 유지)
- HWP/HWPX: 미리보기 패널의 **원본 다운로드** 버튼

### 파일 삭제

1. 파일 카드 → **🗑 삭제 버튼**
2. 확인 대화상자 → "이 파일을 삭제하시겠습니까?"
3. Soft delete (DB에 deleted_at 설정, 실제 파일은 서버에 보관)
4. 목록에서 즉시 사라짐

### 제출용 파일 지정

1. 파일 카드 → **★ 버튼** (별표 없으면 제출용으로 지정, 있으면 해제)
2. 또는 업로드 시 "제출용 파일" 체크 + 제출 월 입력
3. 제출용 필터로 제출용 파일만 보기 가능

### 월별 제출 패키지 preview

1. 파일함 탭 하단 **월별 제출 패키지** 섹션
2. YYYY-MM 형식으로 제출 월 선택
3. **미리보기** 클릭 → 해당 월 활동별 제출파일/누락항목 확인
4. 누락된 항목(activity_report/activity_plan/receipt)이 표시됨

### 월별 ZIP 생성 방법

1. 제출 패키지 섹션에서 월 선택
2. **ZIP 생성** 버튼 클릭
3. 생성 후 **ZIP 다운로드** 버튼으로 일괄 다운로드
4. ZIP 파일명 규칙: `{club_name}_{YYYYMMDD}_{활동명}.{ext}`

API 직접 호출:
```
GET  /api/submission-packages/preview?month=2026-09
POST /api/submission-packages/generate  {"month": "2026-09"}
```

### HWP/HWPX 파일 지원 범위 (Task 19)

- **원본 저장**: 업로드 후 서버에 보관
- **다운로드**: 원본 파일명 그대로 다운로드 가능
- **HWPX 메타데이터**: 가능하면 문서 제목 추출 (header.xml 파싱)
- **편집/생성**: Task 20에서 구현 예정

### Receipts / Reports / Assistant 파일 연동

- 영수증 업로드 파일: `file_category=receipt`, `file_role=evidence`
- 보고서 파일: 파일함에서 제출용으로 직접 지정 가능
- AI 작업실: `activity_id` 포함된 업로드 → `activity_report_id` 연결로 파일함에 표시

### API 엔드포인트 (Task 19 신규)

```
GET  /api/activities/{id}/files         — 활동 파일 목록
POST /api/activities/{id}/files         — 활동 파일 업로드
GET  /api/files/{id}                    — 파일 상세
GET  /api/files/{id}/preview            — 미리보기 메타데이터 JSON
GET  /api/files/{id}/preview/inline     — inline 파일 (PDF/이미지)
GET  /api/files/{id}/download           — 원본 파일 다운로드
DELETE /api/files/{id}                  — soft delete
PATCH /api/files/{id}/activity          — 활동 연결/해제
PATCH /api/files/{id}/submission        — 제출용 지정
GET  /api/submission-packages/preview   — 월별 패키지 미리보기
POST /api/submission-packages/generate  — 월별 ZIP 생성
```

---

## Task 20. HWPX 기반 제출 문서 생성 (신규)

### HWPX 템플릿 업로드 방법

1. `/activities/{id}` 접속
2. **보고서** 탭 클릭
3. 하단 **제출 문서 생성 (HWPX)** 섹션 → **템플릿 업로드** 버튼
4. `.hwpx` 파일 선택 + 템플릿명 + 유형 선택
5. **업로드** 클릭 → placeholder 자동 추출

또는 API 직접 호출:
```
POST /api/document-templates  (multipart: file, name, template_type)
```

### placeholder 작성 규칙

HWPX 파일 내부 XML에 다음 형식으로 작성:
```
{{활동명}}      {{activity_title}}
{{활동일}}      {{activity_date}}
{{활동장소}}    {{location}}
{{활동분류}}    {{category}}
{{활동내용}}    {{content}}
{{활동결과}}    {{result}}
{{참여자명단}}  {{participants}}
{{참여자수}}    {{participant_count}}
{{활동비금액}}  {{activity_fee_amount}}
{{활동비납부현황}} {{payment_summary}}
{{영수증목록}}  {{receipts}}
{{피드백요약}}  {{feedback_summary}}
{{작성일}}      {{generated_date}}
{{동아리명}}    {{club_name}}
```

주의: placeholder는 XML 단일 텍스트 노드 안에 온전히 작성해야 합니다.

### 활동 데이터 자동 매핑 방식

템플릿 선택 후 **매핑 미리보기** 버튼을 클릭하면:
- 현재 활동의 데이터(참여자, 활동비, 영수증, 피드백 등)가 자동 추출
- 각 placeholder에 어떤 값이 들어갈지 미리 확인 가능
- 누락 필드 목록 표시 (생성 시 "미입력"으로 처리)

### 보고서 본문 수정 후 HWPX 생성 방법

1. 보고서 탭에서 AI 초안 또는 직접 작성한 본문 확인
2. 제출 문서 생성 섹션에서 HWPX 템플릿 선택
3. 보고서 본문 textarea에서 최종 내용 수정 (→ `{{활동내용}}` 치환에 사용)
4. 생성 문서 제목 입력 (예: `Oui Parfum_20260530_정기스터디`)
5. 제출용 파일 여부 + 제출 월 선택
6. **HWPX 생성** 클릭

### 생성 문서 다운로드 방법

- 생성 후 **HWPX 다운로드** 버튼 → 원본 파일명 유지
- 파일함 탭에서도 확인/다운로드 가능
- API: `GET /api/files/{id}/download`

### 생성 문서와 파일함/제출 패키지 연동

생성된 HWPX 문서는 자동으로:
- 활동 파일함에 `file_category=activity_report`, `file_role=generated` 으로 등록
- `mark_as_submission=true` 시 `is_submission_file=true`, 파일함 ★ 제출용 표시
- 지정한 `submission_month`와 함께 월별 제출 패키지 preview에 포함

### HWP 파일 지원 범위 (Task 20 기준)

- **HWPX (.hwpx)**: 템플릿 업로드 → placeholder 자동 치환 → 문서 생성 지원
- **HWP (.hwp)**: 원본 저장/다운로드만 지원 (자동 편집 불가, Task 20 범위 외)

### API 엔드포인트 (Task 20 신규)

```
POST /api/document-templates              — 템플릿 업로드
GET  /api/document-templates              — 템플릿 목록
GET  /api/document-templates/{id}         — 템플릿 상세
GET  /api/document-templates/{id}/fields  — placeholder 필드 목록
POST /api/activities/{id}/documents/preview  — 매핑 미리보기
POST /api/activities/{id}/documents/generate — HWPX 문서 생성
GET  /api/activities/{id}/documents          — 생성 문서 목록
```

---

## Task 21. 활동비 오납/환불 정산 관리 (신규)

### 활동비 오납 감지 기준

매칭 후 상태 자동 계산:
- `paid_amount == 0` → `unpaid`
- `0 < paid_amount < required_amount` → `partial`
- `paid_amount == required_amount` → `paid`
- `paid_amount > required_amount` → `overpaid` (오납)
- participant.status = `cancelled` or `no_show` AND `paid_amount > 0` → `refund_required`

### 중복 납부 확인 방법

1. `/activities/{id}` → 활동비 탭 → "오납" 컬럼 확인
2. `/payments?tab=activity_fee` → 상태 필터 "오납" 선택
3. API: `GET /api/settlements/summary?activity_id={id}`

### 참여 취소/불참 시 환불 필요 처리

1. 참여자 status를 `cancelled` 또는 `no_show`로 변경
2. 해당 참여자의 활동비가 납부 상태이면 자동으로 `refund_required` 판단
3. 활동비 탭 → **환불필요** 버튼 클릭으로 `refund_status = refund_required` 설정

### 환불 대기/완료 처리 방법

활동 상세 → 활동비 탭에서:
1. **환불필요** 버튼 → `refund_status = refund_required`
2. **환불대기** 버튼 → `refund_status = refund_pending`
3. **환불완료** 버튼 → `refund_status = refunded`, `status = refunded`
4. **취소** 버튼 → `refund_status = none`으로 복구

또는 API:
```
POST /api/payment-records/{id}/refund-required
POST /api/payment-records/{id}/refund-pending
POST /api/payment-records/{id}/mark-refunded
POST /api/payment-records/{id}/refund-cancel
```

### 출금 거래내역을 환불로 매칭하는 방법

1. Transactions 페이지 → 출금 거래 우측 **환불로 매칭** 버튼
2. 모달에서 환불 대상 납부 기록 선택
3. **환불 매칭** 클릭
4. `transaction.match_status = refund_matched`, `payment_record.refund_status = refunded`

또는 API:
```
POST /api/transactions/{id}/match-refund  {"payment_record_id": "..."}
```

### 환불 매칭 취소 방법

1. Transactions 페이지 → `refund_matched` 거래 → **환불취소** 버튼
2. 확인 → `transaction.match_status = unmatched`, `payment_record.refund_status` 복구

또는 API:
```
POST /api/transactions/{id}/unmatch-refund
```

### 정산 로그 확인 방법

API: `GET /api/payment-records/{id}/adjustment-logs`

기록 액션: `refund_required`, `refund_pending`, `refund_completed`, `refund_cancelled`

### API 엔드포인트 (Task 21 신규)

```
GET  /api/settlements/summary            — 정산 집계 (오납/환불 현황)
GET  /api/settlements/refunds            — 환불 대상 목록
POST /api/payment-records/{id}/refund-required   — 환불 필요 표시
POST /api/payment-records/{id}/refund-pending    — 환불 대기
POST /api/payment-records/{id}/mark-refunded     — 환불 완료
POST /api/payment-records/{id}/refund-cancel     — 환불 취소
GET  /api/payment-records/{id}/adjustment-logs   — 정산 로그
POST /api/transactions/{id}/match-refund         — 환불 거래내역 매칭
POST /api/transactions/{id}/unmatch-refund       — 환불 매칭 취소
```

---

## API 확인

로컬에서 Next.js를 통한 API 확인:

```
http://localhost:3000/api/health
http://localhost:3000/api/dashboard/summary
```

백엔드 직접 확인:

```
http://localhost:8001/api/health
http://localhost:8001/api/activity-reports
```
