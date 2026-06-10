from __future__ import annotations

from datetime import time
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import NotificationRule


DEFAULT_ACTIVITY_NOTIFICATION_RULES: list[dict[str, Any]] = [
    {
        "key": "default_activity_photo_missing",
        "name": "활동 사진 누락 알림",
        "reminder_type": "activity_photo_missing",
        "target_scope": "activity",
        "enabled": True,
        "channel": "gmail",
        "send_time": time(9, 0),
        "days_after": 2,
        "repeat_interval_days": 2,
        "max_send_count": 3,
        "require_confirm_before_send": True,
        "template_subject": "[ClubAgent] 활동 사진 업로드 필요: {{activity_title}}",
        "template_body": (
            "{{activity_title}} 활동의 활동 사진이 아직 업로드되지 않았습니다.\n\n"
            "활동일: {{activity_date}}\n"
            "기준: 활동 종료 후 {{days_after}}일 경과\n"
            "필요 작업: 활동 상세 > 증빙 탭에서 활동 사진을 업로드해주세요.\n\n"
            "바로가기:\n{{target_url}}"
        ),
    },
    {
        "key": "default_activity_upcoming",
        "name": "활동 전날 알림",
        "reminder_type": "activity_upcoming",
        "target_scope": "activity",
        "enabled": True,
        "channel": "gmail",
        "send_time": time(9, 0),
        "days_before": 1,
        "max_send_count": 1,
        "require_confirm_before_send": True,
        "template_subject": "[ClubAgent] 내일 활동 예정: {{activity_title}}",
        "template_body": (
            "{{activity_title}} 활동이 내일 예정되어 있습니다.\n\n"
            "활동일: {{activity_date}}\n"
            "장소: {{location}}\n\n"
            "바로가기:\n{{target_url}}"
        ),
    },
    {
        "key": "default_activity_report_missing",
        "name": "활동 보고서 미작성 알림",
        "reminder_type": "activity_report_missing",
        "target_scope": "activity",
        "enabled": True,
        "channel": "gmail",
        "send_time": time(9, 0),
        "days_after": 2,
        "repeat_interval_days": 2,
        "max_send_count": 3,
        "require_confirm_before_send": True,
        "template_subject": "[ClubAgent] 활동 보고서 작성 필요: {{activity_title}}",
        "template_body": (
            "{{activity_title}} 활동 보고서가 아직 작성되지 않았습니다.\n\n"
            "활동일: {{activity_date}}\n"
            "기준: 활동 종료 후 {{days_after}}일 경과\n\n"
            "바로가기:\n{{target_url}}"
        ),
    },
    {
        "key": "default_activity_evidence_missing",
        "name": "활동 증빙 누락 알림",
        "reminder_type": "activity_evidence_missing",
        "target_scope": "activity",
        "enabled": True,
        "channel": "gmail",
        "send_time": time(9, 0),
        "days_after": 2,
        "repeat_interval_days": 2,
        "max_send_count": 3,
        "require_confirm_before_send": True,
        "template_subject": "[ClubAgent] 활동 증빙 업로드 필요: {{activity_title}}",
        "template_body": (
            "{{activity_title}} 활동에 연결된 증빙이 없습니다.\n\n"
            "활동일: {{activity_date}}\n"
            "기준: 활동 종료 후 {{days_after}}일 경과\n\n"
            "바로가기:\n{{target_url}}"
        ),
    },
]


def ensure_default_notification_rules(db: Session) -> int:
    created = 0
    for default in DEFAULT_ACTIVITY_NOTIFICATION_RULES:
        key = default["key"]
        existing = db.scalar(
            select(NotificationRule).where(
                or_(
                    NotificationRule.reminder_type == default["reminder_type"],
                    NotificationRule.name == default["name"],
                    NotificationRule.conditions.op("->>")("default_rule_key") == key,
                )
            )
        )
        if existing is not None:
            continue

        payload = {k: v for k, v in default.items() if k != "key"}
        payload["conditions"] = {
            "default_rule_key": key,
            "recipient_name": "운영진",
        }
        db.add(NotificationRule(**payload))
        created += 1

    if created:
        db.commit()
    return created


def try_ensure_default_notification_rules(db: Session) -> int:
    try:
        return ensure_default_notification_rules(db)
    except SQLAlchemyError:
        db.rollback()
        return 0
