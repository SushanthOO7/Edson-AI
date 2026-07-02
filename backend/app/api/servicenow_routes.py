from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends

from app.ai.createai_provider import CreateAIProvider
from app.core.config import get_settings
from app.db.repositories import SupportRepository
from app.domains.servicenow.schemas import (
    FieldName,
    FieldStatusRequest,
    FieldStatusResponse,
    GenerateFieldsRequest,
    GeneratedFieldsResponse,
    ReviseFieldRequest,
    RevisedFieldResponse,
)
from app.domains.servicenow.service import ServiceNowAssistantService
from app.memory.example_memory import ExampleMemory
from app.memory.session_memory import SessionMemory
from app.memory.user_memory import UserMemory

router = APIRouter(prefix="/api/servicenow", tags=["servicenow"])

FIELD_GENERATION_INSTRUCTIONS: dict[FieldName, str] = {
    "short_description": "Generate only the short_description field. Return empty strings for all other fields.",
    "description": "Generate only the description field. Return empty strings for all other fields.",
    "additional_comments": "Generate only the additional_comments field. Return empty strings for all other fields.",
    "work_notes": "Generate only the work_notes field. Return empty strings for all other fields.",
}


@lru_cache
def get_servicenow_service() -> ServiceNowAssistantService:
    settings = get_settings()
    repository = SupportRepository(settings) if settings.database_url else None
    return ServiceNowAssistantService(
        createai_provider=CreateAIProvider(settings),
        user_memory=UserMemory(),
        session_memory=SessionMemory(),
        example_memory=ExampleMemory(),
        repository=repository,
    )


@router.post("/generate-fields", response_model=GeneratedFieldsResponse)
async def generate_fields(
    request: GenerateFieldsRequest,
    background_tasks: BackgroundTasks,
    service: ServiceNowAssistantService = Depends(get_servicenow_service),
) -> GeneratedFieldsResponse:
    all_fields_request = request.model_copy(update={"target_fields": None, "user_instruction": "Generate all fields."})
    response = await service.generate_fields(all_fields_request)
    background_tasks.add_task(service.record_generation, all_fields_request, response)
    return response


@router.post("/generate-short-description", response_model=GeneratedFieldsResponse)
async def generate_short_description(
    request: GenerateFieldsRequest,
    background_tasks: BackgroundTasks,
    service: ServiceNowAssistantService = Depends(get_servicenow_service),
) -> GeneratedFieldsResponse:
    return await generate_one_field("short_description", request, background_tasks, service)


@router.post("/generate-description", response_model=GeneratedFieldsResponse)
async def generate_description(
    request: GenerateFieldsRequest,
    background_tasks: BackgroundTasks,
    service: ServiceNowAssistantService = Depends(get_servicenow_service),
) -> GeneratedFieldsResponse:
    return await generate_one_field("description", request, background_tasks, service)


@router.post("/generate-additional-comments", response_model=GeneratedFieldsResponse)
async def generate_additional_comments(
    request: GenerateFieldsRequest,
    background_tasks: BackgroundTasks,
    service: ServiceNowAssistantService = Depends(get_servicenow_service),
) -> GeneratedFieldsResponse:
    return await generate_one_field("additional_comments", request, background_tasks, service)


@router.post("/generate-work-notes", response_model=GeneratedFieldsResponse)
async def generate_work_notes(
    request: GenerateFieldsRequest,
    background_tasks: BackgroundTasks,
    service: ServiceNowAssistantService = Depends(get_servicenow_service),
) -> GeneratedFieldsResponse:
    return await generate_one_field("work_notes", request, background_tasks, service)


async def generate_one_field(
    field_name: FieldName,
    request: GenerateFieldsRequest,
    background_tasks: BackgroundTasks,
    service: ServiceNowAssistantService,
) -> GeneratedFieldsResponse:
    field_request = request.model_copy(
        update={
            "target_fields": [field_name],
            "user_instruction": FIELD_GENERATION_INSTRUCTIONS[field_name],
        }
    )
    response = await service.generate_fields(field_request)
    background_tasks.add_task(service.record_generation, field_request, response)
    return response


@router.post("/revise-field", response_model=RevisedFieldResponse)
async def revise_field(
    request: ReviseFieldRequest,
    background_tasks: BackgroundTasks,
    service: ServiceNowAssistantService = Depends(get_servicenow_service),
) -> RevisedFieldResponse:
    response = await service.revise_field(request)
    background_tasks.add_task(service.record_revision, request, response)
    return response


@router.post("/save-field-status", response_model=FieldStatusResponse)
async def save_field_status(
    request: FieldStatusRequest,
    service: ServiceNowAssistantService = Depends(get_servicenow_service),
) -> FieldStatusResponse:
    return service.save_field_status(request)
