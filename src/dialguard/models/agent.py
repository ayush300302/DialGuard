"""Collections Agent domain model."""

from dataclasses import dataclass
from dialguard.state.agent_state import (
    AgentState,
    can_transition_agent,
    validate_agent_transition,
)


@dataclass
class Agent:
    """Represents a human collections agent who communicates with borrowers."""

    id: str
    state: AgentState = AgentState.OFFLINE

    def can_transition_to(self, target_state: AgentState) -> bool:
        """Check if agent can transition to target state."""
        return can_transition_agent(self.state, target_state)

    def transition_to(self, target_state: AgentState) -> None:
        """Transition agent to target state if valid, raising if invalid.

        Ensures self.state remains unmodified on failure.
        """
        validate_agent_transition(self.id, self.state, target_state)
        self.state = target_state
