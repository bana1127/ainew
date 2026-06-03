from __future__ import annotations
import json
from dataclasses import dataclass, field


@dataclass
class ActivityReportGenerationPayload:
    category_name: str | None = None
    report_template: str | None = None
    title: str = ""
    activity_date: str | None = None
    location: str | None = None
    participant_names: list[str] = field(default_factory=list)
    input_text: str | None = None
    reference_content: str | None = None
    file_names: list[str] = field(default_factory=list)


@dataclass
class ReceiptAnalysisPayload:
    file_name: str = ""
    file_path: str | None = None  # absolute path string for real mode
    mime_type: str | None = None
    manual_payment_method: str | None = None
    manual_category: str | None = None


_SYSTEM_PROMPT = """
당신은 대학교 동아리 활동 내역서를 작성하는 전문가입니다.
주어진 정보를 바탕으로 실제 동아리 활동 내역서 문체에 맞는 간결한 한국어 활동 내용을 작성해 주세요.

[내역서 문체 규칙]
1. 활동 내용은 2~5문장으로 간결하게 작성한다.
2. "~함", "~되었음", "시간을 가짐", "진행함" 중심의 사실 기록형 문체를 사용한다.
3. 활동명, 활동일, 장소, 참여자 수, 활동 분류를 기반으로 자연스러운 내용을 생성한다.
4. 과장된 성과, 장황한 목적 서술, 홍보성 문구를 쓰지 않는다.
5. 반드시 제외: 회비, 활동비, 납부, 명단 등록, 명단 추가, 파일 생성, 매칭, 보고서 만들어줘 등 운영 지시 내용
6. 사용자 요청 문장을 그대로 복사하지 말 것
7. 활동 내용만 작성하고 "향후 계획" 같은 공문서 형식은 쓰지 않는다.

[샘플 문체]
회의: "위퍼퓸 정기 회의를 진행함. 동아리 운영 전반에 대한 논의와 향후 활동 계획을 점검함."
멘토링: "이번 멘토링 활동에서는 향료와 향수들을 직접 맡아보며 다양한 종류의 향을 알아보는 시간을 가짐. 각자 맡아본 향을 기록하고, 자신만의 향수 취향을 공유하며 향수에 대한 이해도를 높였음."
조향/체험: "A401호에서 교내 조향활동을 진행함. 참여자들이 향료와 향수에 대해 알아보고, 직접 시향하며 각자의 취향을 공유하는 시간을 가짐. 이를 통해 향에 대한 이해도를 높이고 동아리원 간의 교류를 도모할 수 있었음."

다음 JSON 형식으로 응답하세요:
{
  "title": "활동 보고서 제목",
  "summary": "한 문장 요약 (~함 문체)",
  "content": "활동 내용 2~5문장 (사실 기록형, 운영 지시 제외)",
  "missing_fields": ["누락된 필드명 리스트"],
  "confidence": 0.85
}
"""

# Keywords indicating operational instructions (not activity content)
_OPERATIONAL_KEYWORDS = [
    "명단 등록", "명단 추가", "명단도", "활동비", "납부 대상", "납부대상", "회비",
    "파일 생성", "hwpx", "보고서 만들어", "업로드", "매칭", "증빙", "영수증 처리",
    "처리해줘", "완납", "미납", "처리해주세요", "만들어줘", "만들어주세요",
    "추가해줘", "추가해주세요", "등록해줘", "등록해주세요", "생성해줘", "생성해주세요",
]


def _filter_operational_instructions(text: str | None) -> str:
    """Remove operational instruction sentences from input text, keeping only activity content."""
    if not text:
        return ""
    import re
    sentences = re.split(r"(?<=[.!?。])\s+|(?<=[.!?。])\n|[.\n]", text)
    result = []
    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        lower_s = s.lower()
        is_operational = any(kw in lower_s for kw in _OPERATIONAL_KEYWORDS)
        if not is_operational:
            result.append(s)
    return " ".join(result).strip()


