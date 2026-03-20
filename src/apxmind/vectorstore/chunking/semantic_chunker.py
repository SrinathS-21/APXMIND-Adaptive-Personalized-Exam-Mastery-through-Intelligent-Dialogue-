"""
Semantic Chunker
================

Intelligent text chunking that preserves conceptual boundaries and
respects sentence/paragraph structure for optimal semantic coherence.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import hashlib

from .base_chunker import BaseChunker, Chunk, ChunkingResult
from ..constants import ChunkMetadata
from ..config import ChunkingConfig
from ..monitoring import get_logger

logger = get_logger(__name__)


class SemanticChunker(BaseChunker):
    """
    Semantic-aware text chunker that preserves conceptual boundaries.
    
    Features:
    - Respects sentence and paragraph boundaries
    - Uses configurable boundary markers
    - Maintains context with overlapping windows
    - Calculates multi-factor quality scores
    - Generates rich metadata
    
    Algorithm:
    1. Identify natural break points (sentences, paragraphs, sections)
    2. Group text into chunks near target size
    3. Ensure chunks don't break mid-sentence
    4. Add overlap for context continuity
    5. Score quality based on completeness, coherence, size
    
    Usage:
        config = ChunkingConfig(target_size=800, overlap=100)
        chunker = SemanticChunker(config=config)
        
        result = chunker.chunk(text, metadata={'subject': 'biology'})
        if result.success:
            print(f"Created {len(result.chunks)} chunks")
    """
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        **kwargs
    ):
        """
        Initialize semantic chunker.
        
        Args:
            config: ChunkingConfig object (creates default if None)
            **kwargs: Override specific config parameters
        """
        # Use provided config or create default
        self.config = config or ChunkingConfig()
        
        # Override config with kwargs if provided
        if kwargs:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        # Initialize base chunker
        super().__init__(
            target_size=self.config.target_size,
            min_size=self.config.min_size,
            max_size=self.config.max_size,
            overlap=self.config.overlap
        )
        
        # Compile boundary patterns for efficiency
        self._sentence_pattern = re.compile(r'[.!?।।।]\s+')
        self._paragraph_pattern = re.compile(r'\n\n+')
        self._section_pattern = re.compile(r'\n#{1,3}\s+.*?\n|^\d+\.\s+[A-Z].*?\n', re.MULTILINE)
        
        logger.info(
            "Initialized SemanticChunker",
            extra={
                'target_size': self.target_size,
                'min_size': self.min_size,
                'max_size': self.max_size,
                'overlap': self.overlap
            }
        )
    
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
            ChunkingResult with generated chunks or error
        """
        try:
            if not text or not text.strip():
                return ChunkingResult(
                    success=False,
                    error="Empty text provided"
                )
            
            # Normalize text
            text = self._normalize_text(text)
            
            # Find all potential split points
            split_points = self._find_all_split_points(text)
            
            # Create chunks using split points
            chunks = self._create_chunks_from_splits(text, split_points, metadata)
            
            # Validate chunks
            valid_chunks = []
            warnings = []
            
            for chunk in chunks:
                if self.validate_chunk(chunk):
                    valid_chunks.append(chunk)
                else:
                    warnings.append(
                        f"Chunk {chunk.chunk_id} failed validation "
                        f"(size={chunk.get_size()}, quality={chunk.quality_score:.2f})"
                    )
            
            # Calculate metrics
            metrics = {
                'total_chunks': len(chunks),
                'valid_chunks': len(valid_chunks),
                'invalid_chunks': len(chunks) - len(valid_chunks),
                'avg_chunk_size': sum(c.get_size() for c in valid_chunks) / len(valid_chunks) if valid_chunks else 0,
                'avg_quality': sum(c.quality_score for c in valid_chunks) / len(valid_chunks) if valid_chunks else 0,
                'text_length': len(text),
                'coverage': sum(c.get_size() for c in valid_chunks) / len(text) if text else 0
            }
            
            logger.info(
                "Chunking completed",
                extra={
                    'subject': metadata.get('subject'),
                    'total_chunks': len(valid_chunks),
                    'avg_quality': metrics['avg_quality'],
                    'text_length': len(text)
                }
            )
            
            return ChunkingResult(
                success=True,
                chunks=valid_chunks,
                warnings=warnings,
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(
                f"Chunking failed: {e}",
                exc_info=True,
                extra={'error': str(e)}
            )
            return ChunkingResult(
                success=False,
                error=str(e)
            )
    
    def find_split_points(
        self,
        text: str,
        target_pos: int
    ) -> List[int]:
        """
        Find optimal split points near target position.
        
        Priority order:
        1. Paragraph boundary (\\n\\n)
        2. Sentence boundary (. ! ? । ।।)
        3. Clause boundary (, ; :)
        4. Word boundary (space)
        
        Args:
            text: Text to analyze
            target_pos: Target position for split
            
        Returns:
            List of candidate split positions (sorted by preference)
        """
        candidates = []
        search_window = 200  # Look ±200 chars around target
        
        start = max(0, target_pos - search_window)
        end = min(len(text), target_pos + search_window)
        window = text[start:end]
        
        # Find paragraph boundaries (highest priority)
        for match in self._paragraph_pattern.finditer(window):
            pos = start + match.end()
            distance = abs(pos - target_pos)
            candidates.append((pos, distance, 0))  # Priority 0 (highest)
        
        # Find sentence boundaries
        for match in self._sentence_pattern.finditer(window):
            pos = start + match.end()
            distance = abs(pos - target_pos)
            candidates.append((pos, distance, 1))  # Priority 1
        
        # Find clause boundaries
        clause_pattern = re.compile(r'[,;:]\s+')
        for match in clause_pattern.finditer(window):
            pos = start + match.end()
            distance = abs(pos - target_pos)
            candidates.append((pos, distance, 2))  # Priority 2
        
        # Find word boundaries
        word_pattern = re.compile(r'\s+')
        for match in word_pattern.finditer(window):
            pos = start + match.end()
            distance = abs(pos - target_pos)
            candidates.append((pos, distance, 3))  # Priority 3
        
        # Sort by priority first, then by distance
        candidates.sort(key=lambda x: (x[2], x[1]))
        
        # Return positions only
        return [pos for pos, _, _ in candidates]
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent processing."""
        # Remove excessive whitespace
        text = re.sub(r' +', ' ', text)
        
        # Normalize line breaks
        text = re.sub(r'\r\n', '\n', text)
        
        # Remove trailing whitespace from lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        
        return text.strip()
    
    def _find_all_split_points(self, text: str) -> List[int]:
        """
        Find all natural split points in text.
        
        Returns:
            Sorted list of positions where text can be split
        """
        split_points = [0]  # Start of text
        
        # Add paragraph boundaries
        for match in self._paragraph_pattern.finditer(text):
            split_points.append(match.end())
        
        # Add sentence boundaries
        for match in self._sentence_pattern.finditer(text):
            pos = match.end()
            # Only add if not too close to existing split point
            if not any(abs(pos - sp) < 20 for sp in split_points):
                split_points.append(pos)
        
        split_points.append(len(text))  # End of text
        
        return sorted(set(split_points))
    
    def _create_chunks_from_splits(
        self,
        text: str,
        split_points: List[int],
        metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Create chunks using identified split points.
        
        Args:
            text: Full text
            split_points: List of positions where splits can occur
            metadata: Document-level metadata
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        current_pos = 0
        chunk_index = 0
        
        # Generate document ID for chunk IDs
        doc_id = self._generate_document_id(metadata)
        
        while current_pos < len(text):
            # Find end position for this chunk
            target_end = current_pos + self.target_size
            
            # Find best split point near target
            best_split = self._find_best_split(
                text,
                current_pos,
                target_end,
                split_points
            )
            
            # Extract chunk text
            chunk_text = text[current_pos:best_split].strip()
            
            # Skip empty chunks
            if not chunk_text:
                current_pos = best_split
                continue
            
            # Create chunk
            chunk = self._create_chunk(
                content=chunk_text,
                start_pos=current_pos,
                end_pos=best_split,
                chunk_index=chunk_index,
                doc_id=doc_id,
                metadata=metadata
            )
            
            chunks.append(chunk)
            chunk_index += 1
            
            # Move to next position with overlap
            current_pos = max(best_split - self.overlap, best_split)
            
            # Prevent infinite loop
            if current_pos >= len(text):
                break
        
        return chunks
    
    def _find_best_split(
        self,
        text: str,
        start: int,
        target_end: int,
        split_points: List[int]
    ) -> int:
        """
        Find the best split point between start and target_end.
        
        Args:
            text: Full text
            start: Start position of current chunk
            target_end: Ideal end position
            split_points: All available split points
            
        Returns:
            Best split position
        """
        # Filter split points in valid range
        valid_splits = [
            sp for sp in split_points
            if start + self.min_size <= sp <= min(start + self.max_size, len(text))
        ]
        
        if not valid_splits:
            # No valid split found, use max_size
            return min(start + self.max_size, len(text))
        
        # Find split closest to target
        best_split = min(valid_splits, key=lambda sp: abs(sp - target_end))
        
        return best_split
    
    def _create_chunk(
        self,
        content: str,
        start_pos: int,
        end_pos: int,
        chunk_index: int,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> Chunk:
        """
        Create a Chunk object with full metadata.
        
        Args:
            content: Chunk text content
            start_pos: Start position in original text
            end_pos: End position in original text
            chunk_index: Index of this chunk
            doc_id: Document identifier
            metadata: Document-level metadata
            
        Returns:
            Chunk object with populated metadata
        """
        # Generate chunk ID
        chunk_id = self.generate_chunk_id(doc_id, chunk_index)
        
        # Create base chunk metadata
        chunk_metadata: ChunkMetadata = {
            'chunk_id': chunk_id,
            'chunk_index': chunk_index,
            'subject': metadata.get('subject', ''),
            'topic': metadata.get('topic', ''),
            'subtopic': metadata.get('subtopic', ''),
            'content_type': metadata.get('content_type', 'textbook'),
            'difficulty': metadata.get('difficulty', 'intermediate'),
            'class_level': metadata.get('class_level', 12),
            'chapter': metadata.get('chapter', ''),
            'section': metadata.get('section', ''),
            'page_number': metadata.get('page_number'),
            'quality_score': 0.0,  # Will be calculated
            'key_terms': [],
            'entities': [],
            'concepts': [],
            'prerequisites': [],
            'related_topics': [],
            'summary': '',
            'has_diagram': False,
            'has_formula': self._detect_formula(content),
            'has_example': self._detect_example(content),
            'has_equation': self._detect_equation(content),
            'language': metadata.get('language', 'english'),
            'source_file': metadata.get('source_file', ''),
            'source_path': metadata.get('source_path', ''),
            'created_at': datetime.now().isoformat(),
            'embedding_model': 'nomic-embed-text',
            'chunk_method': 'semantic',
            'custom_metadata': metadata.get('custom_metadata', {})
        }
        
        # Create chunk object
        chunk = Chunk(
            content=content,
            metadata=chunk_metadata,
            chunk_id=chunk_id,
            start_pos=start_pos,
            end_pos=end_pos,
            quality_score=0.0,  # Temporary
            created_at=datetime.now()
        )
        
        # Calculate and set quality score
        quality_score = self.calculate_quality_score(chunk)
        chunk.quality_score = quality_score
        chunk.metadata['quality_score'] = quality_score
        
        return chunk
    
    def _generate_document_id(self, metadata: Dict[str, Any]) -> str:
        """Generate unique document ID from metadata."""
        # Use source file and subject to create ID
        source = metadata.get('source_file', 'unknown')
        subject = metadata.get('subject', 'general')
        
        # Create hash for uniqueness
        hash_input = f"{source}_{subject}_{datetime.now().isoformat()}"
        hash_hex = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        
        return f"{subject}_{hash_hex}"
    
    def _detect_formula(self, text: str) -> bool:
        """Detect if text contains mathematical formulas."""
        # Look for common formula patterns
        formula_patterns = [
            r'[A-Z][a-z]?\d*[\+\-]',  # Chemical formulas (H2O, CO2)
            r'\\frac\{',  # LaTeX fractions
            r'\\sqrt\{',  # LaTeX square roots
            r'[a-z]\s*=\s*[0-9]',  # Equations (a = 5)
        ]
        
        return any(re.search(pattern, text) for pattern in formula_patterns)
    
    def _detect_example(self, text: str) -> bool:
        """Detect if text contains examples."""
        example_keywords = [
            'example', 'for instance', 'for example', 'e.g.',
            'उदाहरण', 'जैसे', 'such as', 'let us consider'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in example_keywords)
    
    def _detect_equation(self, text: str) -> bool:
        """Detect if text contains equations."""
        # Look for equation patterns
        equation_patterns = [
            r'[a-zA-Z]\s*=\s*[a-zA-Z0-9\+\-\*/\(\)]+',  # a = b + c
            r'\\begin\{equation\}',  # LaTeX equations
            r'\$.*?\$',  # Inline math
            r'F\s*=\s*ma',  # Physics equations
        ]
        
        return any(re.search(pattern, text) for pattern in equation_patterns)


# Export
__all__ = ['SemanticChunker']
