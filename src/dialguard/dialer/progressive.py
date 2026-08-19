"""Progressive Dialer implementation (1:1 agent-bound dialing)."""

from dataclasses import dataclass, field
import logging
from dialguard.allocator.call_allocator import CallAllocator
from dialguard.models.agent import Agent
from dialguard.models.call import Call
from dialguard.repository.in_memory import InMemoryRepository
from dialguard.safety.safety_controller import SafetyContext, SafetyController
from dialguard.state.call_state import CallState
from dialguard.telecom.provider import TelecomProvider

logger = logging.getLogger(__name__)


@dataclass
class DialingResult:
    """Summary of a dialer execution cycle."""

    requested_calls: int
    approved_calls: int
    initiated_calls: int
    allocated_pairs: list[tuple[Agent, Call]] = field(default_factory=list)
    reason: str = ""


class ProgressiveDialer:
    """Progressive Dialer enforcing strict 1:1 agent-to-outbound call ratio.

    Rule from Assignment:
    available agents = maximum number of agent-bound outbound calls allowed at that moment.
    """

    def __init__(
        self,
        repository: InMemoryRepository,
        allocator: CallAllocator,
        safety_controller: SafetyController,
        provider: TelecomProvider,
    ) -> None:
        self.repository = repository
        self.allocator = allocator
        self.safety_controller = safety_controller
        self.provider = provider

    def execute_cycle(self) -> DialingResult:
        """Execute one progressive dialing cycle."""
        # 1. Gather current operational state
        all_agents = self.repository.list_agents()
        available_agents = self.repository.get_available_agents()
        connected_calls = len(
            self.repository.get_calls_by_state(CallState.CONNECTED)
        )
        in_flight_calls = len(
            self.repository.get_calls_by_state(CallState.INITIATED)
        ) + len(self.repository.get_calls_by_state(CallState.RINGING))

        # Progressive rule: requested dials = available agents count
        requested_dials = len(available_agents)

        if requested_dials == 0:
            return DialingResult(
                requested_calls=0,
                approved_calls=0,
                initiated_calls=0,
                reason="No agents currently available.",
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
        )

        decision = self.safety_controller.evaluate_dials(
            requested_dials=requested_dials,
            context=safety_context,
            is_predictive=False,
        )

        if not decision.approved or decision.approved_calls <= 0:
            return DialingResult(
                requested_calls=requested_dials,
                approved_calls=0,
                initiated_calls=0,
                reason=f"Safety Controller rejected: {decision.reason}",
            )

        # 3. Atomically allocate agent-call pairs up to approved limit
        allocated_pairs = self.allocator.allocate_batch(
            max_allocations=decision.approved_calls
        )

        # 4. Initiate dials with provider
        initiated_count = 0
        for agent, call in allocated_pairs:
            success = self.provider.initiate_call(
                call_id=call.id,
                borrower_id=call.borrower_id,
                agent_id=agent.id,
            )
            if success:
                initiated_count += 1

        return DialingResult(
            requested_calls=requested_dials,
            approved_calls=decision.approved_calls,
            initiated_calls=initiated_count,
            allocated_pairs=allocated_pairs,
            reason=decision.reason,
        )
