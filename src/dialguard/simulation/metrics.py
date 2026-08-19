"""Metrics collection for DialGuard simulations."""

from dataclasses import dataclass, field


@dataclass
class SimulationMetrics:
    """Aggregated campaign metrics for a simulation run."""

    scenario_name: str
    dialer_mode: str
    total_cycles: int = 0
    total_dials_attempted: int = 0
    total_calls_answered: int = 0
    total_calls_completed: int = 0
    total_calls_failed: int = 0
    total_calls_abandoned: int = 0  # Unserviced answers (if any)
    safety_throttles: int = 0
    safety_rejections: int = 0
    progressive_fallbacks: int = 0
    cumulative_agent_talk_ticks: int = 0
    cumulative_agent_idle_ticks: int = 0
    cumulative_agent_total_ticks: int = 0

    @property
    def answer_rate(self) -> float:
        """Percentage of attempted calls answered."""
        if self.total_dials_attempted == 0:
            return 0.0
        return (self.total_calls_answered / self.total_dials_attempted) * 100.0

    @property
    def agent_utilization_pct(self) -> float:
        """Percentage of agent time spent actively connected with borrowers."""
        if self.cumulative_agent_total_ticks == 0:
            return 0.0
        return (
            self.cumulative_agent_talk_ticks / self.cumulative_agent_total_ticks
        ) * 100.0

    @property
    def abandonment_rate(self) -> float:
        """Percentage of answered calls that were abandoned without an agent."""
        if self.total_calls_answered == 0:
            return 0.0
        return (
            self.total_calls_abandoned / self.total_calls_answered
        ) * 100.0
