# Task 40. 재무/활동 상태 연결성 점검 및 HWPX 출력 안정화

현재 프로젝트는 ClubAgent입니다.

Task 38~39를 진행하면서 예산 관리 페이지, 회비 관리, 활동비, 거래내역, 플로팅 챗봇 구조가 추가되었습니다.

이번 Task 40의 목표는 새 기능 추가가 아니라, 현재 구현된 기능들의 연결성을 다시 점검하고 상태 기준을 통일하는 것입니다.

현재 문제:
1. 예산 관리 페이지의 처리 필요 항목에 회비 미납이 사람별로 너무 많이 표시되어 다른 중요한 항목이 가려짐
2. 회비 미납은 상시 관리 항목인데 처리 필요 항목에 개별 row로 쌓이는 구조가 부적절함
3. 활동비를 완납 처리했는데 예산 관리나 활동 현황에서 갑자기 확인 필요로 보이는 상태 불일치가 있음
4. 활동 상세, 예산 관리, 거래내역, 회비 화면이 같은 데이터를 서로 다르게 해석하는 경우가 있음
5. HWPX 생성 문서에서 활동 내용이 표 안에서 겹치거나 한 줄로 밀려서 읽기 어려움
6. 전체적으로 target_url, 상태 계산, source of truth 기준을 다시 검토해야 함

---

# 1. 예산 관리 처리 필요 항목 정리

현재 예산 관리 페이지의 처리 필요 항목에 회비 미납이 개별 사람 단위로 많이 표시됩니다.

수정 전:
- 회비 미납
- 회비 미납
- 회비 미납
- 회비 미납
- ...

수정 후:
회비 미납은 처리 필요 항목에서 개별 row로 보여주지 마세요.

회비 미납은 별도 섹션 또는 요약 카드로 분리하세요.

권장 구조:

예산 관리 페이지
1. 재무 요약 카드
2. 받을 돈 요약
   - 회비 미납: 90명 / 1,300,000원
   - 활동비 미납: n건 / n원
3. 처리 필요 항목
   - 확인 필요 거래
   - 미분류 거래
   - 증빙 누락
   - 예산 초과
   - 활동비 상태 불일치
   - 환불 필요
4. 활동별 정산 현황
5. 거래 검토/수동 분류

회비 미납은 다음처럼 보여주세요.

회비 미납 요약:
- 미납 인원: 90명
- 미납 금액: 1,300,000원
- 버튼: 회비 화면에서 관리
- 링크: /payments

처리 필요 항목에는 회비 미납을 사람별로 넣지 않습니다.

단, 다음 경우는 처리 필요 항목에 남겨도 됩니다.
- 회비 PaymentRecord가 없는 부원이 있음
- 회비 금액 정책이 적용되지 않음
- paid_amount와 status가 불일치
- 동명이인/중복 PaymentRecord가 있음
- need_check 상태가 있음

즉, 일반 unpaid는 “회비 관리 대상”이고, 데이터 오류나 확인 필요 상태만 “처리 필요 항목”입니다.

---

# 2. 활동비 상태 일관성 수정

현재 활동비를 완납 처리했는데 예산 관리 또는 활동 상세에서 확인 필요로 보이는 문제가 있습니다.

activity_fee 상태의 source of truth를 명확히 하세요.

activity_fee 상태 기준:
required_amount = 0 → exempt 또는 대상 아님
required_amount > 0 and paid_amount = 0 → unpaid
0 < paid_amount < required_amount → partial
paid_amount == required_amount → paid
paid_amount > required_amount → overpaid

확인 필요 need_check는 다음 경우에만 사용하세요.
1. 금액이 맞지 않는데 자동 판단이 어려움
2. 동명이인 매칭 후보가 있음
3. 거래는 있으나 대상자 확정이 안 됨
4. 관리자가 직접 확인 필요로 지정함

다음 경우에는 need_check로 바뀌면 안 됩니다.
1. paid_amount == required_amount
2. status = paid로 수동 확정된 경우
3. 활동비 납부 현황에서 완납 처리 완료된 경우
4. matched_transaction_id가 있고 금액이 정확히 일치하는 경우

수정 대상:
- 활동 상세 > 활동비 탭
- 예산 관리 > 활동별 정산 현황
- 예산 관리 > 처리 필요 항목
- Dashboard 처리 필요 항목
- 챗봇 활동비 상태 답변
- 감사 체크리스트
- 감사자료 패키지 preview

모든 곳에서 activity_fee 상태를 같은 service 함수로 계산하도록 정리하세요.

권장:
backend/app/services/payment_status_service.py

