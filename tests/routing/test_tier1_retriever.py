"""
Unit Tests for Tier-1 Retriever
================================

Tests for intelligent document retrieval system.

Author: APXMIND Development Team
Created: 2025-11-01
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.apxmind.routing.tier1_retriever import (
    Tier1Retriever,
    RetrievalStage,
    RetrievalMetadata,
    RetrievedDocument,
    Tier1Result
)
from src.apxmind.routing.tier0_classifier import (
    ClassificationResult,
    Intent,
    Subject,
    Difficulty,
    UserProfile,
    LearningLevel
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_hybrid_retriever():
    """Mock HybridRetriever for testing."""
    retriever = Mock()
    retriever.retrieve = AsyncMock()
    return retriever


@pytest.fixture
def mock_chroma_manager():
    """Mock ChromaDBManager for testing."""
    manager = Mock()
    return manager


@pytest.fixture
def mock_llm():
    """Mock LLM for relevance grading."""
    llm = Mock()
    llm.invoke = Mock()
    return llm


@pytest.fixture
def tier1_retriever(mock_hybrid_retriever, mock_chroma_manager, mock_llm):
    """Create Tier1Retriever instance for testing."""
    return Tier1Retriever(
        hybrid_retriever=mock_hybrid_retriever,
        chroma_manager=mock_chroma_manager,
        llm=mock_llm
    )


@pytest.fixture
def user_profile():
    """Sample user profile."""
    return UserProfile(
        user_id="test_user",
        learning_level=LearningLevel.INTERMEDIATE,
        preferred_language="english",
        recent_performance=0.75
    )


@pytest.fixture
def physics_teach_classification():
    """Sample classification: Physics teaching."""
    return ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.9,
        intent=Intent.TEACH,
        intent_confidence=0.85,
        difficulty=Difficulty.MEDIUM,
        focus_area="newtons_second_law",
        language="english",
        overall_confidence=0.88
    )


@pytest.fixture
def chemistry_train_classification():
    """Sample classification: Chemistry training."""
    return ClassificationResult(
        subject=Subject.CHEMISTRY,
        subject_confidence=0.88,
        intent=Intent.TRAIN,
        intent_confidence=0.9,
        difficulty=Difficulty.HARD,
        focus_area="organic_reactions",
        language="english",
        overall_confidence=0.89
    )


@pytest.fixture
def mentor_classification():
    """Sample classification: Mentoring."""
    return ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.7,
        intent=Intent.MENTOR,
        intent_confidence=0.85,
        difficulty=Difficulty.MEDIUM,
        focus_area="exam_preparation",
        language="english",
        overall_confidence=0.78
    )


# ============================================================================
# Test: Collection Selection
# ============================================================================

def test_collection_selection_physics_teach(tier1_retriever, physics_teach_classification):
    """Test collection selection for physics teaching."""
    collection = tier1_retriever._determine_collection(physics_teach_classification)
    assert collection == "physics"


def test_collection_selection_chemistry_train(tier1_retriever, chemistry_train_classification):
    """Test collection selection for chemistry training."""
    collection = tier1_retriever._determine_collection(chemistry_train_classification)
    assert collection == "question_bank"


def test_collection_selection_mentor(tier1_retriever, mentor_classification):
    """Test collection selection for mentoring."""
    collection = tier1_retriever._determine_collection(mentor_classification)
    assert collection == "mentor"


def test_collection_selection_general_intent(tier1_retriever):
    """Test that general intent returns None (no retrieval)."""
    classification = ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.6,
        intent=Intent.GENERAL,
        intent_confidence=0.8,
        difficulty=None,
        focus_area=None,
        language="english",
        overall_confidence=0.7
    )
    
    collection = tier1_retriever._determine_collection(classification)
    assert collection is None


# ============================================================================
# Test: Filter Building
# ============================================================================

def test_filter_building_stage1_teach(tier1_retriever, physics_teach_classification):
    """Test filter building for Stage 1 teaching."""
    filters = tier1_retriever._build_filters(physics_teach_classification, stage=1)
    
    # Check quality threshold
    assert filters["$and"][0] == {"quality_score": {"$gte": 0.85}}
    
    # Check subject filter
    assert {"subject": {"$eq": "physics"}} in filters["$and"]
    
    # Check content type for teaching
    assert {"content_type": {"$in": ["explanation", "concept", "theory"]}} in filters["$and"]
    
    # Check difficulty filter
    assert {"difficulty": {"$in": ["easy", "medium"]}} in filters["$and"]


def test_filter_building_stage1_train(tier1_retriever, chemistry_train_classification):
    """Test filter building for Stage 1 training."""
    filters = tier1_retriever._build_filters(chemistry_train_classification, stage=1)
    
    # Check quality threshold
    assert filters["$and"][0] == {"quality_score": {"$gte": 0.85}}
    
    # Check subject filter
    assert {"subject": {"$eq": "chemistry"}} in filters["$and"]
    
    # Check content type for training
    assert {"content_type": {"$in": ["question", "problem", "exercise", "mcq"]}} in filters["$and"]
    
    # Check difficulty matches classification
    assert {"difficulty": {"$eq": "hard"}} in filters["$and"]


def test_filter_building_stage2_relaxed(tier1_retriever, physics_teach_classification):
    """Test that Stage 2 filters are more relaxed."""
    stage1_filters = tier1_retriever._build_filters(physics_teach_classification, stage=1)
    stage2_filters = tier1_retriever._build_filters(physics_teach_classification, stage=2)
    
    # Stage 2 should have lower quality threshold
    stage1_quality = stage1_filters["$and"][0]["quality_score"]["$gte"]
    stage2_quality = stage2_filters["$and"][0]["quality_score"]["$gte"]
    
    assert stage2_quality < stage1_quality
    assert stage2_quality == 0.70
    assert stage1_quality == 0.85


def test_filter_building_mentor_no_subject_filter(tier1_retriever, mentor_classification):
    """Test that mentor intent doesn't filter by subject."""
    filters = tier1_retriever._build_filters(mentor_classification, stage=1)
    
    # Should NOT have subject filter (mentor is cross-subject)
    subject_filters = [f for f in filters["$and"] if "subject" in f]
    assert len(subject_filters) == 0


