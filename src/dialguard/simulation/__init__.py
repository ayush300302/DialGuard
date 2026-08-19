"""Simulation package for DialGuard."""

from typing import TYPE_CHECKING
from dialguard.simulation.metrics import SimulationMetrics

if TYPE_CHECKING:
    from dialguard.simulation.runner import CampaignSimulator

__all__ = [
    "CampaignSimulator",
    "SimulationMetrics",
]


def __getattr__(name: str):
    if name == "CampaignSimulator":
        from dialguard.simulation.runner import CampaignSimulator

        return CampaignSimulator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

