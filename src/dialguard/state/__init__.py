"""State machines and transition definitions for DialGuard."""

from dialguard.state.agent_state import (
    AGENT_TRANSITIONS,
    AgentState,
    can_transition_agent,
    validate_agent_transition,
)
from dialguard.state.call_state import (
    CALL_TRANSITIONS,
    TERMINAL_CALL_STATES,
    CallState,
    can_transition_call,
    is_terminal_call_state,
    validate_call_transition,
)

__all__ = [
    "AgentState",
    "AGENT_TRANSITIONS",
    "can_transition_agent",
    "validate_agent_transition",
    "CallState",
    "CALL_TRANSITIONS",
    "TERMINAL_CALL_STATES",
    "is_terminal_call_state",
    "can_transition_call",
    "validate_call_transition",
]
