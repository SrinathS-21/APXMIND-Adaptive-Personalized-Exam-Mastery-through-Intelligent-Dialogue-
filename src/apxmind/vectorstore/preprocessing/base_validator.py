"""
Base Validator Abstract Classes
================================

Defines abstract interfaces for all validation components.
All validator implementations must inherit from these base classes.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..chunking.base_chunker import Chunk


class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"      # Fatal issues that prevent processing
    WARNING = "warning"  # Non-fatal issues that should be reviewed
    INFO = "info"        # Informational messages


@dataclass
class ValidationIssue:
    """
    Represents a validation issue found.
    
    Attributes:
        level: Severity level
        message: Human-readable description
        field: Field that failed validation
        value: Value that caused the issue
        suggestion: Suggested fix
    """
    level: ValidationLevel
    message: str
    field: Optional[str] = None
    value: Any = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'level': self.level.value,
            'message': self.message,
            'field': self.field,
            'value': str(self.value) if self.value is not None else None,
            'suggestion': self.suggestion
        }


@dataclass
class ValidationResult:
    """
    Result of a validation operation.
    
    Attributes:
        valid: Whether validation passed
        issues: List of issues found
        metrics: Validation metrics
        score: Overall quality score (0.0-1.0)
    """
    valid: bool
    issues: List[ValidationIssue] = None
    metrics: Dict[str, Any] = None
    score: float = 0.0
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.metrics is None:
            self.metrics = {}
    
    def has_errors(self) -> bool:
        """Check if there are any error-level issues."""
        return any(i.level == ValidationLevel.ERROR for i in self.issues)
    
    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(i.level == ValidationLevel.WARNING for i in self.issues)
    
    def get_error_count(self) -> int:
        """Get number of errors."""
        return sum(1 for i in self.issues if i.level == ValidationLevel.ERROR)
    
    def get_warning_count(self) -> int:
        """Get number of warnings."""
        return sum(1 for i in self.issues if i.level == ValidationLevel.WARNING)


class BaseValidator(ABC):
    """
    Abstract base class for all validators.
    
    Responsibilities:
    - Validate content quality
    - Check metadata completeness
    - Verify structural integrity
    - Calculate quality scores
    
    Implementations:
    - ChunkValidator: Validate individual chunks
    - MetadataValidator: Validate metadata fields
    - ContentQualityValidator: Assess content quality
    """
    
    def __init__(
        self,
        min_score: float = 0.6,
        strict: bool = False,
        **kwargs
    ):
        """
        Initialize validator.
        
        Args:
            min_score: Minimum quality score threshold
            strict: If True, treat warnings as errors
            **kwargs: Additional validator-specific parameters
        """
        self.min_score = min_score
        self.strict = strict
        self.config = kwargs
        self._validation_count = 0
        self._pass_count = 0
    
    @abstractmethod
    def validate(self, item: Any) -> ValidationResult:
        """
        Validate an item.
        
        Args:
            item: Item to validate
            
        Returns:
            ValidationResult with issues and score
        """
        pass
    
    def validate_batch(
        self,
        items: List[Any],
        fail_fast: bool = False
    ) -> List[ValidationResult]:
        """
        Validate multiple items.
        
        Args:
            items: List of items to validate
            fail_fast: If True, stop on first error
            
        Returns:
            List of validation results
        """
        results = []
        
        for item in items:
            result = self.validate(item)
            results.append(result)
            
            self._validation_count += 1
            if result.valid:
                self._pass_count += 1
            
            if fail_fast and not result.valid:
                break
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            'total_validated': self._validation_count,
            'passed': self._pass_count,
            'failed': self._validation_count - self._pass_count,
            'pass_rate': (
                self._pass_count / self._validation_count
                if self._validation_count > 0
                else 0.0
            ),
            'min_score_threshold': self.min_score
        }


class ChunkValidator(BaseValidator):
    """
    Validator specifically for Chunk objects.
    
    Validates:
    - Content quality (readability, completeness)
    - Metadata completeness
    - Size constraints
    - Structural integrity
    """
    
    def __init__(
        self,
        min_size: int = 100,
        max_size: int = 2000,
        required_fields: List[str] = None,
        **kwargs
    ):
        """
        Initialize chunk validator.
        
        Args:
            min_size: Minimum chunk size in characters
            max_size: Maximum chunk size in characters
            required_fields: Metadata fields that must be present
            **kwargs: Additional parameters
        """
        super().__init__(**kwargs)
        self.min_size = min_size
        self.max_size = max_size
        self.required_fields = required_fields or [
            'chunk_id',
            'subject',
            'topic',
            'content_type',
            'source_file'
        ]
    
    def validate(self, chunk: Chunk) -> ValidationResult:
        """
        Validate a chunk.
        
        Args:
            chunk: Chunk to validate
            
        Returns:
            ValidationResult with issues and score
        """
        issues = []
        score = 1.0
        
        # Validate content
        content_issues, content_score = self._validate_content(chunk)
        issues.extend(content_issues)
        score *= content_score
        
        # Validate metadata
        metadata_issues, metadata_score = self._validate_metadata(chunk)
        issues.extend(metadata_issues)
        score *= metadata_score
        
        # Validate size
        size_issues, size_score = self._validate_size(chunk)
        issues.extend(size_issues)
        score *= size_score
        
        # Determine if valid
        has_errors = any(i.level == ValidationLevel.ERROR for i in issues)
        has_warnings = any(i.level == ValidationLevel.WARNING for i in issues)
        valid = not has_errors and (not self.strict or not has_warnings)
        valid = valid and score >= self.min_score
        
        return ValidationResult(
            valid=valid,
            issues=issues,
            score=score,
            metrics={
                'content_score': content_score,
                'metadata_score': metadata_score,
                'size_score': size_score
            }
        )
    
    def _validate_content(self, chunk: Chunk) -> Tuple[List[ValidationIssue], float]:
        """Validate chunk content quality."""
        issues = []
        score = 1.0
        
        # Check if content is empty
        if not chunk.content.strip():
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Chunk content is empty",
                field="content",
                suggestion="Ensure chunker produces non-empty chunks"
            ))
            return issues, 0.0
        
        # Check readability (simple heuristics)
        words = chunk.get_word_count()
        if words < 10:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Chunk has very few words ({words})",
                field="content",
                value=words,
                suggestion="Consider merging with adjacent chunks"
            ))
            score *= 0.8
        
        # Check for completeness (ends with sentence boundary)
        if not chunk.content.rstrip().endswith(('.', '!', '?', '।', '।।')):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message="Chunk does not end with sentence boundary",
                field="content",
                suggestion="Adjust chunking to respect sentence boundaries"
            ))
            score *= 0.9
        
        # Check coherence (no excessive whitespace)
        lines = chunk.content.split('\n')
        empty_lines = sum(1 for line in lines if not line.strip())
        if empty_lines > len(lines) * 0.5:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message="Chunk contains excessive whitespace",
                field="content",
                value=f"{empty_lines}/{len(lines)} empty lines",
                suggestion="Clean up whitespace during preprocessing"
            ))
            score *= 0.85
        
        return issues, score
    
    def _validate_metadata(self, chunk: Chunk) -> Tuple[List[ValidationIssue], float]:
        """Validate chunk metadata completeness."""
        issues = []
        score = 1.0
        
        # Check required fields
        missing_fields = [
            field for field in self.required_fields
            if field not in chunk.metadata or not chunk.metadata[field]
        ]
        
        if missing_fields:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Missing required metadata fields: {', '.join(missing_fields)}",
                field="metadata",
                value=missing_fields,
                suggestion="Ensure metadata enrichment populates all required fields"
            ))
            score *= (len(self.required_fields) - len(missing_fields)) / len(self.required_fields)
        
        # Check metadata quality
        if 'quality_score' in chunk.metadata:
            quality = chunk.metadata['quality_score']
            if quality < 0.3:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Low chunk quality score: {quality:.2f}",
                    field="quality_score",
                    value=quality,
                    suggestion="Review chunking strategy for this content type"
                ))
                score *= quality
        
        return issues, score
    
    def _validate_size(self, chunk: Chunk) -> Tuple[List[ValidationIssue], float]:
        """Validate chunk size constraints."""
        issues = []
        score = 1.0
        
        size = chunk.get_size()
        
        # Check minimum size
        if size < self.min_size:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Chunk size ({size}) below minimum ({self.min_size})",
                field="content",
                value=size,
                suggestion="Merge with adjacent chunks or adjust min_size"
            ))
            score *= size / self.min_size
        
        # Check maximum size
        if size > self.max_size:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Chunk size ({size}) exceeds maximum ({self.max_size})",
                field="content",
                value=size,
                suggestion="Split chunk further or adjust max_size"
            ))
            score *= self.max_size / size
        
        return issues, score


# Export all validator classes
__all__ = [
    'ValidationLevel',
    'ValidationIssue',
    'ValidationResult',
    'BaseValidator',
    'ChunkValidator',
]
