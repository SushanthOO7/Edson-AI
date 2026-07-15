import json
from typing import Any

from app.domains.servicenow.prompts import FIELD_PROMPTS
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
        current_field_values: dict[str, str] | None = None,
        recent_ai_outputs: dict[str, str] | None = None,
        similar_examples: list[dict[str, Any]] | None = None,
    ) -> str:
        fields = target_fields or [
            "short_description",
            "description",
            "additional_comments",
            "work_notes",
        ]
        payload = {
            "task": "generate_single_field" if target_fields and len(target_fields) == 1 else "generate_all_fields",
            "target_fields": fields,
            "ticket_context": ticket_context,
            "current_field_values": current_field_values or {},
            "recent_ai_outputs": recent_ai_outputs or {},
            "user_instruction": user_instruction,
            "field_rules": {field: FIELD_PROMPTS[field] for field in fields if field in FIELD_PROMPTS},
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
        current_field_values: dict[str, str] | None = None,
        recent_ai_outputs: dict[str, str] | None = None,
    ) -> str:
        payload = {
            "task": "revise_single_field",
            "ticket_number": ticket_number,
            "field_name": field_name,
            "current_value": current_field_value,
            "user_instruction": revision_instruction,
            "ticket_context": ticket_context,
            "current_field_values": current_field_values or {},
            "recent_ai_outputs": recent_ai_outputs or {},
            "field_rules": {field_name: FIELD_PROMPTS[field_name]} if field_name in FIELD_PROMPTS else {},
            "current_user": {
                "name": current_user.name,
                "role": current_user.role,
                "team": current_user.team,
                "signature": current_user.signature,
            },
            "team_rules": team_rules,
        }
        return json.dumps(payload, indent=2, ensure_ascii=True)
