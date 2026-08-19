"""Unit tests for PredictivePacingEngine statistical calculations."""

from dialguard.pacing.engine import PacingInputs, PredictivePacingEngine


class TestPredictivePacingEngine:
    def setup_method(self) -> None:
        self.engine = PredictivePacingEngine(
            default_answer_rate=0.30,
            min_answer_rate_floor=0.05,
        )

    def test_basic_pacing_calculation(self) -> None:
        """With 2 available agents and 20% answer rate, recommended dials ≈ 2 / 0.20 = 10."""
        inputs = PacingInputs(
            available_agents=2,
            connected_calls=0,
            ringing_or_dialing_calls=0,
            recent_answer_rate=0.20,
        )
        rec = self.engine.calculate_recommendation(inputs)
        assert rec.recommended_dials == 10
        assert rec.estimated_answer_rate == 0.20
        assert rec.target_answers == 2.0

    def test_pacing_accounts_for_in_flight_calls(self) -> None:
        """With 2 available agents, 20% answer rate, and 5 in-flight calls:

        In-flight expected answers = 5 * 0.20 = 1.0.
        Target answers needed = 2 - 1 = 1.0.
        Recommended dials = 1 / 0.20 = 5.
        """
        inputs = PacingInputs(
            available_agents=2,
            connected_calls=0,
            ringing_or_dialing_calls=5,
            recent_answer_rate=0.20,
        )
        rec = self.engine.calculate_recommendation(inputs)
        assert rec.recommended_dials == 5
        assert rec.target_answers == 1.0

    def test_pacing_accounts_for_expected_agent_completions(self) -> None:
        """With 10 connected calls and 100s avg duration, completion rate is 0.1/s.

        In a 10s latency window, 1 agent is expected to become free.
        """
        inputs = PacingInputs(
            available_agents=0,
            connected_calls=10,
            ringing_or_dialing_calls=0,
            recent_answer_rate=0.50,
            avg_call_duration_seconds=100.0,
            dial_latency_seconds=10.0,
        )
        rec = self.engine.calculate_recommendation(inputs)
        assert rec.expected_agent_completions == 1.0
        assert rec.recommended_dials == 2  # 1.0 / 0.50 = 2

    def test_pacing_scales_with_provider_health(self) -> None:
        inputs = PacingInputs(
            available_agents=4,
            connected_calls=0,
            ringing_or_dialing_calls=0,
            recent_answer_rate=0.40,  # 4 / 0.40 = 10
            provider_health=0.80,
        )
        rec = self.engine.calculate_recommendation(inputs)
        assert rec.recommended_dials == 8  # 10 * 0.80 = 8
