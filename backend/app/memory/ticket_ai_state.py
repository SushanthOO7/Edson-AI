from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class TicketAIAction:
    action: str
    field_name: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TicketAIState:
    ticket_number: str
    normalized_ticket_context: dict[str, Any] = field(default_factory=dict)
    generated_fields: dict[str, str] = field(default_factory=dict)
    user_edits: dict[str, str] = field(default_factory=dict)
    recent_ai_actions: list[TicketAIAction] = field(default_factory=list)
    latest_response_id: str | None = None


class TicketAIStateStore:
    def __init__(self) -> None:
        self._states: dict[str, TicketAIState] = {}

    def get(self, ticket_number: str | None) -> TicketAIState | None:
        if not ticket_number:
            return None
        return self._states.get(ticket_number)

    def get_or_create(self, ticket_number: str | None) -> TicketAIState | None:
        if not ticket_number:
            return None
        if ticket_number not in self._states:
            self._states[ticket_number] = TicketAIState(ticket_number=ticket_number)
        return self._states[ticket_number]

    def record_generation(
        self,
        *,
        ticket_number: str | None,
        normalized_ticket_context: dict[str, Any],
        generated_fields: dict[str, str],
        action: str,
        field_name: str | None = None,
        response_id: str | None = None,
    ) -> None:
        state = self.get_or_create(ticket_number)
        if not state:
            return
        state.normalized_ticket_context = normalized_ticket_context
        state.generated_fields.update(
            {key: value for key, value in generated_fields.items() if value.strip()}
        )
        state.latest_response_id = response_id or state.latest_response_id
        state.recent_ai_actions = [*state.recent_ai_actions, TicketAIAction(action=action, field_name=field_name)][-10:]

    def record_revision(
        self,
        *,
        ticket_number: str | None,
        normalized_ticket_context: dict[str, Any],
        field_name: str,
        revised_value: str,
        response_id: str | None = None,
    ) -> None:
        state = self.get_or_create(ticket_number)
        if not state:
            return
        state.normalized_ticket_context = normalized_ticket_context
        if revised_value.strip():
            state.generated_fields[field_name] = revised_value
        state.latest_response_id = response_id or state.latest_response_id
        state.recent_ai_actions = [
            *state.recent_ai_actions,
            TicketAIAction(action="revise_single_field", field_name=field_name),
        ][-10:]

    def record_user_edit(self, *, ticket_number: str | None, field_name: str, value: str) -> None:
        state = self.get_or_create(ticket_number)
        if not state:
            return
        state.user_edits[field_name] = value