# ============================================================================
# Test: Stage 1 Retrieval
# ============================================================================

@pytest.mark.asyncio
async def test_stage1_retrieval_success(
    tier1_retriever,
    mock_hybrid_retriever,
    mock_llm,
    physics_teach_classification
):
    """Test successful Stage 1 retrieval."""
    # Mock retrieval results
    mock_results = Mock()
    mock_results.success = True
    mock_results.results = [
        {
            'id': 'doc1',
            'content': 'Newton\'s Second Law states that F = ma where...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'easy',
                'quality_score': 0.94
            },
            'rrf_score': 0.95
        },
        {
            'id': 'doc2',
            'content': 'The relationship between force, mass, and acceleration...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'medium',
                'quality_score': 0.90
            },
            'rrf_score': 0.92
        },
        {
            'id': 'doc3',
            'content': 'Applications of Newton\'s Second Law include...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'medium',
                'quality_score': 0.88
            },
            'rrf_score': 0.88
        }
    ]
    
    mock_hybrid_retriever.retrieve.return_value = mock_results
    
    # Mock LLM grading (all relevant)
    mock_response = Mock()
    mock_response.content = '{"is_relevant": true, "relevance_score": 0.92}'
    mock_llm.invoke.return_value = mock_response
    
    # Perform retrieval
    result = await tier1_retriever.retrieve(
        classification=physics_teach_classification,
        query="Explain Newton's Second Law",
        use_corrective=True
    )
    
    # Verify results
    assert result.retrieval_stage == RetrievalStage.INITIAL
    assert len(result.retrieved_documents) == 3
    assert all(doc.is_relevant for doc in result.retrieved_documents)
    assert result.retrieval_quality > 0.85
    assert result.metadata.stage1_threshold_met is True
    assert result.metadata.stage2_attempted is False


