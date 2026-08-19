"""Failure Recovery Supervisor for DialGuard."""

import logging
import time
from dialguard.exceptions import InvalidStateTransitionError
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState

logger = logging.getLogger(__name__)


class RecoverySupervisor:
    """Monitors and recovers system state from worker crashes and provider timeouts.

    Design Decisions / Configurable Choices (Not explicit assignment requirements):
    - max_in_flight_timeout_seconds: 60.0s threshold to recover calls stuck in INITIATED/RINGING.
    """

    def __init__(
        self,
        repository: InMemoryRepository,
        max_in_flight_timeout_seconds: float = 60.0,
    ) -> None:
        self.repository = repository
        self.max_in_flight_timeout_seconds = max_in_flight_timeout_seconds

    def sweep_expired_leases(
        self, current_time: float | None = None
    ) -> list[str]:
        """Release agent and call reservations where the worker lease has expired."""
        recovered = self.repository.release_expired_leases(
            current_time=current_time
        )
        if recovered:
            logger.info("Recovered %d expired call reservations: %s", len(recovered), recovered)
        return recovered

    def sweep_stuck_in_flight_calls(
        self, current_time: float | None = None
    ) -> list[str]:
        """Recover calls stuck in INITIATED or RINGING without provider event updates."""
        now = time.time() if current_time is None else current_time
        stuck_call_ids: list[str] = []

        with self.repository._lock:
            active_calls = self.repository.get_active_calls()
            for call in active_calls:
                if call.state in (CallState.INITIATED, CallState.RINGING):
                    # Check if call exceeded maximum in-flight duration
                    allocated_time = call.allocated_at or (now - self.max_in_flight_timeout_seconds - 1)
                    if (now - allocated_time) >= self.max_in_flight_timeout_seconds:
                        logger.warning(
                            "Call '%s' stuck in '%s' for >%.1fs. Marking FAILED.",
                            call.id,
                            call.state,
                            self.max_in_flight_timeout_seconds,
                        )
                        assigned_agent_id = call.agent_id
                        try:
                            call.transition_to(CallState.FAILED)
                            stuck_call_ids.append(call.id)
                        except InvalidStateTransitionError:
                            pass

                        # Free assigned agent
                        if assigned_agent_id:
                            agent = self.repository.get_agent(assigned_agent_id)
                            if agent and agent.can_transition_to(AgentState.AVAILABLE):
                                agent.transition_to(AgentState.AVAILABLE)

        return stuck_call_ids

    def run_full_recovery_cycle(
        self, current_time: float | None = None
    ) -> dict[str, list[str]]:
        """Run all recovery sweeps and return summary of recovered entities."""
        expired_leases = self.sweep_expired_leases(current_time=current_time)
        stuck_calls = self.sweep_stuck_in_flight_calls(current_time=current_time)
        return {
            "expired_leases": expired_leases,
            "stuck_calls": stuck_calls,
        }
