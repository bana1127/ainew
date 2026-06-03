# Task 32. HWPX 제출 양식 레이아웃 안정화 + 활동비 거래 매칭 제외 기능

현재 프로젝트는 ClubAgent입니다.

Task 31까지 진행하면서 부원 관리, 활동 관리, 회비, 활동비, 거래내역, 활동 내부 활동비 탭 구조를 정리했습니다.

이번 Task 32의 목표는 두 가지입니다.

```text
1. HWPX 활동 내역서 생성 결과가 제출용 양식에 맞게 깨지지 않도록 안정화
2. 활동 내부 활동비 거래내역 매칭 시 특정 거래를 제외할 수 있는 기능 추가
```

---

# Part A. HWPX 제출 양식 레이아웃 안정화

## 현재 문제

현재 HWPX 생성은 값은 들어가지만 제출용 문서로 보기에는 아직 문제가 있습니다.

문제:

```text
1. 활동 내용이 한 칸 안에 길게 들어가면서 아래 영역과 겹침
2. 활동 내용이 중복 삽입되는 경우가 있음
3. 참여자 명단이 표 칸에 정확히 들어가지 않음
4. 이름/학과/학번/서명/비고 칸이 깨지거나 붙어 보임
5. 내용이 길면 다음 영역으로 밀려서 레이아웃이 무너짐
6. 생성된 HWPX가 제출용 양식으로 쓰기 어려움
```

이번 Task에서는 HWPX 완전 편집기를 만들지 않습니다.
목표는 **기존 제출용 HWPX 템플릿에 활동 정보, 활동 내용, 참여자 명단이 깨지지 않게 들어가도록 안정화**하는 것입니다.

---

## 실제 템플릿 기준 검증

반드시 `/data`에 있는 실제 템플릿으로 검증하세요.

```text
/data/Oui Parfum_20250000_교내 활동 참여.hwpx
```

또는 현재 프로젝트에 저장된 동일 템플릿 파일을 사용하세요.

단순 테스트용 XML만으로 검증하지 마세요.
실제 HWPX를 생성하고 다운로드해서 열어보는 브라우저 검증까지 해야 합니다.

---

## 1. 활동 내용 자동 요약/길이 제한

활동 내용이 너무 길면 템플릿 칸을 넘어가서 겹칩니다.

따라서 HWPX 생성 시 제출용 본문은 별도 요약본을 사용하세요.

우선순위:

```text
1. 사용자가 직접 작성한 final_content
2. AI generated_content
3. activity.description
```

다만 HWPX에 넣을 때는 그대로 길게 넣지 말고, 제출 양식에 맞는 길이로 정리합니다.

권장 형식:

```text
본 활동은 교내 조향 체험을 중심으로 진행되었으며, 참여자들이 향료를 직접 조합하고 결과를 공유하는 방식으로 운영되었습니다. 활동을 통해 조향에 대한 이해를 높이고 구성원 간 교류를 증진하였습니다.
```

규칙:

```text
1. HWPX용 본문은 2~4문장 정도로 제한
2. 너무 긴 참석자 전체 나열은 활동 내용에 넣지 않음
3. 참석자는 참여자 명단 표에서 관리
4. 번호 항목 1~8 전체를 그대로 넣지 않음
5. 줄 수가 많으면 레이아웃이 깨지므로 짧은 문단으로 변환
```

---

## 2. 활동 내용 중복 삽입 제거

현재 활동 내용이 두 번 들어가는 문제가 있습니다.

수정 요구:

```text
1. 활동 내용은 실제 제출 양식의 활동 내용 칸에만 한 번 삽입
2. 문서 상단 정보 영역에 report_body 전체를 삽입하지 않음
3. "활동 내용" 라벨이 여러 번 있어도 본문 삽입 대상은 하나만 선택
4. 생성 결과에서 같은 본문이 2번 이상 나오면 실패
```

검증:

```text
생성된 HWPX에서 활동 본문 핵심 문장이 1회만 등장해야 함
```

