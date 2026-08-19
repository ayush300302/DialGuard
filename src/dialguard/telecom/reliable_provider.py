"""Reliable Mock Telecom Provider (Provider 1)."""

import random
from dialguard.telecom.events import ProviderCallEvent, TelecomEventType
from dialguard.telecom.provider import TelecomProvider


class ReliableProvider(TelecomProvider):
    """Provider 1: Fast, reliable, with orderly and deterministic event sequences.

    Design Decision / Configurable Choices:
    - default_answer_rate: 0.40 (used when auto_progressing without an explicit outcome)
    - auto_progress: If True, automatically dispatches full event sequences.
    """

    def __init__(
        self,
        name: str = "ReliableCarrier-Primary",
        default_answer_rate: float = 0.40,
        auto_progress: bool = False,
    ) -> None:
        super().__init__(name=name)
        self.default_answer_rate = default_answer_rate
        self.auto_progress = auto_progress
        self.active_calls: set[str] = set()

    @property
    def health_score(self) -> float:
        """Provider 1 maintains optimal health."""
        return 1.0

    def initiate_call(
        self,
        call_id: str,
        borrower_id: str,
        agent_id: str | None = None,
    ) -> bool:
        """Initiate call and dispatch INITIATED event."""
        self.active_calls.add(call_id)
        self._emit(
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
        will_answer: bool | None = None,
    ) -> None:
        """Progress an active call through its lifecycle in orderly sequence."""
        if call_id not in self.active_calls:
            return

        # Emit RINGING
        self._emit(
            ProviderCallEvent(
                call_id=call_id,
                event_type=TelecomEventType.RINGING,
            )
        )

        answered = (
            will_answer
            if will_answer is not None
            else (random.random() < self.default_answer_rate)
        )

        if answered:
            self._emit(
                ProviderCallEvent(
                    call_id=call_id,
                    event_type=TelecomEventType.ANSWERED,
                )
            )
            # Call completes
            self._emit(
                ProviderCallEvent(
                    call_id=call_id,
                    event_type=TelecomEventType.COMPLETED,
                    reason="Normal call termination",
                )
            )
        else:
            self._emit(
                ProviderCallEvent(
                    call_id=call_id,
                    event_type=TelecomEventType.FAILED,
                    reason="Borrower unanswered / busy",
                )
            )

        self.active_calls.discard(call_id)

    def cancel_call(self, call_id: str) -> bool:
        """Cancel an in-flight call."""
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
