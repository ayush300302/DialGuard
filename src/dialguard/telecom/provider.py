"""Telecom provider base abstraction."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dialguard.telecom.events import ProviderCallEvent


class TelecomProvider(ABC):
    """Abstract interface for interacting with external telecom providers."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._listeners: list[Callable[[ProviderCallEvent], None]] = []

    def register_listener(
        self, callback: Callable[[ProviderCallEvent], None]
    ) -> None:
        """Register an event handler callback to receive telecom events."""
        self._listeners.append(callback)

    def _emit(self, event: ProviderCallEvent) -> None:
        """Dispatch a provider event to all registered listeners."""
        for listener in self._listeners:
            listener(event)

    @property
    @abstractmethod
    def health_score(self) -> float:
        """Return provider health score between 0.0 (dead) and 1.0 (perfect)."""

    @abstractmethod
    def initiate_call(
        self,
        call_id: str,
        borrower_id: str,
        agent_id: str | None = None,
    ) -> bool:
        """Place an outbound call request to the carrier."""

    @abstractmethod
    def cancel_call(self, call_id: str) -> bool:
        """Cancel an in-flight call before it is answered."""