---

## 3. 참여자 명단 표 삽입 안정화

참여자 명단은 반드시 표 구조로 들어가야 합니다.

기본 표 구조:

```text
이름 | 학과 | 학번 | 서명 | 비고
```

요구사항:

```text
1. header row는 유지
2. 참여자 수만큼 row 생성
3. 각 row에는 최소 5개 cell이 있어야 함
4. 이름은 이름 cell
5. 학과는 학과 cell
6. 학번은 학번 cell
7. 서명 cell은 비워둠
8. 비고 cell은 외부인 또는 특이사항이 있을 때만 입력
9. 한 cell에 "이주현 / 2022130026"처럼 넣지 않음
10. participant list를 | 로 join하지 않음
```

참여자가 많아 한 페이지에 다 들어가지 않으면 다음 중 가능한 방식으로 처리하세요.

```text
1. 표 row가 자연스럽게 다음 페이지로 넘어가도록 처리
2. page break를 허용
3. HWPX 구조가 어려우면 참여자 명단 전용 섹션을 별도 생성
```

---

## 4. 참여인원 총 n명 표시

기존 문구:

```text
참여인원 총 00명
```

생성 결과:

```text
참여인원 총 19명
```

참여자 수는 현재 activity participants 기준으로 계산하세요.

```text
cancelled 제외
deleted/inactive 제외
외부인 포함 여부는 현재 activity participant 목록 기준
```

---

## 5. 템플릿 예시값 제거

생성 결과에 다음 값이 남아 있으면 실패입니다.

```text
2025.00.00
종합관 앞
참여인원 총 00명
동아리 홍보전에 참여하여
이하 생략
```

단, 템플릿 정책상 "이하 생략"을 일부러 유지해야 하는 경우는 제외할 수 있지만, 참여자 명단이 실제로 들어간 경우에는 제거하는 것을 권장합니다.

---

## 6. 생성 전 Preview 보강

HWPX 생성 전 preview에서 다음을 표시하세요.

```text
활동명
활동 일시
활동 장소
활동 분류
활동 내용 요약
참여자 수
참여자 명단 row 수
템플릿 모드
레이아웃 경고
```

레이아웃 경고 예시:

```text
활동 내용이 길어 제출 양식용으로 요약됩니다.
참여자 19명이 표에 삽입됩니다.
```

---

## 7. HWPX 생성 후 검증

생성 후 helper로 내부 텍스트를 추출해서 최소 검증하세요.

검증 항목:

```text
1. 활동 장소가 실제 값으로 들어갔는지
2. 활동 일시가 실제 값으로 들어갔는지
3. 참여인원 총 n명이 들어갔는지
4. 템플릿 예시값이 남아 있지 않은지
5. 활동 내용이 중복되지 않는지
6. 참여자 이름과 학번이 포함되는지
```

가능하면 XML 구조도 검증하세요.

```text
1. participant row 수가 참여자 수와 맞는지
2. participant row에 cell이 5개 이상 있는지
3. 이름과 학번이 같은 cell에 들어가지 않았는지
```

---

# Part B. 활동 내부 거래 매칭 시 제외 기능 추가

## 현재 문제

활동 상세 > 활동비 탭에서 거래내역 매칭을 할 때, 특정 거래를 제외할 수 있는 기능이 없습니다.

실제 사용 중에는 다음과 같은 거래가 있을 수 있습니다.

```text
1. 활동비와 관계없는 입금
2. 잘못 입금된 금액
3. 이미 다른 목적으로 처리한 거래
4. 동명이인이지만 해당 활동과 무관한 거래
5. 테스트용 거래
```

이런 거래를 매번 매칭 후보에 계속 띄우면 사용성이 떨어집니다.

---

## 목표

활동 내부 활동비 거래 매칭 preview에서 특정 거래를 제외할 수 있게 하세요.

