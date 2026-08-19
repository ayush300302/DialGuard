"""Thread-safe in-memory repository for DialGuard domain entities."""

import threading
import time
from dialguard.exceptions import InvalidStateTransitionError
from dialguard.models.agent import Agent
from dialguard.models.borrower import Borrower
from dialguard.models.call import Call
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState, TERMINAL_CALL_STATES


class InMemoryRepository:
    """Thread-safe in-memory store for Agents, Calls, and Borrowers.

    Concurrency Design Decision (Prototype Choice):
    Uses a reentrant thread lock (threading.RLock) around all mutation and query
    critical sections to ensure atomic multi-worker access in a local environment.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._agents: dict[str, Agent] = {}
        self._calls: dict[str, Call] = {}
        self._borrowers: dict[str, Borrower] = {}

    def add_agent(self, agent: Agent) -> None:
        """Store an agent in the repository."""
        with self._lock:
            self._agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> Agent | None:
        """Retrieve an agent by ID."""
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> list[Agent]:
        """Return a copy of all registered agents."""
        with self._lock:
            return list(self._agents.values())

    def get_available_agents(self) -> list[Agent]:
        """Return all agents currently in the AVAILABLE state."""
        with self._lock:
            return [
                a for a in self._agents.values() if a.state == AgentState.AVAILABLE
            ]

    def add_borrower(self, borrower: Borrower) -> None:
        """Store a borrower in the repository."""
        with self._lock:
            self._borrowers[borrower.id] = borrower

    def get_borrower(self, borrower_id: str) -> Borrower | None:
        """Retrieve a borrower by ID."""
        with self._lock:
            return self._borrowers.get(borrower_id)

    def add_call(self, call: Call) -> None:
        """Store a call in the repository."""
        with self._lock:
            self._calls[call.id] = call

    def get_call(self, call_id: str) -> Call | None:
        """Retrieve a call by ID."""
        with self._lock:
            return self._calls.get(call_id)

    def list_calls(self) -> list[Call]:
        """Return a copy of all registered calls."""
        with self._lock:
            return list(self._calls.values())

    def get_queued_calls(self) -> list[Call]:
        """Return all calls currently in the QUEUED state."""
        with self._lock:
            return [c for c in self._calls.values() if c.state == CallState.QUEUED]

    def get_active_calls(self) -> list[Call]:
        """Return all non-terminal calls."""
        with self._lock:
            return [
                c
                for c in self._calls.values()
                if c.state not in TERMINAL_CALL_STATES
            ]

    def get_calls_by_state(self, state: CallState) -> list[Call]:
        """Return all calls currently in the specified state."""
        with self._lock:
            return [c for c in self._calls.values() if c.state == state]

    def has_active_call_for_borrower(
        self, borrower_id: str, exclude_call_id: str | None = None
    ) -> bool:
        """Check if borrower already has an active (non-terminal) call."""
        with self._lock:
            for call in self._calls.values():
                if call.borrower_id == borrower_id and not call.is_terminal:
                    if exclude_call_id and call.id == exclude_call_id:
                        continue
                    return True
            return False

    def reserve_agent_and_call(
        self,
        agent_id: str,
        call_id: str,
        lease_duration_seconds: float = 30.0,
        current_time: float | None = None,
    ) -> bool:
        """Atomically reserve an available agent and a queued call.

        Returns True if reservation succeeded; False if either agent or call
        is no longer in an eligible state or the borrower already has an active call.
        """
        now = time.time() if current_time is None else current_time
        with self._lock:
            agent = self._agents.get(agent_id)
            call = self._calls.get(call_id)

            if agent is None or agent.state != AgentState.AVAILABLE:
                return False

            if call is None or call.state != CallState.QUEUED:
                return False

            # Invariant: prevent duplicate active calls for the same borrower
            if self.has_active_call_for_borrower(
                call.borrower_id, exclude_call_id=call.id
            ):
                return False

            try:
                agent.transition_to(AgentState.RESERVED)
                call.agent_id = agent.id
                call.lease_expires_at = now + lease_duration_seconds
                call.allocated_at = now
                call.transition_to(CallState.RESERVED)
                return True
            except InvalidStateTransitionError:
                return False

    def release_expired_leases(
        self, current_time: float | None = None
    ) -> list[str]:
        """Scan for expired RESERVED call leases and release both call and agent.

        Returns a list of recovered call IDs.
        """
        now = time.time() if current_time is None else current_time
        recovered_call_ids: list[str] = []

        with self._lock:
            for call in self._calls.values():
                if (
                    call.state == CallState.RESERVED
                    and call.lease_expires_at is not None
                    and call.lease_expires_at <= now
                ):
                    assigned_agent_id = call.agent_id

                    # Return call to QUEUED
                    call.lease_expires_at = None
                    call.agent_id = None
                    try:
                        call.transition_to(CallState.QUEUED)
                        recovered_call_ids.append(call.id)
                    except InvalidStateTransitionError:
                        pass

                    # Return agent to AVAILABLE if still in RESERVED
                    if assigned_agent_id:
                        agent = self._agents.get(assigned_agent_id)
                        if agent and agent.state == AgentState.RESERVED:
                            try:
                                agent.transition_to(AgentState.AVAILABLE)
                            except InvalidStateTransitionError:
                                pass

        return recovered_call_ids

    def clear(self) -> None:
        """Clear all entities from the repository (useful for test setup)."""
        with self._lock:
            self._agents.clear( )
            self._calls.clear()
            self._borrowers.clear()
