"""Call Allocator component for matching available agents with queued calls."""

from dialguard.models.agent import Agent
from dialguard.models.call import Call
from dialguard.repository.in_memory import InMemoryRepository


class CallAllocator:
    """Allocates available human collections agents to queued borrower calls safely.

    Design Decision / Configurable Choice:
    - default_lease_duration: Defaults to 30.0 seconds. This is a design choice
      for the local prototype to allow lease expiry and failure recovery if a worker
      crashes after reserving, not an explicit requirement of the assignment.
    """

    def __init__(
        self,
        repository: InMemoryRepository,
        default_lease_duration: float = 30.0,
    ) -> None:
        self.repository = repository
        self.default_lease_duration = default_lease_duration

    def allocate_batch(
        self,
        max_allocations: int | None = None,
        lease_duration: float | None = None,
    ) -> list[tuple[Agent, Call]]:
        """Atomically find available agents and queued calls, reserving them.

        Returns a list of reserved (Agent, Call) pairs.
        Guarantees that no agent or borrower is double-allocated across concurrent callers.
        """
        duration = (
            self.default_lease_duration if lease_duration is None else lease_duration
        )
        allocated_pairs: list[tuple[Agent, Call]] = []

        # Lock critical section during candidate selection & reservation
        with self.repository._lock:
            available_agents = self.repository.get_available_agents()
            queued_calls = self.repository.get_queued_calls()

            limit = len(available_agents)
            if max_allocations is not None:
                limit = min(limit, max_allocations)

            limit = min(limit, len(queued_calls))

            agent_idx = 0
            call_idx = 0

            while (
                len(allocated_pairs) < limit
                and agent_idx < len(available_agents)
                and call_idx < len(queued_calls)
            ):
                agent = available_agents[agent_idx]
                call = queued_calls[call_idx]
                agent_idx += 1
                call_idx += 1

                # Attempt atomic reservation
                success = self.repository.reserve_agent_and_call(
                    agent_id=agent.id,
                    call_id=call.id,
                    lease_duration_seconds=duration,
                )
                if success:
                    allocated_pairs.append((agent, call))

        return allocated_pairs

    def allocate_single(
        self, lease_duration: float | None = None
    ) -> tuple[Agent, Call] | None:
        """Atomically allocate a single available agent and queued call."""
        results = self.allocate_batch(max_allocations=1, lease_duration=lease_duration)
        return results[0] if results else None
