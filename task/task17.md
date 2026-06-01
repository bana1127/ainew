# Task 17. Activity-aware Assistant Orchestrator 구현

## 목표

ClubAgent의 AI 작업실과 Assistant Orchestrator를 활동 중심 운영 구조에 맞게 재설계한다.

Task 16에서 Activities가 운영의 중심이 되었다면, Task 17에서는 AI도 같은 방식으로 동작해야 한다.

기존 Assistant는 주로 기능 단위로 요청을 분류했다.

```text
영수증 → 영수증 분석
거래내역서 → 거래내역 파싱
보고서 요청 → 활동 보고서 생성
납부 요청 → 납부 매칭
```

하지만 실제 운영 흐름에서는 먼저 “어떤 활동과 관련된 요청인가?”를 판단해야 한다.

```text
요청/파일 입력
→ 관련 활동이 있는지 판단
→ 기존 활동에 연결하거나 새 활동 생성 제안
→ 그 활동 안에서 보고서, 영수증, 활동비, 첨부 자료 처리
```

이번 Task의 목표는 다음이다.

```text
1. Assistant 요청에 activity_id context 추가
2. 기존 활동 검색 및 연결 후보 추천
3. 활동이 없으면 새 활동 초안 생성 제안
4. 영수증 분석 결과를 활동 증빙으로 연결
5. 활동 보고서 생성을 활동 상세 내부 기능으로 연결
6. 활동비 요청을 참여자 기준 activity_fee 생성으로 연결
7. 활동 상세 페이지에서 AI 작업 실행 시 현재 activity_id 자동 전달
8. Assistant 결과 카드에서 어떤 활동에 연결되었는지 명확히 표시
```

---

## 전제 조건

Task 1~16이 완료되어 있어야 한다.

현재 구현되어 있어야 하는 기능:

```text
- AI 작업실 /assistant
- Assistant Orchestrator
- Intent Router
- 영수증 분석 Agent
- 활동 보고서 생성 Agent
- 거래내역서 파서
- 납부 매칭 및 직접 수정
- Activities 목록
- /activities/{id} 활동 상세 컨트롤 센터
- 활동 참여자 관리
- 활동비 activity_fee 생성
- 활동별 영수증/첨부 연결 구조
- Payments 회비/활동비 탭
- Members 상세 이력
```

---

## 이번 Task 구현 범위

이번 Task에서는 다음을 구현한다.

```text
1. Assistant request schema에 activity_id, activity_mode 추가
2. Assistant response schema에 activity_context 추가
3. Activity Resolver 구현
4. 기존 활동 검색/후보 추천
5. 새 활동 초안 생성 제안
6. 활동 context 기반 intent routing 보강
7. 영수증 분석 결과를 활동에 연결
8. 활동 보고서 생성 결과를 활동에 연결
9. 활동비 요청을 activity_fee 생성으로 연결
10. 첨부 파일을 활동에 연결
11. /assistant 페이지에 활동 선택 옵션 추가
12. /activities/{id}에 “이 활동에서 AI 작업 실행” 영역 추가
13. Assistant 결과 카드에서 활동 연결 상태 표시
14. 활동 후보 선택/새 활동 생성 확인 UX 구현
15. DEMO/README에 activity-aware AI 흐름 추가
```

---

## 이번 Task에서 구현하지 말 것

아래 기능은 이번 Task에서 구현하지 않는다.

```text
- 새로운 Agent 추가
- LLM 기반 완전 자율 계획 Agent
- Notion 연동
- Slack/Telegram 연동
- 로그인/권한 시스템
- 실제 은행 API 연동
- QR/PG 결제 기능
- 기존 영수증 분석 알고리즘 대규모 재작성
- 기존 거래내역서 파서 대규모 재작성
- 기존 납부 매칭 알고리즘 대규모 재작성
```

이번 Task는 기존 Assistant를 활동 중심으로 연결하는 작업이다.

---

# Part A. Activity-aware Assistant 개념

## 1. 핵심 처리 순서

Assistant는 앞으로 다음 순서로 동작한다.