함수 예시:
calculate_payment_status(required_amount, paid_amount, manual_status=None)
get_membership_fee_status(record)
get_activity_fee_status(record)

중복 계산 로직을 화면/서비스마다 따로 두지 마세요.

---

# 3. 상태/링크 연결성 점검

다음 링크 정책을 전체 코드에서 다시 점검하세요.

membership_fee:
- 회비 미납, 회비 완납, 회비 대상 생성
- target_url: /payments

activity_fee:
- 활동비 미납, 활동비 완납, 활동비 확인 필요
- target_url: /activities/{activity_id}?tab=activity-fee

evidence:
- 증빙 누락, 영수증 연결 필요
- target_url: /activities/{activity_id}?tab=evidence

activity report:
- 보고서 미작성, HWPX 미생성
- target_url: /activities/{activity_id}?tab=report

audit package:
- 감사자료 누락
- target_url: /activities/{activity_id}?tab=files 또는 감사자료 섹션

budget:
- 예산 초과, 미분류 거래
- target_url: /budget 또는 /transactions

중요:
activity_fee는 절대 /payments로 보내지 마세요.
membership_fee는 활동 상세 활동비 탭으로 보내지 마세요.

---

# 4. 예산 관리 review item 재정의

Budget review item을 다음 기준으로 정리하세요.

처리 필요 항목에 포함할 것:
1. 미분류 거래
2. 확인 필요 거래
3. 금액 불일치 거래
4. 증빙 없는 지출
5. 환불 필요
6. 예산 초과 항목
7. 활동비 상태 불일치
8. PaymentRecord 누락
9. 중복 PaymentRecord
10. 영수증 분석 실패

처리 필요 항목에서 제외할 것:
1. 일반 회비 미납자 개별 row
2. 일반 활동비 미납자 개별 row가 너무 많은 경우

대신 활동비 미납은 활동별 요약으로 표시하세요.

예:
활동비 미납 활동 2개
- 위퍼퓸 교내조향활동: 2명 / 20,000원
- 시향 활동: 1명 / 10,000원

회비 미납은 별도 카드로 표시하세요.

예:
회비 미납 90명 / 1,300,000원
[회비 화면에서 관리]

---

# 5. HWPX 활동 내용 겹침 수정

현재 생성된 HWPX에서 활동 내용이 표 안에서 한 줄로 겹치거나 셀 안에서 제대로 줄바꿈되지 않는 문제가 있습니다.

현재 문제:
- 활동 내용이 긴 문장 하나로 들어가 표 셀 안에서 겹쳐 보임
- 문단 분리가 제대로 되지 않음
- 기존 템플릿의 예시 문단이 남아 있거나 새 문단과 겹칠 수 있음
- 실제 /data 밑의 템플릿으로 검증이 충분하지 않음

수정 목표:
HWPX 생성 시 활동 내용은 문장/줄 단위로 자연스럽게 들어가야 합니다.
표 셀 안에서 겹치지 않아야 합니다.
기존 템플릿 문단은 제거되고, 새 문단만 남아야 합니다.

반드시 /data 밑에 있는 실제 한글 템플릿 파일을 사용해서 검증하세요.

수정 정책:
1. 활동 내용은 하나의 긴 text run으로 넣지 말 것
2. 줄바꿈 기준으로 여러 paragraph를 생성
3. 긴 문장은 적절히 분리
4. 표 셀 안의 기존 paragraph 전체를 제거한 뒤 새 paragraph를 삽입
5. paragraph clone 시 원본 paragraph style을 유지
6. 셀 내부 여백/문단 높이/줄 간격을 보존
7. 기존 예시 텍스트가 남지 않게 할 것
8. 텍스트 박스나 absolute positioned object와 겹치지 않게 할 것

활동 내용 입력 예:
6월 3일에 A401호에서 교내 조향활동을 진행하였다.
참여자 기준으로 활동비 1만원 납부 대상을 생성하였다.
명단도 추가하고 활동 보고서를 작성하였다.

HWPX 출력 기대:
- 각 문장이 별도 줄 또는 별도 문단으로 표시
- 표 셀 안에서 겹치지 않음
- 기존 템플릿 예시 문구 제거
- 한글에서 열었을 때 읽을 수 있음

수정 대상:
backend/app/services/hwpx_generation_service.py
backend/app/services/document_generation_service.py
backend/tests/test_hwpx_generation_layout.py

가능하면 실제 템플릿 기반 테스트 추가:
backend/tests/test_hwpx_generation_with_data_templates.py

