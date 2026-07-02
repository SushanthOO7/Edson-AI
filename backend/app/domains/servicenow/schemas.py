from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Confidence = Literal["low", "medium", "high"]
FieldName = Literal["short_description", "description", "additional_comments", "work_notes"]
FieldStatus = Literal["generated", "revised", "accepted", "manual_edit_detected", "error"]
FieldSource = Literal["ai_generated", "ai_revised", "manual", "system"]


class TicketContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    ticket_type: str | None = None
    number: str | None = None
    requested_for: str | None = None
    campus: str | None = None
    building: str | None = None
    room_number: str | None = None
    location: str | None = None
    room: str | None = None
    item: str | None = None
    more_information: str | None = None
    recent_activity: str | None = None
    additional_details: str | None = None
    current_short_description: str | None = None
    current_description: str | None = None
    current_additional_comments: str | None = None
    current_work_notes: str | None = None

    def compact_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)

    def source_text(self) -> str:
        values = [
            self.number,
            self.ticket_type,
            self.requested_for,
            self.campus,
            self.building,
            self.room_number,
            self.location,
            self.room,
            self.item,
            self.more_information,
            self.recent_activity,
            self.additional_details,
            self.current_short_description,
            self.current_description,
            self.current_additional_comments,
            self.current_work_notes,
        ]
        return "\n".join(value for value in values if value)


class GenerateFieldsRequest(BaseModel):
    ticket_context: TicketContext
    target_fields: list[FieldName] | None = None
    user_instruction: str = "Generate all fields."


class GeneratedFieldsResponse(BaseModel):
    short_description: str = ""
    description: str = ""
    additional_comments: str = ""
    work_notes: str = ""
    missing_info: list[str] = Field(default_factory=list)
    suggested_next_action: str = "Review the generated fields before updating the ticket."
    confidence: Confidence = "medium"
    needs_review: bool = True

    @field_validator("short_description", "description", "additional_comments", "work_notes", "suggested_next_action", mode="before")
    @classmethod
    def empty_string_for_none(cls, value: Any) -> str:
        return "" if value is None else str(value)


class ReviseFieldRequest(BaseModel):
    ticket_number: str | None = None
    field_name: FieldName
    current_field_value: str
    revision_instruction: str
    ticket_context: TicketContext


class RevisedFieldResponse(BaseModel):
    field_name: FieldName
    revised_value: str
    confidence: Confidence = "medium"
    needs_review: bool = True

    @field_validator("revised_value", mode="before")
    @classmethod
    def empty_string_for_none(cls, value: Any) -> str:
        return "" if value is None else str(value)


class FieldStatusRequest(BaseModel):
    ticket_number: str | None = None
    ticket_type: str | None = None
    field_name: FieldName
    status: FieldStatus
    final_value: str
    source: FieldSource
    ticket_summary: str | None = None


class FieldStatusResponse(BaseModel):
    saved: bool
    field_name: FieldName
    status: FieldStatus
    accepted_example_saved: bool
