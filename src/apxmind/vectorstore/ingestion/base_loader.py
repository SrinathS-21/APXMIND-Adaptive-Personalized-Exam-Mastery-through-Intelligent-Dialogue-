"""
Base Loader Abstract Classes
=============================

Defines abstract interfaces for all data ingestion components.
All loader implementations must inherit from these base classes.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass
from datetime import datetime

from ..constants import Subject, ContentType


@dataclass
class Document:
    """
    Represents a loaded document before chunking.
    
    Attributes:
        content: Raw text content
        metadata: Document-level metadata
        source_path: Original file path
        page_count: Number of pages (for PDFs)
        load_time: When document was loaded
        checksum: MD5 hash for deduplication
    """
    content: str
    metadata: Dict[str, Any]
    source_path: Path
    page_count: Optional[int] = None
    load_time: datetime = None
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.load_time is None:
            self.load_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'content': self.content,
            'metadata': self.metadata,
            'source_path': str(self.source_path),
            'page_count': self.page_count,
            'load_time': self.load_time.isoformat(),
            'checksum': self.checksum
        }


@dataclass
class LoadResult:
    """
    Result of a document loading operation.
    
    Attributes:
        success: Whether loading succeeded
        document: Loaded document (if successful)
        error: Error message (if failed)
        warnings: Non-fatal warnings
        metrics: Performance metrics
    """
    success: bool
    document: Optional[Document] = None
    error: Optional[str] = None
    warnings: List[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metrics is None:
            self.metrics = {}


class BaseLoader(ABC):
    """
    Abstract base class for all document loaders.
    
    Responsibilities:
    - Load documents from various sources (PDF, TXT, etc.)
    - Extract metadata (title, author, creation date)
    - Handle encoding issues
    - Validate content quality
    - Track loading metrics
    
    Implementations:
    - PDFLoader: Extract text from PDF files
    - TextLoader: Load plain text files
    - HTMLLoader: Parse HTML documents (future)
    """
    
    def __init__(
        self,
        subject: Subject,
        content_type: ContentType,
        **kwargs
    ):
        """
        Initialize base loader.
        
        Args:
            subject: Subject area (biology, chemistry, physics)
            content_type: Type of content being loaded
            **kwargs: Additional loader-specific parameters
        """
        self.subject = subject
        self.content_type = content_type
        self.config = kwargs
        self._load_count = 0
        self._error_count = 0
    
    @abstractmethod
    def load(self, file_path: Path) -> LoadResult:
        """
        Load a single document.
        
        Args:
            file_path: Path to the file to load
            
        Returns:
            LoadResult with document or error
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        pass
    
    @abstractmethod
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate that file can be loaded.
        
        Args:
            file_path: Path to validate
            
        Returns:
            True if file is valid and loadable
        """
        pass
    
    def load_batch(
        self,
        file_paths: List[Path],
        fail_fast: bool = False
    ) -> Iterator[LoadResult]:
        """
        Load multiple documents.
        
        Args:
            file_paths: List of file paths to load
            fail_fast: If True, stop on first error
            
        Yields:
            LoadResult for each file
        """
        for path in file_paths:
            result = self.load(path)
            
            if result.success:
                self._load_count += 1
            else:
                self._error_count += 1
                if fail_fast:
                    raise RuntimeError(f"Failed to load {path}: {result.error}")
            
            yield result
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract base metadata from file.
        
        Args:
            file_path: File to extract metadata from
            
        Returns:
            Dictionary of metadata fields
        """
        return {
            'source_file': file_path.name,
            'source_path': str(file_path),
            'file_size': file_path.stat().st_size if file_path.exists() else 0,
            'file_modified': datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat() if file_path.exists() else None,
            'subject': self.subject.value,
            'content_type': self.content_type.value,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get loading statistics."""
        return {
            'total_loaded': self._load_count,
            'total_errors': self._error_count,
            'success_rate': (
                self._load_count / (self._load_count + self._error_count)
                if (self._load_count + self._error_count) > 0
                else 0.0
            )
        }
    
    def reset_statistics(self):
        """Reset loading counters."""
        self._load_count = 0
        self._error_count = 0


class BaseBatchProcessor(ABC):
    """
    Abstract base class for batch processing.
    
    Responsibilities:
    - Process documents in batches
    - Checkpoint progress
    - Handle failures gracefully
    - Track overall progress
    
    Implementations:
    - DatasetBatchProcessor: Process entire datasets
    - IncrementalProcessor: Process new/updated files only
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        checkpoint_dir: Optional[Path] = None,
        **kwargs
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of documents per batch
            checkpoint_dir: Directory for checkpoint files
            **kwargs: Additional processor-specific parameters
        """
        self.batch_size = batch_size
        self.checkpoint_dir = checkpoint_dir
        self.config = kwargs
        self._processed_count = 0
        self._failed_count = 0
    
    @abstractmethod
    def process_batch(
        self,
        documents: List[Document]
    ) -> List[LoadResult]:
        """
        Process a batch of documents.
        
        Args:
            documents: List of documents to process
            
        Returns:
            List of processing results
        """
        pass
    
    @abstractmethod
    def save_checkpoint(self, state: Dict[str, Any]) -> bool:
        """
        Save processing state to checkpoint.
        
        Args:
            state: Current processing state
            
        Returns:
            True if checkpoint saved successfully
        """
        pass
    
    @abstractmethod
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Load processing state from checkpoint.
        
        Returns:
            Saved state or None if no checkpoint exists
        """
        pass
    
    def get_progress(self) -> Dict[str, Any]:
        """Get processing progress."""
        return {
            'processed': self._processed_count,
            'failed': self._failed_count,
            'total': self._processed_count + self._failed_count,
            'success_rate': (
                self._processed_count / (self._processed_count + self._failed_count)
                if (self._processed_count + self._failed_count) > 0
                else 0.0
            )
        }


class BaseValidator(ABC):
    """
    Abstract base class for content validation.
    
    Responsibilities:
    - Validate document content quality
    - Check for encoding issues
    - Detect corrupted content
    - Verify minimum quality thresholds
    
    Implementations:
    - ContentValidator: Check text quality
    - MetadataValidator: Validate metadata completeness
    - StructureValidator: Verify document structure
    """
    
    @abstractmethod
    def validate(self, document: Document) -> LoadResult:
        """
        Validate a document.
        
        Args:
            document: Document to validate
            
        Returns:
            LoadResult indicating validation success/failure
        """
        pass
    
    @abstractmethod
    def get_quality_score(self, document: Document) -> float:
        """
        Calculate quality score for document.
        
        Args:
            document: Document to score
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        pass


# Export all base classes
__all__ = [
    'Document',
    'LoadResult',
    'BaseLoader',
    'BaseBatchProcessor',
    'BaseValidator',
]
