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
당신은 대학교 동아리 활동 보고서를 작성하는 전문가입니다.
주어진 정보를 바탕으로 공식적인 한국어 활동 보고서를 작성해 주세요.

다음 JSON 형식으로 응답하세요:
{
  "title": "활동 보고서 제목",
  "summary": "한 문장 요약",
  "content": "전체 보고서 본문 (활동명, 활동 일시, 활동 장소, 참석자, 활동 목적, 주요 내용, 활동 결과, 향후 계획 포함)",
  "missing_fields": ["누락된 필드명 리스트"],
  "confidence": 0.85
}
"""


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
        if not payload.input_text:
            missing_fields.append("input_text")

        # Title
        base_title = payload.title or "활동"
        if base_title.endswith(" 활동 보고서"):
            title = base_title
        else:
            title = base_title + " 활동 보고서"

        # Summary
        category = payload.category_name or "활동"
        main_body = payload.input_text or payload.title or "활동"
        summary = f"{category}을(를) 통해 {main_body}을(를) 진행하였다."

        # Content fields
        date_str = payload.activity_date or "미정"
        location_str = payload.location or "미정"
        names_str = (
            ", ".join(payload.participant_names)
            if payload.participant_names
            else "미정"
        )

        # Purpose: derived from category and title
        purpose_text = (
            f"{category} 분야에서 '{base_title}' 활동을 진행하여 "
            "부원들의 역량 강화 및 공동체 의식을 높이고자 하였습니다."
        )

        # Main content body
        if payload.input_text:
            main_content = payload.input_text
        else:
            main_content = f"'{base_title}'에 관한 활동을 계획에 따라 진행하였습니다."

        if payload.reference_content:
            main_content += (
                f"\n\n[참고 자료 활용]\n다음 자료를 참고하여 활동을 진행하였습니다:\n{payload.reference_content}"
            )

        if payload.file_names:
            files_str = ", ".join(payload.file_names)
            main_content += f"\n\n[첨부 파일]\n{files_str}"

        # Result
        result_text = (
            f"'{base_title}' 활동을 성공적으로 완료하였습니다. "
            f"총 {len(payload.participant_names)}명의 부원이 참석하여 활동에 적극적으로 참여하였으며, "
            "계획된 목표를 달성하였습니다."
            if payload.participant_names
            else f"'{base_title}' 활동을 완료하였으며 계획된 목표를 달성하였습니다."
        )

        # Future plan
        future_text = (
            f"향후 '{category}' 관련 활동을 지속적으로 기획하고, "
            "이번 활동의 경험을 바탕으로 더욱 발전된 프로그램을 운영할 예정입니다."
        )

        content = (
            f"활동명: {base_title}\n"
            f"활동 일시: {date_str}\n"
            f"활동 장소: {location_str}\n"
            f"참석자: {names_str}\n\n"
            f"활동 목적:\n{purpose_text}\n\n"
            f"주요 내용:\n{main_content}\n\n"
            f"활동 결과:\n{result_text}\n\n"
            f"향후 계획:\n{future_text}"
        )

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

        participant_names_str = (
            ", ".join(payload.participant_names) if payload.participant_names else ""
        )
        file_names_str = (
            ", ".join(payload.file_names) if payload.file_names else ""
        )

        user_prompt_lines = [
            "다음 정보를 바탕으로 활동 보고서를 작성해 주세요:",
            "",
            f"- 카테고리/분야: {payload.category_name or ''}",
            f"- 활동 제목: {payload.title or ''}",
            f"- 활동 일자: {payload.activity_date or ''}",
            f"- 활동 장소: {payload.location or ''}",
            f"- 참석자: {participant_names_str}",
            f"- 활동 내용 요약 (입력): {payload.input_text or ''}",
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
