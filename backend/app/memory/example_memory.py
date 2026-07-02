from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class FieldStatusRecord:
    id: str
    session_id: str
    ticket_number: str | None
    field_name: str
    status: str
    current_value: str
    source: str
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AcceptedExampleRecord:
    id: str
    team_id: str
    user_id: str
    channel: str
    ticket_type: str | None
    intent: str | None
    field_name: str
    ticket_summary: str
    final_text: str
    visibility: str
    quality_score: float
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ExampleMemory:
    def __init__(self) -> None:
        self.generations: list[dict[str, Any]] = []
        self.revisions: list[dict[str, Any]] = []
        self.field_statuses: list[FieldStatusRecord] = []
        self.accepted_examples: list[AcceptedExampleRecord] = []

    def record_generation(self, payload: dict[str, Any]) -> None:
        self.generations.append(payload)

    def record_revision(self, payload: dict[str, Any]) -> None:
        self.revisions.append(payload)

    def save_field_status(
        self,
        *,
        session_id: str,
        user_id: str,
        team_id: str,
        ticket_number: str | None,
        ticket_type: str | None,
        field_name: str,
        status: str,
        current_value: str,
        source: str,
        ticket_summary: str,
    ) -> FieldStatusRecord:
        record = FieldStatusRecord(
            id=str(uuid4()),
            session_id=session_id,
            ticket_number=ticket_number,
            field_name=field_name,
            status=status,
            current_value=current_value,
            source=source,
        )
        self.field_statuses.append(record)

        if status == "accepted" and current_value.strip():
            self.accepted_examples.append(
                AcceptedExampleRecord(
                    id=str(uuid4()),
                    team_id=team_id,
                    user_id=user_id,
                    channel="servicenow",
                    ticket_type=ticket_type,
                    intent=None,
                    field_name=field_name,
                    ticket_summary=ticket_summary,
                    final_text=current_value,
                    visibility="customer_safe" if field_name == "additional_comments" else "internal",
                    quality_score=1.0,
                )
            )
        return record
