"""Call state definitions and transition rules."""

from enum import StrEnum
from dialguard.exceptions import InvalidStateTransitionError, TerminalStateError


class CallState(StrEnum):
    """Lifecycle states of an outbound Call to a Borrower."""

    QUEUED = "QUEUED"
    RESERVED = "RESERVED"
    INITIATED = "INITIATED"
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    CONNECTED = "CONNECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_CALL_STATES: frozenset[CallState] = frozenset({
    CallState.COMPLETED,
    CallState.FAILED,
    CallState.CANCELLED,
})


CALL_TRANSITIONS: dict[CallState, frozenset[CallState]] = {
    CallState.QUEUED: frozenset({
        CallState.RESERVED,
        CallState.CANCELLED,
    }),
    CallState.RESERVED: frozenset({
        CallState.INITIATED,
        CallState.QUEUED,
        CallState.CANCELLED,
    }),
    CallState.INITIATED: frozenset({
        CallState.RINGING,
        CallState.ANSWERED,
        CallState.FAILED,
        CallState.CANCELLED,
    }),
    CallState.RINGING: frozenset({
        CallState.ANSWERED,
        CallState.FAILED,
        CallState.CANCELLED,
    }),
    CallState.ANSWERED: frozenset({
        CallState.CONNECTED,
        CallState.COMPLETED,
        CallState.FAILED,
    }),
    CallState.CONNECTED: frozenset({
        CallState.COMPLETED,
        CallState.FAILED,
    }),
    CallState.COMPLETED: frozenset(),
    CallState.FAILED: frozenset(),
    CallState.CANCELLED: frozenset(),
}


def is_terminal_call_state(state: CallState) -> bool:
    """Check if a given Call state is terminal."""
    return state in TERMINAL_CALL_STATES


def can_transition_call(from_state: CallState, to_state: CallState) -> bool:
    """Check if transitioning between two Call states is permitted."""
    allowed = CALL_TRANSITIONS.get(from_state, frozenset())
    return to_state in allowed


def validate_call_transition(
    call_id: str,
    from_state: CallState,
    to_state: CallState,
) -> None:
    """Validate that a call state transition is permitted, raising if invalid."""
    if is_terminal_call_state(from_state):
        raise TerminalStateError(
            entity_type="Call",
            entity_id=call_id,
            terminal_state=from_state,
            attempted_state=to_state,
        )
    if not can_transition_call(from_state, to_state):
        raise InvalidStateTransitionError(
            entity_type="Call",
            entity_id=call_id,
            from_state=from_state,
            to_state=to_state,
        )
