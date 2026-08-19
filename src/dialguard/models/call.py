"""Call domain model."""

from dataclasses import dataclass
from dialguard.state.call_state import (
    CallState,
    can_transition_call,
    is_terminal_call_state,
    validate_call_transition,
)


@dataclass
class Call:
    """Represents an outbound phone interaction with a borrower."""

    id: str
    borrower_id: str
    agent_id: str | None = None
    state: CallState = CallState.QUEUED
    lease_expires_at: float | None = None
    allocated_at: float | None = None

    @property
    def is_terminal(self) -> bool:
        """Check if the call has reached a terminal lifecycle state."""
        return is_terminal_call_state(self.state)

    def can_transition_to(self, target_state: CallState) -> bool:
        """Check if call can transition to target state."""
        if self.is_terminal:
            return False
        return can_transition_call(self.state, target_state)

    def transition_to(self, target_state: CallState) -> None:
        """Transition call to target state if valid, raising if invalid.

        Ensures self.state remains unmodified on failure.
        """
        validate_call_transition(self.id, self.state, target_state)
        self.state = target_state
