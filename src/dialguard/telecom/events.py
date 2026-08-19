"""Telecom provider event definitions."""

from dataclasses import dataclass, field
from enum import StrEnum
import time
import uuid


class TelecomEventType(StrEnum):
    """Events emitted by external telecom carrier providers."""

    INITIATED = "INITIATED"
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class ProviderCallEvent:
    """Structured event received from an external telecom provider."""

    call_id: str
    event_type: TelecomEventType
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    reason: str | None = None
