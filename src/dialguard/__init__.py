"""DialGuard - SmartDialer prototype for collections operations."""

from dialguard.allocator import CallAllocator
from dialguard.dialer import (
    DialingResult,
    PredictiveDialer,
    PredictiveDialingResult,
    ProgressiveDialer,
)
from dialguard.exceptions import (
    DialGuardError,
    InvalidStateTransitionError,
    TerminalStateError,
)
from dialguard.models import Agent, Borrower, Call
from dialguard.pacing import (
    PacingInputs,
    PacingRecommendation,
    PredictivePacingEngine,
)
from dialguard.recovery import RecoverySupervisor
from dialguard.repository import InMemoryRepository
from dialguard.safety import (
    SafetyContext,
    SafetyController,
    SafetyDecision,
)
from dialguard.simulation import CampaignSimulator, SimulationMetrics
from dialguard.state import AgentState, CallState
from dialguard.telecom import (
    FlakyProvider,
    ProviderCallEvent,
    ProviderEventHandler,
    ReliableProvider,
    TelecomEventType,
    TelecomProvider,
)

__all__ = [
    "Agent",
    "AgentState",
    "Borrower",
    "Call",
    "CallAllocator",
    "CallState",
    "CampaignSimulator",
    "DialGuardError",
    "DialingResult",
    "FlakyProvider",
    "InMemoryRepository",
    "InvalidStateTransitionError",
    "PacingInputs",
    "PacingRecommendation",
    "PredictiveDialer",
    "PredictiveDialingResult",
    "PredictivePacingEngine",
    "ProgressiveDialer",
    "ProviderCallEvent",
    "ProviderEventHandler",
    "RecoverySupervisor",
    "ReliableProvider",
    "SafetyContext",
    "SafetyController",
    "SafetyDecision",
    "SimulationMetrics",
    "TelecomEventType",
    "TelecomProvider",
    "TerminalStateError",
]
