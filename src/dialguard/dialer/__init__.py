"""Dialer package for DialGuard."""

from dialguard.dialer.predictive import PredictiveDialer, PredictiveDialingResult
from dialguard.dialer.progressive import DialingResult, ProgressiveDialer

__all__ = [
    "DialingResult",
    "PredictiveDialer",
    "PredictiveDialingResult",
    "ProgressiveDialer",
]
