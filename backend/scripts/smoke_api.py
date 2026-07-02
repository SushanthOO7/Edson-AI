import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.servicenow_routes import get_servicenow_service
from app.domains.servicenow.schemas import FieldStatusRequest, GenerateFieldsRequest, ReviseFieldRequest


async def main() -> None:
    generate_payload = {
        "ticket_context": {
            "ticket_type": "catalog_task",
            "number": "TASK1378797",
            "requested_for": "Jessica Gentes",
            "location": "MERCA",
            "room": "A213",
            "item": "New Faculty or Staff Technology Onboarding",
            "additional_details": "Would like appointment scheduled on 6/22 at 9 AM.",
            "current_short_description": "",
            "current_description": "",
        },
        "user_instruction": "Generate all fields.",
    }

    service = get_servicenow_service()

    generated = await service.generate_fields(GenerateFieldsRequest.model_validate(generate_payload))
    assert generated.short_description
    assert generated.additional_comments

    revise_payload = {
        "ticket_number": "TASK1378797",
        "field_name": "additional_comments",
        "current_field_value": generated.additional_comments,
        "revision_instruction": "Make it shorter and mention I will follow up once confirmed.",
        "ticket_context": generate_payload["ticket_context"],
    }

    revised = await service.revise_field(ReviseFieldRequest.model_validate(revise_payload))
    assert revised.field_name == "additional_comments"
    assert revised.revised_value

    save_payload = {
        "ticket_number": "TASK1378797",
        "ticket_type": "catalog_task",
        "field_name": "additional_comments",
        "status": "accepted",
        "final_value": revised.revised_value,
        "source": "ai_revised",
        "ticket_summary": "Onboarding appointment request",
    }

    saved = service.save_field_status(FieldStatusRequest.model_validate(save_payload))
    assert saved.saved is True
    assert saved.accepted_example_saved is True

    print("generate-fields:", generated.short_description)
    print("revise-field:", revised.field_name)
    print("save-field-status:", saved.status)


if __name__ == "__main__":
    asyncio.run(main())
