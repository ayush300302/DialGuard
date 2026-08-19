"""Collections Agent state definitions and transition rules."""

from enum import StrEnum
from dialguard.exceptions import InvalidStateTransitionError


class AgentState(StrEnum):
    """Lifecycle states of a human Collections Agent."""

    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    DIALING = "DIALING"
    CONNECTED = "CONNECTED"
    WRAP_UP = "WRAP_UP"
    PAUSED = "PAUSED"


AGENT_TRANSITIONS: dict[AgentState, frozenset[AgentState]] = {
    AgentState.OFFLINE: frozenset({
        AgentState.AVAILABLE,
        AgentState.PAUSED,
    }),
    AgentState.AVAILABLE: frozenset({
        AgentState.RESERVED,
        AgentState.PAUSED,
        AgentState.OFFLINE,
    }),
    AgentState.RESERVED: frozenset({
        AgentState.DIALING,
        AgentState.AVAILABLE,
        AgentState.OFFLINE,
    }),
    AgentState.DIALING: frozenset({
        AgentState.CONNECTED,
        AgentState.WRAP_UP,
        AgentState.AVAILABLE,
        AgentState.OFFLINE,
    }),
    AgentState.CONNECTED: frozenset({
        AgentState.WRAP_UP,
        AgentState.OFFLINE,
    }),
    AgentState.WRAP_UP: frozenset({
        AgentState.AVAILABLE,
        AgentState.PAUSED,
        AgentState.OFFLINE,
    }),
    AgentState.PAUSED: frozenset({
        AgentState.AVAILABLE,
        AgentState.OFFLINE,
    }),
}


def can_transition_agent(from_state: AgentState, to_state: AgentState) -> bool:
    """Check if transitioning between two Agent states is permitted."""
    allowed = AGENT_TRANSITIONS.get(from_state, frozenset())
    return to_state in allowed


def validate_agent_transition(
    agent_id: str,
    from_state: AgentState,
    to_state: AgentState,
) -> None:
    """Validate that an agent state transition is permitted, raising if invalid."""
    if not can_transition_agent(from_state, to_state):
        raise InvalidStateTransitionError(
            entity_type="Agent",
            entity_id=agent_id,
            from_state=from_state,
            to_state=to_state,
        )