@pytest.mark.asyncio
async def test_stage1_insufficient_triggers_stage2(
    tier1_retriever,
    mock_hybrid_retriever,
    mock_llm,
    chemistry_train_classification
):
    """Test that insufficient Stage 1 results trigger Stage 2."""
    # Stage 1: Return only 2 docs (need 3 for training)
    stage1_results = Mock()
    stage1_results.success = True
    stage1_results.results = [
        {
            'id': 'doc1',
            'content': 'Question about organic reactions...',
            'metadata': {
                'subject': 'chemistry',
                'content_type': 'question',
                'difficulty': 'hard',
                'quality_score': 0.90
            },
            'rrf_score': 0.92
        },
        {
            'id': 'doc2',
            'content': 'Another question about organic reactions...',
            'metadata': {
                'subject': 'chemistry',
                'content_type': 'question',
                'difficulty': 'hard',
                'quality_score': 0.88
            },
            'rrf_score': 0.89
        }
    ]
    
    # Stage 2: Return more docs
    stage2_results = Mock()
    stage2_results.success = True
    stage2_results.results = stage1_results.results + [
        {
            'id': 'doc3',
            'content': 'Third question about organic reactions...',
            'metadata': {
                'subject': 'chemistry',
                'content_type': 'question',
                'difficulty': 'hard',
                'quality_score': 0.85
            },
            'rrf_score': 0.85
        },
        {
            'id': 'doc4',
            'content': 'Fourth question about organic reactions...',
            'metadata': {
                'subject': 'chemistry',
                'content_type': 'question',
                'difficulty': 'hard',
                'quality_score': 0.82
            },
            'rrf_score': 0.83
        }
    ]
    
    # Mock retrieval to return different results on each call
    mock_hybrid_retriever.retrieve.side_effect = [stage1_results, stage2_results]
    
    # Mock LLM grading (all relevant)
    mock_response = Mock()
    mock_response.content = '{"is_relevant": true, "relevance_score": 0.88}'
    mock_llm.invoke.return_value = mock_response
    
    # Perform retrieval
    result = await tier1_retriever.retrieve(
        classification=chemistry_train_classification,
        query="Give me practice questions on organic reactions",
        use_corrective=True
    )
    
    # Verify Stage 2 was triggered
    assert result.retrieval_stage == RetrievalStage.CORRECTIVE
    assert result.metadata.stage2_attempted is True
    assert result.metadata.stage1_threshold_met is False
    assert len(result.retrieved_documents) >= 3
    assert mock_hybrid_retriever.retrieve.call_count == 2


# ============================================================================
# Test: Relevance Grading
# ============================================================================

@pytest.mark.asyncio
async def test_relevance_grading_with_llm(tier1_retriever, mock_llm, physics_teach_classification):
    """Test relevance grading using LLM."""
    documents = [
        {
            'id': 'doc1',
            'content': 'Newton\'s Second Law F=ma...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'easy',
                'quality_score': 0.9
            },
            'similarity_score': 0.95
        },
        {
            'id': 'doc2',
            'content': 'Thermodynamics first law...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'medium',
                'quality_score': 0.85
            },
            'similarity_score': 0.75
        }
    ]
    
    # Mock LLM responses
    mock_llm.invoke.side_effect = [
        Mock(content='{"is_relevant": true, "relevance_score": 0.95}'),
        Mock(content='{"is_relevant": false, "relevance_score": 0.45}')
    ]
    
    graded_docs = await tier1_retriever._grade_relevance(
        documents=documents,
        classification=physics_teach_classification,
        query="Explain Newton's Second Law"
    )
    
    # First doc should be relevant
    assert graded_docs[0].is_relevant is True
    assert graded_docs[0].relevance_score == 0.95
    
    # Second doc should not be relevant
    assert graded_docs[1].is_relevant is False
    assert graded_docs[1].relevance_score == 0.45


@pytest.mark.asyncio
async def test_relevance_grading_handles_invalid_json(tier1_retriever, mock_llm, physics_teach_classification):
    """Test that invalid JSON responses are handled gracefully."""
    documents = [
        {
            'id': 'doc1',
            'content': 'Some content...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'easy',
                'quality_score': 0.9
            },
            'similarity_score': 0.9
        }
    ]
    
    # Mock invalid JSON response
    mock_llm.invoke.return_value = Mock(content='This is not valid JSON')
    
    graded_docs = await tier1_retriever._grade_relevance(
        documents=documents,
        classification=physics_teach_classification,
        query="Some query"
    )
    
    # Should fallback to default values
    assert len(graded_docs) == 1
    assert graded_docs[0].is_relevant is True  # Default fallback
    assert graded_docs[0].relevance_score == 0.7  # Default fallback


# ============================================================================
# Test: Quality Calculation
# ============================================================================

def test_quality_calculation_with_relevant_docs(tier1_retriever):
    """Test quality calculation with relevant documents."""
    documents = [
        RetrievedDocument(
            id="doc1",
            content="...",
            subject="physics",
            content_type="explanation",
            difficulty="easy",
            quality_score=0.9,
            relevance_score=0.95,
            is_relevant=True
        ),
        RetrievedDocument(
            id="doc2",
            content="...",
            subject="physics",
            content_type="explanation",
            difficulty="medium",
            quality_score=0.85,
            relevance_score=0.88,
            is_relevant=True
        ),
        RetrievedDocument(
            id="doc3",
            content="...",
            subject="physics",
            content_type="explanation",
            difficulty="medium",
            quality_score=0.8,
            relevance_score=0.82,
            is_relevant=True
        )
    ]
    
    quality = tier1_retriever._calculate_quality(documents)
    
    # Should be average of relevance scores
    expected = (0.95 + 0.88 + 0.82) / 3
    assert abs(quality - expected) < 0.01


