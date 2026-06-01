# ClubAgent 자동 점검 API 가이드

n8n 또는 curl/PowerShell로 주기적 자동 점검을 실행하는 방법을 설명합니다.

---

## 자동 점검 API 목록

| 엔드포인트 | 설명 |
|----------|------|
| `POST /api/automations/weekly-check` | 주간 운영 현황 점검 |
| `POST /api/automations/audit-check` | 감사 규정 준수 점검 |
| `POST /api/automations/quarterly-summary` | 분기 운영 요약 |

---

## 호출 URL

로컬 개발:

```
http://127.0.0.1:8001/api/automations/weekly-check
http://127.0.0.1:8001/api/automations/audit-check
http://127.0.0.1:8001/api/automations/quarterly-summary
```

외부 배포:

```
https://agent.banawy.store/api/automations/weekly-check
https://agent.banawy.store/api/automations/audit-check
https://agent.banawy.store/api/automations/quarterly-summary
```

분기 지정 (옵션):

```
POST /api/automations/quarterly-summary?year=2026&quarter=2
```

---

## AUTOMATION_API_TOKEN 인증

`backend/.env`에 토큰을 설정하면 모든 automation 엔드포인트에서 인증을 요구합니다.

```env
AUTOMATION_API_TOKEN=my-secret-token
```

- 토큰이 비어 있으면 → 인증 없이 호출 가능 (로컬 개발용)
- 토큰이 설정되어 있으면 → `X-Automation-Token` 헤더 필수

토큰은 코드나 로그에 절대 노출하지 마세요.

---

## curl 테스트

### 토큰 없이 (로컬 개발)

```bash
# 주간 점검
curl -X POST http://127.0.0.1:8001/api/automations/weekly-check

# 감사 점검
curl -X POST http://127.0.0.1:8001/api/automations/audit-check

# 분기 요약 (현재 분기 자동)
curl -X POST http://127.0.0.1:8001/api/automations/quarterly-summary

# 분기 지정
curl -X POST "http://127.0.0.1:8001/api/automations/quarterly-summary?year=2026&quarter=1"
```

### 토큰 사용

```bash
curl -X POST https://agent.banawy.store/api/automations/weekly-check \
  -H "X-Automation-Token: my-secret-token"
```

PowerShell:

```powershell
curl.exe -X POST https://agent.banawy.store/api/automations/weekly-check `
  -H "X-Automation-Token: my-secret-token"
```

---

## n8n 설정

### Schedule Trigger

1. n8n 캔버스에서 **Schedule Trigger** 노드 추가
2. 간격 설정 (예: 매주 월요일 오전 9시)

### HTTP Request 노드

1. Method: `POST`
2. URL: `https://agent.banawy.store/api/automations/weekly-check`
3. Headers:
   - `X-Automation-Token: {{$env.CLUBAGENT_TOKEN}}`
   - `Content-Type: application/json`

4. 응답 예시:
```json
{
  "ok": true,
  "pending_receipts": 3,
  "unpaid_members": 5,
  "items": ["확인 필요 영수증 3건", "미납/부분납부 5건"],
  "severity": "warning",
  "notification_saved": true
}
```

### n8n 환경변수

n8n → Settings → Variables:

```
CLUBAGENT_TOKEN = my-secret-token
```

---

## Notifications에서 결과 확인

자동 점검이 실행되면 결과가 `notifications` 테이블에 자동 저장됩니다.

확인 방법:

1. `http://localhost:3000/notifications` 접속
2. **자동 점검** 필터 클릭
3. 최신 점검 결과 확인

또는 API로 직접 조회:

```bash
curl "http://127.0.0.1:8001/api/notifications?type=automation"
```

---

## 점검 항목 설명

### weekly-check

| 항목 | 설명 |
|------|------|
| `pending_receipts` | 증빙 확인 필요(need_check) 영수증 수 |
| `unpaid_members` | 미납/부분납부 payment record 수 |
| `unmatched_transactions` | 매칭 안 된 거래 수 |
| `draft_reports` | 초안/생성됨 상태 보고서 수 |
| `unread_notifications` | 읽지 않은 비-automation 알림 수 |

### audit-check

| 항목 | 설명 |
|------|------|
| `need_check_receipts` | 감사 확인 필요 영수증 |
| `invalid_receipts` | 부적합 영수증 |
| `zero_amount_receipts` | 금액 0원 영수증 |
| `unlinked_receipts` | 활동 보고서 미연결 영수증 |

### quarterly-summary

| 항목 | 설명 |
|------|------|
| `activity_reports` | 분기 활동 보고서 수 |
| `receipts` | 분기 영수증 수 |
| `total_deposit` | 분기 총 입금액 |
| `total_withdraw` | 분기 총 출금액 |
| `unpaid_count` | 현재 미납 건수 |
| `need_check_receipts` | 분기 확인 필요 증빙 수 |
