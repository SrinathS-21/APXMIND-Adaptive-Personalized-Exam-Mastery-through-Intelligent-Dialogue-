"""
ChromaDB Manager
================

Manages ChromaDB vector store operations for APXMIND.
Handles 5 subject-specific collections with quality filtering.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from ..config import ChromaDBConfig
from ..chunking.base_chunker import Chunk
from ..constants import Subject, ContentType
from ..monitoring import get_logger, MetricsCollector


logger = get_logger(__name__)


@dataclass
class AddResult:
    """Result of adding documents to collection."""
    
    success: bool
    collection_name: str
    documents_added: int
    total_documents: int
    errors: List[str]
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'collection_name': self.collection_name,
            'documents_added': self.documents_added,
            'total_documents': self.total_documents,
            'error_count': len(self.errors),
            'processing_time': self.processing_time
        }


@dataclass
class QueryResult:
    """Result of querying a collection."""
    
    success: bool
    collection_name: str
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    processing_time: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'collection_name': self.collection_name,
            'query': query,
            'total_results': self.total_results,
            'processing_time': self.processing_time,
            'error': self.error
        }


class ChromaDBManager:
    """
    Manages ChromaDB vector store operations.
    
    Features:
    - 5 subject-specific collections (biology, chemistry, physics, mentor, question_bank)
    - Quality-based filtering
    - Metadata-rich storage
    - Efficient retrieval with filters
    - Collection management (create, delete, reset)
    
    Usage:
        config = ChromaDBConfig()
        manager = ChromaDBManager(config)
        
        # Add chunks to collection
        result = manager.add_chunks('biology', chunks, embeddings)
        
        # Query collection
        results = manager.query('biology', query_text, top_k=5)
    """
    
    def __init__(self, config: Optional[ChromaDBConfig] = None):
        """
        Initialize ChromaDB manager.
        
        Args:
            config: ChromaDB configuration (uses defaults if None)
        """
        self.config = config or ChromaDBConfig()
        self.metrics = MetricsCollector()
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.config.base_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize collections dictionary
        self.collections: Dict[str, Any] = {}
        
        logger.info(
            f"Initialized ChromaDBManager",
            extra={
                'base_path': str(self.config.base_path),
                'collections': list(self.config.collections.keys()),
                'distance_metric': self.config.distance_metric
            }
        )
    
    def _get_or_create_collection(self, collection_key: str) -> Any:
        """
        Get or create a collection.
        
        Args:
            collection_key: Collection key (biology, chemistry, etc.)
            
        Returns:
            ChromaDB collection object
        """
        if collection_key in self.collections:
            return self.collections[collection_key]
        
        collection_name = self.config.collections.get(collection_key)
        if not collection_name:
            raise ValueError(f"Unknown collection key: {collection_key}")
        
        try:
            # Get or create collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": self.config.distance_metric,
                    "created_at": datetime.now().isoformat(),
                    "subject": collection_key
                }
            )
            
            self.collections[collection_key] = collection
            logger.info(f"Loaded collection: {collection_name}")
            
            return collection
            
        except Exception as e:
            logger.error(f"Failed to get/create collection {collection_name}: {e}")
            raise
    
    def add_chunks(
        self,
        collection_key: str,
        chunks: List[Chunk],
        embeddings: List[List[float]],
        batch_size: int = 100
    ) -> AddResult:
        """
        Add chunks with embeddings to collection.
        
        Args:
            collection_key: Collection to add to (biology, chemistry, etc.)
            chunks: List of chunks to add
            embeddings: List of embedding vectors (same length as chunks)
            batch_size: Batch size for adding documents
            
        Returns:
            AddResult with success status and statistics
        """
        start_time = datetime.now()
        
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have same length")
        
        collection = self._get_or_create_collection(collection_key)
        
        documents_added = 0
        errors = []
        
        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            
            try:
                # Prepare batch data
                ids = [chunk.chunk_id for chunk in batch_chunks]
                documents = [chunk.content for chunk in batch_chunks]
                metadatas = [self._prepare_metadata(chunk) for chunk in batch_chunks]
                
                # Add to collection
                collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=batch_embeddings,
                    metadatas=metadatas
                )
                
                documents_added += len(batch_chunks)
                
                logger.debug(
                    f"Added batch {i // batch_size + 1}: {len(batch_chunks)} documents"
                )
                
            except Exception as e:
                error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Track metrics
        self.metrics.record_metric("documents_added", documents_added)
        self.metrics.record_metric("add_processing_time", processing_time)
        
        logger.info(
            f"Added {documents_added}/{len(chunks)} documents to {collection_key} "
            f"in {processing_time:.2f}s"
        )
        
        return AddResult(
            success=len(errors) == 0,
            collection_name=collection_key,
            documents_added=documents_added,
            total_documents=len(chunks),
            errors=errors,
            processing_time=processing_time
        )
    
    def _prepare_metadata(self, chunk: Chunk) -> Dict[str, Any]:
        """
        Prepare metadata for storage.
        
        Args:
            chunk: Chunk to extract metadata from
            
        Returns:
            Metadata dictionary compatible with ChromaDB
        """
        # ChromaDB only supports: str, int, float, bool
        # Convert complex types to JSON strings
        metadata = {}
        
        for key, value in chunk.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                if value and isinstance(value[0], str):
                    metadata[key] = ",".join(str(v) for v in value)
            elif value is not None:
                # Convert other types to strings
                metadata[key] = str(value)
        
        # Add chunk-specific metadata
        metadata['chunk_id'] = chunk.chunk_id
        metadata['quality_score'] = chunk.quality_score
        metadata['created_at'] = chunk.created_at.isoformat()
        
        return metadata
    
    def query(
        self,
        collection_key: str,
        query_texts: List[str],
        query_embeddings: Optional[List[List[float]]] = None,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        Query a collection.
        
        Args:
            collection_key: Collection to query
            query_texts: Query text(s)
            query_embeddings: Pre-computed query embeddings (optional)
            top_k: Number of results to return
            where: Metadata filters
            where_document: Document content filters
            
        Returns:
            QueryResult with retrieved documents
        """
        start_time = datetime.now()
        
        try:
            collection = self._get_or_create_collection(collection_key)
            
            # Query collection
            results = collection.query(
                query_texts=query_texts if not query_embeddings else None,
                query_embeddings=query_embeddings,
                n_results=top_k,
                where=where,
                where_document=where_document
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Format results
            formatted_results = []
            if results and results['ids']:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else None
                    })
            
            # Track metrics
            self.metrics.record_metric("query_processing_time", processing_time)
            self.metrics.record_metric("results_returned", len(formatted_results))
            
            logger.debug(
                f"Query returned {len(formatted_results)} results in {processing_time:.3f}s"
            )
            
            return QueryResult(
                success=True,
                collection_name=collection_key,
                query=query_texts[0] if query_texts else "",
                results=formatted_results,
                total_results=len(formatted_results),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return QueryResult(
                success=False,
                collection_name=collection_key,
                query=query_texts[0] if query_texts else "",
                results=[],
                total_results=0,
                processing_time=0.0,
                error=str(e)
            )
    
    def get_collection_stats(self, collection_key: str) -> Dict[str, Any]:
        """
        Get statistics about a collection.
        
        Args:
            collection_key: Collection to get stats for
            
        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self._get_or_create_collection(collection_key)
            count = collection.count()
            
            return {
                'name': collection_key,
                'document_count': count,
                'metadata': collection.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {collection_key}: {e}")
            return {
                'name': collection_key,
                'document_count': 0,
                'error': str(e)
            }
    
    def delete_collection(self, collection_key: str) -> bool:
        """
        Delete a collection.
        
        Args:
            collection_key: Collection to delete
            
        Returns:
            True if successful
        """
        try:
            collection_name = self.config.collections.get(collection_key)
            if not collection_name:
                raise ValueError(f"Unknown collection key: {collection_key}")
            
            self.client.delete_collection(name=collection_name)
            
            # Remove from cache
            if collection_key in self.collections:
                del self.collections[collection_key]
            
            logger.info(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_key}: {e}")
            return False
    
    def reset_collection(self, collection_key: str) -> bool:
        """
        Reset a collection (delete and recreate).
        
        Args:
            collection_key: Collection to reset
            
        Returns:
            True if successful
        """
        try:
            # Delete existing
            self.delete_collection(collection_key)
            
            # Recreate
            self._get_or_create_collection(collection_key)
            
            logger.info(f"Reset collection: {collection_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset collection {collection_key}: {e}")
            return False
    
    def get_all_collection_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all collections.
        
        Returns:
            Dictionary mapping collection keys to their stats
        """
        stats = {}
        for collection_key in self.config.collections.keys():
            stats[collection_key] = self.get_collection_stats(collection_key)
        return stats
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics.get_summary()
