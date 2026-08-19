"""Unit tests for Call state transitions, terminal states, and invariants."""

import pytest
from dialguard.exceptions import (
    InvalidStateTransitionError,
    TerminalStateError,
)
from dialguard.models.call import Call
from dialguard.state.call_state import (
    CALL_TRANSITIONS,
    TERMINAL_CALL_STATES,
    CallState,
    can_transition_call,
    is_terminal_call_state,
    validate_call_transition,
)


class TestCallInitialization:
    def test_default_call_initialization(self) -> None:
        call = Call(id="call-001", borrower_id="borrower-100")
        assert call.id == "call-001"
        assert call.borrower_id == "borrower-100"
        assert call.agent_id is None
        assert call.state == CallState.QUEUED
        assert call.is_terminal is False

    def test_explicit_call_initialization(self) -> None:
        call = Call(
            id="call-002",
            borrower_id="borrower-200",
            agent_id="agent-001",
            state=CallState.INITIATED,
        )
        assert call.agent_id == "agent-001"
        assert call.state == CallState.INITIATED


class TestCallValidTransitions:
    def test_happy_path_lifecycle(self) -> None:
        """QUEUED -> RESERVED -> INITIATED -> RINGING -> ANSWERED -> CONNECTED -> COMPLETED"""
        call = Call(id="call-happy", borrower_id="b-1")

        call.transition_to(CallState.RESERVED)
        assert call.state == CallState.RESERVED
        assert not call.is_terminal

        call.transition_to(CallState.INITIATED)
        assert call.state == CallState.INITIATED

        call.transition_to(CallState.RINGING)
        assert call.state == CallState.RINGING

        call.transition_to(CallState.ANSWERED)
        assert call.state == CallState.ANSWERED

        call.transition_to(CallState.CONNECTED)
        assert call.state == CallState.CONNECTED

        call.transition_to(CallState.COMPLETED)
        assert call.state == CallState.COMPLETED
        assert call.is_terminal is True

    def test_direct_carrier_answer_lifecycle(self) -> None:
        """Some telecom carriers skip ringing event: INITIATED -> ANSWERED -> CONNECTED -> COMPLETED"""
        call = Call(id="call-direct", borrower_id="b-2")
        call.transition_to(CallState.RESERVED)
        call.transition_to(CallState.INITIATED)
        call.transition_to(CallState.ANSWERED)
        call.transition_to(CallState.CONNECTED)
        call.transition_to(CallState.COMPLETED)
        assert call.state == CallState.COMPLETED
        assert call.is_terminal is True

    def test_unanswered_call_failed_path(self) -> None:
        """Call rings and borrower does not answer / busy: RINGING -> FAILED"""
        call = Call(id="call-busy", borrower_id="b-3")
        call.transition_to(CallState.RESERVED)
        call.transition_to(CallState.INITIATED)
        call.transition_to(CallState.RINGING)
        call.transition_to(CallState.FAILED)
        assert call.state == CallState.FAILED
        assert call.is_terminal is True

    def test_immediate_telecom_failure_path(self) -> None:
        """Invalid number or carrier congestion: INITIATED -> FAILED"""
        call = Call(id="call-err", borrower_id="b-4")
        call.transition_to(CallState.RESERVED)
        call.transition_to(CallState.INITIATED)
        call.transition_to(CallState.FAILED)
        assert call.state == CallState.FAILED
        assert call.is_terminal is True

    def test_self_service_or_ivr_completed_path(self) -> None:
        """Borrower answers and self-resolves via IVR without agent bridge: ANSWERED -> COMPLETED"""
        call = Call(id="call-ivr", borrower_id="b-5")
        call.transition_to(CallState.RESERVED)
        call.transition_to(CallState.INITIATED)
        call.transition_to(CallState.ANSWERED)
        call.transition_to(CallState.COMPLETED)
        assert call.state == CallState.COMPLETED
        assert call.is_terminal is True

    def test_reservation_timeout_release_path(self) -> None:
        """Reservation expires before dialing: RESERVED -> QUEUED"""
        call = Call(id="call-release", borrower_id="b-6")
        call.transition_to(CallState.RESERVED)
        call.transition_to(CallState.QUEUED)
        assert call.state == CallState.QUEUED

    @pytest.mark.parametrize(
        "initial_state",
        [CallState.QUEUED, CallState.RESERVED, CallState.INITIATED, CallState.RINGING],
    )
    def test_cancellation_paths(self, initial_state: CallState) -> None:
        call = Call(id="call-cancel", borrower_id="b-7", state=initial_state)
        assert call.can_transition_to(CallState.CANCELLED) is True
        call.transition_to(CallState.CANCELLED)
        assert call.state == CallState.CANCELLED
        assert call.is_terminal is True

    def test_call_dropped_in_conversation(self) -> None:
        """Call drops mid-conversation: CONNECTED -> FAILED"""
        call = Call(id="call-drop", borrower_id="b-8", state=CallState.CONNECTED)
        call.transition_to(CallState.FAILED)
        assert call.state == CallState.FAILED
        assert call.is_terminal is True