```text
1. activity_id가 요청에 포함되어 있는지 확인
2. 있으면 해당 활동 context 사용
3. 없으면 메시지에서 활동명, 날짜, 장소, 키워드 추출
4. 기존 활동 후보 검색
5. 후보가 명확하면 자동 연결
6. 후보가 애매하면 사용자 확인 요청
7. 후보가 없고 요청이 활동 관련이면 새 활동 초안 생성 제안
8. 활동 context가 결정되면 intent별 작업 실행
```

즉, 기능 분류보다 활동 context 판단이 먼저다.

---

## 2. activity context mode

Assistant response에는 activity_context를 포함한다.

mode 값:

```text
linked
candidate
create_draft
needs_confirmation
none
```

의미:

```text
linked
→ 기존 활동에 바로 연결됨

candidate
→ 연결 가능한 후보 활동이 있음

create_draft
→ 기존 활동이 없어서 새 활동 초안 생성 제안

needs_confirmation
→ 후보가 여러 개이거나 자동 연결이 애매해서 사용자 확인 필요

none
→ 활동과 연결하지 않고 일반 작업으로 처리
```

---

# Part B. Backend Schema 수정

## 1. Assistant request schema 보강

수정 대상:

```text
backend/app/schemas/assistant.py
```

기존 `AssistantExecuteRequest` 또는 multipart form 처리에 다음 필드를 추가한다.

```python
activity_id: UUID | None = None
activity_mode: str = "auto"
create_activity_if_missing: bool = False
```

activity_mode 값:

```text
auto
link_existing
create_new
none
```

의미:

```text
auto
→ Assistant가 활동 연결 여부 판단

link_existing
→ 사용자가 선택한 activity_id 또는 기존 활동 후보 연결 우선

create_new
→ 새 활동 생성 또는 초안 생성 우선

none
→ 활동에 연결하지 않고 일반 작업 실행
```

multipart form 요청에서도 다음 필드를 받을 수 있어야 한다.

```text
activity_id
activity_mode
create_activity_if_missing
```

---

## 2. Assistant response schema 보강

`AssistantExecuteResponse`에 다음 optional 필드를 추가한다.

```python
activity_context: dict | None = None
activity_candidates: list[dict] | None = None
activity_draft: dict | None = None
```

응답 예시:

```json
{
  "intent": "receipt_analysis",
  "confidence": 0.86,
  "activity_context": {
    "mode": "linked",
    "activity_id": "activity-id",
    "activity_title": "5월 AI 스터디",
    "confidence": 0.91
  },
  "activity_candidates": [],
  "activity_draft": null,
  "result_type": "receipt_analysis",
  "requires_confirmation": false,
  "message": "영수증을 5월 AI 스터디 활동 증빙으로 연결했습니다."
}
```

후보가 여러 개인 경우:

```json
{
  "intent": "receipt_analysis",
  "activity_context": {
    "mode": "needs_confirmation",
    "confidence": 0.54
  },
  "activity_candidates": [
    {
      "id": "activity-id-1",
      "title": "5월 AI 스터디",
      "activity_date": "2026-05-30",
      "location": "동아리방",
      "score": 0.72
    },
    {
      "id": "activity-id-2",
      "title": "AI 프로젝트 회의",
      "activity_date": "2026-05-31",
      "location": "온라인",
      "score": 0.66
    }
  ],
  "requires_confirmation": true,
  "message": "연결할 활동 후보를 선택해 주세요."
}
```

새 활동 초안 생성 제안:

```json
{
  "activity_context": {
    "mode": "create_draft",
    "confidence": 0.78
  },
  "activity_draft": {
    "title": "신입 부원 OT",
    "activity_date": "2026-05-31",
    "location": null,
    "description": "신입 부원 OT 활동으로 추정됩니다."
  },
  "requires_confirmation": true,
  "message": "관련 활동을 찾지 못했습니다. 새 활동으로 생성할까요?"
}
```

---

# Part C. Activity Resolver 구현

## 1. 파일 추가

다음 파일을 추가한다.

