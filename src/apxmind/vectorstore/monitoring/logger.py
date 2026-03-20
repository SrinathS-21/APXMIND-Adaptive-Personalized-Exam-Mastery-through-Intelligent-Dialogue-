"""
Structured Logging System for APXMIND Vector Store
==================================================

Production-grade logging with:
- Structured JSON output for machine parsing
- Log rotation to prevent disk overflow
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Context managers for operation tracking
- Performance timing utilities
"""

import logging
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager
import time

from ..config import MonitoringConfig


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    
    Benefits:
    - Machine-parseable logs
    - Easy integration with log analysis tools
    - Consistent format across all log entries
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add custom fields from extra parameter
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class PlainFormatter(logging.Formatter):
    """
    Human-readable formatter for console output.
    
    Format: [TIMESTAMP] LEVEL - Module.Function:Line - Message
    """
    
    def __init__(self):
        super().__init__(
            fmt="[%(asctime)s] %(levelname)-8s - %(name)s.%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(config: Optional[MonitoringConfig] = None) -> None:
    """
    Initialize logging system with configured handlers.
    
    Sets up:
    - File handler with rotation (structured JSON logs)
    - Console handler (human-readable logs)
    - Log level based on configuration
    
    Args:
        config: Monitoring configuration. Uses default if not provided.
    """
    if config is None:
        from ..config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG.monitoring
    
    # Create log directory if it doesn't exist
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger("APXMIND.vectorstore")
    root_logger.setLevel(getattr(logging, config.log_level))
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # File handler with rotation (JSON format)
    if config.structured_logging:
        log_file = log_dir / "vectorstore.json"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=config.log_rotation_size_mb * 1024 * 1024,
            backupCount=config.log_backup_count
        )
        file_handler.setLevel(logging.DEBUG)  # Capture all levels in file
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # Plain text file handler (for human reading)
    plain_log_file = log_dir / "vectorstore.log"
    plain_file_handler = RotatingFileHandler(
        plain_log_file,
        maxBytes=config.log_rotation_size_mb * 1024 * 1024,
        backupCount=config.log_backup_count
    )
    plain_file_handler.setLevel(logging.DEBUG)
    plain_file_handler.setFormatter(PlainFormatter())
    root_logger.addHandler(plain_file_handler)
    
    # Console handler (human-readable)
    if config.console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.log_level))
        console_handler.setFormatter(PlainFormatter())
        root_logger.addHandler(console_handler)
    
    root_logger.info("Logging system initialized", extra={
        "extra_fields": {
            "log_level": config.log_level,
            "log_dir": str(log_dir),
            "structured_logging": config.structured_logging
        }
    })


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__ of calling module)
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    return logging.getLogger(f"APXMIND.vectorstore.{name}")


class LogContext:
    """
    Context manager for logging operation execution with timing.
    
    Example:
        with LogContext(logger, "embedding_generation", batch_size=32):
            embeddings = generate_embeddings(texts)
        # Automatically logs: operation, duration, and context
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        level: int = logging.INFO,
        **context: Any
    ):
        """
        Initialize log context.
        
        Args:
            logger: Logger instance to use
            operation: Operation name
            level: Log level for messages
            **context: Additional context to include in logs
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.context = context
        self.start_time = None
        self.success = False
    
    def __enter__(self):
        """Enter context - log operation start."""
        self.start_time = time.time()
        self.logger.log(
            self.level,
            f"Starting: {self.operation}",
            extra={"extra_fields": {"operation": self.operation, **self.context}}
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - log operation completion/failure."""
        duration = time.time() - self.start_time
        
        log_data = {
            "operation": self.operation,
            "duration_seconds": round(duration, 3),
            **self.context
        }
        
        if exc_type is None:
            # Success
            self.logger.log(
                self.level,
                f"Completed: {self.operation} ({duration:.2f}s)",
                extra={"extra_fields": {**log_data, "status": "success"}}
            )
        else:
            # Failure
            log_data["status"] = "failed"
            log_data["error_type"] = exc_type.__name__
            log_data["error_message"] = str(exc_val)
            
            self.logger.error(
                f"Failed: {self.operation} ({duration:.2f}s)",
                extra={"extra_fields": log_data},
                exc_info=True
            )
        
        # Don't suppress exceptions
        return False


@contextmanager
def log_operation(
    logger: logging.Logger,
    operation: str,
    **context: Any
):
    """
    Convenience context manager for logging operations.
    
    Example:
        with log_operation(logger, "pdf_loading", filename="biology.pdf"):
            documents = load_pdf(filename)
    """
    ctx = LogContext(logger, operation, **context)
    with ctx:
        yield ctx


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration: float,
    **metrics: Any
):
    """
    Log performance metrics for an operation.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration: Duration in seconds
        **metrics: Additional performance metrics
    
    Example:
        log_performance(
            logger,
            "embedding_generation",
            duration=5.2,
            batch_size=32,
            embeddings_per_second=6.15
        )
    """
    log_data = {
        "operation": operation,
        "duration_seconds": round(duration, 3),
        **metrics
    }
    
    logger.info(
        f"Performance: {operation}",
        extra={"extra_fields": {**log_data, "metric_type": "performance"}}
    )


def log_quality_metrics(
    logger: logging.Logger,
    component: str,
    **metrics: Any
):
    """
    Log quality metrics.
    
    Args:
        logger: Logger instance
        component: Component name (e.g., "chunker", "validator")
        **metrics: Quality metrics
    
    Example:
        log_quality_metrics(
            logger,
            "semantic_chunker",
            avg_quality_score=0.87,
            chunks_above_threshold=0.92
        )
    """
    log_data = {
        "component": component,
        **metrics
    }
    
    logger.info(
        f"Quality Metrics: {component}",
        extra={"extra_fields": {**log_data, "metric_type": "quality"}}
    )
