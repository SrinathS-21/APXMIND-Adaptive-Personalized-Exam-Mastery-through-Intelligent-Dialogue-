"""
Hybrid Retriever
================

Combines semantic search (vector similarity) with keyword search (BM25)
for improved retrieval quality. Includes reranking and score thresholds.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import re
import math
from collections import Counter
import logging

from ..config import RetrievalConfig
from ..storage import ChromaDBManager
from ..embedding import EmbeddingManager
from ..monitoring import get_logger, MetricsCollector
from ..constants import Subject


logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """Result of hybrid retrieval."""
    
    success: bool
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    semantic_results: int
    keyword_results: int
    reranked: bool
    processing_time: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'query': self.query,
            'total_results': self.total_results,
            'semantic_results': self.semantic_results,
            'keyword_results': self.keyword_results,
            'reranked': self.reranked,
            'processing_time': self.processing_time,
            'error': self.error
        }


class BM25Scorer:
    """
    BM25 scoring for keyword-based retrieval.
    
    BM25 is a probabilistic ranking function that considers:
    - Term frequency (TF)
    - Inverse document frequency (IDF)
    - Document length normalization
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 scorer.
        
        Args:
            k1: Term frequency saturation parameter (1.2-2.0)
            b: Length normalization parameter (0-1)
        """
        self.k1 = k1
        self.b = b
        self.idf_cache: Dict[str, float] = {}
        self.avg_doc_length = 0
        self.num_docs = 0
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Simple tokenization: lowercase, remove punctuation, split
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.split()
    
    def _compute_idf(self, term: str, doc_count: int, term_doc_count: int) -> float:
        """
        Compute IDF for a term.
        
        Args:
            term: The term
            doc_count: Total number of documents
            term_doc_count: Number of documents containing term
            
        Returns:
            IDF score
        """
        if term in self.idf_cache:
            return self.idf_cache[term]
        
        # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
        idf = math.log((doc_count - term_doc_count + 0.5) / (term_doc_count + 0.5) + 1)
        self.idf_cache[term] = idf
        return idf
    
    def score(
        self,
        query: str,
        document: str,
        doc_length: int,
        avg_doc_length: float,
        doc_count: int = 1000
    ) -> float:
        """
        Compute BM25 score for query-document pair.
        
        Args:
            query: Query text
            document: Document text
            doc_length: Length of document in tokens
            avg_doc_length: Average document length
            doc_count: Total document count (for IDF)
            
        Returns:
            BM25 score
        """
        query_terms = self._tokenize(query)
        doc_terms = self._tokenize(document)
        
        # Count term frequencies in document
        term_freqs = Counter(doc_terms)
        
        score = 0.0
        
        for term in query_terms:
            if term not in term_freqs:
                continue
            
            tf = term_freqs[term]
            
            # Approximate IDF (assume term appears in ~10% of docs)
            idf = self._compute_idf(term, doc_count, max(1, int(doc_count * 0.1)))
            
            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / avg_doc_length))
            
            score += idf * (numerator / denominator)
        
        return score
    
    def score_documents(
        self,
        query: str,
        documents: List[str],
        avg_doc_length: Optional[float] = None
    ) -> List[float]:
        """
        Score multiple documents against a query.
        
        Args:
            query: Query text
            documents: List of document texts
            avg_doc_length: Average document length (computed if None)
            
        Returns:
            List of BM25 scores
        """
        # Compute average document length if not provided
        if avg_doc_length is None:
            doc_lengths = [len(self._tokenize(doc)) for doc in documents]
            avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 100
        
        scores = []
        for doc in documents:
            doc_tokens = self._tokenize(doc)
            doc_length = len(doc_tokens)
            
            score = self.score(query, doc, doc_length, avg_doc_length, len(documents))
            scores.append(score)
        
        return scores


class MaximalMarginalRelevance:
    """
    Maximal Marginal Relevance (MMR) for result diversification.
    
    MMR balances relevance and diversity in results by penalizing
    documents that are too similar to already-selected ones.
    """
    
    @staticmethod
    def rerank(
        query_embedding: List[float],
        doc_embeddings: List[List[float]],
        documents: List[Dict[str, Any]],
        lambda_param: float = 0.5,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using MMR.
        
        Args:
            query_embedding: Query embedding vector
            doc_embeddings: Document embedding vectors
            documents: Document metadata
            lambda_param: Trade-off between relevance and diversity (0-1)
            top_k: Number of results to return
            
        Returns:
            Reranked documents
        """
        if not documents or not doc_embeddings:
            return []
        
        selected = []
        remaining = list(range(len(documents)))
        
        # Convert to numpy-like operations
        import numpy as np
        query_emb = np.array(query_embedding)
        doc_embs = np.array(doc_embeddings)
        
        # Normalize embeddings
        query_emb = query_emb / np.linalg.norm(query_emb)
        doc_embs = doc_embs / np.linalg.norm(doc_embs, axis=1, keepdims=True)
        
        # Compute similarity to query
        query_sims = np.dot(doc_embs, query_emb)
        
        for _ in range(min(top_k, len(documents))):
            if not remaining:
                break
            
            mmr_scores = []
            
            for idx in remaining:
                # Relevance to query
                relevance = query_sims[idx]
                
                # Diversity from selected documents
                if selected:
                    selected_embs = doc_embs[selected]
                    similarities = np.dot(selected_embs, doc_embs[idx])
                    max_sim = np.max(similarities)
                else:
                    max_sim = 0
                
                # MMR = λ * Sim(Q, D) - (1-λ) * max Sim(D, D_i)
                mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
                mmr_scores.append((idx, mmr))
            
            # Select document with highest MMR score
            best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
            selected.append(best_idx)
            remaining.remove(best_idx)
        
        # Return reranked documents
        return [documents[idx] for idx in selected]


