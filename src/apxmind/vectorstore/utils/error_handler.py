"""
Error Handler Utilities
========================

Provides robust error handling with retries, logging, and recovery strategies.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import time
import functools
from typing import Callable, Any, Optional, Type, Tuple, List
from enum import Enum
import logging

from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"           # Non-critical, can continue
    MEDIUM = "medium"     # Important but recoverable
    HIGH = "high"         # Critical, may need intervention
    FATAL = "fatal"       # Unrecoverable, must stop


class ErrorStrategy(Enum):
    """Error handling strategies."""
    RETRY = "retry"                # Retry with backoff
    SKIP = "skip"                  # Skip and continue
    FAIL_FAST = "fail_fast"        # Raise immediately
    LOG_AND_CONTINUE = "log"       # Log but don't raise


class RetryableError(Exception):
    """Exception that should trigger retry logic."""
    pass


class FatalError(Exception):
    """Exception that should stop all processing."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback called on each retry
        
    Usage:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def fetch_data():
            # Code that might fail temporarily
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Log retry attempt
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}",
                            extra={
                                'function': func.__name__,
                                'attempt': attempt + 1,
                                'max_retries': max_retries,
                                'delay': delay,
                                'error': str(e)
                            }
                        )
                        
                        # Call retry callback if provided
                        if on_retry:
                            on_retry(attempt, e)
                        
                        # Wait before retry
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        # Max retries exceeded
                        logger.error(
                            f"Max retries exceeded for {func.__name__}",
                            extra={
                                'function': func.__name__,
                                'max_retries': max_retries,
                                'final_error': str(e)
                            },
                            exc_info=True
                        )
            
            # All retries failed, raise last exception
            raise last_exception
        
        return wrapper
    return decorator


def handle_errors(
    strategy: ErrorStrategy = ErrorStrategy.LOG_AND_CONTINUE,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    default_return: Any = None,
    log_traceback: bool = True
):
    """
    Decorator for standardized error handling.
    
    Args:
        strategy: How to handle errors
        severity: Error severity level
        default_return: Value to return on error (if not raising)
        log_traceback: Whether to log full traceback
        
    Usage:
        @handle_errors(strategy=ErrorStrategy.SKIP, default_return=[])
        def process_items(items):
            # Code that might fail
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
                
            except FatalError as e:
                # Always raise fatal errors
                logger.error(
                    f"Fatal error in {func.__name__}: {e}",
                    extra={
                        'function': func.__name__,
                        'severity': 'fatal',
                        'error': str(e)
                    },
                    exc_info=log_traceback
                )
                raise
                
            except Exception as e:
                # Handle based on strategy
                error_msg = f"Error in {func.__name__}: {e}"
                
                if strategy == ErrorStrategy.FAIL_FAST:
                    logger.error(
                        error_msg,
                        extra={
                            'function': func.__name__,
                            'severity': severity.value,
                            'strategy': 'fail_fast'
                        },
                        exc_info=log_traceback
                    )
                    raise
                    
                elif strategy == ErrorStrategy.LOG_AND_CONTINUE:
                    logger.warning(
                        error_msg,
                        extra={
                            'function': func.__name__,
                            'severity': severity.value,
                            'strategy': 'log_and_continue',
                            'default_return': type(default_return).__name__
                        },
                        exc_info=log_traceback
                    )
                    return default_return
                    
                elif strategy == ErrorStrategy.SKIP:
                    logger.info(
                        f"Skipping {func.__name__} due to error: {e}",
                        extra={
                            'function': func.__name__,
                            'severity': severity.value,
                            'strategy': 'skip'
                        }
                    )
                    return default_return
                    
                elif strategy == ErrorStrategy.RETRY:
                    # Convert to retryable error
                    raise RetryableError(str(e)) from e
        
        return wrapper
    return decorator


class ErrorAccumulator:
    """
    Accumulates errors during batch processing.
    
    Usage:
        accumulator = ErrorAccumulator(max_errors=10)
        
        for item in items:
            try:
                process(item)
            except Exception as e:
                if not accumulator.add_error(item, e):
                    break  # Too many errors
        
        # Review errors
        for error_info in accumulator.get_errors():
            print(f"Failed: {error_info['item']} - {error_info['error']}")
    """
    
    def __init__(
        self,
        max_errors: Optional[int] = None,
        group_by_type: bool = True
    ):
        """
        Initialize error accumulator.
        
        Args:
            max_errors: Stop after this many errors (None = unlimited)
            group_by_type: Group errors by exception type
        """
        self.max_errors = max_errors
        self.group_by_type = group_by_type
        self._errors: List[Dict[str, Any]] = []
        self._error_counts: Dict[str, int] = {}
    
    def add_error(
        self,
        item: Any,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add an error to the accumulator.
        
        Args:
            item: Item that caused the error
            error: Exception that was raised
            context: Additional context about the error
            
        Returns:
            True if can continue, False if max_errors reached
        """
        error_type = type(error).__name__
        
        # Record error
        self._errors.append({
            'item': str(item),
            'error': str(error),
            'error_type': error_type,
            'context': context or {},
            'timestamp': time.time()
        })
        
        # Update counts
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        
        # Check if max errors reached
        if self.max_errors and len(self._errors) >= self.max_errors:
            logger.error(
                f"Maximum error count reached: {self.max_errors}",
                extra={
                    'total_errors': len(self._errors),
                    'error_types': self._error_counts
                }
            )
            return False
        
        return True
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all accumulated errors."""
        return self._errors.copy()
    
    def get_error_count(self) -> int:
        """Get total error count."""
        return len(self._errors)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics."""
        return {
            'total_errors': len(self._errors),
            'error_types': self._error_counts.copy(),
            'most_common': max(
                self._error_counts.items(),
                key=lambda x: x[1]
            )[0] if self._error_counts else None,
            'unique_types': len(self._error_counts)
        }
    
    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self._errors) > 0
    
    def clear(self):
        """Clear all accumulated errors."""
        self._errors.clear()
        self._error_counts.clear()


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        if breaker.can_proceed():
            try:
                result = risky_operation()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure()
                raise
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Failures before opening circuit
            timeout: Seconds before attempting recovery
            half_open_max_calls: Max calls in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._state = "CLOSED"
    
    def can_proceed(self) -> bool:
        """Check if operation can proceed."""
        current_time = time.time()
        
        if self._state == "OPEN":
            # Check if timeout has elapsed
            if current_time - self._last_failure_time >= self.timeout:
                logger.info("Circuit breaker entering HALF_OPEN state")
                self._state = "HALF_OPEN"
                self._half_open_calls = 0
                return True
            else:
                return False
        
        elif self._state == "HALF_OPEN":
            # Allow limited calls in half-open state
            return self._half_open_calls < self.half_open_max_calls
        
        else:  # CLOSED
            return True
    
    def record_success(self):
        """Record successful operation."""
        if self._state == "HALF_OPEN":
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                logger.info("Circuit breaker closing after successful recovery")
                self._state = "CLOSED"
                self._failure_count = 0
        elif self._state == "CLOSED":
            self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self):
        """Record failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == "HALF_OPEN":
            logger.warning("Circuit breaker reopening after failure in HALF_OPEN state")
            self._state = "OPEN"
        elif self._failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker opening after {self._failure_count} failures",
                extra={'failure_threshold': self.failure_threshold}
            )
            self._state = "OPEN"
    
    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self._state


# Export all utilities
__all__ = [
    'ErrorSeverity',
    'ErrorStrategy',
    'RetryableError',
    'FatalError',
    'retry_with_backoff',
    'handle_errors',
    'ErrorAccumulator',
    'CircuitBreaker',
]
