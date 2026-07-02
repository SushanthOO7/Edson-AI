from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass
class SessionRecord:
    id: str
    user_id: str
    channel: str
    external_ref: str | None
    metadata: dict
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SessionMemory:
    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str | None], SessionRecord] = {}

    def get_or_create(self, *, user_id: str, channel: str, external_ref: str | None, metadata: dict | None = None) -> SessionRecord:
        key = (channel, external_ref)
        if key not in self._sessions:
            self._sessions[key] = SessionRecord(
                id=str(uuid4()),
                user_id=user_id,
                channel=channel,
                external_ref=external_ref,
                metadata=metadata or {},
            )
        record = self._sessions[key]
        record.updated_at = datetime.now(UTC)
        return record
