"""
Metrics Collector
=================

Collects and tracks performance metrics for all vectorstore operations.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class OperationMetrics:
    """
    Metrics for a single operation.
    
    Attributes:
        operation_name: Name of the operation
        start_time: When operation started
        end_time: When operation ended
        duration: Operation duration in seconds
        success: Whether operation succeeded
        items_processed: Number of items processed
        errors: Number of errors encountered
        metadata: Additional operation-specific metrics
    """
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    items_processed: int = 0
    errors: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self, success: bool = True):
        """Mark operation as complete."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'operation_name': self.operation_name,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            'duration': self.duration,
            'success': self.success,
            'items_processed': self.items_processed,
            'errors': self.errors,
            'throughput': self.items_processed / self.duration if self.duration else 0,
            'metadata': self.metadata
        }


class MetricsCollector:
    """
    Collects and aggregates performance metrics.
    
    Features:
    - Track operation latency and throughput
    - Monitor success/failure rates
    - Calculate aggregated statistics
    - Export metrics for analysis
    - Real-time metric queries
    
    Usage:
        collector = MetricsCollector()
        
        # Record operation
        with collector.track_operation("pdf_loading"):
            load_pdfs()
        
        # Get statistics
        stats = collector.get_statistics("pdf_loading")
        print(f"Average latency: {stats['avg_duration']:.2f}s")
    """
    
    def __init__(self, export_dir: Optional[Path] = None):
        """
        Initialize metrics collector.
        
        Args:
            export_dir: Directory to export metrics (optional)
        """
        self.export_dir = Path(export_dir) if export_dir else None
        self._metrics: List[OperationMetrics] = []
        self._operation_stats: Dict[str, List[float]] = defaultdict(list)
        self._current_operations: Dict[str, OperationMetrics] = {}
        
        if self.export_dir:
            self.export_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Initialized metrics collector")
    
    def start_operation(self, operation_name: str, **metadata) -> str:
        """
        Start tracking an operation.
        
        Args:
            operation_name: Name of the operation
            **metadata: Additional metadata to record
            
        Returns:
            Operation ID for later reference
        """
        operation_id = f"{operation_name}_{time.time()}"
        
        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata
        )
        
        self._current_operations[operation_id] = metrics
        
        logger.debug(
            f"Started operation: {operation_name}",
            extra={'operation_id': operation_id, **metadata}
        )
        
        return operation_id
    
    def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        items_processed: int = 0,
        errors: int = 0,
        **metadata
    ):
        """
        End tracking an operation.
        
        Args:
            operation_id: ID returned from start_operation
            success: Whether operation succeeded
            items_processed: Number of items processed
            errors: Number of errors encountered
            **metadata: Additional metadata to record
        """
        if operation_id not in self._current_operations:
            logger.warning(f"Unknown operation ID: {operation_id}")
            return
        
        metrics = self._current_operations.pop(operation_id)
        metrics.complete(success)
        metrics.items_processed = items_processed
        metrics.errors = errors
        metrics.metadata.update(metadata)
        
        # Store metrics
        self._metrics.append(metrics)
        self._operation_stats[metrics.operation_name].append(metrics.duration)
        
        logger.info(
            f"Completed operation: {metrics.operation_name}",
            extra={
                'operation_id': operation_id,
                'duration': metrics.duration,
                'success': success,
                'items_processed': items_processed,
                'throughput': items_processed / metrics.duration if metrics.duration else 0
            }
        )
    
    def track_operation(self, operation_name: str, **metadata):
        """
        Context manager for tracking operations.
        
        Usage:
            with collector.track_operation("chunking", subject="biology"):
                process_chunks()
        """
        class OperationContext:
            def __init__(self, collector, name, metadata):
                self.collector = collector
                self.name = name
                self.metadata = metadata
                self.operation_id = None
                self.items_processed = 0
                self.errors = 0
            
            def __enter__(self):
                self.operation_id = self.collector.start_operation(
                    self.name,
                    **self.metadata
                )
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                success = exc_type is None
                self.collector.end_operation(
                    self.operation_id,
                    success=success,
                    items_processed=self.items_processed,
                    errors=self.errors
                )
                return False  # Don't suppress exceptions
        
        return OperationContext(self, operation_name, metadata)
    
    def record_metric(
        self,
        operation_name: str,
        value: float,
        unit: str = "seconds",
        **metadata
    ):
        """
        Record a single metric value.
        
        Args:
            operation_name: Name of the operation
            value: Metric value
            unit: Unit of measurement
            **metadata: Additional metadata
        """
        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            duration=value,
            metadata={'unit': unit, **metadata}
        )
        metrics.end_time = metrics.start_time + value
        
        self._metrics.append(metrics)
        self._operation_stats[operation_name].append(value)
    
    def get_statistics(
        self,
        operation_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics.
        
        Args:
            operation_name: Specific operation (all if None)
            
        Returns:
            Dictionary of statistics
        """
        if operation_name:
            # Statistics for specific operation
            metrics = [m for m in self._metrics if m.operation_name == operation_name]
        else:
            # Statistics for all operations
            metrics = self._metrics
        
        if not metrics:
            return {}
        
        durations = [m.duration for m in metrics if m.duration is not None]
        successes = sum(1 for m in metrics if m.success)
        total_items = sum(m.items_processed for m in metrics)
        total_errors = sum(m.errors for m in metrics)
        
        stats = {
            'operation_name': operation_name or 'all',
            'total_operations': len(metrics),
            'successful_operations': successes,
            'failed_operations': len(metrics) - successes,
            'success_rate': successes / len(metrics) if metrics else 0,
            'total_items_processed': total_items,
            'total_errors': total_errors,
            'error_rate': total_errors / total_items if total_items else 0,
        }
        
        if durations:
            stats.update({
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'total_duration': sum(durations),
                'avg_throughput': total_items / sum(durations) if sum(durations) else 0,
            })
        
        return stats
    
    def get_operation_names(self) -> List[str]:
        """Get list of all tracked operation names."""
        return list(set(m.operation_name for m in self._metrics))
    
    def get_recent_metrics(
        self,
        operation_name: Optional[str] = None,
        limit: int = 10
    ) -> List[OperationMetrics]:
        """
        Get most recent metrics.
        
        Args:
            operation_name: Filter by operation (all if None)
            limit: Maximum number of metrics to return
            
        Returns:
            List of recent metrics
        """
        if operation_name:
            metrics = [m for m in self._metrics if m.operation_name == operation_name]
        else:
            metrics = self._metrics
        
        # Sort by start time (most recent first)
        metrics = sorted(metrics, key=lambda m: m.start_time, reverse=True)
        
        return metrics[:limit]
    
    def export_metrics(self, filepath: Optional[Path] = None) -> bool:
        """
        Export metrics to JSON file.
        
        Args:
            filepath: Export file path (auto-generated if None)
            
        Returns:
            True if export succeeded
        """
        try:
            if filepath is None:
                if self.export_dir is None:
                    logger.warning("No export directory configured")
                    return False
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = self.export_dir / f"metrics_{timestamp}.json"
            
            # Prepare export data
            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_metrics': len(self._metrics),
                'operations': self.get_operation_names(),
                'statistics': {
                    name: self.get_statistics(name)
                    for name in self.get_operation_names()
                },
                'metrics': [m.to_dict() for m in self._metrics]
            }
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(
                f"Exported metrics to {filepath}",
                extra={
                    'filepath': str(filepath),
                    'total_metrics': len(self._metrics)
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to export metrics: {e}",
                exc_info=True
            )
            return False
    
    def clear(self):
        """Clear all collected metrics."""
        self._metrics.clear()
        self._operation_stats.clear()
        self._current_operations.clear()
        logger.info("Cleared all metrics")
    
    def get_summary(self) -> str:
        """Get human-readable summary of metrics."""
        stats = self.get_statistics()
        
        summary = f"""
Metrics Summary
===============
Total Operations: {stats.get('total_operations', 0)}
Success Rate: {stats.get('success_rate', 0):.1%}
Total Items Processed: {stats.get('total_items_processed', 0)}
Total Errors: {stats.get('total_errors', 0)}
Average Duration: {stats.get('avg_duration', 0):.2f}s
Average Throughput: {stats.get('avg_throughput', 0):.1f} items/sec

Operations:
{chr(10).join(f"  - {name}" for name in self.get_operation_names())}
        """.strip()
        
        return summary


# Export
__all__ = ['MetricsCollector', 'OperationMetrics']
