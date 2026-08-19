"""Flaky Mock Telecom Provider (Provider 2)."""

import random
from dialguard.telecom.events import ProviderCallEvent, TelecomEventType
from dialguard.telecom.provider import TelecomProvider


class FlakyProvider(TelecomProvider):
    """Provider 2: Simulates realistic carrier faults including duplicate events,

    out-of-order delivery, timeouts, dropped calls, and degraded health.

    Design Decision / Configurable Choices (Not explicit assignment requirements):
    - timeout_rate: 0.15 probability of timeout failure
    - duplicate_rate: 0.20 probability of emitting duplicate events
    - out_of_order_rate: 0.20 probability of inverted event delivery
    - failure_rate: 0.15 carrier network drop rate
    - base_health_score: 0.65
    """

    def __init__(
        self,
        name: str = "FlakyCarrier-Secondary",
        timeout_rate: float = 0.15,
        duplicate_rate: float = 0.20,
        out_of_order_rate: float = 0.20,
        failure_rate: float = 0.15,
        base_health_score: float = 0.65,
        auto_progress: bool = False,
    ) -> None:
        super().__init__(name=name)
        self.timeout_rate = timeout_rate
        self.duplicate_rate = duplicate_rate
        self.out_of_order_rate = out_of_order_rate
        self.failure_rate = failure_rate
        self._health_score = base_health_score
        self.auto_progress = auto_progress
        self.active_calls: set[str] = set()

    @property
    def health_score(self) -> float:
        """Return dynamically degraded health score."""
        return self._health_score

    def set_health_score(self, score: float) -> None:
        """Allow test/simulation harness to dynamically adjust carrier health."""
        self._health_score = max(0.0, min(1.0, score))

    def _emit_with_potential_duplication(self, event: ProviderCallEvent) -> None:
        """Emit event and optionally emit a duplicate with the same or different event_id."""
        self._emit(event)
        if random.random() < self.duplicate_rate:
            # Emit duplicate with identical event_id
            self._emit(
                ProviderCallEvent(
                    call_id=event.call_id,
                    event_type=event.event_type,
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    reason="Carrier duplicate transmission",
                )
            )

    def initiate_call(
        self,
        call_id: str,
        borrower_id: str,
        agent_id: str | None = None,
    ) -> bool:
        """Place an outbound call request with potential timeouts or out-of-order anomalies."""
        self.active_calls.add(call_id)

        # Timeout simulation at initiation
        if random.random() < self.timeout_rate:
            self._emit(
                ProviderCallEvent(
                    call_id=call_id,
                    event_type=TelecomEventType.TIMEOUT,
                    reason="Carrier initiation gateway timed out",
                )
            )
            self.active_calls.discard(call_id)
            return False

        self._emit_with_potential_duplication(
            ProviderCallEvent(
                call_id=call_id,
                event_type=TelecomEventType.INITIATED,
            )
        )

        if self.auto_progress:
            self.progress_call(call_id)

        return True

    def progress_call(
        self,
        call_id: str,
        force_out_of_order: bool = False,
        force_duplicate: bool = False,
    ) -> None:
        """Progress call with injected carrier anomalies."""
        if call_id not in self.active_calls:
            return

        is_out_of_order = force_out_of_order or (
            random.random() < self.out_of_order_rate
        )

        if is_out_of_order:
            # Anomaly: Emit ANSWERED before RINGING, then emit RINGING late
            ans_event = ProviderCallEvent(
                call_id=call_id,
                event_type=TelecomEventType.ANSWERED,
            )
            self._emit(ans_event)

            # Late RINGING event arrives after ANSWERED
            late_ringing = ProviderCallEvent(
                call_id=call_id,
                event_type=TelecomEventType.RINGING,
            )
            self._emit(late_ringing)

            # Now complete call
            comp_event = ProviderCallEvent(
                call_id=call_id,
                event_type=TelecomEventType.COMPLETED,
            )
            self._emit(comp_event)

            if force_duplicate or (random.random() < self.duplicate_rate):
                # Stale duplicate event after completion
                self._emit(late_ringing)

        else:
            # Orderly progression with possible duplicate / failure
            self._emit_with_potential_duplication(
                ProviderCallEvent(
                    call_id=call_id,
                    event_type=TelecomEventType.RINGING,
                )
            )

            if random.random() < self.failure_rate:
                self._emit(
                    ProviderCallEvent(
                        call_id=call_id,
                        event_type=TelecomEventType.FAILED,
                        reason="Carrier circuit disconnect",
                    )
                )
            else:
                self._emit_with_potential_duplication(
                    ProviderCallEvent(
                        call_id=call_id,
                        event_type=TelecomEventType.ANSWERED,
                    )
                )
                self._emit(
                    ProviderCallEvent(
                        call_id=call_id,
                        event_type=TelecomEventType.COMPLETED,
                    )
                )

        self.active_calls.discard(call_id)

    def cancel_call(self, call_id: str) -> bool:
        """Cancel in-flight call."""
        if call_id in self.active_calls:
            self.active_calls.discard(call_id)
            self._emit(
                ProviderCallEvent(
                    call_id=call_id,
                    event_type=TelecomEventType.FAILED,
                    reason="Cancelled by dialer",
                )
            )
            return True
        return False
