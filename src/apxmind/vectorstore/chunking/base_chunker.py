"""
Base Chunker Abstract Classes
==============================

Defines abstract interfaces for all text chunking components.
All chunker implementations must inherit from these base classes.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..constants import ChunkMetadata, Subject, ContentType, Difficulty


@dataclass
class Chunk:
    """
    Represents a text chunk after semantic chunking.
    
    Attributes:
        content: Chunk text content
        metadata: Chunk-level metadata (30+ fields)
        chunk_id: Unique identifier
        start_pos: Start position in original document
        end_pos: End position in original document
        quality_score: Quality rating (0.0-1.0)
        created_at: Creation timestamp
    """
    content: str
    metadata: ChunkMetadata
    chunk_id: str
    start_pos: int
    end_pos: int
    quality_score: float = 0.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        
        # Validate quality score
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError(f"Quality score must be 0.0-1.0, got {self.quality_score}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'content': self.content,
            'metadata': dict(self.metadata),
            'chunk_id': self.chunk_id,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'quality_score': self.quality_score,
            'created_at': self.created_at.isoformat()
        }
    
    def get_size(self) -> int:
        """Get chunk size in characters."""
        return len(self.content)
    
    def get_word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())


@dataclass
class ChunkingResult:
    """
    Result of a chunking operation.
    
    Attributes:
        success: Whether chunking succeeded
        chunks: List of generated chunks
        error: Error message (if failed)
        warnings: Non-fatal warnings
        metrics: Chunking metrics
    """
    success: bool
    chunks: List[Chunk] = None
    error: Optional[str] = None
    warnings: List[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.chunks is None:
            self.chunks = []
        if self.warnings is None:
            self.warnings = []
        if self.metrics is None:
            self.metrics = {}
    
    def get_chunk_count(self) -> int:
        """Get number of chunks created."""
        return len(self.chunks)
    
    def get_average_quality(self) -> float:
        """Get average quality score across chunks."""
        if not self.chunks:
            return 0.0
        return sum(c.quality_score for c in self.chunks) / len(self.chunks)


class BaseChunker(ABC):
    """
    Abstract base class for all text chunkers.
    
    Responsibilities:
    - Split documents into semantic chunks
    - Preserve conceptual boundaries
    - Respect sentence/paragraph structure
    - Generate rich metadata
    - Validate chunk quality
    
    Implementations:
    - SemanticChunker: Boundary-aware intelligent chunking
    - FixedSizeChunker: Simple fixed-size splitting (fallback)
    - RecursiveChunker: Hierarchical multi-level chunking
    """
    
    def __init__(
        self,
        target_size: int = 800,
        min_size: int = 100,
        max_size: int = 2000,
        overlap: int = 100,
        **kwargs
    ):
        """
        Initialize base chunker.
        
        Args:
            target_size: Target chunk size in characters
            min_size: Minimum acceptable chunk size
            max_size: Maximum acceptable chunk size
            overlap: Overlap between consecutive chunks
            **kwargs: Additional chunker-specific parameters
        """
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size
        self.overlap = overlap
        self.config = kwargs
        self._chunk_count = 0
        self._total_quality = 0.0
    
    @abstractmethod
    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> ChunkingResult:
        """
        Split text into semantic chunks.
        
        Args:
            text: Text to chunk
            metadata: Document-level metadata to inherit
            
        Returns:
            ChunkingResult with generated chunks
        """
        pass
    
    @abstractmethod
    def find_split_points(
        self,
        text: str,
        target_pos: int
    ) -> List[int]:
        """
        Find optimal split points in text.
        
        Args:
            text: Text to analyze
            target_pos: Target position for split
            
        Returns:
            List of candidate split positions
        """
        pass
    
    def validate_chunk(self, chunk: Chunk) -> bool:
        """
        Validate that chunk meets quality requirements.
        
        Args:
            chunk: Chunk to validate
            
        Returns:
            True if chunk is valid
        """
        # Size validation
        if not self.min_size <= chunk.get_size() <= self.max_size:
            return False
        
        # Content validation
        if not chunk.content.strip():
            return False
        
        # Quality validation
        if chunk.quality_score < 0.3:  # Minimum threshold
            return False
        
        return True
    
    def calculate_quality_score(self, chunk: Chunk) -> float:
        """
        Calculate quality score for chunk.
        
        Args:
            chunk: Chunk to score
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Size score (prefer chunks near target size)
        size = chunk.get_size()
        size_ratio = min(size / self.target_size, self.target_size / size)
        score += size_ratio * 0.3
        
        # Completeness score (ends with sentence boundary)
        if chunk.content.rstrip().endswith(('.', '!', '?', '।', '।।')):
            score += 0.3
        
        # Content density (avoid too much whitespace)
        words = chunk.get_word_count()
        if words > 0:
            density = words / (size / 5)  # Assume avg word length 5
            score += min(density, 1.0) * 0.2
        
        # Metadata completeness
        required_fields = ['subject', 'topic', 'content_type']
        present = sum(1 for f in required_fields if chunk.metadata.get(f))
        score += (present / len(required_fields)) * 0.2
        
        return min(score, 1.0)
    
    def generate_chunk_id(
        self,
        document_id: str,
        chunk_index: int
    ) -> str:
        """
        Generate unique chunk ID.
        
        Args:
            document_id: Parent document identifier
            chunk_index: Index of this chunk in document
            
        Returns:
            Unique chunk identifier
        """
        return f"{document_id}_chunk_{chunk_index:04d}"
    
    def merge_metadata(
        self,
        base_metadata: Dict[str, Any],
        chunk_metadata: Dict[str, Any]
    ) -> ChunkMetadata:
        """
        Merge document and chunk-level metadata.
        
        Args:
            base_metadata: Document-level metadata
            chunk_metadata: Chunk-specific metadata
            
        Returns:
            Complete ChunkMetadata
        """
        merged = {**base_metadata, **chunk_metadata}
        
        # Ensure required fields are present
        if 'chunk_id' not in merged:
            merged['chunk_id'] = f"chunk_{self._chunk_count}"
        if 'chunk_index' not in merged:
            merged['chunk_index'] = self._chunk_count
        
        return merged  # type: ignore
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get chunking statistics."""
        avg_quality = (
            self._total_quality / self._chunk_count
            if self._chunk_count > 0
            else 0.0
        )
        
        return {
            'total_chunks': self._chunk_count,
            'average_quality': avg_quality,
            'target_size': self.target_size,
            'overlap': self.overlap
        }
    
    def reset_statistics(self):
        """Reset chunking counters."""
        self._chunk_count = 0
        self._total_quality = 0.0


class BaseChunkEnricher(ABC):
    """
    Abstract base class for chunk metadata enrichment.
    
    Responsibilities:
    - Extract key terms and concepts
    - Identify entities (formulas, reactions, etc.)
    - Determine difficulty level
    - Extract prerequisites
    - Generate summaries
    
    Implementations:
    - SemanticEnricher: NLP-based enrichment
    - RuleBasedEnricher: Pattern-based enrichment
    - LLMEnricher: LLM-powered enrichment (future)
    """
    
    @abstractmethod
    def enrich(self, chunk: Chunk) -> Chunk:
        """
        Enrich chunk with additional metadata.
        
        Args:
            chunk: Chunk to enrich
            
        Returns:
            Enriched chunk with updated metadata
        """
        pass
    
    @abstractmethod
    def extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key terms from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of key terms
        """
        pass
    
    @abstractmethod
    def extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities (formulas, reactions, etc.).
        
        Args:
            text: Text to analyze
            
        Returns:
            List of entities
        """
        pass
    
    @abstractmethod
    def determine_difficulty(self, text: str) -> Difficulty:
        """
        Determine content difficulty level.
        
        Args:
            text: Text to analyze
            
        Returns:
            Difficulty level enum
        """
        pass


# Export all base classes
__all__ = [
    'Chunk',
    'ChunkingResult',
    'BaseChunker',
    'BaseChunkEnricher',
]