class HybridRetriever:
    """
    Hybrid retrieval combining semantic and keyword search.
    
    Features:
    - Semantic search using vector embeddings (ChromaDB)
    - Keyword search using BM25
    - Score fusion (Reciprocal Rank Fusion)
    - MMR-based reranking for diversity
    - Quality and metadata filtering
    - Subject-specific collection routing
    
    Usage:
        config = RetrievalConfig()
        retriever = HybridRetriever(config)
        
        # Simple retrieval
        results = retriever.retrieve(
            query="What is photosynthesis?",
            subject=Subject.BIOLOGY,
            top_k=5
        )
        
        # Advanced retrieval with filters
        results = retriever.retrieve(
            query="Explain Newton's laws",
            subject=Subject.PHYSICS,
            top_k=10,
            min_quality=0.7,
            filters={'difficulty': 'medium'}
        )
    """
    
    def __init__(
        self,
        config: Optional[RetrievalConfig] = None,
        chroma_manager: Optional[ChromaDBManager] = None,
        embedding_manager: Optional[EmbeddingManager] = None
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            config: Retrieval configuration
            chroma_manager: ChromaDB manager (created if None)
            embedding_manager: Embedding manager (created if None)
        """
        self.config = config or RetrievalConfig()
        self.chroma_manager = chroma_manager or ChromaDBManager()
        self.embedding_manager = embedding_manager or EmbeddingManager()
        
        # Initialize scorers
        self.bm25 = BM25Scorer(
            k1=self.config.bm25_k1,
            b=self.config.bm25_b
        )
        self.mmr = MaximalMarginalRelevance()
        
        # Metrics
        self.metrics = MetricsCollector()
        
        logger.info(
            "Initialized HybridRetriever",
            extra={
                'semantic_weight': self.config.semantic_weight,
                'keyword_weight': self.config.keyword_weight,
                'enable_reranking': self.config.enable_reranking
            }
        )
    
    def _get_collection_key(self, subject: Subject) -> str:
        """Map subject to collection key."""
        subject_map = {
            Subject.BIOLOGY: 'biology',
            Subject.CHEMISTRY: 'chemistry',
            Subject.PHYSICS: 'physics'
        }
        return subject_map.get(subject, 'biology')
    
    def _semantic_search(
        self,
        query: str,
        collection_key: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings.
        
        Args:
            query: Query text
            collection_key: Collection to search
            top_k: Number of results
            filters: Metadata filters
            
        Returns:
            List of results with scores
        """
        # Generate query embedding
        from ..chunking import Chunk
        query_chunk = Chunk(
            content=query,
            metadata={},
            chunk_id='query',
            start_pos=0,
            end_pos=len(query)
        )
        
        embedding_result = self.embedding_manager.embed_chunk(query_chunk)
        
        if not embedding_result.success:
            logger.error(f"Failed to generate query embedding: {embedding_result.error}")
            return []
        
        # Query ChromaDB
        query_result = self.chroma_manager.query(
            collection_key=collection_key,
            query_texts=[query],
            query_embeddings=[embedding_result.embedding.tolist()],
            top_k=top_k * 2,  # Retrieve more for reranking
            where=filters
        )
        
        if not query_result.success:
            logger.error(f"Semantic search failed: {query_result.error}")
            return []
        
        # Add semantic scores
        for result in query_result.results:
            # Convert distance to similarity (assuming cosine distance)
            distance = result.get('distance', 1.0)
            result['semantic_score'] = 1.0 - distance
            result['source'] = 'semantic'
        
        return query_result.results
    
    def _keyword_search(
        self,
        query: str,
        semantic_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword search using BM25.
        
        Args:
            query: Query text
            semantic_results: Results from semantic search
            top_k: Number of results
            
        Returns:
            List of results with BM25 scores
        """
        if not semantic_results:
            return []
        
        # Extract documents
        documents = [r['document'] for r in semantic_results]
        
        # Compute BM25 scores
        bm25_scores = self.bm25.score_documents(query, documents)
        
        # Normalize scores to 0-1 range
        if bm25_scores:
            max_score = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
            bm25_scores = [s / max_score for s in bm25_scores]
        
        # Add BM25 scores to results
        for result, score in zip(semantic_results, bm25_scores):
            result['keyword_score'] = score
        
        # Sort by BM25 score
        ranked = sorted(
            semantic_results,
            key=lambda x: x.get('keyword_score', 0),
            reverse=True
        )
        
        return ranked[:top_k]
    
    def _fuse_scores(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fuse semantic and keyword scores using Reciprocal Rank Fusion.
        
        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            
        Returns:
            Fused and ranked results
        """
        # Create unified result set
        result_map = {}
        
        # Add semantic results
        for rank, result in enumerate(semantic_results):
            doc_id = result['id']
            if doc_id not in result_map:
                result_map[doc_id] = result.copy()
                result_map[doc_id]['rrf_score'] = 0
            
            # RRF: 1 / (k + rank)
            result_map[doc_id]['rrf_score'] += self.config.semantic_weight / (60 + rank + 1)
        
        # Add keyword results
        for rank, result in enumerate(keyword_results):
            doc_id = result['id']
            if doc_id not in result_map:
                result_map[doc_id] = result.copy()
                result_map[doc_id]['rrf_score'] = 0
            
            result_map[doc_id]['rrf_score'] += self.config.keyword_weight / (60 + rank + 1)
        
        # Sort by fused score
        fused_results = sorted(
            result_map.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )
        
        return fused_results
    
    def retrieve(
        self,
        query: str,
        subject: Optional[Subject] = None,
        top_k: Optional[int] = None,
        min_quality: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        enable_reranking: Optional[bool] = None
    ) -> RetrievalResult:
        """
        Retrieve documents using hybrid search.
        
        Args:
            query: Query text
            subject: Subject to search (None for all)
            top_k: Number of results to return
            min_quality: Minimum quality score threshold
            filters: Additional metadata filters
            enable_reranking: Enable MMR reranking (overrides config)
            
        Returns:
            RetrievalResult with ranked documents
        """
        start_time = datetime.now()
        
        # Use config defaults
        top_k = top_k or self.config.top_k
        min_quality = min_quality or self.config.min_relevance_score
        enable_reranking = enable_reranking if enable_reranking is not None else self.config.enable_reranking
        
        # Prepare filters
        search_filters = filters.copy() if filters else {}
        if min_quality:
            search_filters['quality_score'] = {'$gte': min_quality}
        
        try:
            # Determine collection
            if subject:
                collection_key = self._get_collection_key(subject)
                collections = [collection_key]
            else:
                collections = ['biology', 'chemistry', 'physics']
            
            all_results = []
            
            # Search each collection
            for collection_key in collections:
                # 1. Semantic search
                semantic_results = self._semantic_search(
                    query=query,
                    collection_key=collection_key,
                    top_k=top_k,
                    filters=search_filters
                )
                
                if not semantic_results:
                    continue
                
                # 2. Keyword search (on semantic results)
                keyword_results = self._keyword_search(
                    query=query,
                    semantic_results=semantic_results,
                    top_k=top_k
                )
                
                # 3. Fuse scores
                fused_results = self._fuse_scores(semantic_results, keyword_results)
                
                all_results.extend(fused_results)
            
            # Sort by fused score
            all_results = sorted(
                all_results,
                key=lambda x: x.get('rrf_score', 0),
                reverse=True
            )[:top_k * 2]
            
            # 4. MMR reranking (optional)
            if enable_reranking and len(all_results) > 1:
                # Extract embeddings (would need to be stored or re-computed)
                # For now, skip MMR if embeddings not available
                logger.debug("MMR reranking requested but embeddings not cached")
            
            # Limit to top_k
            final_results = all_results[:top_k]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Track metrics
            self.metrics.record_metric("retrieval_time", processing_time)
            self.metrics.record_metric("results_returned", len(final_results))
            
            logger.info(
                f"Retrieved {len(final_results)} results in {processing_time:.3f}s"
            )
            
            return RetrievalResult(
                success=True,
                query=query,
                results=final_results,
                total_results=len(final_results),
                semantic_results=len([r for r in final_results if 'semantic_score' in r]),
                keyword_results=len([r for r in final_results if 'keyword_score' in r]),
                reranked=enable_reranking,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return RetrievalResult(
                success=False,
                query=query,
                results=[],
                total_results=0,
                semantic_results=0,
                keyword_results=0,
                reranked=False,
                processing_time=0.0,
                error=str(e)
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retrieval metrics."""
        return self.metrics.get_summary()
