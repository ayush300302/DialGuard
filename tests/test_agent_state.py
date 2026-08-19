"""Unit tests for Collections Agent state transitions and invariants."""

import pytest
from dialguard.exceptions import InvalidStateTransitionError
from dialguard.models.agent import Agent
from dialguard.state.agent_state import (
    AGENT_TRANSITIONS,
    AgentState,
    can_transition_agent,
    validate_agent_transition,
)


class TestAgentInitialization:
    def test_default_agent_state_is_offline(self) -> None:
        agent = Agent(id="agent-001")
        assert agent.id == "agent-001"
        assert agent.state == AgentState.OFFLINE

    def test_explicit_agent_state_initialization(self) -> None:
        agent = Agent(id="agent-002", state=AgentState.AVAILABLE)
        assert agent.state == AgentState.AVAILABLE


class TestAgentValidTransitions:
    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            # From OFFLINE
            (AgentState.OFFLINE, AgentState.AVAILABLE),
            (AgentState.OFFLINE, AgentState.PAUSED),
            # From AVAILABLE
            (AgentState.AVAILABLE, AgentState.RESERVED),
            (AgentState.AVAILABLE, AgentState.PAUSED),
            (AgentState.AVAILABLE, AgentState.OFFLINE),
            # From RESERVED
            (AgentState.RESERVED, AgentState.DIALING),
            (AgentState.RESERVED, AgentState.AVAILABLE),
            (AgentState.RESERVED, AgentState.OFFLINE),
            # From DIALING
            (AgentState.DIALING, AgentState.CONNECTED),
            (AgentState.DIALING, AgentState.WRAP_UP),
            (AgentState.DIALING, AgentState.AVAILABLE),
            (AgentState.DIALING, AgentState.OFFLINE),
            # From CONNECTED
            (AgentState.CONNECTED, AgentState.WRAP_UP),
            (AgentState.CONNECTED, AgentState.OFFLINE),
            # From WRAP_UP
            (AgentState.WRAP_UP, AgentState.AVAILABLE),
            (AgentState.WRAP_UP, AgentState.PAUSED),
            (AgentState.WRAP_UP, AgentState.OFFLINE),
            # From PAUSED
            (AgentState.PAUSED, AgentState.AVAILABLE),
            (AgentState.PAUSED, AgentState.OFFLINE),
        ],
    )
    def test_valid_transitions_succeed(
        self, from_state: AgentState, to_state: AgentState
    ) -> None:
        agent = Agent(id="agent-test", state=from_state)
        assert agent.can_transition_to(to_state) is True
        agent.transition_to(to_state)
        assert agent.state == to_state

    def test_full_operational_lifecycle(self) -> None:
        """Test a complete end-to-end agent shift lifecycle."""
        agent = Agent(id="agent-shift")
        assert agent.state == AgentState.OFFLINE

        # Login -> Available
        agent.transition_to(AgentState.AVAILABLE)
        assert agent.state == AgentState.AVAILABLE

        # Reserved by dialer -> Dialing
        agent.transition_to(AgentState.RESERVED)
        agent.transition_to(AgentState.DIALING)

        # Call connects -> In conversation
        agent.transition_to(AgentState.CONNECTED)

        # Call ends -> Post-call wrap-up
        agent.transition_to(AgentState.WRAP_UP)

        # Finished notes -> Take a quick break
        agent.transition_to(AgentState.PAUSED)

        # Return from break -> Available
        agent.transition_to(AgentState.AVAILABLE)

        # End of shift -> Logout
        agent.transition_to(AgentState.OFFLINE)
        assert agent.state == AgentState.OFFLINE


class TestAgentInvalidTransitions:
    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            # Cannot jump directly to connected without dialing
            (AgentState.OFFLINE, AgentState.CONNECTED),
            (AgentState.AVAILABLE, AgentState.CONNECTED),
            # Cannot jump directly to dialing from offline/available
            (AgentState.OFFLINE, AgentState.DIALING),
            (AgentState.AVAILABLE, AgentState.DIALING),
            # Cannot skip wrap_up directly to available from connected
            (AgentState.CONNECTED, AgentState.AVAILABLE),
            (AgentState.CONNECTED, AgentState.PAUSED),
            # Cannot reserve an offline or paused agent
            (AgentState.OFFLINE, AgentState.RESERVED),
            (AgentState.PAUSED, AgentState.RESERVED),
            # Self-transitions are not permitted
            (AgentState.AVAILABLE, AgentState.AVAILABLE),
            (AgentState.CONNECTED, AgentState.CONNECTED),
            (AgentState.PAUSED, AgentState.PAUSED),
        ],
    )
    def test_invalid_transitions_raise_error(
        self, from_state: AgentState, to_state: AgentState
    ) -> None:
        agent = Agent(id="agent-err", state=from_state)
        assert agent.can_transition_to(to_state) is False

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            agent.transition_to(to_state)

        assert exc_info.value.entity_type == "Agent"
        assert exc_info.value.entity_id == "agent-err"
        assert exc_info.value.from_state == from_state
        assert exc_info.value.to_state == to_state

    def test_invalid_transition_does_not_mutate_state(self) -> None:
        agent = Agent(id="agent-preserve", state=AgentState.AVAILABLE)

        with pytest.raises(InvalidStateTransitionError):
            agent.transition_to(AgentState.CONNECTED)

        assert agent.state == AgentState.AVAILABLE

    def test_exhaustively_check_all_undefined_transitions_are_rejected(self) -> None:
        """Ensure any transition not explicitly in AGENT_TRANSITIONS is rejected."""
        all_states = list(AgentState)
        for from_state in all_states:
            allowed = AGENT_TRANSITIONS.get(from_state, frozenset())
            for target_state in all_states:
                if target_state not in allowed:
                    assert can_transition_agent(from_state, target_state) is False
                    with pytest.raises(InvalidStateTransitionError):
                        validate_agent_transition("agent-x", from_state, target_state)
