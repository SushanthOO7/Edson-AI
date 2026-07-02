import json
import re
from typing import Any


class AIResponseValidationError(ValueError):
    pass


class ResponseValidator:
    GENERATE_KEYS = {
        "short_description",
        "description",
        "additional_comments",
        "work_notes",
        "missing_info",
        "suggested_next_action",
        "confidence",
        "needs_review",
    }
    REVISE_KEYS = {"field_name", "revised_value", "confidence", "needs_review"}

    @classmethod
    def parse_generate_response(cls, raw: Any) -> dict[str, Any]:
        payload = cls._extract_json_payload(raw)
        missing = cls.GENERATE_KEYS - set(payload)
        if missing:
            raise AIResponseValidationError(f"Generate response missing keys: {sorted(missing)}")
        return cls._normalize_generate_payload(payload)

    @classmethod
    def parse_revise_response(cls, raw: Any) -> dict[str, Any]:
        payload = cls._extract_json_payload(raw)
        missing = cls.REVISE_KEYS - set(payload)
        if missing:
            raise AIResponseValidationError(f"Revise response missing keys: {sorted(missing)}")
        return cls._normalize_revise_payload(payload)

    @classmethod
    def _extract_json_payload(cls, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict) and (cls.GENERATE_KEYS <= set(raw) or cls.REVISE_KEYS <= set(raw)):
            return raw

        content = raw
        if isinstance(raw, dict):
            for key in ("response", "answer", "result", "content", "output", "data"):
                if key in raw:
                    content = raw[key]
                    break
            else:
                choices = raw.get("choices")
                if isinstance(choices, list) and choices:
                    content = choices[0].get("message", {}).get("content")

        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise AIResponseValidationError("AI response did not contain JSON content.")

        cleaned = cls._strip_code_fences(content.strip())
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AIResponseValidationError("AI response was not valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise AIResponseValidationError("AI response JSON must be an object.")
        return parsed

    @staticmethod
    def _strip_code_fences(value: str) -> str:
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.DOTALL | re.IGNORECASE)
        return fenced.group(1) if fenced else value

    @classmethod
    def _normalize_generate_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        for key in ("short_description", "description", "additional_comments", "work_notes", "suggested_next_action"):
            normalized[key] = "" if normalized.get(key) is None else str(normalized.get(key))
        missing_info = normalized.get("missing_info")
        normalized["missing_info"] = missing_info if isinstance(missing_info, list) else []
        normalized["confidence"] = cls._normalize_confidence(normalized.get("confidence"))
        normalized["needs_review"] = bool(normalized.get("needs_review", True))
        return normalized

    @classmethod
    def _normalize_revise_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        normalized["field_name"] = "" if normalized.get("field_name") is None else str(normalized.get("field_name"))
        normalized["revised_value"] = "" if normalized.get("revised_value") is None else str(normalized.get("revised_value"))
        normalized["confidence"] = cls._normalize_confidence(normalized.get("confidence"))
        normalized["needs_review"] = bool(normalized.get("needs_review", True))
        return normalized

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        confidence = str(value or "medium").lower()
        return confidence if confidence in {"low", "medium", "high"} else "medium"
