import json
import re
from typing import Any

from app.domains.servicenow.schemas import TicketContext


class TicketContextBuilder:
    @classmethod
    def normalize(cls, context: TicketContext) -> dict[str, Any]:
        more_information = cls._clean_text(context.more_information) or cls._clean_text(context.additional_details)
        campus = cls._split_name_and_code(cls._clean_text(context.campus) or cls._clean_text(context.location))
        building = cls._split_name_and_code(cls._clean_text(context.building))
        room = cls._clean_text(context.room_number) or cls._clean_text(context.room)

        ticket = {
            "number": cls._clean_text(context.number),
            "type": cls._clean_text(context.ticket_type),
            "current_short_description": cls._clean_text(context.current_short_description),
            "current_description": cls._clean_text(context.current_description),
            "current_additional_comments": cls._clean_text(context.current_additional_comments),
            "current_work_notes": cls._clean_text(context.current_work_notes),
            "more_information": more_information,
            "additional_details": cls._clean_text(context.additional_details) or more_information,
            "campus": campus,
            "building": building,
            "room": room,
            "requester": {"name": cls._clean_text(context.requested_for)},
            "item": cls._clean_text(context.item),
            "location": cls._clean_text(context.location),
        }
        return {
            "ticket": cls._drop_empty(ticket),
            "recent_activity": cls._parse_recent_activity(context.recent_activity),
            "conversation": cls._build_conversation_context(context.recent_activity),
        }

    @classmethod
    def current_field_values(cls, context: TicketContext) -> dict[str, str]:
        return {
            "short_description": cls._clean_text(context.current_short_description),
            "description": cls._clean_text(context.current_description),
            "additional_comments": cls._clean_text(context.current_additional_comments),
            "work_notes": cls._clean_text(context.current_work_notes),
        }

    @classmethod
    def _parse_recent_activity(cls, recent_activity: str | None) -> list[dict[str, str]]:
        value = cls._clean_text(recent_activity)
        if not value:
            return []
        structured = cls._parse_structured_activity(value)
        if structured:
            return structured
        chunks = [chunk.strip() for chunk in re.split(r"\n{2,}", value) if chunk.strip()]
        if not chunks:
            chunks = [value]
        return [
            {
                "type": cls._infer_activity_type(chunk),
                "author": "",
                "text": chunk[:1000],
            }
            for chunk in chunks[-5:]
        ]

    @classmethod
    def _build_conversation_context(cls, recent_activity: str | None) -> dict[str, Any]:
        entries = cls._parse_recent_activity(recent_activity)
        if not entries:
            return {}

        comments = [entry for entry in entries if entry.get("type") == "additional_comments"]
        work_notes = [entry for entry in entries if entry.get("type") == "work_notes"]
        latest_visible = comments[0] if comments else entries[0]
        previous_visible = comments[1] if len(comments) > 1 else None

        return cls._drop_empty(
            {
                "activity_order": "newest_first",
                "latest_visible_activity": latest_visible,
                "previous_visible_activity": previous_visible,
                "latest_work_note": work_notes[0] if work_notes else None,
                "instruction": (
                    "Use latest_visible_activity as the strongest signal for the next customer-facing reply. "
                    "If the latest requester message answers a previous technician question, acknowledge it and move to the next logical step."
                ),
            }
        )

    @classmethod
    def _parse_structured_activity(cls, value: str) -> list[dict[str, str]]:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict) or payload.get("format") != "servicenow_activity_v1":
            return []
        entries = payload.get("entries")
        if not isinstance(entries, list):
            return []

        parsed_entries: list[dict[str, str]] = []
        for entry in entries[:12]:
            if not isinstance(entry, dict):
                continue
            text = cls._clean_text(str(entry.get("text") or ""))
            if not text:
                continue
            parsed_entries.append(
                cls._drop_empty(
                    {
                        "type": cls._clean_text(str(entry.get("type") or "activity")),
                        "author": cls._clean_text(str(entry.get("author") or "")),
                        "timestamp": cls._clean_text(str(entry.get("timestamp") or "")),
                        "text": text[:1200],
                        "display_order": str(entry.get("display_order", "")),
                    }
                )
            )
        return parsed_entries

    @staticmethod
    def _infer_activity_type(value: str) -> str:
        lowered = value.lower()
        if "work note" in lowered:
            return "work_notes"
        if "comment" in lowered:
            return "additional_comments"
        return "activity"

    @classmethod
    def _split_name_and_code(cls, value: str) -> dict[str, str]:
        if not value:
            return {}
        match = re.search(r"\(([A-Z0-9-]+)\)", value)
        code = match.group(1).strip() if match else ""
        name = re.sub(r"\s*\([A-Z0-9-]+\)\s*", " ", value).strip()
        return cls._drop_empty({"name": name, "code": code})

    @classmethod
    def _clean_text(cls, value: str | None) -> str:
        if not value:
            return ""
        cleaned = re.sub(r"\s+", " ", value).strip()
        if re.fullmatch(r"[0-9a-f]{32}", cleaned, flags=re.IGNORECASE):
            return ""
        return cleaned

    @classmethod
    def _drop_empty(cls, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in payload.items()
            if value not in ("", None, {}, [])
        }
