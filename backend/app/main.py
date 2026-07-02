from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.servicenow_routes import router as servicenow_router
from app.api.user_routes import router as user_router
from app.api.chat_routes import router as chat_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_env)

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="Shared AI support backend for ServiceNow and future IT Help Chatbot workflows.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(servicenow_router)
    app.include_router(user_router)
    app.include_router(chat_router)
    return app


app = create_app()