```text
backend/app/agents/activity_resolver.py
```

역할:

```text
Assistant 요청에서 활동 context를 결정한다.
```

주요 함수 예시:

```python
resolve_activity_context(
    db: Session,
    message: str | None,
    files: list[Any] | None,
    activity_id: UUID | None,
    activity_mode: str = "auto",
    create_activity_if_missing: bool = False,
) -> ActivityResolutionResult
```

---

## 2. ActivityResolutionResult 구조

간단한 dataclass 또는 Pydantic model로 구현한다.

필드:

```text
mode
activity_id
activity_title
confidence
candidates
draft
reason
```

mode:

```text
linked
candidate
create_draft
needs_confirmation
none
```

---

## 3. 기존 activity_id 우선 처리

요청에 activity_id가 있으면 해당 활동을 조회한다.

동작:

```text
- activity_id가 존재하면 linked
- activity_id가 존재하지 않으면 404 또는 needs_confirmation
```

응답:

```text
mode = linked
confidence = 1.0
```

---

## 4. 메시지 기반 활동 후보 검색

activity_id가 없으면 메시지에서 다음 정보를 사용해 기존 활동을 검색한다.

```text
활동명 키워드
날짜
장소
카테고리 키워드
사용자 요청에 포함된 명사
```

검색 기준:

```text
- title 부분 일치
- activity_date 근접
- location 부분 일치
- description 부분 일치
```

복잡한 벡터 검색은 구현하지 않는다.

이번 Task에서는 SQL LIKE 또는 단순 점수 기반으로 충분하다.

---

## 5. 후보 점수 계산

간단한 scoring 방식으로 구현한다.

예시:

```text
title match +0.5
date match +0.2
location match +0.1
category keyword match +0.1
recent activity +0.1
```

기준:

```text
score >= 0.75 and 후보 1개 → linked
0.45 <= score < 0.75 또는 후보 여러 개 → needs_confirmation
score < 0.45 and 활동 관련 요청 → create_draft
그 외 → none
```

정확한 수치는 구현 상황에 맞게 조정 가능하다.

---

## 6. 새 활동 초안 생성

기존 활동 후보가 없고 요청이 활동 관련이면 새 활동 초안을 만든다.

활동 관련 키워드 예시:

```text
활동
스터디
회의
OT
행사
MT
공모전
세미나
모임
교육
발표
워크숍
```

activity_draft 필드:

```json
{
  "title": "추정 활동명",
  "activity_date": "YYYY-MM-DD 또는 null",
  "location": "string 또는 null",
  "description": "string"
}
```

초안은 자동 저장하지 않는다.

사용자가 확인해야 저장한다.

---

# Part D. Assistant Orchestrator 수정

## 1. 수정 대상

```text
backend/app/agents/assistant_orchestrator.py
backend/app/agents/intent_router.py
backend/app/routers/assistant.py
```

---

## 2. 처리 순서 변경

기존:

```text
Intent Router
→ Agent 실행
```

수정 후:

```text
Activity Resolver
→ Intent Router
→ activity_context 기반 Agent 실행
→ 결과를 activity에 연결
```

---

## 3. intent router 보강

활동비 관련 intent를 추가한다.

새 intent:

```text
activity_fee_generate
activity_link
activity_create
```

기존 intent:

```text
receipt_analysis
bank_statement_import
payment_matching
activity_report_generate
unknown
```

활동비 intent 키워드:

```text
활동비
참가비
회비 말고 활동비
참여자 기준
비용 걷어
돈 걷어
납부 대상 만들어
```

예시:

```text
"이 활동 참가비 10000원 걷어줘"
→ activity_fee_generate

"참여자 기준으로 활동비 납부 대상 만들어줘"
→ activity_fee_generate

"이 영수증 5월 AI 스터디 증빙으로 연결해줘"
→ receipt_analysis + activity_context linked
```

---

# Part E. 활동 연결별 작업 처리

## 1. 영수증 분석

activity_context가 linked이면 영수증 분석 결과를 해당 활동에 연결한다.

