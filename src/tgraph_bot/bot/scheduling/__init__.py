"""
Scheduling package for TGraph Bot.

This package contains the refactored scheduling system components that were
originally in the monolithic update_tracker.py file.
"""

from .types import (
    TaskStatus,
    ErrorType,
    CircuitState,
    RetryConfig,
    ErrorMetrics,
    SchedulingConfig,
    ScheduleState,
    PersistentScheduleData,
    MissedUpdate,
)
from .error_handling import ErrorClassifier, CircuitBreaker
from .task_manager import BackgroundTaskManager
from .schedule import UpdateSchedule
from .persistence import StateManager
from .recovery import RecoveryManager

__all__ = [
    # Types and enums
    "TaskStatus",
    "ErrorType", 
    "CircuitState",
    # Configuration and state
    "RetryConfig",
    "ErrorMetrics",
    "SchedulingConfig",
    "ScheduleState",
    "PersistentScheduleData",
    "MissedUpdate",
    # Core components
    "ErrorClassifier",
    "CircuitBreaker",
    "BackgroundTaskManager", 
    "UpdateSchedule",
    "StateManager",
    "RecoveryManager",
]