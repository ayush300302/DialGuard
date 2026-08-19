"""Unit tests for SafetyController limits, health checks, and fallback mechanisms."""

from dialguard.safety.safety_controller import SafetyContext, SafetyController


class TestSafetyController:
    def setup_method(self) -> None:
        self.controller = SafetyController(
            max_overdial_ratio=3.0,
            min_provider_health=0.70,
            critical_provider_health=0.30,
        )

    def test_approve_within_bounds(self) -> None:
        context = SafetyContext(
            total_agents=10,
            available_agents=5,
            reserved_agents=0,
            connected_calls=5,
            ringing_or_dialing_calls=0,
            provider_health=1.0,
            estimated_answer_rate=0.30,
        )
        decision = self.controller.evaluate_dials(
            requested_dials=10, context=context, is_predictive=True
        )

        assert decision.approved is True
        assert decision.approved_calls == 10

    def test_throttle_exceeding_max_overdial_ratio(self) -> None:
        """With 5 available agents and max ratio 3.0, max in-flight is 15.

        If 10 are already ringing, max allowed new dials is 5.
        """
        context = SafetyContext(
            total_agents=10,
            available_agents=5,
            reserved_agents=0,
            connected_calls=5,
            ringing_or_dialing_calls=10,
            provider_health=1.0,
            estimated_answer_rate=0.20,
        )
        decision = self.controller.evaluate_dials(
            requested_dials=20, context=context, is_predictive=True
        )

        assert decision.approved is True
        assert decision.approved_calls == 5
        assert "max_overdial_ratio_cap" in decision.applied_caps

    def test_reject_when_zero_available_agents(self) -> None:
        context = SafetyContext(
            total_agents=10,
            available_agents=0,
            reserved_agents=0,
            connected_calls=10,
            ringing_or_dialing_calls=0,
            provider_health=1.0,
        )
        decision = self.controller.evaluate_dials(
            requested_dials=5, context=context, is_predictive=True
        )

        assert decision.approved is False
        assert decision.approved_calls == 0
        assert "zero_available_agents" in decision.applied_caps

    def test_reject_when_critical_provider_health(self) -> None:
        context = SafetyContext(
            total_agents=10,
            available_agents=5,
            reserved_agents=0,
            connected_calls=0,
            ringing_or_dialing_calls=0,
            provider_health=0.25,  # Below 0.30 critical threshold
        )
        decision = self.controller.evaluate_dials(
            requested_dials=5, context=context, is_predictive=True
        )

        assert decision.approved is False
        assert decision.approved_calls == 0
        assert "critical_provider_health_rejection" in decision.applied_caps

    def test_fallback_to_progressive_on_degraded_health(self) -> None:
        """Provider health 0.60 (< 0.70) forces 1:1 progressive cap even in predictive mode."""
        context = SafetyContext(
            total_agents=10,
            available_agents=4,
            reserved_agents=0,
            connected_calls=2,
            ringing_or_dialing_calls=0,
            provider_health=0.60,
        )
        decision = self.controller.evaluate_dials(
            requested_dials=12, context=context, is_predictive=True
        )

        assert decision.approved is True
        assert decision.approved_calls == 4  # Capped to available agents
        assert decision.fallback_to_progressive is True
        assert "provider_health_progressive_fallback" in decision.applied_caps

    def test_progressive_mode_strictly_caps_to_available_agents(self) -> None:
        context = SafetyContext(
            total_agents=10,
            available_agents=3,
            reserved_agents=0,
            connected_calls=2,
            ringing_or_dialing_calls=0,
            provider_health=1.0,
        )
        decision = self.controller.evaluate_dials(
            requested_dials=10, context=context, is_predictive=False
        )

        assert decision.approved is True
        assert decision.approved_calls == 3
        assert "progressive_1_to_1_limit" in decision.applied_caps
