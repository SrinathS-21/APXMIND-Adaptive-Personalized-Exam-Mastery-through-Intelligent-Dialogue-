"""
Quality Tracker
===============

Tracks chunk quality scores and identifies quality trends over time.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import statistics

from ..chunking.base_chunker import Chunk
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class QualityReport:
    """
    Quality assessment report.
    
    Attributes:
        timestamp: When report was generated
        total_chunks: Total number of chunks assessed
        avg_quality: Average quality score
        min_quality: Minimum quality score
        max_quality: Maximum quality score
        quality_distribution: Distribution across quality bins
        low_quality_count: Number of chunks below threshold
        issues: List of quality issues found
    """
    timestamp: datetime
    total_chunks: int
    avg_quality: float
    min_quality: float
    max_quality: float
    quality_distribution: Dict[str, int]
    low_quality_count: int
    issues: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_chunks': self.total_chunks,
            'avg_quality': self.avg_quality,
            'min_quality': self.min_quality,
            'max_quality': self.max_quality,
            'quality_distribution': self.quality_distribution,
            'low_quality_count': self.low_quality_count,
            'low_quality_percentage': (
                self.low_quality_count / self.total_chunks * 100
                if self.total_chunks > 0 else 0
            ),
            'issues': self.issues
        }


class QualityTracker:
    """
    Tracks and analyzes chunk quality over time.
    
    Features:
    - Monitor quality score distribution
    - Identify low-quality chunks
    - Track quality trends by subject/topic
    - Generate quality reports
    - Alert on quality degradation
    
    Usage:
        tracker = QualityTracker(min_quality=0.6)
        
        # Track chunk quality
        for chunk in chunks:
            tracker.track_chunk(chunk)
        
        # Generate report
        report = tracker.generate_report()
        print(f"Average quality: {report.avg_quality:.2f}")
        
        # Get low-quality chunks
        low_quality = tracker.get_low_quality_chunks(threshold=0.5)
    """
    
    def __init__(
        self,
        min_quality: float = 0.6,
        export_dir: Optional[Path] = None
    ):
        """
        Initialize quality tracker.
        
        Args:
            min_quality: Minimum acceptable quality score
            export_dir: Directory to export reports (optional)
        """
        self.min_quality = min_quality
        self.export_dir = Path(export_dir) if export_dir else None
        
        # Storage
        self._chunk_quality: List[Tuple[str, float, Dict[str, Any]]] = []
        self._quality_by_subject: Dict[str, List[float]] = defaultdict(list)
        self._quality_by_content_type: Dict[str, List[float]] = defaultdict(list)
        self._low_quality_chunks: List[Tuple[str, float, str]] = []
        
        if self.export_dir:
            self.export_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Initialized quality tracker",
            extra={'min_quality': min_quality}
        )
    
    def track_chunk(self, chunk: Chunk):
        """
        Track quality for a single chunk.
        
        Args:
            chunk: Chunk to track
        """
        chunk_id = chunk.chunk_id
        quality = chunk.quality_score
        metadata = chunk.metadata
        
        # Store overall quality
        self._chunk_quality.append((chunk_id, quality, metadata))
        
        # Track by subject
        if 'subject' in metadata:
            self._quality_by_subject[metadata['subject']].append(quality)
        
        # Track by content type
        if 'content_type' in metadata:
            self._quality_by_content_type[metadata['content_type']].append(quality)
        
        # Track low-quality chunks
        if quality < self.min_quality:
            reason = self._diagnose_low_quality(chunk)
            self._low_quality_chunks.append((chunk_id, quality, reason))
            
            logger.warning(
                f"Low-quality chunk detected: {chunk_id}",
                extra={
                    'chunk_id': chunk_id,
                    'quality_score': quality,
                    'min_quality': self.min_quality,
                    'reason': reason,
                    'subject': metadata.get('subject'),
                    'content_type': metadata.get('content_type')
                }
            )
    
    def track_batch(self, chunks: List[Chunk]):
        """
        Track quality for multiple chunks.
        
        Args:
            chunks: List of chunks to track
        """
        for chunk in chunks:
            self.track_chunk(chunk)
        
        logger.info(
            f"Tracked quality for {len(chunks)} chunks",
            extra={
                'total_chunks': len(self._chunk_quality),
                'avg_quality': self.get_average_quality()
            }
        )
    
    def generate_report(self) -> QualityReport:
        """
        Generate comprehensive quality report.
        
        Returns:
            QualityReport with statistics and issues
        """
        if not self._chunk_quality:
            logger.warning("No chunks tracked yet")
            return QualityReport(
                timestamp=datetime.now(),
                total_chunks=0,
                avg_quality=0.0,
                min_quality=0.0,
                max_quality=0.0,
                quality_distribution={},
                low_quality_count=0
            )
        
        # Calculate statistics
        qualities = [q for _, q, _ in self._chunk_quality]
        avg_quality = statistics.mean(qualities)
        min_quality = min(qualities)
        max_quality = max(qualities)
        
        # Quality distribution (bins: 0-0.3, 0.3-0.6, 0.6-0.8, 0.8-1.0)
        distribution = {
            'poor (0.0-0.3)': sum(1 for q in qualities if q < 0.3),
            'fair (0.3-0.6)': sum(1 for q in qualities if 0.3 <= q < 0.6),
            'good (0.6-0.8)': sum(1 for q in qualities if 0.6 <= q < 0.8),
            'excellent (0.8-1.0)': sum(1 for q in qualities if q >= 0.8)
        }
        
        # Identify issues
        issues = self._identify_issues()
        
        report = QualityReport(
            timestamp=datetime.now(),
            total_chunks=len(self._chunk_quality),
            avg_quality=avg_quality,
            min_quality=min_quality,
            max_quality=max_quality,
            quality_distribution=distribution,
            low_quality_count=len(self._low_quality_chunks),
            issues=issues
        )
        
        logger.info(
            "Generated quality report",
            extra={
                'total_chunks': report.total_chunks,
                'avg_quality': report.avg_quality,
                'low_quality_count': report.low_quality_count,
                'issues_found': len(issues)
            }
        )
        
        return report
    
    def get_average_quality(self) -> float:
        """Get overall average quality score."""
        if not self._chunk_quality:
            return 0.0
        qualities = [q for _, q, _ in self._chunk_quality]
        return statistics.mean(qualities)
    
    def get_quality_by_subject(self) -> Dict[str, Dict[str, float]]:
        """
        Get quality statistics by subject.
        
        Returns:
            Dictionary mapping subject to quality stats
        """
        result = {}
        
        for subject, qualities in self._quality_by_subject.items():
            result[subject] = {
                'avg_quality': statistics.mean(qualities),
                'min_quality': min(qualities),
                'max_quality': max(qualities),
                'chunk_count': len(qualities)
            }
        
        return result
    
    def get_quality_by_content_type(self) -> Dict[str, Dict[str, float]]:
        """
        Get quality statistics by content type.
        
        Returns:
            Dictionary mapping content type to quality stats
        """
        result = {}
        
        for content_type, qualities in self._quality_by_content_type.items():
            result[content_type] = {
                'avg_quality': statistics.mean(qualities),
                'min_quality': min(qualities),
                'max_quality': max(qualities),
                'chunk_count': len(qualities)
            }
        
        return result
    
    def get_low_quality_chunks(
        self,
        threshold: Optional[float] = None
    ) -> List[Tuple[str, float, str]]:
        """
        Get list of low-quality chunks.
        
        Args:
            threshold: Quality threshold (uses min_quality if None)
            
        Returns:
            List of (chunk_id, quality_score, reason) tuples
        """
        threshold = threshold or self.min_quality
        
        return [
            (chunk_id, quality, reason)
            for chunk_id, quality, reason in self._low_quality_chunks
            if quality < threshold
        ]
    
    def export_report(
        self,
        filepath: Optional[Path] = None,
        include_low_quality_details: bool = True
    ) -> bool:
        """
        Export quality report to JSON file.
        
        Args:
            filepath: Export file path (auto-generated if None)
            include_low_quality_details: Include details of low-quality chunks
            
        Returns:
            True if export succeeded
        """
        try:
            if filepath is None:
                if self.export_dir is None:
                    logger.warning("No export directory configured")
                    return False
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = self.export_dir / f"quality_report_{timestamp}.json"
            
            # Generate report
            report = self.generate_report()
            
            # Prepare export data
            export_data = report.to_dict()
            export_data['quality_by_subject'] = self.get_quality_by_subject()
            export_data['quality_by_content_type'] = self.get_quality_by_content_type()
            
            if include_low_quality_details:
                export_data['low_quality_chunks'] = [
                    {
                        'chunk_id': chunk_id,
                        'quality_score': quality,
                        'reason': reason
                    }
                    for chunk_id, quality, reason in self._low_quality_chunks
                ]
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(
                f"Exported quality report to {filepath}",
                extra={'filepath': str(filepath)}
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to export quality report: {e}",
                exc_info=True
            )
            return False
    
    def _diagnose_low_quality(self, chunk: Chunk) -> str:
        """Diagnose why a chunk has low quality."""
        reasons = []
        
        # Size issues
        size = chunk.get_size()
        if size < 100:
            reasons.append(f"too short ({size} chars)")
        elif size > 2000:
            reasons.append(f"too long ({size} chars)")
        
        # Content issues
        if not chunk.content.rstrip().endswith(('.', '!', '?', '।', '।।')):
            reasons.append("incomplete sentence")
        
        words = chunk.get_word_count()
        if words < 10:
            reasons.append(f"too few words ({words})")
        
        # Metadata issues
        required_fields = ['subject', 'topic', 'content_type']
        missing = [f for f in required_fields if f not in chunk.metadata]
        if missing:
            reasons.append(f"missing metadata: {', '.join(missing)}")
        
        return "; ".join(reasons) if reasons else "unknown"
    
    def _identify_issues(self) -> List[Dict[str, Any]]:
        """Identify quality issues across all tracked chunks."""
        issues = []
        
        # Issue: High percentage of low-quality chunks
        if self._chunk_quality:
            low_quality_pct = len(self._low_quality_chunks) / len(self._chunk_quality)
            if low_quality_pct > 0.2:  # More than 20%
                issues.append({
                    'severity': 'high',
                    'type': 'high_low_quality_rate',
                    'message': f'{low_quality_pct:.1%} of chunks have low quality',
                    'recommendation': 'Review chunking strategy and preprocessing'
                })
        
        # Issue: Subject-specific quality problems
        for subject, qualities in self._quality_by_subject.items():
            avg = statistics.mean(qualities)
            if avg < self.min_quality:
                issues.append({
                    'severity': 'medium',
                    'type': 'low_subject_quality',
                    'subject': subject,
                    'avg_quality': avg,
                    'message': f'{subject} has low average quality ({avg:.2f})',
                    'recommendation': f'Review {subject} content and chunking parameters'
                })
        
        # Issue: Content type quality problems
        for content_type, qualities in self._quality_by_content_type.items():
            avg = statistics.mean(qualities)
            if avg < self.min_quality:
                issues.append({
                    'severity': 'medium',
                    'type': 'low_content_type_quality',
                    'content_type': content_type,
                    'avg_quality': avg,
                    'message': f'{content_type} has low average quality ({avg:.2f})',
                    'recommendation': f'Adjust chunking for {content_type} content'
                })
        
        return issues
    
    def clear(self):
        """Clear all tracked quality data."""
        self._chunk_quality.clear()
        self._quality_by_subject.clear()
        self._quality_by_content_type.clear()
        self._low_quality_chunks.clear()
        logger.info("Cleared all quality tracking data")
    
    def get_summary(self) -> str:
        """Get human-readable summary of quality tracking."""
        if not self._chunk_quality:
            return "No chunks tracked yet."
        
        report = self.generate_report()
        
        summary = f"""
Quality Tracking Summary
========================
Total Chunks: {report.total_chunks}
Average Quality: {report.avg_quality:.2f}
Low-Quality Chunks: {report.low_quality_count} ({report.low_quality_count / report.total_chunks * 100:.1f}%)

Quality Distribution:
{chr(10).join(f"  {bin_name}: {count}" for bin_name, count in report.quality_distribution.items())}

By Subject:
{chr(10).join(f"  {subj}: {stats['avg_quality']:.2f} ({stats['chunk_count']} chunks)" 
              for subj, stats in self.get_quality_by_subject().items())}

Issues Found: {len(report.issues)}
        """.strip()
        
        return summary


# Export
__all__ = ['QualityTracker', 'QualityReport']