동작:

```text
1. 영수증 이미지 분석
2. receipt row 생성 또는 preview 반환
3. activity_id 또는 activity_report_id 필드에 연결
4. 활동 상세의 증빙 탭에서 보이도록 처리
```

필요 API/서비스:

```text
receipt.activity_id 또는 receipt.activity_report_id
```

프로젝트가 activity_report_id를 사용하면 그 필드명을 사용한다.

---

## 2. 활동 보고서 생성

activity_context가 linked이면 해당 활동 정보를 보고서 생성 입력에 포함한다.

포함 정보:

```text
활동명
활동일
장소
카테고리
참여자
첨부 파일명
사용자 메모
레퍼런스 보고서
```

결과:

```text
- 해당 활동의 report/generated_content 또는 final_content에 연결
- 활동 상세의 보고서 탭에서 확인 가능
```

activity_context가 none이면 기존 일반 보고서 생성 흐름을 유지한다.

---

## 3. 첨부 파일 연결

activity_id가 있는 요청에서 파일이 업로드되면 파일 metadata에 활동 연결 정보를 저장한다.

가능한 필드:

```text
uploaded_files.activity_id
uploaded_files.activity_report_id
```

이미 구현된 파일 모델에 연결 필드가 없으면 최소 보강하거나 TODO를 남긴다.

---

## 4. 활동비 생성

intent가 `activity_fee_generate`이고 activity_context가 linked이면 참여자 기준으로 activity_fee payment_records를 생성한다.

요구사항:

```text
- 메시지에서 금액 추출
- 금액 추출 실패 시 requires_confirmation=true로 금액 입력 요청
- 참여자 목록 기준으로 생성
- payment_type = activity_fee
- required_amount = 추출 금액
- status = unpaid
```

응답 예시:

```json
{
  "intent": "activity_fee_generate",
  "result_type": "activity_fee_generation_result",
  "activity_context": {
    "mode": "linked",
    "activity_id": "activity-id",
    "activity_title": "5월 AI 스터디"
  },
  "result": {
    "created_count": 8,
    "updated_count": 0,
    "amount": 10000
  },
  "detail_url": "/activities/activity-id",
  "message": "참여자 8명 기준으로 활동비 납부 대상을 생성했습니다."
}
```

---

## 5. 활동이 없는 경우

활동 관련 요청인데 기존 활동이 없으면 바로 기능을 실행하지 않는다.

예:

```text
"오늘 신입 부원 OT 했고 사진이랑 영수증 올릴게. 보고서도 만들어줘."
```

응답:

```text
관련 활동을 찾지 못했습니다.
새 활동을 먼저 생성한 뒤 업로드 자료를 연결할 수 있습니다.
```

activity_draft를 반환한다.

프론트에서 “새 활동 생성 후 계속” 버튼을 제공한다.

---

# Part F. Backend API 추가

## 1. Assistant activity confirmation API

후보 활동을 사용자가 선택하거나 새 활동 초안을 생성하기 위한 API를 추가한다.

선택 구현 방식은 둘 중 하나다.

### 방식 A: 기존 /api/assistant/execute에 재요청

프론트가 선택한 activity_id를 다시 넣고 execute를 호출한다.

권장:

```text
복잡한 별도 confirm API 없이 기존 execute 재사용
```

### 방식 B: 별도 confirm API

필요하면 추가한다.

```http
POST /api/assistant/confirm-activity
```

이번 Task에서는 방식 A를 우선한다.

---

## 2. 새 활동 생성 API 재사용

Task 16에서 구현된 활동 생성 API를 재사용한다.

```http
POST /api/activities
```

activity_draft를 사용자가 확인하면 이 API로 활동을 생성한다.

생성 후 새 activity_id를 Assistant execute에 다시 전달한다.

---

# Part G. Frontend /assistant 수정

## 1. 활동 선택 옵션 추가

수정 대상:

```text
frontend/app/assistant/page.tsx
frontend/lib/api.ts
frontend/components/assistant/*
```

`/assistant` 입력 카드에 활동 연결 옵션을 추가한다.

