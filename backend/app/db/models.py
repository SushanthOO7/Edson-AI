from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - only used when pgvector package is absent
    Vector = None


def uuid_pk() -> Mapped[str]:
    return mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))


def json_dict() -> Mapped[dict[str, Any]]:
    return mapped_column(JSONB, default=dict)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Team(Base, TimestampMixin):
    __tablename__ = "teams"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    settings_json: Mapped[dict[str, Any]] = json_dict()

    users: Mapped[list["User"]] = relationship(back_populates="team")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    role: Mapped[str | None] = mapped_column(String(255))
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    signature: Mapped[str | None] = mapped_column(Text)
    preferences_json: Mapped[dict[str, Any]] = json_dict()

    team: Mapped[Team | None] = relationship(back_populates="users")


class SessionRecord(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = json_dict()
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = uuid_pk()
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = json_dict()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details_json: Mapped[dict[str, Any]] = json_dict()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceNowAIGeneration(Base):
    __tablename__ = "servicenow_ai_generations"

    id: Mapped[str] = uuid_pk()
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    ticket_number: Mapped[str | None] = mapped_column(String(80))
    ticket_type: Mapped[str | None] = mapped_column(String(80))
    input_context_json: Mapped[dict[str, Any]] = json_dict()
    ai_output_json: Mapped[dict[str, Any]] = json_dict()
    model_used: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceNowAIRevision(Base):
    __tablename__ = "servicenow_ai_revisions"

    id: Mapped[str] = uuid_pk()
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    revision_instruction: Mapped[str] = mapped_column(Text, nullable=False)
    new_value: Mapped[str | None] = mapped_column(Text)
    accepted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceNowFieldStatus(Base):
    __tablename__ = "servicenow_field_status"

    id: Mapped[str] = uuid_pk()
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    current_value: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AcceptedExample(Base):
    __tablename__ = "accepted_examples"

    id: Mapped[str] = uuid_pk()
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    ticket_type: Mapped[str | None] = mapped_column(String(80))
    intent: Mapped[str | None] = mapped_column(String(255))
    field_name: Mapped[str | None] = mapped_column(String(80))
    ticket_summary: Mapped[str | None] = mapped_column(Text)
    final_text: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536) if Vector else Text)
    quality_score: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = uuid_pk()
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    visibility: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[dict[str, Any]] = json_dict()


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = uuid_pk()
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536) if Vector else Text)
    visibility: Mapped[str] = mapped_column(String(80), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = json_dict()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
