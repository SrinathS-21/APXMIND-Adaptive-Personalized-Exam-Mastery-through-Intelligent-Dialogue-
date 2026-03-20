"""
Tier-1 Routing & Retrieval System
==================================

Intelligent document retrieval using Tier-0 classification results.

This is the second layer of the hierarchical routing system that:
1. Selects appropriate vector store collection based on subject/intent
2. Builds dynamic metadata filters for optimized search
3. Performs Stage 1 retrieval with relevance grading
4. Checks if threshold is met for quality
5. Triggers Stage 2 corrective retrieval if needed
6. Aggregates retrieval quality metrics

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .tier0_classifier import ClassificationResult, Intent, Subject
from ..vectorstore.storage import ChromaDBManager
from ..vectorstore.retrieval import HybridRetriever
from ..llm.llm import get_llm

logger = logging.getLogger(__name__)


class RetrievalStage(int, Enum):
    """Retrieval stage indicator."""
    INITIAL = 0  # Stage 1 - initial retrieval
    CORRECTIVE = 1  # Stage 2 - corrective retrieval


@dataclass
class RetrievalMetadata:
    """Metadata about retrieval process."""
    collection_searched: str
    filters_applied: Dict[str, Any]
    stage1_results: int
    stage1_relevant: int
    stage1_threshold_met: bool
    stage2_attempted: bool = False
    stage2_results: int = 0
    stage2_relevant: int = 0
    total_search_time_ms: float = 0.0


@dataclass
class RetrievedDocument:
    """A single retrieved document with relevance grading."""
    id: str
    content: str
    subject: str
    content_type: str
    difficulty: str
    quality_score: float
    relevance_score: float
    is_relevant: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    similarity_score: float = 0.0  # From vector search
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'content': self.content,
            'subject': self.subject,
            'content_type': self.content_type,
            'difficulty': self.difficulty,
            'quality_score': round(self.quality_score, 3),
            'relevance_score': round(self.relevance_score, 3),
            'is_relevant': self.is_relevant,
            'similarity_score': round(self.similarity_score, 3),
            'metadata': self.metadata
        }


@dataclass
class Tier1Result:
    """Result of Tier-1 retrieval."""
    retrieved_documents: List[RetrievedDocument]
    retrieval_stage: RetrievalStage
    retrieval_quality: float
    metadata: RetrievalMetadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'retrieved_documents': [doc.to_dict() for doc in self.retrieved_documents],
            'retrieval_stage': self.retrieval_stage.value,
            'retrieval_quality': round(self.retrieval_quality, 3),
            'metadata': {
                'collection_searched': self.metadata.collection_searched,
                'filters_applied': self.metadata.filters_applied,
                'stage1_results': self.metadata.stage1_results,
                'stage1_relevant': self.metadata.stage1_relevant,
                'stage1_threshold_met': self.metadata.stage1_threshold_met,
                'stage2_attempted': self.metadata.stage2_attempted,
                'stage2_results': self.metadata.stage2_results,
                'stage2_relevant': self.metadata.stage2_relevant,
                'total_search_time_ms': round(self.metadata.total_search_time_ms, 2)
            },
            'timestamp': self.timestamp
        }


class Tier1Retriever:
    """
    Tier-1 Routing & Retrieval System.
    
    Uses Tier-0 classification to intelligently retrieve documents:
    - Routes to correct collection based on subject/intent
    - Applies dynamic filters for optimization
    - Grades relevance using LLM
    - Triggers corrective retrieval if needed
    
    Usage:
        retriever = Tier1Retriever(
            hybrid_retriever=hybrid_retriever,
            chroma_manager=chroma_manager
        )
        
        classification = tier0_classifier.classify_query(query, user_profile)
        
        result = await retriever.retrieve(
            classification=classification,
            query=query
        )
        
        for doc in result.retrieved_documents:
            if doc.is_relevant:
                print(f"Content: {doc.content[:100]}...")
                print(f"Relevance: {doc.relevance_score}")
    """
    
    # Relevance thresholds by intent (minimum relevant docs needed)
    RELEVANCE_THRESHOLDS = {
        Intent.TEACH: 1,    # Need at least 1 good explanation
        Intent.TRAIN: 3,    # Need at least 3 practice questions
        Intent.MENTOR: 2,   # Need at least 2 guidance docs
        Intent.DOUBT: 0,    # Doubt solving is zero-shot (no retrieval needed)
        Intent.GENERAL: 0   # General queries don't use retrieval
    }
    
    # Initial top-K by intent
    INITIAL_TOP_K = {
        Intent.TEACH: 3,
        Intent.TRAIN: 5,
        Intent.MENTOR: 3,
        Intent.DOUBT: 1,
        Intent.GENERAL: 0
    }
    
    # Stage 2 corrective top-K (more documents)
    CORRECTIVE_TOP_K = {
        Intent.TEACH: 6,
        Intent.TRAIN: 10,
        Intent.MENTOR: 6,
        Intent.DOUBT: 1,
        Intent.GENERAL: 0
    }
    
    # Collection mapping patterns
    COLLECTION_MAP = {
        (Intent.TEACH, Subject.PHYSICS): "physics",
        (Intent.TEACH, Subject.CHEMISTRY): "chemistry",
        (Intent.TEACH, Subject.BIOLOGY): "biology",
        (Intent.TRAIN, Subject.PHYSICS): "question_bank",  # All questions together
        (Intent.TRAIN, Subject.CHEMISTRY): "question_bank",
        (Intent.TRAIN, Subject.BIOLOGY): "question_bank",
        (Intent.MENTOR, Subject.PHYSICS): "mentor",  # Mentor is subject-agnostic
        (Intent.MENTOR, Subject.CHEMISTRY): "mentor",
        (Intent.MENTOR, Subject.BIOLOGY): "mentor",
        (Intent.DOUBT, Subject.PHYSICS): "question_bank",  # Problem solving uses examples
        (Intent.DOUBT, Subject.CHEMISTRY): "question_bank",
        (Intent.DOUBT, Subject.BIOLOGY): "question_bank",
    }
    
    def __init__(
        self,
        hybrid_retriever: HybridRetriever,
        chroma_manager: ChromaDBManager,
        llm = None
    ):
        """
        Initialize Tier-1 retriever.
        
        Args:
            hybrid_retriever: HybridRetriever instance for search
            chroma_manager: ChromaDBManager instance for collection access
            llm: Language model for relevance grading (optional, will use get_llm() if None)
        """
        self.hybrid_retriever = hybrid_retriever
        self.chroma_manager = chroma_manager
        self.llm = llm or get_llm()
        
        logger.info("Initialized Tier1Retriever")
    
    async def retrieve(
        self,
        classification: ClassificationResult,
        query: str,
        use_corrective: bool = True
    ) -> Tier1Result:
        """
        Perform intelligent retrieval using Tier-0 classification.
        
        Args:
            classification: Tier-0 classification result
            query: Original query text
            use_corrective: Whether to attempt Stage 2 corrective retrieval
            
        Returns:
            Tier1Result with retrieved documents and metadata
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: Determine collection
            collection = self._determine_collection(classification)
            
            if not collection:
                # No retrieval needed (general/doubt intents)
                return self._empty_result(classification, query)
            
            # Step 2: Build filters
            filters = self._build_filters(classification, stage=1)
            
            # Step 3: Stage 1 retrieval
            top_k = self.INITIAL_TOP_K.get(classification.intent, 3)
            stage1_docs = await self._retrieve_with_filters(
                collection=collection,
                query=query,
                filters=filters,
                top_k=top_k,
                classification=classification
            )
            
            # Step 4: Grade relevance
            graded_stage1 = await self._grade_relevance(
                documents=stage1_docs,
                classification=classification,
                query=query
            )
            
            # Step 5: Check threshold
            relevant_count = sum(1 for doc in graded_stage1 if doc.is_relevant)
            threshold = self.RELEVANCE_THRESHOLDS.get(classification.intent, 1)
            threshold_met = relevant_count >= threshold
            
            # Create metadata
            metadata = RetrievalMetadata(
                collection_searched=collection,
                filters_applied=filters,
                stage1_results=len(stage1_docs),
                stage1_relevant=relevant_count,
                stage1_threshold_met=threshold_met,
                total_search_time_ms=(time.time() - start_time) * 1000
            )
            
            # If threshold met, return Stage 1 results
            if threshold_met:
                quality = self._calculate_quality(graded_stage1)
                
                logger.info(
                    f"Stage 1 success: {relevant_count}/{len(graded_stage1)} relevant "
                    f"(threshold: {threshold}, quality: {quality:.2f})"
                )
                
                return Tier1Result(
                    retrieved_documents=graded_stage1,
                    retrieval_stage=RetrievalStage.INITIAL,
                    retrieval_quality=quality,
                    metadata=metadata
                )
            
            # Step 6: Corrective retrieval (Stage 2)
            if not use_corrective:
                # Return Stage 1 results even if threshold not met
                quality = self._calculate_quality(graded_stage1)
                return Tier1Result(
                    retrieved_documents=graded_stage1,
                    retrieval_stage=RetrievalStage.INITIAL,
                    retrieval_quality=quality,
                    metadata=metadata
                )
            
            logger.info(
                f"Stage 1 insufficient: {relevant_count}/{len(graded_stage1)} relevant "
                f"(need {threshold}). Triggering Stage 2..."
            )
            
            # Relax filters for Stage 2
            relaxed_filters = self._build_filters(classification, stage=2)
            corrective_top_k = self.CORRECTIVE_TOP_K.get(classification.intent, 10)
            
            stage2_docs = await self._retrieve_with_filters(
                collection=collection,
                query=query,
                filters=relaxed_filters,
                top_k=corrective_top_k,
                classification=classification
            )
            
            # Grade Stage 2 documents
            graded_stage2 = await self._grade_relevance(
                documents=stage2_docs,
                classification=classification,
                query=query
            )
            
            stage2_relevant = sum(1 for doc in graded_stage2 if doc.is_relevant)
            
            # Update metadata
            metadata.stage2_attempted = True
            metadata.stage2_results = len(stage2_docs)
            metadata.stage2_relevant = stage2_relevant
            metadata.total_search_time_ms = (time.time() - start_time) * 1000
            
            # Calculate quality and return
            quality = self._calculate_quality(graded_stage2)
            
            logger.info(
                f"Stage 2 complete: {stage2_relevant}/{len(graded_stage2)} relevant "
                f"(quality: {quality:.2f})"
            )
            
            return Tier1Result(
                retrieved_documents=graded_stage2,
                retrieval_stage=RetrievalStage.CORRECTIVE,
                retrieval_quality=quality,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            # Return empty result on failure
            return self._empty_result(classification, query)
    
    def _determine_collection(self, classification: ClassificationResult) -> Optional[str]:
        """
        Determine which collection to search based on classification.
        
        Args:
            classification: Tier-0 classification result
            
        Returns:
            Collection name or None if no retrieval needed
        """
        # General and doubt intents don't use retrieval
        if classification.intent in [Intent.GENERAL]:
            return None
        
        # Map (intent, subject) to collection
        key = (classification.intent, classification.subject)
        collection = self.COLLECTION_MAP.get(key)
        
        if not collection:
            logger.warning(
                f"No collection mapping for {classification.intent}/{classification.subject}"
            )
            return None
        
        return collection
    
    def _build_filters(
        self,
        classification: ClassificationResult,
        stage: int = 1
    ) -> Dict[str, Any]:
        """
        Build metadata filters for optimized search.
        
        Args:
            classification: Tier-0 classification result
            stage: 1 for initial, 2 for corrective (relaxed filters)
            
        Returns:
            ChromaDB filter dictionary
        """
        # Quality threshold (relaxed in Stage 2)
        quality_threshold = 0.85 if stage == 1 else 0.70
        
        # Base filters (always applied)
        filters = {
            "$and": [
                {"quality_score": {"$gte": quality_threshold}}
            ]
        }
        
        # Add subject filter (except for mentor which is cross-subject)
        if classification.intent != Intent.MENTOR:
            filters["$and"].append({
                "subject": {"$eq": classification.subject.value}
            })
        
        # Add content-type filter based on intent (only in Stage 1)
        if stage == 1:
            if classification.intent == Intent.TEACH:
                # Teaching needs explanations
                filters["$and"].append({
                    "content_type": {"$in": ["explanation", "concept", "theory"]}
                })
                # Prefer easier content for teaching
                filters["$and"].append({
                    "difficulty": {"$in": ["easy", "medium"]}
                })
            
            elif classification.intent == Intent.TRAIN:
                # Training needs questions
                filters["$and"].append({
                    "content_type": {"$in": ["question", "problem", "exercise", "mcq"]}
                })
                # Match difficulty to user level
                if classification.difficulty:
                    filters["$and"].append({
                        "difficulty": {"$eq": classification.difficulty.value}
                    })
            
            elif classification.intent == Intent.MENTOR:
                # Mentoring needs guidance
                filters["$and"].append({
                    "content_type": {"$in": ["guidance", "strategy", "advice"]}
                })
        
        return filters
    
    async def _retrieve_with_filters(
        self,
        collection: str,
        query: str,
        filters: Dict[str, Any],
        top_k: int,
        classification: ClassificationResult
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents with filters applied.
        
        Args:
            collection: Collection name
            query: Query text
            filters: Metadata filters
            top_k: Number of documents to retrieve
            classification: Classification result for context
            
        Returns:
            List of retrieved documents
        """
        try:
            # Use hybrid retriever for best results
            result = self.hybrid_retriever.retrieve(
                query=query,
                subject=classification.subject,
                top_k=top_k,
                min_quality=filters["$and"][0]["quality_score"]["$gte"],
                filters=filters
            )
            
            if not result.success:
                logger.warning(f"Retrieval failed: {result.error}")
                return []
            
            # Convert to document format
            documents = []
            for doc_result in result.results:
                documents.append({
                    'id': doc_result.get('id', 'unknown'),
                    'content': doc_result.get('content', ''),
                    'metadata': doc_result.get('metadata', {}),
                    'similarity_score': doc_result.get('rrf_score', 0.0)
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []
    
    async def _grade_relevance(
        self,
        documents: List[Dict[str, Any]],
        classification: ClassificationResult,
        query: str
    ) -> List[RetrievedDocument]:
        """
        Grade each document for relevance using LLM.
        
        Args:
            documents: Retrieved documents
            classification: Classification result
            query: Original query
            
        Returns:
            List of graded documents
        """
        graded_docs = []
        
        for doc in documents:
            try:
                # Extract metadata
                metadata = doc.get('metadata', {})
                content = doc.get('content', '')
                
                # Create grading prompt
                grade_prompt = f"""You are evaluating document relevance for a student query.

User Query: "{query}"
Focus Area: {classification.focus_area or 'general'}
Subject: {classification.subject.value}
Intent: {classification.intent.value}

Document Content (first 300 chars):
{content[:300]}...

Is this document relevant to the user's query?
Consider:
1. Does it address the focus area directly?
2. Is it appropriate for the intent ({classification.intent.value})?
3. Is the content clear and accurate?

Respond ONLY with JSON in this exact format:
{{"is_relevant": true, "relevance_score": 0.95}}

The relevance_score should be 0.0 to 1.0 where:
- 1.0 = perfectly relevant
- 0.7-0.9 = mostly relevant
- 0.5-0.7 = somewhat relevant
- <0.5 = not relevant (set is_relevant to false)
"""
                
                # Call LLM for grading
                response = self.llm.invoke(grade_prompt)
                
                # Parse JSON response
                try:
                    # Extract JSON from response
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    
                    # Try to find JSON in response
                    import re
                    json_match = re.search(r'\{[^}]+\}', response_text)
                    if json_match:
                        grade = json.loads(json_match.group())
                    else:
                        # Fallback: assume relevant if we got content
                        grade = {"is_relevant": True, "relevance_score": 0.7}
                    
                    is_relevant = grade.get('is_relevant', False)
                    relevance_score = float(grade.get('relevance_score', 0.5))
                    
                    # Ensure consistency
                    if relevance_score < 0.7:
                        is_relevant = False
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse LLM grading response: {e}")
                    # Default to somewhat relevant
                    is_relevant = True
                    relevance_score = 0.7
                
                # Create graded document
                graded_doc = RetrievedDocument(
                    id=doc.get('id', 'unknown'),
                    content=content,
                    subject=metadata.get('subject', classification.subject.value),
                    content_type=metadata.get('content_type', 'unknown'),
                    difficulty=metadata.get('difficulty', 'medium'),
                    quality_score=metadata.get('quality_score', 0.0),
                    relevance_score=relevance_score,
                    is_relevant=is_relevant,
                    metadata=metadata,
                    similarity_score=doc.get('similarity_score', 0.0)
                )
                
                graded_docs.append(graded_doc)
                
            except Exception as e:
                logger.error(f"Failed to grade document: {e}")
                # Mark as not relevant on error
                graded_docs.append(RetrievedDocument(
                    id=doc.get('id', 'unknown'),
                    content=doc.get('content', ''),
                    subject=classification.subject.value,
                    content_type='unknown',
                    difficulty='medium',
                    quality_score=0.0,
                    relevance_score=0.0,
                    is_relevant=False,
                    metadata=doc.get('metadata', {}),
                    similarity_score=doc.get('similarity_score', 0.0)
                ))
        
        return graded_docs
    
    def _calculate_quality(self, documents: List[RetrievedDocument]) -> float:
        """
        Calculate overall retrieval quality.
        
        Args:
            documents: Graded documents
            
        Returns:
            Average relevance score of relevant documents
        """
        relevant_docs = [doc for doc in documents if doc.is_relevant]
        
        if not relevant_docs:
            return 0.0
        
        avg_score = sum(doc.relevance_score for doc in relevant_docs) / len(relevant_docs)
        return round(avg_score, 3)
    
    def _empty_result(
        self,
        classification: ClassificationResult,
        query: str
    ) -> Tier1Result:
        """
        Create empty result for intents that don't use retrieval.
        
        Args:
            classification: Classification result
            query: Original query
            
        Returns:
            Empty Tier1Result
        """
        metadata = RetrievalMetadata(
            collection_searched="none",
            filters_applied={},
            stage1_results=0,
            stage1_relevant=0,
            stage1_threshold_met=True,  # No threshold for these intents
            total_search_time_ms=0.0
        )
        
        return Tier1Result(
            retrieved_documents=[],
            retrieval_stage=RetrievalStage.INITIAL,
            retrieval_quality=1.0,  # No retrieval = no quality issue
            metadata=metadata
        )
