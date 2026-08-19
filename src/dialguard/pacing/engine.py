"""Statistical rule-based Predictive Pacing Engine for DialGuard."""

from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PacingInputs:
    """Inputs to the statistical Predictive Pacing Engine."""

    available_agents: int
    connected_calls: int
    ringing_or_dialing_calls: int
    recent_answer_rate: float = 0.30
    avg_call_duration_seconds: float = 120.0
    dial_latency_seconds: float = 5.0
    provider_health: float = 1.0


@dataclass
class PacingRecommendation:
    """Advisory recommendation from the Predictive Pacing Engine."""

    recommended_dials: int
    target_answers: float
    estimated_answer_rate: float
    expected_agent_completions: float
    rationale: str


class PredictivePacingEngine:
    """Statistical rule-based engine that recommends dial volume.

    Important Constraint:
    The Pacing Engine only RECOMMENDS a dial count. It does not dispatch calls.
    The Safety Controller makes the final decision before any dials are placed.

    Configurable Design Choices (Not explicit assignment requirements):
    - default_answer_rate: 0.30 fallback if no historical data
    - min_answer_rate_floor: 0.05 (Prevents division by zero)
    - completion_lookahead_seconds: 5.0s dial latency window
    """

    def __init__(
        self,
        default_answer_rate: float = 0.30,
        min_answer_rate_floor: float = 0.05,
    ) -> None:
        self.default_answer_rate = default_answer_rate
        self.min_answer_rate_floor = min_answer_rate_floor

    def calculate_recommendation(
        self, inputs: PacingInputs
    ) -> PacingRecommendation:
        """Calculate recommended dial count using statistical pacing formula."""
        # 1. Effective answer rate
        effective_rate = max(
            self.min_answer_rate_floor,
            min(1.0, inputs.recent_answer_rate or self.default_answer_rate),
        )

        # 2. Expected agent completions during dial latency window
        # Using Little's Law / Poisson arrival approximation:
        # Rate of completions = connected_calls / avg_call_duration
        if inputs.avg_call_duration_seconds > 0 and inputs.connected_calls > 0:
            completion_rate_per_sec = (
                inputs.connected_calls / inputs.avg_call_duration_seconds
            )
            expected_completions = (
                completion_rate_per_sec * inputs.dial_latency_seconds
            )
        else:
            expected_completions = 0.0

        # 3. Target answers desired to match available + soon-to-be-available agents
        target_answers = max(
            0.0,
            (inputs.available_agents + expected_completions)
            - (inputs.ringing_or_dialing_calls * effective_rate),
        )

        # 4. Recommended dials = target_answers / effective_answer_rate
        raw_recommended = target_answers / effective_rate
        recommended_dials = max(0, int(round(raw_recommended)))

        # 5. If provider health is low, scale down recommendation
        if inputs.provider_health < 1.0:
            recommended_dials = int(
                round(recommended_dials * inputs.provider_health)
            )

        rationale = (
            f"Available agents: {inputs.available_agents}, "
            f"Expected completions: {expected_completions:.2f}, "
            f"In-flight calls: {inputs.ringing_or_dialing_calls}, "
            f"Est. answer rate: {effective_rate * 100:.1f}%, "
            f"Target answers: {target_answers:.2f} -> Recommended dials: {recommended_dials}"
        )

        return PacingRecommendation(
            recommended_dials=recommended_dials,
            target_answers=target_answers,
            estimated_answer_rate=effective_rate,
            expected_agent_completions=expected_completions,
            rationale=rationale,
        )