def test_quality_calculation_with_no_relevant_docs(tier1_retriever):
    """Test quality calculation when no documents are relevant."""
    documents = [
        RetrievedDocument(
            id="doc1",
            content="...",
            subject="physics",
            content_type="explanation",
            difficulty="easy",
            quality_score=0.9,
            relevance_score=0.45,
            is_relevant=False
        )
    ]
    
    quality = tier1_retriever._calculate_quality(documents)
    assert quality == 0.0


# ============================================================================
# Test: Empty Results for General/Doubt Intents
# ============================================================================

@pytest.mark.asyncio
async def test_general_intent_returns_empty(tier1_retriever):
    """Test that GENERAL intent returns empty result without retrieval."""
    classification = ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.6,
        intent=Intent.GENERAL,
        intent_confidence=0.9,
        difficulty=None,
        focus_area=None,
        language="english",
        overall_confidence=0.75
    )
    
    result = await tier1_retriever.retrieve(
        classification=classification,
        query="Hello, how are you?",
        use_corrective=True
    )
    
    assert len(result.retrieved_documents) == 0
    assert result.retrieval_quality == 1.0
    assert result.metadata.collection_searched == "none"
    assert result.metadata.stage1_threshold_met is True


# ============================================================================
# Test: Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_retrieval_pipeline_teach(
    tier1_retriever,
    mock_hybrid_retriever,
    mock_llm,
    physics_teach_classification
):
    """Test full retrieval pipeline for teaching."""
    # Setup mock retrieval
    mock_results = Mock()
    mock_results.success = True
    mock_results.results = [
        {
            'id': 'physics_ch5_p1',
            'content': 'Newton\'s Second Law: F = ma. Force equals mass times acceleration...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'easy',
                'quality_score': 0.94,
                'source': 'NCERT Physics Class 11'
            },
            'rrf_score': 0.96
        },
        {
            'id': 'physics_ch5_p2',
            'content': 'Applications of Newton\'s Second Law in everyday life...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'medium',
                'quality_score': 0.90,
                'source': 'NCERT Physics Class 11'
            },
            'rrf_score': 0.92
        },
        {
            'id': 'physics_ch5_p3',
            'content': 'Examples of F=ma: pushing a cart, car acceleration...',
            'metadata': {
                'subject': 'physics',
                'content_type': 'explanation',
                'difficulty': 'easy',
                'quality_score': 0.88,
                'source': 'NCERT Physics Class 11'
            },
            'rrf_score': 0.89
        }
    ]
    
    mock_hybrid_retriever.retrieve.return_value = mock_results
    
    # Setup mock LLM grading
    mock_llm.invoke.side_effect = [
        Mock(content='{"is_relevant": true, "relevance_score": 0.94}'),
        Mock(content='{"is_relevant": true, "relevance_score": 0.89}'),
        Mock(content='{"is_relevant": true, "relevance_score": 0.87}')
    ]
    
    # Execute retrieval
    result = await tier1_retriever.retrieve(
        classification=physics_teach_classification,
        query="I'm stuck on Newton's Second Law. Can you explain how F=ma works?",
        use_corrective=True
    )
    
    # Verify results
    assert result.retrieval_stage == RetrievalStage.INITIAL
    assert len(result.retrieved_documents) == 3
    assert all(doc.is_relevant for doc in result.retrieved_documents)
    assert result.retrieval_quality >= 0.85
    assert result.metadata.stage1_threshold_met is True
    assert result.metadata.stage2_attempted is False
    assert result.metadata.collection_searched == "physics"
    
    # Verify document details
    doc1 = result.retrieved_documents[0]
    assert doc1.id == 'physics_ch5_p1'
    assert doc1.subject == 'physics'
    assert doc1.content_type == 'explanation'
    assert doc1.quality_score == 0.94
    assert doc1.relevance_score == 0.94
    assert doc1.is_relevant is True


