# Task 33. 전체 데모 시나리오 E2E 검증 및 AI 명령 안정화

현재 프로젝트는 ClubAgent입니다.

Task 32까지 진행하면서 다음 구조가 어느 정도 정리되었습니다.

```text
1. 부원 명단 전용 업로드
2. 임원/회장/부회장/일반 부원 분리
3. 가입 시기 기반 회비 산정
4. 회비와 활동비 도메인 분리
5. 활동 참가자 import
6. 활동 내부 활동비 관리
7. 거래내역 기반 회비/활동비 매칭
8. HWPX 활동 내역서 생성
9. 활동비 거래 매칭 제외 기능
10. Human-in-the-loop 확인 후 반영 구조
```

이번 Task 33의 목표는 새 기능을 크게 추가하는 것이 아니라, **실제 데모 시나리오가 처음부터 끝까지 끊기지 않게 검증하고, AI 자연어 명령이 올바른 기능으로 연결되는지 안정화**하는 것입니다.

---

# 현재 문제

현재 기능은 개별적으로는 구현되었지만, 실제 사용 흐름에서는 다음 문제가 남아 있을 수 있습니다.

```text
1. AI가 자연어 명령을 잘못된 intent로 보내는 경우
2. 회비/활동비/거래내역 매칭이 실제 브라우저 흐름에서 꼬이는 경우
3. confirm 후 화면 refetch가 안 되어 반영 여부가 바로 안 보이는 경우
4. activity_id / payment_type / period scope가 일부 API에서 누락되는 경우
5. HWPX 생성, 활동비 매칭, 회비 매칭이 각각 따로는 되지만 데모 전체 흐름에서는 끊기는 경우
6. 오류가 나도 UI에서 원인을 알기 어려운 경우
```

---

# 핵심 목표

Task 33에서는 다음 전체 시나리오를 안정화합니다.

```text
DB 초기화
→ 부원 명단 업로드
→ 회비 대상 생성
→ 회비 거래내역 매칭
→ 활동 생성
→ 활동 참가자 명단 업로드
→ 활동비 대상 생성
→ 활동비 거래내역 매칭
→ 영수증/증빙 연결
→ HWPX 활동 내역서 생성
→ 파일함에서 결과 확인
```

이 흐름이 실제 브라우저에서 가능해야 합니다.

---

# Part A. E2E 데모 시나리오 정의

다음 시나리오를 기준으로 검증하세요.

## 1. 부원/회비 시나리오

```text
1. DB 초기화
2. Members 페이지에서 /data/26년 1학기 Oui parfum.xlsx 업로드
3. Preview 확인
4. 확인 후 반영
5. Members 목록에서 전체 인원 수 확인
6. 임원/회장/부회장/일반 부원 분리 확인
7. Payments 또는 회비 화면으로 이동
8. current_term=2026-1 기준 회비 대상 생성 preview
9. 신규 15,000원 / 기존 10,000원 / 임원 0원 확인
10. 확인 후 반영
11. 회비 현황에서 각 금액과 상태 확인
```

## 2. 회비 거래내역 매칭 시나리오

```text
1. 거래내역 업로드
2. 회비 화면에서 거래내역 매칭 실행
3. required_amount와 deposit_amount exact match만 자동 후보인지 확인
4. 3,737원 같은 불일치 금액은 amount_mismatch로 표시
5. 확인 후 반영
6. matched record만 paid 처리
7. 불일치 record는 미납/확인 필요로 유지
```

## 3. 활동/활동비 시나리오

```text
1. 활동 생성
2. 활동 상세 진입
3. 참가자 명단/신청서 업로드
4. 기존 Members와 매칭 preview
5. 확인 후 활동 참가자로 반영
6. 활동비 탭에서 1인당 활동비 설정
7. 활동 참가자 기준 activity_fee 대상 생성
8. 활동비 요약 카드 확인
9. 거래내역에서 이 활동 활동비 매칭 실행
10. 현재 activity_id의 activity_fee만 매칭되는지 확인
11. 금액 exact match만 자동 후보인지 확인
12. 확인 후 반영
13. membership_fee가 바뀌지 않는지 확인
```

## 4. 문서/HWPX 시나리오

```text
1. 활동 보고서 본문 작성
2. HWPX 템플릿 선택
3. 생성 전 preview 확인
4. HWPX 생성
5. 파일함 저장 확인
6. 다운로드 후 열기
7. 활동 내용이 중복되지 않는지 확인
8. 참여자 명단이 표 형태로 들어갔는지 확인
9. 템플릿 예시값이 남지 않는지 확인
```

---

# Part B. AI 자연어 명령 검증

아래 명령이 실제 브라우저에서 올바른 intent와 결과 카드로 연결되는지 확인하고, 안 되는 부분을 수정하세요.

## 회비 명령

```text
전체 회비 완납 처리해줘
현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘
이번 학기 회비 대상 생성해줘
거래내역에서 회비 납부 확인해줘
미납자 확인해줘
```

기대 결과:

```text
- membership_fee 도메인으로 처리
- activity_fee 수정 금지
- 30,000원 legacy 문구 금지
- preview 후 confirm 구조
```

## 활동비 명령

활동 상세 내부에서:

```text
이 활동 활동비 대상 생성해줘
이 거래내역으로 활동비 매칭해줘
참가자들 활동비 입금 확인해줘
박민서 활동비 25000원 냈어
```

기대 결과:

```text
- 현재 activity_id 기준 activity_fee만 처리
- membership_fee 수정 금지
- 거래 금액 exact match
- preview 후 confirm 구조
```

전역 AI에서:

```text
활동비 매칭해줘
활동비 완납 처리해줘
```

기대 결과:

```text
- 바로 실행하지 않음
- 어떤 활동인지 물어봄
```

## 활동/문서 명령

```text
이 명단 참여자로 넣어줘
이 활동 보고서 초안 만들어줘
HWPX 생성해줘
이 영수증을 현재 활동 증빙으로 연결해줘
```

기대 결과:

```text
- 현재 activity_id가 필요한 작업은 activity_id 확인
- preview 또는 확인 후 반영 구조 유지
- 파일함/증빙/문서 결과 refetch
```

---

# Part C. AI Command Diagnostics 추가

AI가 어떤 intent로 처리했는지 UI와 로그에서 확인 가능해야 합니다.

AI 결과 카드 또는 개발용 collapse 영역에 다음을 표시하세요.

```text
intent
domain
scope
activity_id
payment_type
requires_confirmation
action_id
service_called
```

예시:

```text
intent: bulk_membership_fee_mark_paid
domain: membership_fee
scope: term
payment_type: membership_fee
requires_confirmation: true
```

이 정보는 일반 사용자에게 과하게 보일 필요는 없지만, 디버깅을 위해 접기/펼치기로 볼 수 있게 하세요.

---

# Part D. Confirm 후 Refetch 안정화

확인 후 반영을 눌렀는데 화면이 그대로이면 사용자가 실패로 느낍니다.

다음 작업 후 반드시 관련 데이터를 refetch하세요.

```text
부원 import confirm → Members 목록 refetch
회비 생성 confirm → 회비 현황 refetch
회비 매칭 confirm → 회비 현황 + dashboard refetch
활동 참가자 import confirm → 참가자 목록 refetch
활동비 생성 confirm → 활동비 현황 refetch
활동비 매칭 confirm → 활동비 현황 refetch
영수증 연결 confirm → 증빙/파일함 refetch
HWPX 생성 confirm → 파일함/문서 목록 refetch
```

---

# Part E. 오류 메시지 개선

API 실패나 검증 실패 시 빈 화면/조용한 실패가 나오면 안 됩니다.

다음 경우에 명확한 메시지를 보여주세요.

```text
activity_id가 필요한데 없음
회비/활동비가 모호함
PaymentRecord가 없음
거래내역이 없음
매칭 가능한 거래가 없음
HWPX 템플릿이 없음
파일 다운로드 실패
confirm action이 만료됨
```

예시:

```text
활동비 작업을 실행하려면 먼저 활동을 선택해야 합니다.
현재 활동에 활동비 납부 대상이 없습니다. 활동비 대상을 먼저 생성해주세요.
거래내역이 없습니다. 먼저 거래내역을 업로드해주세요.
```

---

# Part F. Test / E2E Seed 추가

가능하면 E2E 테스트용 fixture 또는 script를 추가하세요.

권장 파일:

```text
backend/tests/test_demo_e2e_flow.py
backend/tests/test_assistant_command_browser_scenarios.py
backend/app/scripts/demo_seed.py
```

`demo_seed.py`는 선택입니다.
다만 있으면 브라우저 검증이 빨라집니다.

데모용 데이터:

```text
- 3명 부원
  - 신규 부원 1명
  - 기존 부원 1명
  - 임원 1명
- 활동 1개
- 참가자 2명
- 회비 record
- 활동비 record
- 거래내역 몇 개
  - exact match
  - amount mismatch
  - unrelated transaction
```

---

# Part G. 테스트 요구사항

추가 또는 보강:

```text
backend/tests/test_demo_e2e_flow.py
backend/tests/test_assistant_command_intent_matrix.py
backend/tests/test_confirm_refetch_contract.py
backend/tests/test_domain_scope_safety.py
```

필수 테스트:

```text
1. 전체 회비 완납 명령이 bulk_membership_fee_mark_paid로 감
2. 활동비 전역 요청은 clarification 반환
3. 활동 상세 활동비 요청은 현재 activity_id로 처리
4. 회비 매칭은 membership_fee만 수정
5. 활동비 매칭은 현재 activity_id activity_fee만 수정
6. confirm 없이 DB가 변경되지 않음
7. confirm 후 관련 상태가 changed result로 반환됨
8. HWPX 생성 결과 file_id가 반환됨
```

---

# Part H. 완료 기준

Task 33은 다음을 만족해야 완료입니다.

```text
1. 전체 데모 흐름이 브라우저에서 끊기지 않는다.
2. AI 자연어 명령이 기대 intent로 라우팅된다.
3. 회비/활동비/거래내역/문서 작업의 domain과 scope가 명확하다.
4. confirm 후 화면이 즉시 갱신된다.
5. 실패 시 명확한 오류 메시지가 표시된다.
6. legacy 30,000원 같은 과거 흔적이 AI 결과에 나오지 않는다.
7. 활동비 전역 요청은 활동 선택을 요구한다.
8. 활동 상세 요청은 현재 activity_id만 처리한다.
9. pytest 통과
10. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 33 완료 보고

1. 원인
- 전체 흐름이 끊기던 원인:
- AI 명령이 실패하던 원인:
- refetch가 부족했던 위치:

2. 수정한 파일
- backend:
- frontend:
- tests:
- scripts:

3. E2E 시나리오 검증
- 부원:
- 회비:
- 거래내역:
- 활동:
- 활동비:
- HWPX:

4. AI 명령 검증
- 회비:
- 활동비:
- 거래내역:
- 문서:

5. Diagnostics
- intent:
- domain:
- scope:
- action_id:

6. Refetch/UX
- confirm 후 갱신:
- 오류 메시지:

7. 검증 결과
- pytest:
- npm run build:
- browser:

권장 커밋 메시지:
task33: stabilize demo e2e flow and assistant command execution
```
