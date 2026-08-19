"""Deterministic Safety Controller for DialGuard dialing operations."""

from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SafetyContext:
    """Current operational state evaluated by the Safety Controller."""

    total_agents: int
    available_agents: int
    reserved_agents: int
    connected_calls: int
    ringing_or_dialing_calls: int
    provider_health: float
    estimated_answer_rate: float = 0.30


@dataclass
class SafetyDecision:
    """Deterministic output from the Safety Controller."""

    approved: bool
    requested_calls: int
    approved_calls: int
    reason: str
    fallback_to_progressive: bool = False
    applied_caps: list[str] = field(default_factory=list)


class SafetyController:
    """Enforces deterministic safety constraints before any call can be dispatched.

    The Predictive Pacing Engine cannot initiate calls directly; it only recommends
    a dial count to the Safety Controller, which makes the final binding decision.

    Configurable Design Choices (Not explicit assignment requirements):
    - max_overdial_ratio: 3.0 (Maximum ratio of in-flight dials to available agents)
    - min_provider_health: 0.70 (Triggers fallback to progressive 1:1 mode)
    - critical_provider_health: 0.30 (Rejects all dials completely)
    """

    def __init__(
        self,
        max_overdial_ratio: float = 3.0,
        min_provider_health: float = 0.70,
        critical_provider_health: float = 0.30,
    ) -> None:
        self.max_overdial_ratio = max_overdial_ratio
        self.min_provider_health = min_provider_health
        self.critical_provider_health = critical_provider_health

    def evaluate_dials(
        self,
        requested_dials: int,
        context: SafetyContext,
        is_predictive: bool = True,
    ) -> SafetyDecision:
        """Evaluate and constrain requested dial count against safety invariants."""
        applied_caps: list[str] = []

        # Invariant 1: If requested dials is 0 or negative
        if requested_dials <= 0:
            return SafetyDecision(
                approved=False,
                requested_calls=requested_dials,
                approved_calls=0,
                reason="No calls requested.",
            )

        # Invariant 2: Total agents must be > 0
        if context.total_agents <= 0:
            return SafetyDecision(
                approved=False,
                requested_calls=requested_dials,
                approved_calls=0,
                reason="Zero total agents in campaign.",
            )

        # Invariant 3: Critical provider failure check
        if context.provider_health < self.critical_provider_health:
            return SafetyDecision(
                approved=False,
                requested_calls=requested_dials,
                approved_calls=0,
                reason=f"Provider health critically low ({context.provider_health:.2f} < {self.critical_provider_health:.2f}). All dials halted.",
                applied_caps=["critical_provider_health_rejection"],
            )

        # Invariant 4: Available agent capacity
        if context.available_agents <= 0:
            return SafetyDecision(
                approved=False,
                requested_calls=requested_dials,
                approved_calls=0,
                reason="No agents currently AVAILABLE to take calls.",
                applied_caps=["zero_available_agents"],
            )

        # Invariant 5: Provider health degradation -> Fallback to Progressive
        fallback_progressive = False
        if context.provider_health < self.min_provider_health:
            fallback_progressive = True
            applied_caps.append("provider_health_progressive_fallback")
            logger.warning(
                "Provider health degraded (%.2f < %.2f). Falling back to progressive 1:1 dialing.",
                context.provider_health,
                self.min_provider_health,
            )

        approved = requested_dials

        # Invariant 6: Progressive mode enforcement
        if not is_predictive or fallback_progressive:
            max_allowed = context.available_agents
            if approved > max_allowed:
                applied_caps.append("progressive_1_to_1_limit")
                approved = max_allowed

        else:
            # Invariant 7: Predictive Overdial Hard Limit
            # Total outstanding in-flight calls + new dials cannot exceed (available_agents * max_overdial_ratio)
            max_outstanding = int(
                context.available_agents * self.max_overdial_ratio
            )
            current_outstanding = context.ringing_or_dialing_calls
            available_dial_slots = max(0, max_outstanding - current_outstanding)

            if approved > available_dial_slots:
                applied_caps.append("max_overdial_ratio_cap")
                approved = available_dial_slots

            # Invariant 8: Abandonment Prevention Cap
            # Expected answered calls cannot exceed available agents * 1.5
            safe_expected_answers_limit = max(1, context.available_agents)
            effective_answer_rate = max(0.05, context.estimated_answer_rate)
            max_dials_by_answers = int(
                safe_expected_answers_limit / effective_answer_rate
            )

            if approved > max_dials_by_answers:
                applied_caps.append("expected_abandonment_cap")
                approved = max_dials_by_answers

        # Invariant 9: Final bound checks
        approved = max(0, approved)

        if approved == 0:
            return SafetyDecision(
                approved=False,
                requested_calls=requested_dials,
                approved_calls=0,
                reason="Requested dials throttled to 0 by safety capacity limits.",
                fallback_to_progressive=fallback_progressive,
                applied_caps=applied_caps,
            )

        reason = (
            f"Approved {approved} of {requested_dials} requested dials."
            if approved == requested_dials
            else f"Throttled {requested_dials} requested dials down to {approved}."
        )

        return SafetyDecision(
            approved=True,
            requested_calls=requested_dials,
            approved_calls=approved,
            reason=reason,
            fallback_to_progressive=fallback_progressive,
            applied_caps=applied_caps,
        )
