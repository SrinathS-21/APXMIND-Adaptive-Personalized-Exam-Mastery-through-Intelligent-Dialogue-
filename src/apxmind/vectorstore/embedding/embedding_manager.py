"""
Embedding Manager
=================

Manages embedding generation using nomic-embed-text model via Ollama.
Provides batched processing, caching, and normalization.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import hashlib
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass, asdict

from langchain_community.embeddings import OllamaEmbeddings

from ..config import EmbeddingConfig
from ..chunking.base_chunker import Chunk
from ..monitoring import get_logger, MetricsCollector


logger = get_logger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    
    success: bool
    embedding: Optional[np.ndarray]
    chunk_id: str
    model_name: str
    dimension: int
    normalized: bool
    cache_hit: bool
    processing_time: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'chunk_id': self.chunk_id,
            'model_name': self.model_name,
            'dimension': self.dimension,
            'normalized': self.normalized,
            'cache_hit': self.cache_hit,
            'processing_time': self.processing_time,
            'error': self.error
        }


@dataclass
class BatchEmbeddingResult:
    """Result of batch embedding generation."""
    
    success: bool
    embeddings: List[np.ndarray]
    chunk_ids: List[str]
    total_chunks: int
    successful_embeddings: int
    failed_embeddings: int
    cache_hits: int
    total_processing_time: float
    errors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'total_chunks': self.total_chunks,
            'successful_embeddings': self.successful_embeddings,
            'failed_embeddings': self.failed_embeddings,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': self.cache_hits / self.total_chunks if self.total_chunks > 0 else 0,
            'total_processing_time': self.total_processing_time,
            'avg_time_per_chunk': self.total_processing_time / self.total_chunks if self.total_chunks > 0 else 0,
            'error_count': len(self.errors)
        }


class EmbeddingCache:
    """
    LRU cache for embeddings.
    
    Stores embeddings on disk to avoid re-computation.
    Uses chunk content hash as key for cache lookups.
    """
    
    def __init__(self, cache_dir: str, max_size_mb: int = 1000):
        """
        Initialize embedding cache.
        
        Args:
            cache_dir: Directory to store cache files
            max_size_mb: Maximum cache size in MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        
        # Cache metadata file
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()
        
        logger.info(f"Initialized embedding cache: {self.cache_dir}")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {'entries': {}, 'total_size_mb': 0}
    
    def _save_metadata(self):
        """Save cache metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _compute_hash(self, text: str) -> str:
        """Compute hash of text for cache key."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, content_hash: str) -> Path:
        """Get cache file path for content hash."""
        return self.cache_dir / f"{content_hash}.npy"
    
    def get(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding from cache.
        
        Args:
            text: Text to get embedding for
            
        Returns:
            Cached embedding or None if not found
        """
        content_hash = self._compute_hash(text)
        cache_path = self._get_cache_path(content_hash)
        
        if cache_path.exists():
            try:
                embedding = np.load(cache_path)
                
                # Update access time
                if content_hash in self.metadata['entries']:
                    self.metadata['entries'][content_hash]['last_access'] = datetime.now().isoformat()
                    self._save_metadata()
                
                logger.debug(f"Cache hit for hash: {content_hash[:8]}...")
                return embedding
            except Exception as e:
                logger.warning(f"Failed to load cached embedding: {e}")
                return None
        
        return None
    
    def put(self, text: str, embedding: np.ndarray):
        """
        Store embedding in cache.
        
        Args:
            text: Text the embedding is for
            embedding: Embedding vector
        """
        content_hash = self._compute_hash(text)
        cache_path = self._get_cache_path(content_hash)
        
        # Save embedding
        np.save(cache_path, embedding)
        
        # Update metadata
        size_mb = cache_path.stat().st_size / (1024 * 1024)
        self.metadata['entries'][content_hash] = {
            'created': datetime.now().isoformat(),
            'last_access': datetime.now().isoformat(),
            'size_mb': size_mb
        }
        self.metadata['total_size_mb'] = sum(
            entry['size_mb'] for entry in self.metadata['entries'].values()
        )
        self._save_metadata()
        
        # Check if we need to evict
        self._evict_if_needed()
        
        logger.debug(f"Cached embedding for hash: {content_hash[:8]}...")
    
    def _evict_if_needed(self):
        """Evict oldest entries if cache size exceeds limit."""
        if self.metadata['total_size_mb'] <= self.max_size_mb:
            return
        
        # Sort by last access time
        sorted_entries = sorted(
            self.metadata['entries'].items(),
            key=lambda x: x[1]['last_access']
        )
        
        # Remove oldest until under limit
        for content_hash, entry in sorted_entries:
            if self.metadata['total_size_mb'] <= self.max_size_mb:
                break
            
            cache_path = self._get_cache_path(content_hash)
            if cache_path.exists():
                cache_path.unlink()
            
            self.metadata['total_size_mb'] -= entry['size_mb']
            del self.metadata['entries'][content_hash]
            
            logger.debug(f"Evicted cache entry: {content_hash[:8]}...")
        
        self._save_metadata()
    
    def clear(self):
        """Clear all cached embeddings."""
        for cache_file in self.cache_dir.glob("*.npy"):
            cache_file.unlink()
        
        self.metadata = {'entries': {}, 'total_size_mb': 0}
        self._save_metadata()
        
        logger.info("Cleared embedding cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'total_entries': len(self.metadata['entries']),
            'total_size_mb': self.metadata['total_size_mb'],
            'max_size_mb': self.max_size_mb,
            'utilization': self.metadata['total_size_mb'] / self.max_size_mb if self.max_size_mb > 0 else 0
        }


class EmbeddingManager:
    """
    Manages embedding generation using nomic-embed-text.
    
    Features:
    - Batched processing for efficiency
    - LRU caching to avoid re-computation
    - Automatic normalization
    - Error handling and retries
    - Performance metrics tracking
    
    Usage:
        config = EmbeddingConfig()
        manager = EmbeddingManager(config)
        
        # Embed single chunk
        result = manager.embed_chunk(chunk)
        
        # Embed batch of chunks
        batch_result = manager.embed_chunks(chunks)
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize embedding manager.
        
        Args:
            config: Embedding configuration (uses defaults if None)
        """
        self.config = config or EmbeddingConfig()
        
        # Initialize Ollama embeddings
        self.embedder = OllamaEmbeddings(
            model=self.config.model_name,
            base_url=self.config.ollama_base_url
        )
        
        # Initialize cache if enabled
        self.cache = None
        if self.config.enable_cache:
            self.cache = EmbeddingCache(
                cache_dir=self.config.cache_dir,
                max_size_mb=self.config.max_cache_size_mb
            )
        
        # Initialize metrics
        self.metrics = MetricsCollector()
        
        logger.info(
            f"Initialized EmbeddingManager",
            extra={
                'model': self.config.model_name,
                'dimension': self.config.embedding_dim,
                'batch_size': self.config.batch_size,
                'cache_enabled': self.config.enable_cache
            }
        )
    
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """
        Normalize embedding to unit length.
        
        Args:
            embedding: Embedding vector
            
        Returns:
            Normalized embedding
        """
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm
    
    def _generate_embedding(self, text: str) -> Tuple[np.ndarray, float]:
        """
        Generate embedding for text using Ollama.
        
        Args:
            text: Text to embed
            
        Returns:
            Tuple of (embedding, processing_time)
        """
        start_time = datetime.now()
        
        # Generate embedding
        embedding_list = self.embedder.embed_query(text)
        embedding = np.array(embedding_list, dtype=np.float32)
        
        # Normalize if configured
        if self.config.normalize_embeddings:
            embedding = self._normalize_embedding(embedding)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return embedding, processing_time
    
    def embed_chunk(self, chunk: Chunk) -> EmbeddingResult:
        """
        Generate embedding for a single chunk.
        
        Args:
            chunk: Chunk to embed
            
        Returns:
            EmbeddingResult with embedding and metadata
        """
        cache_hit = False
        
        # Check cache first
        if self.cache:
            cached_embedding = self.cache.get(chunk.content)
            if cached_embedding is not None:
                return EmbeddingResult(
                    success=True,
                    embedding=cached_embedding,
                    chunk_id=chunk.chunk_id,
                    model_name=self.config.model_name,
                    dimension=len(cached_embedding),
                    normalized=self.config.normalize_embeddings,
                    cache_hit=True,
                    processing_time=0.0
                )
        
        # Generate embedding
        try:
            embedding, processing_time = self._generate_embedding(chunk.content)
            
            # Cache the result
            if self.cache:
                self.cache.put(chunk.content, embedding)
            
            # Track metrics
            self.metrics.record_metric("embedding_generation", processing_time)
            
            return EmbeddingResult(
                success=True,
                embedding=embedding,
                chunk_id=chunk.chunk_id,
                model_name=self.config.model_name,
                dimension=len(embedding),
                normalized=self.config.normalize_embeddings,
                cache_hit=False,
                processing_time=processing_time
            )
        
        except Exception as e:
            logger.error(f"Failed to generate embedding for chunk {chunk.chunk_id}: {e}")
            return EmbeddingResult(
                success=False,
                embedding=None,
                chunk_id=chunk.chunk_id,
                model_name=self.config.model_name,
                dimension=0,
                normalized=self.config.normalize_embeddings,
                cache_hit=False,
                processing_time=0.0,
                error=str(e)
            )
    
    def embed_chunks(self, chunks: List[Chunk]) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple chunks.
        
        Args:
            chunks: List of chunks to embed
            
        Returns:
            BatchEmbeddingResult with all embeddings and statistics
        """
        start_time = datetime.now()
        
        embeddings: List[np.ndarray] = []
        chunk_ids: List[str] = []
        errors: List[str] = []
        cache_hits = 0
        successful = 0
        failed = 0
        
        # Process in batches
        for i in range(0, len(chunks), self.config.batch_size):
            batch = chunks[i:i + self.config.batch_size]
            
            logger.debug(f"Processing batch {i // self.config.batch_size + 1}/{(len(chunks) - 1) // self.config.batch_size + 1}")
            
            for chunk in batch:
                result = self.embed_chunk(chunk)
                
                if result.success:
                    embeddings.append(result.embedding)
                    chunk_ids.append(result.chunk_id)
                    successful += 1
                    
                    if result.cache_hit:
                        cache_hits += 1
                else:
                    failed += 1
                    errors.append(f"{chunk.chunk_id}: {result.error}")
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Track batch metrics
        self.metrics.record_metric("batch_embedding_generation", total_time)
        self.metrics.record_metric("batch_size", len(chunks))
        
        logger.info(
            f"Batch embedding complete: {successful}/{len(chunks)} successful, "
            f"{cache_hits} cache hits, {total_time:.2f}s"
        )
        
        return BatchEmbeddingResult(
            success=failed == 0,
            embeddings=embeddings,
            chunk_ids=chunk_ids,
            total_chunks=len(chunks),
            successful_embeddings=successful,
            failed_embeddings=failed,
            cache_hits=cache_hits,
            total_processing_time=total_time,
            errors=errors
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics or empty dict if cache disabled
        """
        if self.cache:
            return self.cache.get_stats()
        return {}
    
    def clear_cache(self):
        """Clear embedding cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Embedding cache cleared")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics.get_summary()