UI:

```text
활동 연결
- 자동 감지
- 기존 활동 선택
- 새 활동으로 만들기
- 활동에 연결하지 않음
```

기존 활동 선택 시 select 표시:

```text
활동 선택 select
```

필요 API:

```text
GET /api/activities
```

---

## 2. 요청 전송 필드

FormData에 다음을 포함한다.

```text
activity_id
activity_mode
create_activity_if_missing
```

---

## 3. 결과 카드에 activity_context 표시

Assistant 결과 카드에서 활동 연결 상태를 표시한다.

표시 예시:

```text
연결된 활동: 5월 AI 스터디
```

후보가 있을 경우:

```text
연결할 활동을 선택해 주세요.
[5월 AI 스터디] [AI 프로젝트 회의]
```

새 활동 초안이 있을 경우:

```text
새 활동으로 생성할까요?

활동명: 신입 부원 OT
활동일: 2026-05-31
장소: 미정

[새 활동 생성 후 계속]
```

---

## 4. 새 활동 생성 후 계속

activity_draft가 반환되면 버튼을 제공한다.

동작:

```text
1. POST /api/activities로 새 활동 생성
2. 생성된 activity_id를 사용해 Assistant 요청 재실행
3. 결과를 새 활동에 연결
```

---

# Part H. /activities/{id} 내부 AI 실행

## 1. 활동 상세 AI 실행 영역 추가

수정 대상:

```text
frontend/app/activities/[id]/page.tsx
```

활동 상세 페이지에 간단한 AI 실행 영역을 추가한다.

표시:

```text
이 활동에서 AI 작업 실행
```

입력:

```text
메모/요청 textarea
파일 업로드
실행 버튼
```

동작:

```text
- activity_id를 자동으로 FormData에 포함
- activity_mode = link_existing
- Assistant execute 호출
- 결과를 현재 활동 상세에 표시
```

예시 요청:

```text
이 사진과 메모로 보고서 작성해줘
이 영수증을 이 활동 증빙으로 연결해줘
참여자 기준으로 활동비 10000원 납부 대상 만들어줘
```

---

## 2. 활동 상세 새로고침

AI 실행 후 활동 상세 정보를 새로고침한다.

갱신 대상:

```text
보고서
활동비
영수증
첨부
체크리스트
```

---

# Part I. Activity-aware 결과 카드

## 1. 결과 타입 추가

필요 시 result_type을 추가한다.

```text
activity_candidate
activity_draft
activity_linked_result
activity_fee_generation_result
```

---

## 2. Agent flow 표시

결과 카드에 Activity Resolver 단계를 포함한다.

예시:

```text
Activity Resolver
→ FileParser Agent
→ Classifier Agent
→ Policy Agent
→ Publisher Agent
```

보고서 생성:

```text
Activity Resolver
→ Classifier Agent
→ Post Agent
→ Publisher Agent
```

활동비 생성:

```text
Activity Resolver
→ Budget Agent
→ Publisher Agent
```

---

# Part J. 데모 시나리오 업데이트

README 또는 DEMO 문서에 Activity-aware Assistant 데모를 추가한다.

데모 흐름:

```text
1. Activities에서 활동 생성
2. 활동 상세에서 AI 실행
3. "이 사진과 메모로 보고서 작성해줘"
4. 보고서 탭에 결과 연결 확인
5. "이 영수증을 이 활동 증빙으로 연결해줘"
6. 증빙 탭에 영수증 연결 확인
7. "참여자 기준으로 활동비 10000원 만들어줘"
8. 활동비 탭과 Payments 활동비 탭에서 확인
9. /assistant에서 활동명만 입력해도 기존 활동 후보 추천 확인
10. 활동이 없을 경우 새 활동 초안 생성 확인
```

---

# 실행 검증

## Backend