제외 범위는 우선 **해당 활동의 활동비 매칭에서만 제외**하는 것으로 구현합니다.

```text
transaction_id + activity_id + payment_type=activity_fee
```

즉, 어떤 거래를 특정 활동의 활동비 매칭에서 제외하더라도, 다른 회비 매칭이나 다른 활동 매칭에서는 필요하면 사용할 수 있어야 합니다.

---

## 1. 제외 기능 UI

활동비 거래 매칭 preview row에 다음 버튼을 추가하세요.

```text
[이 거래 제외]
```

또는 row action 메뉴 안에 추가하세요.

```text
더보기
- 이 거래 제외
```

제외 시 확인 모달:

```text
이 거래를 현재 활동의 활동비 매칭 후보에서 제외하시겠습니까?
이 작업은 현재 활동의 활동비 매칭에만 적용됩니다.
```

---

## 2. 제외된 거래 표시

제외된 거래는 기본 preview 후보에서 숨깁니다.

다만 사용자가 볼 수 있도록 다음 옵션을 제공하세요.

```text
[제외된 거래 보기]
```

제외된 거래 목록에서는 다음 작업을 제공하세요.

```text
[제외 해제]
```

---

## 3. Backend 저장 방식

권장 모델 또는 테이블:

```text
transaction_match_exclusions
```

필드 예시:

```text
id
transaction_id
activity_report_id nullable
payment_type
reason nullable
created_at
created_by nullable
is_active
```

이번 Task에서는 사용자 계정이 없다면 created_by는 생략해도 됩니다.

중복 방지:

```text
transaction_id + activity_report_id + payment_type
```

이미 제외된 거래를 다시 제외하려 하면 중복 row를 만들지 말고 기존 row를 유지하거나 is_active=true로 갱신하세요.

---

## 4. 제외 적용 범위

활동비 매칭 preview 생성 시 다음 조건을 제외하세요.

```text
transaction_id가 transaction_match_exclusions에 있고
activity_report_id = 현재 activity_id
payment_type = activity_fee
is_active = true
```

이 조건에 해당하면 matching 후보에서 제외합니다.

단, 회비 매칭에서는 제외하지 않습니다.

---

## 5. 제외 해제 API

다음 API를 구현하거나 기존 API에 추가하세요.

```http
POST /api/activities/{activity_id}/activity-fees/transactions/{transaction_id}/exclude
POST /api/activities/{activity_id}/activity-fees/transactions/{transaction_id}/include
GET /api/activities/{activity_id}/activity-fees/excluded-transactions
```

또는 REST 스타일에 맞게 구현하세요.

---

## 6. Preview Summary에 제외 건수 표시

활동비 매칭 preview summary에 다음을 추가하세요.

```text
excluded_transactions: n
```

UI 예시:

```text
자동 매칭 후보 8건
금액 불일치 2건
이름 확인 필요 3건
제외된 거래 4건
```

---

## 7. AI 연동

활동 내부 AI에서 다음 자연어도 처리할 수 있으면 좋습니다.

```text
이 거래는 활동비 매칭에서 제외해줘
방금 후보 중 김성래 3737원 거래는 제외해줘
제외한 거래 다시 보여줘
```

복잡하면 이번 Task에서는 UI 버튼만 구현해도 됩니다.

단, AI가 구현되어 있다면 반드시 현재 activity_id 범위에서만 처리하세요.

---

# Backend 수정 대상

```text
backend/app/routers/activities.py
backend/app/services/activity_fee_transaction_matching_service.py
backend/app/models/payment.py
backend/app/schemas/payment.py
backend/alembic/versions/*
```

필요하면 신규 모델:

```text
backend/app/models/transaction_match_exclusion.py
backend/app/services/transaction_match_exclusion_service.py
```

---

# Frontend 수정 대상

```text
frontend/app/activities/[id]/page.tsx
frontend/lib/api.ts
frontend/components/assistant/AssistantResultCard.tsx
```

가능하면 컴포넌트 분리:

