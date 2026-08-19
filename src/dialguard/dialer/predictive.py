"""Predictive Dialer orchestrating Pacing Engine, Safety Controller, and Allocator."""

from dataclasses import dataclass, field
import logging
from dialguard.allocator.call_allocator import CallAllocator
from dialguard.models.agent import Agent
from dialguard.models.call import Call
from dialguard.pacing.engine import (
    PacingInputs,
    PacingRecommendation,
    PredictivePacingEngine,
)
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.safety.safety_controller import (
    SafetyContext,
    SafetyController,
    SafetyDecision,
)
from dialguard.state.agent_state import AgentState
from dialguard.state.call_state import CallState
from dialguard.telecom.provider import TelecomProvider

logger = logging.getLogger(__name__)


@dataclass
class PredictiveDialingResult:
    """Detailed summary of a predictive dialing cycle."""

    pacing_recommendation: PacingRecommendation
    safety_decision: SafetyDecision
    initiated_calls: int
    allocated_pairs: list[tuple[Agent, Call]] = field(default_factory=list)


class PredictiveDialer:
    """Predictive Dialer orchestrator.

    Architecture Rule:
    Pacing Engine -> Safety Controller -> Call Allocator -> Provider

    The Pacing Engine recommends dial volume based on statistics, while the Safety Controller
    retains strict, deterministic authority to approve, throttle, or reject the request.
    """

    def __init__(
        self,
        repository: InMemoryRepository,
        allocator: CallAllocator,
        pacing_engine: PredictivePacingEngine,
        safety_controller: SafetyController,
        provider: TelecomProvider,
    ) -> None:
        self.repository = repository
        self.allocator = allocator
        self.pacing_engine = pacing_engine
        self.safety_controller = safety_controller
        self.provider = provider

    def execute_cycle(
        self,
        recent_answer_rate: float = 0.30,
        avg_call_duration_seconds: float = 120.0,
    ) -> PredictiveDialingResult:
        """Execute one predictive pacing and dialing cycle."""
        all_agents = self.repository.list_agents()
        available_agents = self.repository.get_available_agents()
        connected_calls = len(
            self.repository.get_calls_by_state(CallState.CONNECTED)
        )
        in_flight_calls = len(
            self.repository.get_calls_by_state(CallState.INITIATED)
        ) + len(self.repository.get_calls_by_state(CallState.RINGING))

        # 1. Calculate statistical recommendation from Pacing Engine
        pacing_inputs = PacingInputs(
            available_agents=len(available_agents),
            connected_calls=connected_calls,
            ringing_or_dialing_calls=in_flight_calls,
            recent_answer_rate=recent_answer_rate,
            avg_call_duration_seconds=avg_call_duration_seconds,
            provider_health=self.provider.health_score,
        )
        recommendation = self.pacing_engine.calculate_recommendation(
            pacing_inputs
        )

        # 2. Evaluate with Safety Controller
        safety_context = SafetyContext(
            total_agents=len(all_agents),
            available_agents=len(available_agents),
            reserved_agents=len(
                [a for a in all_agents if a.state.name == "RESERVED"]
            ),
            connected_calls=connected_calls,
            ringing_or_dialing_calls=in_flight_calls,
            provider_health=self.provider.health_score,
            estimated_answer_rate=recent_answer_rate,
        )

        decision = self.safety_controller.evaluate_dials(
            requested_dials=recommendation.recommended_dials,
            context=safety_context,
            is_predictive=True,
        )

        # 3. If approved > 0, allocate pairs and dispatch
        initiated_count = 0
        allocated_pairs: list[tuple[Agent, Call]] = []

        if decision.approved and decision.approved_calls > 0:
            allocated_pairs = self.allocator.allocate_batch(
                max_allocations=decision.approved_calls
            )

            for agent, call in allocated_pairs:
                success = self.provider.initiate_call(
                    call_id=call.id,
                    borrower_id=call.borrower_id,
                    agent_id=agent.id,
                )
                if success:
                    initiated_count += 1
                else:
                    # Carrier initiation failed / timed out before INITIATED
                    if call.state == CallState.RESERVED:
                        try:
                            call.transition_to(CallState.CANCELLED)
                        except Exception:
                            pass
                    if agent.state == AgentState.RESERVED:
                        try:
                            agent.transition_to(AgentState.AVAILABLE)
                        except Exception:
                            pass

        return PredictiveDialingResult(
            pacing_recommendation=recommendation,
            safety_decision=decision,
            initiated_calls=initiated_count,
            allocated_pairs=allocated_pairs,
        )