```bash
cd backend
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

## 시나리오 1. activity_id 직접 전달

```text
1. /activities/{id} 접속
2. AI 실행 영역에서 “이 사진과 메모로 보고서 작성해줘” 입력
3. activity_id가 Assistant에 전달되는지 확인
4. 보고서 결과가 해당 활동에 연결되는지 확인
```

## 시나리오 2. 기존 활동 후보 검색

```text
1. /assistant 접속
2. “5월 AI 스터디 영수증 증빙으로 정리해줘” 입력
3. 기존 활동 후보가 검색되는지 확인
4. 후보 선택 후 영수증이 해당 활동에 연결되는지 확인
```

## 시나리오 3. 새 활동 초안 생성

```text
1. /assistant 접속
2. “오늘 신입 부원 OT 했고 사진이랑 영수증 올릴게. 보고서도 만들어줘.” 입력
3. 기존 활동이 없으면 activity_draft가 생성되는지 확인
4. 새 활동 생성 후 계속 동작 확인
```

## 시나리오 4. 활동비 생성

```text
1. /activities/{id} 접속
2. “참여자 기준으로 활동비 10000원 납부 대상 만들어줘” 입력
3. 참여자 기준 activity_fee payment_records 생성 확인
4. 활동 상세 활동비 탭과 /payments?tab=activity_fee에서 확인
```

## 시나리오 5. 일반 요청 유지

```text
1. /assistant 접속
2. 활동 연결하지 않음 선택
3. 일반 영수증 분석 실행
4. 기존 기능이 깨지지 않는지 확인
```

---

## 완료 기준

Task 17은 다음을 모두 만족해야 완료로 본다.

```text
1. Assistant request에 activity_id/activity_mode가 추가됨
2. Assistant response에 activity_context가 포함됨
3. Activity Resolver가 구현됨
4. activity_id가 있으면 해당 활동에 바로 연결됨
5. activity_id가 없으면 기존 활동 후보를 검색함
6. 후보가 애매하면 사용자 확인을 요청함
7. 관련 활동이 없으면 새 활동 초안을 제안함
8. 영수증 분석 결과를 활동 증빙으로 연결할 수 있음
9. 활동 보고서 생성 결과를 활동에 연결할 수 있음
10. 첨부 파일을 활동에 연결할 수 있음
11. 활동비 요청으로 activity_fee 납부 대상 생성 가능
12. /assistant에서 활동 선택/자동 감지/새 활동 생성/연결 안 함 옵션 제공
13. /activities/{id}에서 AI 실행 시 activity_id가 자동 전달됨
14. Assistant 결과 카드에 Activity Resolver flow가 표시됨
15. 기존 activity_id 없는 일반 요청이 계속 동작함
16. README 또는 DEMO 문서에 Activity-aware Assistant 데모가 추가됨
17. frontend build 성공
18. backend compile/test 성공
19. 이번 Task에서 신규 Agent, Notion, Slack, 로그인 기능은 구현하지 않음
```

---

## 작업 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
Task 17 완료 보고

1. 생성/수정한 주요 파일
- ...

2. Activity-aware Assistant schema
- request:
- response:
- activity_context:

3. Activity Resolver
- activity_id 직접 연결:
- 기존 활동 검색:
- 후보 추천:
- 새 활동 초안:

4. Assistant Orchestrator 변경
- 처리 순서:
- intent router 보강:
- activity_context 기반 실행:

5. 활동 연결 처리
- 영수증:
- 보고서:
- 첨부:
- 활동비:

6. Frontend /assistant 변경
- 활동 선택 옵션:
- 후보 선택 UX:
- 새 활동 생성 후 계속:
- 결과 카드:

7. /activities/{id} AI 실행 영역
- activity_id 자동 전달:
- 실행 결과 반영:
- 상세 새로고침:

8. 실행 검증 결과
- backend compile/test:
- frontend build:
- activity_id 직접 전달:
- 기존 활동 후보:
- 새 활동 초안:
- 활동비 생성:
- 일반 요청 유지:

9. 이번 Task에서 의도적으로 구현하지 않은 기능
- ...

10. Git 상태 및 권장 커밋 메시지
- git status 결과:
- 권장 커밋 메시지:
  task17: make assistant activity aware
```