class TestCallTerminalStates:
    @pytest.mark.parametrize(
        "terminal_state",
        [CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED],
    )
    def test_terminal_states_reject_all_outgoing_transitions(
        self, terminal_state: CallState
    ) -> None:
        call = Call(id="call-term", borrower_id="b-term", state=terminal_state)
        assert call.is_terminal is True

        for target_state in CallState:
            assert call.can_transition_to(target_state) is False
            with pytest.raises(TerminalStateError) as exc_info:
                call.transition_to(target_state)

            assert exc_info.value.entity_type == "Call"
            assert exc_info.value.entity_id == "call-term"
            assert exc_info.value.from_state == terminal_state
            assert exc_info.value.to_state == target_state

        # State must remain unmodified
        assert call.state == terminal_state


class TestCallInvalidTransitions:
    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            # Cannot jump from QUEUED directly to CONNECTED or RINGING
            (CallState.QUEUED, CallState.CONNECTED),
            (CallState.QUEUED, CallState.RINGING),
            (CallState.QUEUED, CallState.ANSWERED),
            # Cannot jump from INITIATED directly to CONNECTED (must go through ANSWERED)
            (CallState.INITIATED, CallState.CONNECTED),
            # Cannot jump from RINGING directly to CONNECTED (must go through ANSWERED)
            (CallState.RINGING, CallState.CONNECTED),
            # Self-transitions are not permitted
            (CallState.QUEUED, CallState.QUEUED),
            (CallState.RINGING, CallState.RINGING),
            (CallState.CONNECTED, CallState.CONNECTED),
            # Cannot regress from CONNECTED back to INITIATED/RINGING
            (CallState.CONNECTED, CallState.INITIATED),
            (CallState.CONNECTED, CallState.RINGING),
            (CallState.CONNECTED, CallState.QUEUED),
        ],
    )
    def test_invalid_transitions_raise_error(
        self, from_state: CallState, to_state: CallState
    ) -> None:
        call = Call(id="call-invalid", borrower_id="b-inv", state=from_state)
        assert call.can_transition_to(to_state) is False

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            call.transition_to(to_state)

        assert exc_info.value.entity_type == "Call"
        assert exc_info.value.entity_id == "call-invalid"
        assert exc_info.value.from_state == from_state
        assert exc_info.value.to_state == to_state

    def test_invalid_transition_does_not_mutate_state(self) -> None:
        call = Call(id="call-preserve", borrower_id="b-pres", state=CallState.RINGING)

        with pytest.raises(InvalidStateTransitionError):
            call.transition_to(CallState.CONNECTED)

        assert call.state == CallState.RINGING

    def test_exhaustively_check_all_undefined_transitions_are_rejected(self) -> None:
        """Ensure any transition not explicitly defined in CALL_TRANSITIONS is rejected."""
        all_states = list(CallState)
        for from_state in all_states:
            allowed = CALL_TRANSITIONS.get(from_state, frozenset())
            for target_state in all_states:
                if target_state not in allowed:
                    assert can_transition_call(from_state, target_state) is False
                    with pytest.raises(InvalidStateTransitionError):
                        validate_call_transition("call-x", from_state, target_state)
