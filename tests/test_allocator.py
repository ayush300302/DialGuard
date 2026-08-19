"""Unit and concurrency tests for CallAllocator and InMemoryRepository."""

from concurrent.futures import ThreadPoolExecutor
from dialguard.allocator.call_allocator import CallAllocator
from dialguard.models.agent import Agent
from dialguard.models.borrower import Borrower
from dialguard.models.call import Call
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState


class TestCallAllocatorBasics:
    def test_single_allocation_success(self) -> None:
        repo = InMemoryRepository()
        repo.add_agent(Agent(id="a1", state=AgentState.AVAILABLE))
        repo.add_borrower(Borrower(id="b1"))
        repo.add_call(Call(id="c1", borrower_id="b1"))

        allocator = CallAllocator(repo, default_lease_duration=30.0)
        pair = allocator.allocate_single()

        assert pair is not None
        agent, call = pair
        assert agent.id == "a1"
        assert agent.state == AgentState.RESERVED
        assert call.id == "c1"
        assert call.agent_id == "a1"
        assert call.state == CallState.RESERVED
        assert call.lease_expires_at is not None

    def test_cannot_allocate_when_no_agent_available(self) -> None:
        repo = InMemoryRepository()
        repo.add_agent(Agent(id="a1", state=AgentState.PAUSED))
        repo.add_borrower(Borrower(id="b1"))
        repo.add_call(Call(id="c1", borrower_id="b1"))

        allocator = CallAllocator(repo)
        pair = allocator.allocate_single()
        assert pair is None

    def test_cannot_allocate_when_no_calls_queued(self) -> None:
        repo = InMemoryRepository()
        repo.add_agent(Agent(id="a1", state=AgentState.AVAILABLE))

        allocator = CallAllocator(repo)
        pair = allocator.allocate_single()
        assert pair is None

    def test_prevents_duplicate_active_borrower_call(self) -> None:
        """Borrower already has an in-flight call; second call for same borrower must not allocate."""
        repo = InMemoryRepository()
        repo.add_agent(Agent(id="a1", state=AgentState.AVAILABLE))
        repo.add_agent(Agent(id="a2", state=AgentState.AVAILABLE))

        repo.add_borrower(Borrower(id="b1"))
        repo.add_call(
            Call(
                id="c1",
                borrower_id="b1",
                agent_id="a1",
                state=CallState.CONNECTED,
            )
        )
        repo.add_call(Call(id="c2", borrower_id="b1", state=CallState.QUEUED))

        allocator = CallAllocator(repo)
        # Attempt to allocate c2 for b1 while c1 is active
        pairs = allocator.allocate_batch(max_allocations=2)
        assert len(pairs) == 0


class TestCallAllocatorConcurrency:
    def test_concurrent_workers_cannot_double_book_agent(self) -> None:
        """10 concurrent workers competing for 1 available agent and 1 queued call."""
        repo = InMemoryRepository()
        repo.add_agent(Agent(id="agent-solo", state=AgentState.AVAILABLE))
        repo.add_borrower(Borrower(id="b-solo"))
        repo.add_call(Call(id="call-solo", borrower_id="b-solo"))

        allocator = CallAllocator(repo)

        successful_allocations: list[tuple[Agent, Call]] = []

        def worker_task() -> None:
            res = allocator.allocate_single()
            if res is not None:
                successful_allocations.append(res)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_task) for _ in range(10)]
            for f in futures:
                f.result()

        # Exactly 1 worker must succeed
        assert len(successful_allocations) == 1
        agent, call = successful_allocations[0]
        assert agent.state == AgentState.RESERVED
        assert call.state == CallState.RESERVED
        assert call.agent_id == "agent-solo"
