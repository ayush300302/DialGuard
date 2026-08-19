"""Load and high-concurrency stress test for CallAllocator."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dialguard.allocator.call_allocator import CallAllocator
from dialguard.models.agent import Agent
from dialguard.models.borrower import Borrower
from dialguard.models.call import Call
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState


class TestLoadAndConcurrency:
    def test_high_concurrency_multi_worker_allocation_integrity(self) -> None:
        """Stress test: 50 agents and 500 borrower calls with 30 concurrent workers

        hammering the allocator simultaneously.
        """
        repo = InMemoryRepository()
        num_agents = 50
        num_borrowers = 500

        # Seed agents
        for i in range(1, num_agents + 1):
            repo.add_agent(Agent(id=f"agent-{i:03d}", state=AgentState.AVAILABLE))

        # Seed borrowers & calls
        for i in range(1, num_borrowers + 1):
            b = Borrower(id=f"borrower-{i:04d}")
            repo.add_borrower(b)
            c = Call(id=f"call-{i:04d}", borrower_id=b.id, state=CallState.QUEUED)
            repo.add_call(c)

        allocator = CallAllocator(repo, default_lease_duration=60.0)

        allocated_results: list[tuple[Agent, Call]] = []
        lock = threading.Lock()

        def worker_loop() -> None:
            # Each worker attempts to allocate up to 5 pairs repeatedly
            for _ in range(20):
                pairs = allocator.allocate_batch(max_allocations=5)
                if pairs:
                    with lock:
                        allocated_results.extend(pairs)

        num_workers = 30
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_loop) for _ in range(num_workers)]
            for f in as_completed(futures):
                f.result()

        # Invariants verification:
        # 1. Total allocated pairs must exactly equal total available agents (50)
        assert len(allocated_results) == num_agents

        allocated_agent_ids = [agent.id for agent, _ in allocated_results]
        allocated_call_ids = [call.id for _, call in allocated_results]
        allocated_borrower_ids = [call.borrower_id for _, call in allocated_results]

        # 2. No agent is double-booked (unique agent IDs)
        assert len(allocated_agent_ids) == len(set(allocated_agent_ids))

        # 3. No call is double-allocated (unique call IDs)
        assert len(allocated_call_ids) == len(set(allocated_call_ids))

        # 4. No borrower is double-allocated (unique borrower IDs)
        assert len(allocated_borrower_ids) == len(set(allocated_borrower_ids))

        # 5. State invariants: All allocated agents and calls are in RESERVED state
        for agent, call in allocated_results:
            assert agent.state == AgentState.RESERVED
            assert call.state == CallState.RESERVED
            assert call.agent_id == agent.id

        # 6. Repository state integrity: 0 available agents left, 450 queued calls left
        assert len(repo.get_available_agents()) == 0
        assert len(repo.get_queued_calls()) == (num_borrowers - num_agents)
