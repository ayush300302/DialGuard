"""Unit tests for ProviderEventHandler idempotency, deduplication, and out-of-order resilience."""

from dialguard.models.agent import Agent
from dialguard.models.borrower import Borrower
from dialguard.models.call import Call
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState
from dialguard.telecom.event_handler import ProviderEventHandler
from dialguard.telecom.events import ProviderCallEvent, TelecomEventType


class TestEventHandlerIdempotencyAndSafety:
    def setup_method(self) -> None:
        self.repo = InMemoryRepository()
        self.agent = Agent(id="a1", state=AgentState.AVAILABLE)
        self.borrower = Borrower(id="b1")
        self.call = Call(id="c1", borrower_id="b1")
        self.repo.add_agent(self.agent)
        self.repo.add_borrower(self.borrower)
        self.repo.add_call(self.call)
        self.repo.reserve_agent_and_call("a1", "c1")
        self.handler = ProviderEventHandler(self.repo)

    def test_happy_path_state_synchronization(self) -> None:
        """INITIATED -> RINGING -> ANSWERED -> COMPLETED synchronizes both Call and Agent."""
        # INITIATED
        e1 = ProviderCallEvent(
            call_id="c1", event_type=TelecomEventType.INITIATED
        )
        assert self.handler.handle_event(e1) is True
        assert self.call.state == CallState.INITIATED
        assert self.agent.state == AgentState.DIALING

        # RINGING
        e2 = ProviderCallEvent(call_id="c1", event_type=TelecomEventType.RINGING)
        assert self.handler.handle_event(e2) is True
        assert self.call.state == CallState.RINGING
        assert self.agent.state == AgentState.DIALING

        # ANSWERED
        e3 = ProviderCallEvent(
            call_id="c1", event_type=TelecomEventType.ANSWERED
        )
        assert self.handler.handle_event(e3) is True
        assert self.call.state == CallState.CONNECTED
        assert self.agent.state == AgentState.CONNECTED

        # COMPLETED
        e4 = ProviderCallEvent(
            call_id="c1", event_type=TelecomEventType.COMPLETED
        )
        assert self.handler.handle_event(e4) is True
        assert self.call.state == CallState.COMPLETED
        assert self.call.is_terminal is True
        assert self.agent.state == AgentState.WRAP_UP

    def test_duplicate_event_id_is_safely_ignored(self) -> None:
        e1 = ProviderCallEvent(
            call_id="c1",
            event_type=TelecomEventType.INITIATED,
            event_id="evt-dup-1",
        )
        assert self.handler.handle_event(e1) is True
        assert self.call.state == CallState.INITIATED

        # Duplicate event with identical event_id
        e1_dup = ProviderCallEvent(
            call_id="c1",
            event_type=TelecomEventType.INITIATED,
            event_id="evt-dup-1",
        )
        assert self.handler.handle_event(e1_dup) is False
        assert self.call.state == CallState.INITIATED

    def test_duplicate_milestone_is_ignored(self) -> None:
        e1 = ProviderCallEvent(
            call_id="c1",
            event_type=TelecomEventType.INITIATED,
            event_id="evt-1",
        )
        assert self.handler.handle_event(e1) is True

        # Second INITIATED with different event_id
        e2 = ProviderCallEvent(
            call_id="c1",
            event_type=TelecomEventType.INITIATED,
            event_id="evt-2",
        )
        assert self.handler.handle_event(e2) is False
        assert self.call.state == CallState.INITIATED

    def test_events_after_terminal_state_are_safely_ignored(self) -> None:
        # Move call to COMPLETED
        self.call.state = CallState.COMPLETED

        # Late RINGING or INITIATED arrives from slow carrier
        late_event = ProviderCallEvent(
            call_id="c1",
            event_type=TelecomEventType.RINGING,
            event_id="evt-late",
        )
        assert self.handler.handle_event(late_event) is False
        assert self.call.state == CallState.COMPLETED  # State intact

    def test_out_of_order_answered_before_ringing(self) -> None:
        """Carrier delivers ANSWERED before RINGING."""
        e_init = ProviderCallEvent(
            call_id="c1", event_type=TelecomEventType.INITIATED
        )
        self.handler.handle_event(e_init)

        # Carrier skips ringing, sends ANSWERED directly
        e_ans = ProviderCallEvent(
            call_id="c1", event_type=TelecomEventType.ANSWERED
        )
        assert self.handler.handle_event(e_ans) is True
        assert self.call.state == CallState.CONNECTED
        assert self.agent.state == AgentState.CONNECTED

        # Late RINGING arrives after ANSWERED -> Ignored without error
        e_ring = ProviderCallEvent(
            call_id="c1", event_type=TelecomEventType.RINGING
        )
        assert self.handler.handle_event(e_ring) is False
        assert self.call.state == CallState.CONNECTED