검증:
1. /data 하위 템플릿 파일을 사용해 HWPX 생성
2. 생성된 HWPX 압축 해제
3. section XML에서 기존 예시 문구 제거 여부 확인
4. 활동 내용 paragraph 수 확인
5. 긴 활동 내용이 하나의 run으로만 들어가지 않는지 확인
6. 가능하면 실제 한글에서 열어 육안 검증

---

# 6. 전체 연결성 점검표 작성

이번 Task에서 주요 기능 연결성을 표로 점검하세요.

점검 대상:
1. Dashboard
2. Budget 예산 관리
3. Payments 회비
4. Transactions 거래내역
5. Activities 활동 목록
6. Activity Detail 활동비
7. Activity Detail 증빙
8. Activity Detail 보고서/HWPX
9. Audit Package
10. Floating Chatbot

점검 항목:
- 같은 count를 쓰는가
- 같은 status 계산을 쓰는가
- 같은 target_url 정책을 쓰는가
- activity_fee와 membership_fee가 분리되는가
- 수동 처리 결과가 다른 화면에 반영되는가
- 거래 매칭 결과가 다른 화면에 반영되는가
- 삭제/비활성 데이터가 집계에서 제외되는가

간단한 문서나 주석 형태로 남겨도 됩니다.

---

# 7. 테스트

추가 또는 보강 테스트:

backend/tests/test_budget_review_items_policy.py
backend/tests/test_payment_status_consistency.py
backend/tests/test_activity_fee_status_consistency.py
backend/tests/test_navigation_target_urls.py
backend/tests/test_hwpx_generation_with_data_templates.py

필수 테스트:
1. 일반 회비 미납자는 budget review item에 개별 row로 들어가지 않음
2. 회비 미납 요약은 budget summary에 포함됨
3. activity_fee paid_amount == required_amount이면 paid
4. paid 상태 activity_fee가 budget에서 need_check로 바뀌지 않음
5. activity_fee target_url은 /activities/{id}?tab=activity-fee
6. membership_fee target_url은 /payments
7. 증빙 누락 target_url은 /activities/{id}?tab=evidence
8. HWPX 활동 내용이 여러 paragraph로 들어감
9. HWPX 기존 템플릿 예시 내용이 남지 않음
10. Payment status 계산이 Dashboard/Budget/Activity Detail에서 일치

---

# 8. 브라우저 검증

1. 예산 관리 페이지 접속
2. 처리 필요 항목에서 회비 미납 개별 row가 사라졌는지 확인
3. 회비 미납은 별도 요약 카드/섹션에서 확인
4. 회비 미납 버튼 클릭 시 /payments 이동 확인
5. 활동비 미납 버튼 클릭 시 활동 상세 활동비 탭 이동 확인
6. 활동 상세에서 활동비 완납 처리
7. 예산 관리로 돌아와 해당 활동이 확인 필요로 잘못 표시되지 않는지 확인
8. Dashboard에서도 활동비 상태가 일치하는지 확인
9. HWPX 생성
10. 한글에서 열어 활동 내용이 겹치지 않는지 확인
11. 긴 활동 내용으로 다시 생성해도 겹치지 않는지 확인

---

# 완료 기준

1. 예산 관리 처리 필요 항목에 회비 미납자가 개별 row로 대량 표시되지 않는다.
2. 회비 미납은 별도 요약 카드/섹션으로 분리된다.
3. 활동비 완납 상태가 Budget/Dashboard/Activity Detail에서 일관되게 보인다.
4. activity_fee와 membership_fee의 링크 정책이 전역에서 일치한다.
5. HWPX 활동 내용이 겹치지 않는다.
6. 실제 /data 템플릿 기반 검증이 추가된다.
7. pytest 통과
8. npm run build 통과

---

# 완료 보고 형식

Task 40 완료 보고

1. 원인
- 회비 미납이 처리 필요 항목에 대량 표시되던 이유:
- 활동비 완납 후 확인 필요로 바뀌던 이유:
- HWPX 활동 내용이 겹치던 이유:

2. 수정 파일
- backend:
- frontend:
- tests:

3. 예산 관리 정리
- 회비 미납 분리:
- 처리 필요 항목 재정의:
- 활동비 미납 요약:

4. 상태 일관성
- membership_fee:
- activity_fee:
- payment_status_service:
- Dashboard/Budget/Activity Detail 동기화:

5. 링크 정책
- 회비:
- 활동비:
- 증빙:
- 보고서:
- 예산:

6. HWPX 수정
- 실제 /data 템플릿:
- paragraph 분리:
- 기존 문단 제거:
- 겹침 방지:

7. 검증
- pytest:
- npm run build:
- browser:
- HWPX 한글 열기 검증:

권장 커밋 메시지:
task40: align finance status flows and stabilize hwpx layout