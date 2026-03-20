"""
Utility Components
==================

Common utilities for the vectorstore system.

Components:
- checkpoint_manager: Save/restore processing state
- error_handler: Robust error handling with retries

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

from .checkpoint_manager import CheckpointManager
from .error_handler import (
    ErrorSeverity,
    ErrorStrategy,
    RetryableError,
    FatalError,
    retry_with_backoff,
    handle_errors,
    ErrorAccumulator,
    CircuitBreaker
)

__all__ = [
    # Checkpoint management
    'CheckpointManager',
    
    # Error handling
    'ErrorSeverity',
    'ErrorStrategy',
    'RetryableError',
    'FatalError',
    'retry_with_backoff',
    'handle_errors',
    'ErrorAccumulator',
    'CircuitBreaker',
]
