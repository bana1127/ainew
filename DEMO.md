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
