"""Unit tests for ReliableProvider and FlakyProvider telecom abstractions."""

from dialguard.telecom.events import ProviderCallEvent, TelecomEventType
from dialguard.telecom.flaky_provider import FlakyProvider
from dialguard.telecom.reliable_provider import ReliableProvider


class TestReliableProvider:
    def test_reliable_provider_health_score(self) -> None:
        provider = ReliableProvider()
        assert provider.health_score == 1.0

    def test_reliable_provider_normal_event_flow(self) -> None:
        events: list[ProviderCallEvent] = []
        provider = ReliableProvider()
        provider.register_listener(events.append)

        # Initiate
        success = provider.initiate_call("c1", "b1", "a1")
        assert success is True
        assert len(events) == 1
        assert events[0].event_type == TelecomEventType.INITIATED

        # Progress with answer
        provider.progress_call("c1", will_answer=True)
        assert len(events) == 4
        assert events[1].event_type == TelecomEventType.RINGING
        assert events[2].event_type == TelecomEventType.ANSWERED
        assert events[3].event_type == TelecomEventType.COMPLETED

    def test_reliable_provider_unanswered_flow(self) -> None:
        events: list[ProviderCallEvent] = []
        provider = ReliableProvider()
        provider.register_listener(events.append)

        provider.initiate_call("c2", "b2", "a2")
        provider.progress_call("c2", will_answer=False)

        assert len(events) == 3
        assert events[0].event_type == TelecomEventType.INITIATED
        assert events[1].event_type == TelecomEventType.RINGING
        assert events[2].event_type == TelecomEventType.FAILED

    def test_reliable_provider_cancel(self) -> None:
        events: list[ProviderCallEvent] = []
        provider = ReliableProvider()
        provider.register_listener(events.append)

        provider.initiate_call("c3", "b3")
        assert provider.cancel_call("c3") is True
        assert events[-1].event_type == TelecomEventType.FAILED
        assert events[-1].reason == "Cancelled by dialer"


class TestFlakyProvider:
    def test_flaky_provider_health_adjustment(self) -> None:
        provider = FlakyProvider(base_health_score=0.65)
        assert provider.health_score == 0.65
        provider.set_health_score(0.40)
        assert provider.health_score == 0.40

    def test_flaky_provider_out_of_order_progression(self) -> None:
        events: list[ProviderCallEvent] = []
        provider = FlakyProvider(
            timeout_rate=0.0,
            duplicate_rate=0.0,
            out_of_order_rate=1.0,
            failure_rate=0.0,
        )
        provider.register_listener(events.append)

        provider.initiate_call("c-flaky", "b-flaky")
        provider.progress_call("c-flaky", force_out_of_order=True)

        event_types = [e.event_type for e in events]
        # Inverted: ANSWERED arrives before RINGING, followed by COMPLETED
        assert event_types == [
            TelecomEventType.INITIATED,
            TelecomEventType.ANSWERED,
            TelecomEventType.RINGING,
            TelecomEventType.COMPLETED,
        ]

    def test_flaky_provider_timeout_simulation(self) -> None:
        events: list[ProviderCallEvent] = []
        provider = FlakyProvider(timeout_rate=1.0)  # Always times out
        provider.register_listener(events.append)

        success = provider.initiate_call("c-timeout", "b-timeout")
        assert success is False
        assert len(events) == 1
        assert events[0].event_type == TelecomEventType.TIMEOUT
