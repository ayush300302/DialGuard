"""Unit tests for Progressive and Predictive dialers."""

from dialguard.allocator.call_allocator import CallAllocator
from dialguard.dialer.predictive import PredictiveDialer
from dialguard.dialer.progressive import ProgressiveDialer
from dialguard.models.agent import Agent
from dialguard.models.borrower import Borrower
from dialguard.models.call import Call
from dialguard.pacing.engine import PredictivePacingEngine
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.safety.safety_controller import SafetyController
from dialguard.state.agent_state import AgentState
from dialguard.telecom.reliable_provider import ReliableProvider


class TestDialers:
    def setup_method(self) -> None:
        self.repo = InMemoryRepository()
        for i in range(1, 6):
            self.repo.add_agent(
                Agent(id=f"a{i}", state=AgentState.AVAILABLE)
            )
            self.repo.add_borrower(Borrower(id=f"b{i}"))
            self.repo.add_call(Call(id=f"c{i}", borrower_id=f"b{i}"))

        self.allocator = CallAllocator(self.repo)
        self.safety = SafetyController()
        self.pacing = PredictivePacingEngine()
        self.provider = ReliableProvider()

    def test_progressive_dialer_exact_one_to_one(self) -> None:
        dialer = ProgressiveDialer(
            repository=self.repo,
            allocator=self.allocator,
            safety_controller=self.safety,
            provider=self.provider,
        )

        res = dialer.execute_cycle()
        assert res.requested_calls == 5
        assert res.approved_calls == 5
        assert res.initiated_calls == 5
        assert len(res.allocated_pairs) == 5

        # All 5 agents are now reserved
        assert len(self.repo.get_available_agents()) == 0

    def test_predictive_dialer_orchestration_passes_safety(self) -> None:
        dialer = PredictiveDialer(
            repository=self.repo,
            allocator=self.allocator,
            pacing_engine=self.pacing,
            safety_controller=self.safety,
            provider=self.provider,
        )

        # 5 available agents, answer rate 0.50 -> recommends 10 dials
        # But Safety Controller caps max in-flight and allocator reserves available pairs (5)
        res = dialer.execute_cycle(recent_answer_rate=0.50)
        assert res.pacing_recommendation.recommended_dials == 10
        assert res.safety_decision.approved is True
        assert res.initiated_calls == 5
        assert len(res.allocated_pairs) == 5
