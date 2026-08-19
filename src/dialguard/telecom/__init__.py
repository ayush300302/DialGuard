"""Telecom provider package for DialGuard."""

from dialguard.telecom.event_handler import ProviderEventHandler
from dialguard.telecom.events import ProviderCallEvent, TelecomEventType
from dialguard.telecom.flaky_provider import FlakyProvider
from dialguard.telecom.provider import TelecomProvider
from dialguard.telecom.reliable_provider import ReliableProvider

__all__ = [
    "FlakyProvider",
    "ProviderCallEvent",
    "ProviderEventHandler",
    "ReliableProvider",
    "TelecomEventType",
    "TelecomProvider",
]
