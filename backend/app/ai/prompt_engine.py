import json
from typing import Any

from app.memory.user_memory import UserProfile


class PromptEngine:
    @staticmethod
    def build_generate_fields_query(
        *,
        ticket_context: dict[str, Any],
        target_fields: list[str] | None,
        user_instruction: str,
        current_user: UserProfile,
        team_rules: list[str],
        similar_examples: list[dict[str, Any]] | None = None,
    ) -> str:
        payload = {
            "task": "generate_servicenow_fields",
            "target_fields": target_fields or [
                "short_description",
                "description",
                "additional_comments",
                "work_notes",
            ],
            "ticket_context": ticket_context,
            "user_instruction": user_instruction,
            "current_user": {
                "name": current_user.name,
                "role": current_user.role,
                "team": current_user.team,
                "signature": current_user.signature,
            },
            "team_rules": team_rules,
            "similar_accepted_examples": similar_examples or [],
        }
        return json.dumps(payload, indent=2, ensure_ascii=True)

    @staticmethod
    def build_revise_field_query(
        *,
        ticket_number: str | None,
        field_name: str,
        current_field_value: str,
        revision_instruction: str,
        ticket_context: dict[str, Any],
        current_user: UserProfile,
        team_rules: list[str],
    ) -> str:
        payload = {
            "task": "revise_one_servicenow_field",
            "ticket_number": ticket_number,
            "field_name": field_name,
            "current_field_value": current_field_value,
            "revision_instruction": revision_instruction,
            "ticket_context": ticket_context,
            "current_user": {
                "name": current_user.name,
                "role": current_user.role,
                "team": current_user.team,
                "signature": current_user.signature,
            },
            "team_rules": team_rules,
        }
        return json.dumps(payload, indent=2, ensure_ascii=True)
