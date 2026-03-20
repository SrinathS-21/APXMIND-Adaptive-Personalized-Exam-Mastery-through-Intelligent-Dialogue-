"""
Data Ingestion Components
==========================

Components for loading documents from various sources.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

from .base_loader import (
    Document,
    LoadResult,
    BaseLoader,
    BaseBatchProcessor,
    BaseValidator
)
from .pdf_loader import (
    PDFLoader,
    NCERTBookLoader,
    QuestionPaperLoader
)
from .batch_processor import (
    BatchProcessor,
    DatasetBatchProcessor,
    ProcessingStats,
    BatchResult
)

__all__ = [
    'Document',
    'LoadResult',
    'BaseLoader',
    'BaseBatchProcessor',
    'BaseValidator',
    'PDFLoader',
    'NCERTBookLoader',
    'QuestionPaperLoader',
    'BatchProcessor',
    'DatasetBatchProcessor',
    'ProcessingStats',
    'BatchResult',
]