```text
ActivityFeeMatchPreview
ExcludedTransactionsPanel
```

---

# 테스트

추가 또는 보강:

```text
backend/tests/test_hwpx_generation_layout_stability.py
backend/tests/test_hwpx_generation_real_template.py
backend/tests/test_activity_fee_transaction_exclusion.py
```

필수 테스트:

## HWPX

```text
1. 실제 템플릿으로 HWPX 생성
2. 활동 내용이 중복 삽입되지 않음
3. 템플릿 예시값이 제거됨
4. 참여인원 총 n명이 반영됨
5. 참여자 이름과 학번이 포함됨
6. "이름 / 학번" 형태로 한 셀에 들어가지 않음
```

## 거래 제외

```text
1. 특정 transaction을 activity_fee 매칭에서 exclude
2. 같은 activity_id + payment_type=activity_fee preview에서 해당 거래가 제외됨
3. excluded 목록에서 조회 가능
4. include 처리 후 다시 preview 후보에 나타남
5. 회비 membership_fee 매칭에는 영향을 주지 않음
6. 다른 activity_id의 activity_fee 매칭에는 영향을 주지 않음
7. 같은 transaction exclude를 두 번 해도 중복 row가 생기지 않음
```

---

# 브라우저 검증

## HWPX

```text
1. 활동 상세 > 보고서 탭
2. 실제 템플릿 선택
3. HWPX 생성
4. 다운로드 후 열기
5. 확인:
   - 활동 내용이 칸을 넘어서 겹치지 않음
   - 활동 내용이 중복되지 않음
   - 참여자 명단이 표 형태로 보임
   - 참여인원 총 n명이 표시됨
   - 템플릿 예시값이 남아 있지 않음
```

## 거래 제외

```text
1. 활동 상세 > 활동비 탭
2. 거래내역 매칭 preview 실행
3. 특정 거래 row에서 [이 거래 제외] 클릭
4. preview 재실행
5. 해당 거래가 후보에서 사라졌는지 확인
6. [제외된 거래 보기]에서 확인
7. [제외 해제] 클릭
8. preview 재실행
9. 해당 거래가 다시 후보로 나타나는지 확인
```

---

# 완료 기준

```text
1. HWPX 활동 내용이 제출 양식 칸을 깨지 않도록 요약/제한된다.
2. 활동 내용이 중복 삽입되지 않는다.
3. 참여자 명단이 표 구조로 안정적으로 들어간다.
4. 템플릿 예시값이 남지 않는다.
5. HWPX 생성 전 preview에 레이아웃 경고가 표시된다.
6. 활동비 거래 매칭 preview에서 특정 거래를 제외할 수 있다.
7. 제외된 거래는 해당 activity_id의 activity_fee 매칭에서 숨겨진다.
8. 제외 해제하면 다시 후보로 나타난다.
9. 제외 기능은 회비 매칭과 다른 활동 매칭에 영향을 주지 않는다.
10. pytest 통과
11. npm run build 통과
```

---

# 완료 보고 형식

```text
Task 32 완료 보고

1. 원인
- HWPX 레이아웃 깨짐 원인:
- 활동 내용 중복 삽입 원인:
- 거래 매칭 제외 기능 부재 원인:

2. 수정한 파일
- backend:
- frontend:
- migration:
- tests:

3. HWPX 안정화
- 내용 요약:
- 중복 제거:
- 참여자 표:
- 템플릿 예시값 제거:
- preview warning:

4. 거래 제외 기능
- 모델/API:
- exclude:
- include:
- excluded list:
- matching preview 반영:

5. Scope 보호
- activity_id:
- payment_type=activity_fee:
- membership_fee 영향 없음:
- 다른 activity 영향 없음:

6. 검증
- 실제 HWPX 다운로드:
- 거래 제외:
- 제외 해제:
- pytest:
- npm run build:

권장 커밋 메시지:
task32: stabilize hwpx output and add activity fee transaction exclusions
```
