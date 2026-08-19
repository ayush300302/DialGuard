"""Unit tests for Failure Recovery supervisor and lease expiry sweeps."""

from dialguard.models.agent import Agent
from dialguard.models.borrower import Borrower
from dialguard.models.call import Call
from dialguard.recovery.supervisor import RecoverySupervisor
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState


class TestRecoverySupervisor:
    def test_recovers_expired_reservations_after_worker_crash(self) -> None:
        repo = InMemoryRepository()
        repo.add_agent(Agent(id="a-crash", state=AgentState.AVAILABLE))
        repo.add_borrower(Borrower(id="b-crash"))
        repo.add_call(Call(id="c-crash", borrower_id="b-crash"))

        # Worker reserves with 10s lease at t=100
        repo.reserve_agent_and_call(
            "a-crash", "c-crash", lease_duration_seconds=10.0, current_time=100.0
        )

        agent = repo.get_agent("a-crash")
        call = repo.get_call("c-crash")
        assert agent.state == AgentState.RESERVED
        assert call.state == CallState.RESERVED

        supervisor = RecoverySupervisor(repo)

        # At t=105 (lease not yet expired)
        recovered_early = supervisor.sweep_expired_leases(current_time=105.0)
        assert len(recovered_early) == 0
        assert agent.state == AgentState.RESERVED
        assert call.state == CallState.RESERVED

        # At t=115 (lease expired) -> Worker crashed and never finished
        recovered_late = supervisor.sweep_expired_leases(current_time=115.0)
        assert len(recovered_late) == 1
        assert recovered_late[0] == "c-crash"

        # Both entities returned to clean pool
        assert call.state == CallState.QUEUED
        assert call.agent_id is None
        assert agent.state == AgentState.AVAILABLE

    def test_recovers_stuck_in_flight_calls(self) -> None:
        repo = InMemoryRepository()
        repo.add_agent(Agent(id="a-stuck", state=AgentState.DIALING))
        repo.add_borrower(Borrower(id="b-stuck"))
        call = Call(
            id="c-stuck",
            borrower_id="b-stuck",
            agent_id="a-stuck",
            state=CallState.INITIATED,
            allocated_at=100.0,
        )
        repo.add_call(call)

        supervisor = RecoverySupervisor(
            repo, max_in_flight_timeout_seconds=60.0
        )

        # At t=170 (70s passed > 60s timeout)
        stuck_recovered = supervisor.sweep_stuck_in_flight_calls(
            current_time=170.0
        )
        assert len(stuck_recovered) == 1
        assert stuck_recovered[0] == "c-stuck"
        assert call.state == CallState.FAILED
        assert repo.get_agent("a-stuck").state == AgentState.AVAILABLE
