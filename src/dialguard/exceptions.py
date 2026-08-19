"""Domain exceptions for DialGuard."""

from typing import Any


class DialGuardError(Exception):
    """Base exception for all DialGuard domain errors."""


class InvalidStateTransitionError(DialGuardError):
    """Raised when an invalid state transition is attempted."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        from_state: Any,
        to_state: Any,
        message: str | None = None,
    ) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.from_state = from_state
        self.to_state = to_state
        if message is None:
            message = (
                f"Cannot transition {entity_type} '{entity_id}' from "
                f"'{from_state}' to '{to_state}'"
            )
        super().__init__(message)


class TerminalStateError(InvalidStateTransitionError):
    """Raised when attempting to transition from a terminal state."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        terminal_state: Any,
        attempted_state: Any,
    ) -> None:
        message = (
            f"Cannot transition {entity_type} '{entity_id}' from terminal state "
            f"'{terminal_state}' to '{attempted_state}'"
        )
        super().__init__(
            entity_type=entity_type,
            entity_id=entity_id,
            from_state=terminal_state,
            to_state=attempted_state,
            message=message,
        )
