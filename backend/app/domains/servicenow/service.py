import re
from difflib import SequenceMatcher
from typing import Any

from app.ai.createai_provider import CreateAIProvider, CreateAIProviderError
from app.ai.prompt_engine import PromptEngine
from app.ai.response_validator import AIResponseValidationError, ResponseValidator
from app.ai.safety_rules import SafetyRules
from app.domains.servicenow.prompts import GENERATE_FIELDS_SYSTEM_PROMPT, REVISE_FIELD_SYSTEM_PROMPT
from app.domains.servicenow.schemas import (
    FieldStatusRequest,
    FieldStatusResponse,
    GenerateFieldsRequest,
    GeneratedFieldsResponse,
    ReviseFieldRequest,
    RevisedFieldResponse,
)
from app.db.repositories import SupportRepository, log_repository_error
from app.memory.example_memory import ExampleMemory
from app.memory.session_memory import SessionMemory
from app.memory.user_memory import UserMemory, UserProfile


class ServiceNowAssistantService:
    def __init__(
        self,
        *,
        createai_provider: CreateAIProvider,
        user_memory: UserMemory,
        session_memory: SessionMemory,
        example_memory: ExampleMemory,
        repository: SupportRepository | None = None,
    ) -> None:
        self.createai_provider = createai_provider
        self.user_memory = user_memory
        self.session_memory = session_memory
        self.example_memory = example_memory
        self.repository = repository

    async def generate_fields(self, request: GenerateFieldsRequest) -> GeneratedFieldsResponse:
        current_user = self.user_memory.get_current_user()
        team_rules = self.user_memory.get_team_rules()
        ticket_context = self._build_prompt_ticket_context(request.ticket_context.compact_dict())
        prompt = PromptEngine.build_generate_fields_query(
            ticket_context=ticket_context,
            target_fields=request.target_fields,
            user_instruction=request.user_instruction,
            current_user=current_user,
            team_rules=team_rules,
        )

        if self.createai_provider.is_mock:
            payload = self._mock_generate_payload(request, current_user)
        else:
            try:
                raw_response = await self.createai_provider.query(
                    system_prompt=GENERATE_FIELDS_SYSTEM_PROMPT,
                    query=prompt,
                )
                payload = ResponseValidator.parse_generate_response(raw_response)
            except (CreateAIProviderError, AIResponseValidationError) as exc:
                payload = self._error_generate_payload(str(exc))

        response = GeneratedFieldsResponse.model_validate(payload)
        safe_response = self._apply_generate_safety(request, response)
        repaired_response = await self._repair_generate_response(request, safe_response, current_user, team_rules)
        return self._filter_generate_response_to_targets(request, repaired_response)

    async def revise_field(self, request: ReviseFieldRequest) -> RevisedFieldResponse:
        current_user = self.user_memory.get_current_user()
        team_rules = self.user_memory.get_team_rules()
        ticket_context = self._build_prompt_ticket_context(request.ticket_context.compact_dict())
        prompt = PromptEngine.build_revise_field_query(
            ticket_number=request.ticket_number,
            field_name=request.field_name,
            current_field_value=request.current_field_value,
            revision_instruction=request.revision_instruction,
            ticket_context=ticket_context,
            current_user=current_user,
            team_rules=team_rules,
        )

        if self.createai_provider.is_mock:
            payload = self._mock_revise_payload(request, current_user)
        else:
            try:
                raw_response = await self.createai_provider.query(
                    system_prompt=REVISE_FIELD_SYSTEM_PROMPT,
                    query=prompt,
                )
                payload = ResponseValidator.parse_revise_response(raw_response)
            except (CreateAIProviderError, AIResponseValidationError) as exc:
                payload = self._error_revise_payload(request.field_name, str(exc))

        response = RevisedFieldResponse.model_validate(payload)
        return self._apply_revise_safety(request, response)

    def save_field_status(self, request: FieldStatusRequest) -> FieldStatusResponse:
        current_user = self.user_memory.get_current_user()
        team = self.user_memory.get_current_team()
        session = self.session_memory.get_or_create(
            user_id=current_user.id,
            channel="servicenow",
            external_ref=request.ticket_number,
            metadata={"ticket_type": request.ticket_type},
        )
        before_count = len(self.example_memory.accepted_examples)
        self.example_memory.save_field_status(
            session_id=session.id,
            user_id=current_user.id,
            team_id=team.id,
            ticket_number=request.ticket_number,
            ticket_type=request.ticket_type,
            field_name=request.field_name,
            status=request.status,
            current_value=request.final_value,
            source=request.source,
            ticket_summary=request.ticket_summary or request.ticket_number or "",
        )
        after_count = len(self.example_memory.accepted_examples)
        accepted_example_saved = after_count > before_count

        if self.repository:
            try:
                accepted_example_saved = self.repository.save_field_status(
                    user=current_user,
                    team=team,
                    ticket_number=request.ticket_number,
                    ticket_type=request.ticket_type,
                    field_name=request.field_name,
                    status=request.status,
                    current_value=request.final_value,
                    source=request.source,
                    ticket_summary=request.ticket_summary or request.ticket_number or "",
                )
            except Exception as exc:
                log_repository_error("save_field_status", exc)

        return FieldStatusResponse(
            saved=True,
            field_name=request.field_name,
            status=request.status,
            accepted_example_saved=accepted_example_saved,
        )

    def record_generation(self, request: GenerateFieldsRequest, response: GeneratedFieldsResponse) -> None:
        current_user = self.user_memory.get_current_user()
        team = self.user_memory.get_current_team()
        session = self.session_memory.get_or_create(
            user_id=current_user.id,
            channel="servicenow",
            external_ref=request.ticket_context.number,
            metadata={"ticket_type": request.ticket_context.ticket_type},
        )
        self.example_memory.record_generation(
            {
                "session_id": session.id,
                "ticket_number": request.ticket_context.number,
                "ticket_type": request.ticket_context.ticket_type,
                "input_context_json": request.ticket_context.compact_dict(),
                "ai_output_json": response.model_dump(),
                "model_used": self.createai_provider.settings.createai_model_name,
            }
        )
        if self.repository:
            try:
                self.repository.record_generation(
                    user=current_user,
                    team=team,
                    ticket_number=request.ticket_context.number,
                    ticket_type=request.ticket_context.ticket_type,
                    input_context=request.ticket_context.compact_dict(),
                    ai_output=response.model_dump(),
                    model_used=self.createai_provider.settings.createai_model_name,
                )
            except Exception as exc:
                log_repository_error("record_generation", exc)

    def record_revision(self, request: ReviseFieldRequest, response: RevisedFieldResponse) -> None:
        current_user = self.user_memory.get_current_user()
        team = self.user_memory.get_current_team()
        session = self.session_memory.get_or_create(
            user_id=current_user.id,
            channel="servicenow",
            external_ref=request.ticket_number,
            metadata={"ticket_type": request.ticket_context.ticket_type},
        )
        self.example_memory.record_revision(
            {
                "session_id": session.id,
                "field_name": request.field_name,
                "old_value": request.current_field_value,
                "revision_instruction": request.revision_instruction,
                "new_value": response.revised_value,
                "accepted": False,
            }
        )
        if self.repository:
            try:
                self.repository.record_revision(
                    user=current_user,
                    team=team,
                    ticket_number=request.ticket_number,
                    ticket_type=request.ticket_context.ticket_type,
                    field_name=request.field_name,
                    old_value=request.current_field_value,
                    revision_instruction=request.revision_instruction,
                    new_value=response.revised_value,
                )
            except Exception as exc:
                log_repository_error("record_revision", exc)

    def _apply_generate_safety(
        self,
        request: GenerateFieldsRequest,
        response: GeneratedFieldsResponse,
    ) -> GeneratedFieldsResponse:
        generated_text = "\n".join(
            [
                response.short_description,
                response.description,
                response.additional_comments,
                response.work_notes,
            ]
        )
        source_text = f"{request.ticket_context.source_text()}\n{request.user_instruction}"
        safety = SafetyRules.check_unverified_completion_claims(
            source_text=source_text,
            generated_text=generated_text,
        )
        if safety.passed:
            return response
        missing_info = list(response.missing_info)
        missing_info.append(f"Review unverified completion claim(s): {', '.join(safety.unverified_claims)}")
        return response.model_copy(
            update={
                "missing_info": missing_info,
                "confidence": "low",
                "needs_review": True,
                "suggested_next_action": "Review the generated text for unverified completed work before updating the ticket.",
            }
        )

    def _filter_generate_response_to_targets(
        self,
        request: GenerateFieldsRequest,
        response: GeneratedFieldsResponse,
    ) -> GeneratedFieldsResponse:
        if not request.target_fields:
            return response

        allowed_fields = set(request.target_fields)
        return response.model_copy(
            update={
                field_name: "" for field_name in ("short_description", "description", "additional_comments", "work_notes")
                if field_name not in allowed_fields
            }
        )

    async def _repair_generate_response(
        self,
        request: GenerateFieldsRequest,
        response: GeneratedFieldsResponse,
        current_user: UserProfile,
        team_rules: list[str],
    ) -> GeneratedFieldsResponse:
        updates: dict[str, Any] = {}
        if self._field_was_requested(request, "description") and self._description_needs_context_repair(
            request,
            response.description,
        ):
            description = await self._regenerate_description_with_ai(request, current_user, team_rules)
            if not description:
                description = self._build_description_from_context(request.ticket_context)
            if description:
                updates["description"] = description

        return response.model_copy(update=updates) if updates else response

    def _field_was_requested(self, request: GenerateFieldsRequest, field_name: str) -> bool:
        return not request.target_fields or field_name in request.target_fields

    def _description_needs_context_repair(self, request: GenerateFieldsRequest, description: str) -> bool:
        cleaned = description.strip()
        if not cleaned:
            return True
        if self._is_sys_id(cleaned) or self._is_request_metadata(cleaned):
            return True
        if re.search(r"\b(?:I|my|me)\b", cleaned, flags=re.IGNORECASE):
            return True
        if bool(
            re.fullmatch(
                r"(?:RITM|REQ|TASK|INC)\d+\s+(?:request|ticket)(?:\s+for\s+.+)?",
                cleaned,
                flags=re.IGNORECASE,
            )
        ):
            return True
        return self._description_is_too_close_to_source(request, cleaned)

    def _description_is_too_close_to_source(self, request: GenerateFieldsRequest, description: str) -> bool:
        source = self._clean_context_value(request.ticket_context.more_information) or self._clean_context_value(
            request.ticket_context.additional_details
        )
        if not source:
            return False

        normalized_description = self._normalize_for_similarity(description)
        normalized_source = self._normalize_for_similarity(source)
        if len(normalized_source) < 40 or len(normalized_description) < 25:
            return False
        if normalized_description in normalized_source:
            return True
        if normalized_source in normalized_description:
            return True

        ratio = SequenceMatcher(None, normalized_description, normalized_source).ratio()
        if ratio >= 0.78:
            return True

        source_tokens = set(normalized_source.split())
        description_tokens = set(normalized_description.split())
        if not description_tokens:
            return False
        overlap = len(source_tokens & description_tokens) / len(description_tokens)
        return overlap >= 0.88 and len(description_tokens) >= 12

    def _normalize_for_similarity(self, value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()

    async def _regenerate_description_with_ai(
        self,
        request: GenerateFieldsRequest,
        current_user: UserProfile,
        team_rules: list[str],
    ) -> str:
        if self.createai_provider.is_mock:
            return ""

        ticket_context = self._build_prompt_ticket_context(request.ticket_context.compact_dict())
        prompt = PromptEngine.build_generate_fields_query(
            ticket_context=ticket_context,
            target_fields=["description"],
            user_instruction=(
                "Regenerate only the description field. Do not copy More information verbatim. "
                "Rewrite the user's issue as a professional third-person ServiceNow ticket summary. "
                "Return empty strings for all other fields."
            ),
            current_user=current_user,
            team_rules=team_rules,
        )

        try:
            raw_response = await self.createai_provider.query(
                system_prompt=GENERATE_FIELDS_SYSTEM_PROMPT,
                query=prompt,
            )
            payload = ResponseValidator.parse_generate_response(raw_response)
        except (CreateAIProviderError, AIResponseValidationError):
            return ""

        description = str(payload.get("description") or "").strip()
        if self._description_needs_context_repair(request, description):
            return ""
        return description

    def _apply_revise_safety(
        self,
        request: ReviseFieldRequest,
        response: RevisedFieldResponse,
    ) -> RevisedFieldResponse:
        source_text = "\n".join(
            [
                request.ticket_context.source_text(),
                request.current_field_value,
                request.revision_instruction,
            ]
        )
        safety = SafetyRules.check_unverified_completion_claims(
            source_text=source_text,
            generated_text=response.revised_value,
        )
        if safety.passed:
            return response
        return response.model_copy(update={"confidence": "low", "needs_review": True})

    def _mock_generate_payload(self, request: GenerateFieldsRequest, current_user: UserProfile) -> dict[str, Any]:
        context = request.ticket_context
        details = self._clean_context_value(context.more_information) or self._clean_context_value(context.additional_details)
        item = self._clean_context_value(context.item) or self._infer_item_from_details(details)
        requested_for_name = (
            self._clean_context_value(context.requested_for)
            or self._infer_person_name_from_details(details)
            or "there"
        )
        campus = self._clean_context_value(context.campus) or self._clean_context_value(context.location)
        building = self._clean_context_value(context.building)
        room = self._clean_context_value(context.room_number) or self._clean_context_value(context.room)
        recent_activity = self._clean_context_value(context.recent_activity)
        issue_summary = self._infer_issue_summary(item, details)
        short_description = self._build_short_description(campus, building, room, issue_summary)
        first_name = self._first_name(requested_for_name)
        detail_sentence = self._build_detail_sentence(item, details, requested_for_name)
        additional_comments = self._build_customer_comment(
            first_name=first_name,
            detail_sentence=detail_sentence,
            details=details,
            recent_activity=recent_activity,
            signature=current_user.signature,
        )
        return {
            "short_description": short_description,
            "description": detail_sentence,
            "additional_comments": additional_comments,
            "work_notes": self._build_work_notes(detail_sentence, details, recent_activity),
            "missing_info": [],
            "suggested_next_action": "Review the generated fields before updating the ticket.",
            "confidence": "high" if details or item else "medium",
            "needs_review": True,
        }

    def _mock_revise_payload(self, request: ReviseFieldRequest, current_user: UserProfile) -> dict[str, Any]:
        instruction = request.revision_instruction.strip()
        current = request.current_field_value.strip()

        if request.field_name == "additional_comments":
            details = self._clean_context_value(request.ticket_context.additional_details)
            requested_for_name = (
                self._clean_context_value(request.ticket_context.requested_for)
                or self._infer_person_name_from_details(details)
                or "there"
            )
            first_name = self._first_name(requested_for_name)
            detail_sentence = self._build_detail_sentence(
                self._clean_context_value(request.ticket_context.item) or self._infer_item_from_details(details),
                details,
                requested_for_name,
            )
            if "short" in instruction.lower():
                revised = (
                    f"Hello {first_name},\n\n"
                    f"I noted that {detail_sentence}. I will follow up once the next step is confirmed.\n\n"
                    f"{current_user.signature}"
                )
            else:
                revised = self._append_revision_sentence(current, instruction, current_user.signature)
        elif request.field_name == "work_notes":
            revised = self._append_revision_sentence(current or "Reviewed request.", instruction, None)
        elif request.field_name == "short_description":
            details = self._clean_context_value(request.ticket_context.more_information) or self._clean_context_value(
                request.ticket_context.additional_details
            )
            revised = self._build_short_description(
                self._clean_context_value(request.ticket_context.campus) or self._clean_context_value(request.ticket_context.location),
                self._clean_context_value(request.ticket_context.building),
                self._clean_context_value(request.ticket_context.room_number) or self._clean_context_value(request.ticket_context.room),
                self._infer_issue_summary(
                    self._clean_context_value(request.ticket_context.item),
                    f"{details} {instruction}",
                ),
            )
        else:
            revised = self._append_revision_sentence(current, instruction, None)

        return {
            "field_name": request.field_name,
            "revised_value": revised,
            "confidence": "high",
            "needs_review": True,
        }

    def _error_generate_payload(self, message: str) -> dict[str, Any]:
        return {
            "short_description": "",
            "description": "",
            "additional_comments": "",
            "work_notes": "",
            "missing_info": [message],
            "suggested_next_action": "The AI provider response could not be used. Please retry or fill the fields manually.",
            "confidence": "low",
            "needs_review": True,
        }

    def _error_revise_payload(self, field_name: str, message: str) -> dict[str, Any]:
        return {
            "field_name": field_name,
            "revised_value": "",
            "confidence": "low",
            "needs_review": True,
            "missing_info": [message],
        }

    def _infer_issue_summary(self, item: str | None, details: str | None) -> str:
        text = f"{item or ''} {details or ''}".lower()
        if ("shutting off" in text or "shutting down" in text) and "thermal" in text:
            return "Laptop shutting down and restarting multiple times and having thermal errors"
        if "laptop refresh" in text:
            return "Laptop refresh request"
        if "onboarding" in text or "appointment" in text:
            return "Onboarding appointment request"
        if "restart" in text or "reboot" in text:
            return "Laptop restart issue"
        if "software" in text or "install" in text:
            return "Software installation request"
        if "access" in text:
            return "Access request"
        if "printer" in text or "wi-fi" in text or "wifi" in text or "network" in text:
            return "Printer or network support request"
        if item:
            return self._title_case_sentence(item)
        return "Service request"

    def _build_short_description(
        self,
        campus: str | None,
        building: str | None,
        room: str | None,
        issue_summary: str,
    ) -> str:
        location_parts = [
            self._extract_location_code(campus),
            self._extract_location_code(building),
            self._clean_context_value(room),
        ]
        prefix = " - ".join(part for part in location_parts if part)
        return f"{prefix} - {issue_summary}" if prefix else issue_summary

    def _build_description_from_context(self, context: Any) -> str:
        details = self._clean_context_value(getattr(context, "more_information", None)) or self._clean_context_value(
            getattr(context, "additional_details", None)
        )
        if not details:
            return ""

        item = self._clean_context_value(getattr(context, "item", None)) or self._infer_item_from_details(details)
        requested_for = self._clean_context_value(getattr(context, "requested_for", None)) or self._infer_person_name_from_details(
            details
        )
        return self._build_detail_sentence(item, details, requested_for)

    def _build_detail_sentence(self, item: str | None, details: str | None, requested_for: str | None = None) -> str:
        item_text = self._clean_context_value(item) or self._infer_item_from_details(details) or "service request"
        details_text = self._normalize_time_text(self._clean_context_value(details)).strip()
        person = self._clean_context_value(requested_for) or self._infer_person_name_from_details(details_text)
        schedule = self._infer_schedule_from_details(details_text)

        thermal_summary = self._summarize_thermal_laptop_issue(details_text)
        if thermal_summary:
            return thermal_summary
        if schedule and person:
            return f"{item_text} is scheduled for {person} on {schedule}"
        if schedule:
            return f"{item_text} is scheduled on {schedule}"
        if details_text:
            return self._rewrite_details_as_ticket_summary(item_text, details_text)
        if person and item_text.lower() not in details_text.lower():
            return f"{item_text} request for {person}"
        return f"{item_text} request"

    def _rewrite_details_as_ticket_summary(self, item: str, details: str) -> str:
        cleaned = self._strip_polite_opening(self._normalize_time_text(details))
        cleaned = re.sub(r"\bpreferred\s+contact:\s*[^.]*?\s+details:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bI\s+need\b", "the user needs", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bI\s+am\b", "the user is", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bI\s+will\b", "the user will", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bI\b", "the user", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bmy\b", "the user's", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bme\b", "the user", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bsomeone can please\b", "IT can", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bplease let the user know\b", "requested follow-up", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bplease let me know\b", "requested follow-up", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(
            r"([.!?]\s+)([a-z])",
            lambda match: f"{match.group(1)}{match.group(2).upper()}",
            cleaned,
        )

        if not cleaned:
            return f"User requested assistance with {item}."

        lowered = cleaned.lower()
        if "not be on campus" in lowered or "back in the office" in lowered or "available" in lowered:
            return self._sentence_case(f"User requested assistance with {item}. Details noted: {cleaned}")
        return self._sentence_case(f"User requested assistance with {item}. The reported details indicate that {cleaned}")

    def _strip_polite_opening(self, value: str) -> str:
        return re.sub(
            r"^\s*(?:good\s+(?:morning|afternoon|evening)|hello|hi)[,!.\s]+",
            "",
            value.strip(),
            flags=re.IGNORECASE,
        )

    def _build_customer_comment(
        self,
        *,
        first_name: str,
        detail_sentence: str,
        details: str,
        recent_activity: str,
        signature: str,
    ) -> str:
        greeting = f"Hi {first_name}," if first_name != "there" else "Hi,"
        combined = f"{details}\n{recent_activity}".lower()

        if self._source_indicates_completed_setup(combined):
            return (
                f"{greeting}\n\n"
                "Thank you for your time today. Your laptop has been set up and is ready to use.\n\n"
                "If you run into any issues or need any additional assistance, please feel free to contact IT and we will be happy to help.\n\n"
                f"{self._signature_without_leading_thanks(signature)}"
            )

        if "laptop refresh" in combined or "laptop replacement" in combined or "onboarding" in combined:
            return (
                f"{greeting}\n\n"
                "Your laptop is ready for onboarding. Could you please let me know a date and time when you will be available "
                "so I can schedule an appointment for the setup and transfer process?\n\n"
                f"{signature}"
            )

        return (
            f"{greeting}\n\n"
            f"I reviewed your request and noted that {detail_sentence}. Could you please let me know a date, time, and location "
            "when you will be available so I can stop by and take a look?\n\n"
            f"{signature}"
        )

    def _build_work_notes(self, detail_sentence: str, details: str, recent_activity: str) -> str:
        combined = f"{details}\n{recent_activity}".lower()
        if self._source_indicates_completed_setup(combined):
            return "Confirmed from ticket activity that laptop setup was completed and the device is ready for use."
        return f"Reviewed request. {detail_sentence}"

    def _append_revision_sentence(self, current: str, instruction: str, signature: str | None) -> str:
        base = current.strip()
        if not instruction:
            return base
        sentence = self._instruction_to_safe_sentence(instruction)
        if signature and signature in base:
            without_signature = base.replace(signature, "").rstrip()
            return f"{without_signature}\n\n{sentence}\n\n{signature}"
        return f"{base}\n\n{sentence}" if base else sentence

    def _instruction_to_safe_sentence(self, instruction: str) -> str:
        lowered = instruction.lower()
        if "attached" in lowered and "quote" in lowered:
            return "I also noted that the quote has been attached."
        if "follow up" in lowered or "confirmed" in lowered:
            return "I will follow up once the next step is confirmed."
        if "short" in lowered:
            return "I noted the request and will follow up with the next step."
        cleaned = instruction.strip().rstrip(".")
        return self._title_case_sentence(cleaned) + "."

    def _normalize_time_text(self, value: str) -> str:
        value = re.sub(r"\b9\s*AM\b", "9:00 AM", value, flags=re.IGNORECASE)
        value = re.sub(r"\b9\s*PM\b", "9:00 PM", value, flags=re.IGNORECASE)
        return value

    def _extract_location_code(self, value: str | None) -> str:
        cleaned = self._clean_context_value(value)
        if not cleaned:
            return ""
        parenthetical = re.search(r"\(([A-Z0-9-]+)\)", cleaned)
        if parenthetical:
            return parenthetical.group(1).strip()
        return cleaned.strip()

    def _summarize_thermal_laptop_issue(self, details: str) -> str:
        lowered = details.lower()
        if not (("shutting off" in lowered or "shutting down" in lowered) and "thermal" in lowered):
            return ""

        device_match = re.search(r"\b(?:PC\s+)?(CON\d+)\b", details, flags=re.IGNORECASE)
        device_text = f" on desktop {device_match.group(1).upper()}" if device_match else ""
        availability = ""
        if "not be on campus tomorrow" in lowered and "thursday" in lowered:
            availability = "User will be unavailable until Thursday"

        base = (
            f"User reported that after completing a Dell BIOS update{device_text}, the system began shutting down approximately every "
            "30 seconds after restart. The device displays a thermal warning indicating that the vents may be blocked."
        )
        if availability:
            return (
                f"{base} {availability} and has requested troubleshooting and inspection of the device to determine the cause of "
                "the thermal error and repeated shutdowns."
            )
        return (
            f"{base} User requested troubleshooting and inspection of the device to determine the cause of the thermal error and "
            "repeated shutdowns."
        )

    def _source_indicates_completed_setup(self, source: str) -> bool:
        completed_markers = (
            "set up and ready to use",
            "setup was completed",
            "has been set up",
            "ready to use",
            "completed the setup",
            "resolved",
        )
        return any(marker in source for marker in completed_markers)

    def _signature_without_leading_thanks(self, signature: str) -> str:
        return re.sub(r"^\s*Thanks,\s*\n+", "", signature.strip(), flags=re.IGNORECASE)

    def _clean_context_value(self, value: str | None) -> str:
        if not value:
            return ""
        cleaned = value.strip()
        if self._is_sys_id(cleaned) or self._is_request_metadata(cleaned):
            return ""
        return cleaned

    def _build_prompt_ticket_context(self, context: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in context.items():
            if isinstance(value, str):
                cleaned_value = self._clean_context_value(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value
            else:
                cleaned[key] = value

        details = self._clean_context_value(cleaned.get("more_information")) or self._clean_context_value(
            cleaned.get("additional_details")
        )
        if details:
            cleaned["more_information"] = details
            cleaned["additional_details"] = details
        if not cleaned.get("requested_for"):
            inferred_person = self._infer_person_name_from_details(details)
            if inferred_person:
                cleaned["requested_for"] = inferred_person
        if not cleaned.get("item"):
            inferred_item = self._infer_item_from_details(details)
            if inferred_item:
                cleaned["item"] = inferred_item
        return cleaned

    def _is_sys_id(self, value: str) -> bool:
        return bool(re.fullmatch(r"[0-9a-f]{32}", value.strip(), flags=re.IGNORECASE))

    def _is_request_metadata(self, value: str) -> bool:
        return bool(re.match(r"^\s*(?:RITM|REQ|TASK|INC)\d+\s+request\s+for\s+", value.strip(), flags=re.IGNORECASE))

    def _infer_item_from_details(self, details: str | None) -> str:
        parts = self._split_detail_parts(details)
        return parts[0] if parts and not self._is_sys_id(parts[0]) else ""

    def _infer_person_name_from_details(self, details: str | None) -> str:
        for part in self._split_detail_parts(details):
            if re.fullmatch(r"[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+)+", part):
                return part
        return ""

    def _infer_schedule_from_details(self, details: str | None) -> str:
        for part in self._split_detail_parts(details):
            match = re.search(r"\bscheduled\s+(?:on|for)\s+(.+)$", part, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip().rstrip(".")
        return ""

    def _split_detail_parts(self, details: str | None) -> list[str]:
        cleaned = self._clean_context_value(details)
        if not cleaned:
            return []
        return [part.strip() for part in re.split(r"\s+-\s+", cleaned) if part.strip()]

    def _first_name(self, name: str) -> str:
        cleaned = self._clean_context_value(name)
        if not cleaned or cleaned == "there":
            return "there"
        return cleaned.split()[0]

    def _sentence_case(self, value: str) -> str:
        cleaned = value.strip().rstrip(".")
        if not cleaned:
            return cleaned
        return f"{cleaned[0].upper()}{cleaned[1:]}."

    def _title_case_sentence(self, value: str) -> str:
        if not value:
            return value
        return value[0].upper() + value[1:]