@pytest.mark.asyncio
async def test_full_retrieval_pipeline_train_with_corrective(
    tier1_retriever,
    mock_hybrid_retriever,
    mock_llm,
    chemistry_train_classification
):
    """Test full retrieval pipeline for training with corrective retrieval."""
    # Stage 1: Only 2 relevant docs (need 3)
    stage1_results = Mock()
    stage1_results.success = True
    stage1_results.results = [
        {
            'id': 'chem_q1',
            'content': 'Question 1: Explain SN1 mechanism...',
            'metadata': {'subject': 'chemistry', 'content_type': 'question', 'difficulty': 'hard', 'quality_score': 0.92},
            'rrf_score': 0.93
        },
        {
            'id': 'chem_q2',
            'content': 'Question 2: Draw mechanism for reaction...',
            'metadata': {'subject': 'chemistry', 'content_type': 'question', 'difficulty': 'hard', 'quality_score': 0.89},
            'rrf_score': 0.90
        }
    ]
    
    # Stage 2: 5 docs total
    stage2_results = Mock()
    stage2_results.success = True
    stage2_results.results = stage1_results.results + [
        {
            'id': 'chem_q3',
            'content': 'Question 3: Compare SN1 vs SN2...',
            'metadata': {'subject': 'chemistry', 'content_type': 'question', 'difficulty': 'hard', 'quality_score': 0.85},
            'rrf_score': 0.87
        },
        {
            'id': 'chem_q4',
            'content': 'Question 4: Predict product...',
            'metadata': {'subject': 'chemistry', 'content_type': 'question', 'difficulty': 'hard', 'quality_score': 0.83},
            'rrf_score': 0.84
        },
        {
            'id': 'chem_q5',
            'content': 'Question 5: Rate determining step...',
            'metadata': {'subject': 'chemistry', 'content_type': 'question', 'difficulty': 'hard', 'quality_score': 0.80},
            'rrf_score': 0.82
        }
    ]
    
    mock_hybrid_retriever.retrieve.side_effect = [stage1_results, stage2_results]
    
    # Mock LLM: Stage 1 - 2 relevant, Stage 2 - 4 relevant
    mock_llm.invoke.side_effect = [
        # Stage 1 grading
        Mock(content='{"is_relevant": true, "relevance_score": 0.91}'),
        Mock(content='{"is_relevant": true, "relevance_score": 0.88}'),
        # Stage 2 grading
        Mock(content='{"is_relevant": true, "relevance_score": 0.91}'),
        Mock(content='{"is_relevant": true, "relevance_score": 0.88}'),
        Mock(content='{"is_relevant": true, "relevance_score": 0.84}'),
        Mock(content='{"is_relevant": true, "relevance_score": 0.82}'),
        Mock(content='{"is_relevant": false, "relevance_score": 0.65}')
    ]
    
    # Execute retrieval
    result = await tier1_retriever.retrieve(
        classification=chemistry_train_classification,
        query="Give me practice questions on organic reactions",
        use_corrective=True
    )
    
    # Verify corrective retrieval was triggered
    assert result.retrieval_stage == RetrievalStage.CORRECTIVE
    assert result.metadata.stage2_attempted is True
    assert result.metadata.stage1_threshold_met is False
    assert result.metadata.stage1_relevant == 2
    assert result.metadata.stage2_relevant == 4
    assert len(result.retrieved_documents) == 5
    assert sum(1 for doc in result.retrieved_documents if doc.is_relevant) == 4


# ============================================================================
# Test: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_retrieval_handles_hybrid_retriever_failure(
    tier1_retriever,
    mock_hybrid_retriever,
    physics_teach_classification
):
    """Test that retrieval handles hybrid retriever failures gracefully."""
    # Mock retrieval failure
    mock_results = Mock()
    mock_results.success = False
    mock_results.error = "Connection timeout"
    mock_results.results = []
    
    mock_hybrid_retriever.retrieve.return_value = mock_results
    
    # Execute retrieval
    result = await tier1_retriever.retrieve(
        classification=physics_teach_classification,
        query="Explain Newton's Second Law",
        use_corrective=True
    )
    
    # Should return empty result
    assert len(result.retrieved_documents) == 0
    assert result.retrieval_quality == 0.0


@pytest.mark.asyncio
async def test_retrieval_handles_llm_grading_failure(
    tier1_retriever,
    mock_hybrid_retriever,
    mock_llm,
    physics_teach_classification
):
    """Test that retrieval handles LLM grading failures gracefully."""
    # Mock retrieval success
    mock_results = Mock()
    mock_results.success = True
    mock_results.results = [
        {
            'id': 'doc1',
            'content': 'Some content...',
            'metadata': {'subject': 'physics', 'content_type': 'explanation', 'difficulty': 'easy', 'quality_score': 0.9},
            'rrf_score': 0.9
        }
    ]
    
    mock_hybrid_retriever.retrieve.return_value = mock_results
    
    # Mock LLM failure
    mock_llm.invoke.side_effect = Exception("LLM service unavailable")
    
    # Execute retrieval
    result = await tier1_retriever.retrieve(
        classification=physics_teach_classification,
        query="Explain Newton's Second Law",
        use_corrective=True
    )
    
    # Should still return documents but marked as not relevant
    assert len(result.retrieved_documents) == 1
    assert result.retrieved_documents[0].is_relevant is False
    assert result.retrieved_documents[0].relevance_score == 0.0


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