class LLMService:
    def __init__(self, api_key: str | None, model: str, mock_mode: bool, vision_model: str = ""):
        self.api_key = api_key
        self.model = model
        self.mock_mode = mock_mode
        self.vision_model = vision_model or model  # fallback to model if vision_model empty

    def generate_activity_report(self, payload: ActivityReportGenerationPayload) -> dict:
        if self.mock_mode:
            return self._generate_mock(payload)

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다. "
                "OPENAI_MOCK_MODE=true로 설정하거나 API 키를 제공해 주세요."
            )

        return self._generate_real(payload)

    def _generate_mock(self, payload: ActivityReportGenerationPayload) -> dict:
        missing_fields: list[str] = []

        if not payload.category_name:
            missing_fields.append("category_name")
        if not payload.title:
            missing_fields.append("title")
        if not payload.activity_date:
            missing_fields.append("activity_date")
        if not payload.location:
            missing_fields.append("location")
        if not payload.participant_names:
            missing_fields.append("participant_names")

        base_title = payload.title or "활동"
        category = payload.category_name or ""
        location_str = payload.location or ""
        participant_count = len(payload.participant_names)

        # Title
        if base_title.endswith(" 활동 보고서"):
            title = base_title
        else:
            title = base_title + " 활동 보고서"

        # Filter operational instructions from input
        filtered_input = _filter_operational_instructions(payload.input_text)

        # Determine activity type for style selection
        category_lower = category.lower()
        title_lower = base_title.lower()
        is_meeting = any(k in title_lower or k in category_lower for k in ["회의", "정기", "운영 회의", "임원"])
        is_mentoring = any(k in title_lower or k in category_lower for k in ["멘토링", "스터디", "교육", "강의"])
        is_external = any(k in title_lower or k in category_lower for k in ["협업", "외부", "협찬", "연합"])

        # Build concise 2~5 sentence content in 내역서 style
        location_prefix = f"{location_str}에서 " if location_str else ""
        count_suffix = f" 총 {participant_count}명이 참여함." if participant_count > 0 else ""

        if is_meeting:
            sentences = [
                f"{base_title}을(를) 진행함.",
                "동아리 운영 전반에 대한 논의와 향후 활동 계획을 점검함.",
            ]
            if count_suffix:
                sentences.append(f"총 {participant_count}명이 참석하여 활발한 의견 교환이 이루어졌음.")
        elif is_mentoring:
            sentences = [
                f"이번 {base_title}에서는 관련 내용을 직접 체험하며 알아보는 시간을 가짐.",
                "참여자들이 각자의 경험과 의견을 공유하며 이해도를 높였음.",
                f"이를 통해 동아리원 간의 교류를 도모할 수 있었음.",
            ]
        elif is_external:
            sentences = [
                f"외부 단체와의 협업 활동을 진행함.",
                f"참여자들이 다양한 관점에서 활동을 경험하고, 서로의 의견을 나누는 시간을 가짐.",
                f"이를 통해 동아리원들이 새로운 경험을 쌓고 교류를 강화할 수 있었음.",
            ]
        else:
            sentences = [
                f"{location_prefix}{base_title}을(를) 진행함.",
            ]
            if filtered_input:
                sentences.append(f"참여자들이 관련 활동에 참여하며 다양한 내용을 경험하는 시간을 가짐.")
            sentences.append("이를 통해 동아리원 간의 교류를 도모하고 활동에 대한 이해도를 높였음.")
            if count_suffix and participant_count > 0:
                sentences.append(f"총 {participant_count}명이 참여함.")

        content = " ".join(sentences)

        # Summary (one sentence)
        summary = f"{base_title}을(를) 진행하며 관련 활동에 참여함."

        return {
            "title": title,
            "summary": summary,
            "content": content,
            "missing_fields": missing_fields,
            "confidence": 0.75,
            "model": "mock",
        }

    def _generate_real(self, payload: ActivityReportGenerationPayload) -> dict:
        import openai  # imported here to avoid errors when running in mock mode

        client = openai.OpenAI(api_key=self.api_key)

        # Filter operational instructions before sending to LLM
        filtered_input = _filter_operational_instructions(payload.input_text)

        participant_names_str = (
            f"{len(payload.participant_names)}명" if payload.participant_names else ""
        )
        file_names_str = (
            ", ".join(payload.file_names) if payload.file_names else ""
        )

        user_prompt_lines = [
            "다음 정보를 바탕으로 실제 동아리 활동 내역서 문체(2~5문장, ~함/~되었음/시간을 가짐)로 작성해 주세요.",
            "운영 지시(회비, 활동비, 명단 등록, 파일 생성 등)는 활동 내용에서 제외하세요.",
            "",
            f"- 활동 분류: {payload.category_name or ''}",
            f"- 활동 제목: {payload.title or ''}",
            f"- 활동 일자: {payload.activity_date or ''}",
            f"- 활동 장소: {payload.location or ''}",
            f"- 참여 인원: {participant_names_str}",
            f"- 활동 내용 (참고용): {filtered_input or ''}",
        ]

        if payload.reference_content:
            user_prompt_lines.append(f"- 참고 자료: {payload.reference_content}")

        if file_names_str:
            user_prompt_lines.append(f"- 첨부 파일: {file_names_str}")

        user_prompt = "\n".join(user_prompt_lines)

        try:
            response = client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT.strip()},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except openai.OpenAIError as exc:
            # Re-raise without leaking the API key
            raise RuntimeError(f"OpenAI API 호출 중 오류가 발생했습니다: {exc}") from exc

        raw_content = response.choices[0].message.content or ""

        try:
            parsed: dict = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI 응답 파싱 실패") from exc

        return {
            "title": parsed.get("title", ""),
            "summary": parsed.get("summary", ""),
            "content": parsed.get("content", ""),
            "missing_fields": parsed.get("missing_fields", []),
            "confidence": parsed.get("confidence", 0.0),
            "model": self.model,
        }

    def analyze_receipt(self, payload: ReceiptAnalysisPayload) -> dict:
        if self.mock_mode:
            return self._analyze_receipt_mock(payload)
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. OPENAI_MOCK_MODE=true로 설정하거나 API 키를 제공해 주세요.")
        return self._analyze_receipt_real(payload)

    def _analyze_receipt_mock(self, payload: ReceiptAnalysisPayload) -> dict:
        import re
        fname = payload.file_name.lower()

        # Try to extract amount from filename (first number found)
        amounts = re.findall(r'\d+', fname)
        amount = int(amounts[0]) if amounts else 50000

        # Try to detect payment method from filename keywords
        payment_method = "card"  # default
        if "transfer_student" in fname or "trans_student" in fname:
            payment_method = "transfer_student"
        elif "transfer_company" in fname or "trans_company" in fname:
            payment_method = "transfer_company"
        elif "cash" in fname:
            payment_method = "cash_withdrawal"
        elif "online" in fname:
            payment_method = "online_card"
        elif "recurring" in fname:
            payment_method = "recurring_payment"
        elif "personal" in fname:
            payment_method = "personal_card_reimbursement"
        elif "unknown" in fname:
            payment_method = "unknown"
        elif "card" in fname or "receipt" in fname:
            payment_method = "card"

        # Override with manual if provided
        if payload.manual_payment_method:
            payment_method = payload.manual_payment_method

        category = payload.manual_category or "기타"

        return {
            "receipt_date": "2026-05-30",
            "store_name": "스타벅스",
            "amount": amount,
            "payment_method": payment_method,
            "category": category,
            "raw_text": f"MOCK RECEIPT {payload.file_name} {amount:,}원 {payment_method}",
            "confidence": 0.75,
        }

    def _analyze_receipt_real(self, payload: ReceiptAnalysisPayload) -> dict:
        import openai
        import base64
        from pathlib import Path

        client = openai.OpenAI(api_key=self.api_key)

        RECEIPT_SYSTEM_PROMPT = """
당신은 영수증 분석 전문가입니다. 영수증 이미지 또는 파일 정보를 분석하여 다음 JSON을 반환하세요:
{
  "receipt_date": "YYYY-MM-DD 또는 null",
  "store_name": "string 또는 null",
  "amount": 0,
  "payment_method": "card | online_card | transfer_student | transfer_company | cash_withdrawal | personal_card_reimbursement | recurring_payment | unknown",
  "category": "string 또는 null",
  "raw_text": "인식된 전체 텍스트 또는 null",
  "confidence": 0.0
}
payment_method는 반드시 위 목록 중 하나여야 합니다. amount는 정수여야 합니다.
"""

        messages = [{"role": "system", "content": RECEIPT_SYSTEM_PROMPT.strip()}]

        # Try to include image if file path is available and mime_type is image
        if payload.file_path and payload.mime_type and payload.mime_type.startswith("image/"):
            try:
                file_path = Path(payload.file_path)
                if file_path.exists():
                    b64 = base64.b64encode(file_path.read_bytes()).decode()
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:{payload.mime_type};base64,{b64}"}},
                            {"type": "text", "text": f"파일명: {payload.file_name}\n위 영수증을 분석해 주세요."},
                        ]
                    })
                else:
                    messages.append({"role": "user", "content": f"파일명: {payload.file_name}\n파일을 기반으로 영수증 정보를 추론해 주세요."})
            except Exception:
                messages.append({"role": "user", "content": f"파일명: {payload.file_name}\n파일을 기반으로 영수증 정보를 추론해 주세요."})
        else:
            messages.append({"role": "user", "content": f"파일명: {payload.file_name}\n파일을 기반으로 영수증 정보를 추론해 주세요."})

        try:
            response = client.chat.completions.create(
                model=self.vision_model,
                response_format={"type": "json_object"},
                messages=messages,
            )
        except openai.OpenAIError as exc:
            raise RuntimeError(f"OpenAI API 호출 중 오류가 발생했습니다: {exc}") from exc

        raw_content = response.choices[0].message.content or ""
        try:
            parsed: dict = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI 응답 파싱 실패") from exc

        return {
            "receipt_date": parsed.get("receipt_date"),
            "store_name": parsed.get("store_name"),
            "amount": int(parsed.get("amount", 0)),
            "payment_method": parsed.get("payment_method", "unknown"),
            "category": parsed.get("category"),
            "raw_text": parsed.get("raw_text"),
            "confidence": float(parsed.get("confidence", 0.0)),
        }
