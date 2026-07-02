import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.models import (
    AcceptedExample,
    ServiceNowAIGeneration,
    ServiceNowAIRevision,
    ServiceNowFieldStatus,
    SessionRecord,
    Team,
    User,
)
from app.domains.servicenow.field_mapper import field_visibility
from app.memory.user_memory import TeamProfile, UserProfile

logger = logging.getLogger(__name__)

DISABLE_PERSISTENCE_SECONDS = 300


class SupportRepository:
    def __init__(self, settings: Settings) -> None:
        if not settings.database_url:
            raise ValueError("DATABASE_URL is required for SupportRepository.")
        self.engine = create_engine(settings.database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.disabled_until = 0.0

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def is_available(self) -> bool:
        return time.monotonic() >= self.disabled_until

    def mark_unavailable(self, action: str, exc: Exception) -> None:
        self.disabled_until = time.monotonic() + DISABLE_PERSISTENCE_SECONDS
        try:
            setattr(exc, "_edson_repository_logged", True)
        except Exception:
            pass
        logger.warning(
            "Database persistence unavailable for %s; skipping DB saves for %s seconds. Reason: %s",
            action,
            DISABLE_PERSISTENCE_SECONDS,
            self._short_error(exc),
        )

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            self.mark_unavailable("database operation", exc)
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_generation(
        self,
        *,
        user: UserProfile,
        team: TeamProfile,
        ticket_number: str | None,
        ticket_type: str | None,
        input_context: dict[str, Any],
        ai_output: dict[str, Any],
        model_used: str | None,
    ) -> None:
        if not self.is_available():
            return
        with self.session_scope() as session:
            db_team = self._get_or_create_team(session, team)
            db_user = self._get_or_create_user(session, user, db_team.id)
            db_session = self._get_or_create_session(
                session,
                user_id=db_user.id,
                channel="servicenow",
                external_ref=ticket_number,
                metadata={"ticket_type": ticket_type},
            )
            session.add(
                ServiceNowAIGeneration(
                    session_id=db_session.id,
                    ticket_number=ticket_number,
                    ticket_type=ticket_type,
                    input_context_json=input_context,
                    ai_output_json=ai_output,
                    model_used=model_used,
                )
            )

    def record_revision(
        self,
        *,
        user: UserProfile,
        team: TeamProfile,
        ticket_number: str | None,
        ticket_type: str | None,
        field_name: str,
        old_value: str,
        revision_instruction: str,
        new_value: str,
    ) -> None:
        if not self.is_available():
            return
        with self.session_scope() as session:
            db_team = self._get_or_create_team(session, team)
            db_user = self._get_or_create_user(session, user, db_team.id)
            db_session = self._get_or_create_session(
                session,
                user_id=db_user.id,
                channel="servicenow",
                external_ref=ticket_number,
                metadata={"ticket_type": ticket_type},
            )
            session.add(
                ServiceNowAIRevision(
                    session_id=db_session.id,
                    field_name=field_name,
                    old_value=old_value,
                    revision_instruction=revision_instruction,
                    new_value=new_value,
                    accepted=False,
                )
            )

    def save_field_status(
        self,
        *,
        user: UserProfile,
        team: TeamProfile,
        ticket_number: str | None,
        ticket_type: str | None,
        field_name: str,
        status: str,
        current_value: str,
        source: str,
        ticket_summary: str,
    ) -> bool:
        accepted_example_saved = False
        if not self.is_available():
            return accepted_example_saved
        with self.session_scope() as session:
            db_team = self._get_or_create_team(session, team)
            db_user = self._get_or_create_user(session, user, db_team.id)
            db_session = self._get_or_create_session(
                session,
                user_id=db_user.id,
                channel="servicenow",
                external_ref=ticket_number,
                metadata={"ticket_type": ticket_type},
            )

            session.add(
                ServiceNowFieldStatus(
                    session_id=db_session.id,
                    field_name=field_name,
                    status=status,
                    current_value=current_value,
                    source=source,
                )
            )

            if status == "accepted" and current_value.strip():
                session.add(
                    AcceptedExample(
                        team_id=db_team.id,
                        user_id=db_user.id,
                        channel="servicenow",
                        ticket_type=ticket_type,
                        intent=None,
                        field_name=field_name,
                        ticket_summary=ticket_summary,
                        final_text=current_value,
                        visibility=field_visibility(field_name),
                        quality_score=1,
                    )
                )
                accepted_example_saved = True
        return accepted_example_saved

    def _get_or_create_team(self, session: Session, team: TeamProfile) -> Team:
        existing = session.scalar(select(Team).where(Team.name == team.name))
        if existing:
            return existing
        created = Team(name=team.name, settings_json={"rules": team.rules})
        session.add(created)
        session.flush()
        return created

    def _get_or_create_user(self, session: Session, user: UserProfile, team_id: str) -> User:
        existing = session.scalar(select(User).where(User.email == user.email))
        if existing:
            return existing
        created = User(
            name=user.name,
            email=user.email,
            role=user.role,
            team_id=team_id,
            signature=user.signature,
            preferences_json={},
        )
        session.add(created)
        session.flush()
        return created

    def _get_or_create_session(
        self,
        session: Session,
        *,
        user_id: str,
        channel: str,
        external_ref: str | None,
        metadata: dict[str, Any],
    ) -> SessionRecord:
        existing = session.scalar(
            select(SessionRecord).where(
                SessionRecord.channel == channel,
                SessionRecord.external_ref == external_ref,
            )
        )
        if existing:
            existing.metadata_json = {**(existing.metadata_json or {}), **metadata}
            return existing
        created = SessionRecord(
            user_id=user_id,
            channel=channel,
            external_ref=external_ref,
            metadata_json=metadata,
        )
        session.add(created)
        session.flush()
        return created

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).splitlines()[0].strip()
        return message or exc.__class__.__name__


def log_repository_error(action: str, exc: Exception) -> None:
    if getattr(exc, "_edson_repository_logged", False):
        return
    if isinstance(exc, SQLAlchemyError):
        logger.warning("Database persistence failed for %s: %s", action, exc)
    else:
        logger.exception("Unexpected persistence failure for %s", action)
