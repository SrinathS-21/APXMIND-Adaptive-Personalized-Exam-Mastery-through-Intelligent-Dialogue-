"""
Unit Tests for Tier-2 Orchestrator and Agents
=============================================

Tests for agent selection, orchestration, and execution.

Author: APXMIND Development Team
Created: 2025-11-01
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.apxmind.routing.tier2_orchestrator import (
    Tier2Orchestrator,
    AgentType,
    AgentContext,
    AgentResponse,
    RetrievalMethod,
    BaseAgent
)
from src.apxmind.routing.agents import (
    TeacherAgent,
    TrainerAgent,
    DoubtSolverAgent,
    MentorAgent,
    GeneralAgent
)
from src.apxmind.routing.tier0_classifier import (
    ClassificationResult,
    Intent,
    Subject,
    Difficulty,
    LearningLevel
)
from src.apxmind.routing.tier1_retriever import (
    Tier1Result,
    RetrievedDocument,
    RetrievalStage,
    RetrievalMetadata
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = Mock()
    llm.invoke = Mock()
    return llm


@pytest.fixture
def mock_agents(mock_llm):
    """Create mock agent instances."""
    return {
        AgentType.TEACHER: TeacherAgent(llm=mock_llm),
        AgentType.TRAINER: TrainerAgent(llm=mock_llm),
        AgentType.DOUBT_SOLVER: DoubtSolverAgent(llm=mock_llm),
        AgentType.MENTOR: MentorAgent(llm=mock_llm),
        AgentType.GENERAL: GeneralAgent(llm=mock_llm)
    }


@pytest.fixture
def tier2_orchestrator(mock_agents):
    """Create Tier2Orchestrator instance."""
    return Tier2Orchestrator(agents=mock_agents)


@pytest.fixture
def physics_teach_classification():
    """Sample classification for physics teaching."""
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
    """Sample classification for chemistry training."""
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
def general_classification():
    """Sample classification for general query."""
    return ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.6,
        intent=Intent.GENERAL,
        intent_confidence=0.9,
        difficulty=None,
        focus_area=None,
        language="english",
        overall_confidence=0.75
    )


@pytest.fixture
def high_quality_tier1_result():
    """High-quality Tier-1 result with 3 relevant docs."""
    return Tier1Result(
        retrieved_documents=[
            RetrievedDocument(
                id="doc1",
                content="Newton's Second Law states that F = ma...",
                subject="physics",
                content_type="explanation",
                difficulty="easy",
                quality_score=0.94,
                relevance_score=0.94,
                is_relevant=True
            ),
            RetrievedDocument(
                id="doc2",
                content="Applications of F=ma in real life...",
                subject="physics",
                content_type="explanation",
                difficulty="medium",
                quality_score=0.90,
                relevance_score=0.89,
                is_relevant=True
            ),
            RetrievedDocument(
                id="doc3",
                content="Examples of Newton's Second Law...",
                subject="physics",
                content_type="explanation",
                difficulty="easy",
                quality_score=0.88,
                relevance_score=0.87,
                is_relevant=True
            )
        ],
        retrieval_stage=RetrievalStage.INITIAL,
        retrieval_quality=0.90,
        metadata=RetrievalMetadata(
            collection_searched="physics",
            filters_applied={},
            stage1_results=3,
            stage1_relevant=3,
            stage1_threshold_met=True
        )
    )


@pytest.fixture
def low_quality_tier1_result():
    """Low-quality Tier-1 result with insufficient docs."""
    return Tier1Result(
        retrieved_documents=[
            RetrievedDocument(
                id="doc1",
                content="Some chemistry content...",
                subject="chemistry",
                content_type="question",
                difficulty="hard",
                quality_score=0.85,
                relevance_score=0.75,
                is_relevant=True
            )
        ],
        retrieval_stage=RetrievalStage.INITIAL,
        retrieval_quality=0.75,
        metadata=RetrievalMetadata(
            collection_searched="question_bank",
            filters_applied={},
            stage1_results=1,
            stage1_relevant=1,
            stage1_threshold_met=False
        )
    )


@pytest.fixture
def empty_tier1_result():
    """Empty Tier-1 result (for general queries)."""
    return Tier1Result(
        retrieved_documents=[],
        retrieval_stage=RetrievalStage.INITIAL,
        retrieval_quality=1.0,
        metadata=RetrievalMetadata(
            collection_searched="none",
            filters_applied={},
            stage1_results=0,
            stage1_relevant=0,
            stage1_threshold_met=True
        )
    )


@pytest.fixture
def user_profile():
    """Sample user profile."""
    return {
        'user_id': 'student123',
        'learning_level': 'intermediate',
        'recent_accuracy': 0.75,
        'conversation_history': [],
        'preferences': {}
    }


# ============================================================================
# Test: Agent Selection
# ============================================================================

def test_agent_selection_teach(tier2_orchestrator, physics_teach_classification):
    """Test agent selection for TEACH intent."""
    agent_type = tier2_orchestrator._select_agent(physics_teach_classification)
    assert agent_type == AgentType.TEACHER


def test_agent_selection_train(tier2_orchestrator, chemistry_train_classification):
    """Test agent selection for TRAIN intent."""
    agent_type = tier2_orchestrator._select_agent(chemistry_train_classification)
    assert agent_type == AgentType.TRAINER


def test_agent_selection_general(tier2_orchestrator, general_classification):
    """Test agent selection for GENERAL intent."""
    agent_type = tier2_orchestrator._select_agent(general_classification)
    assert agent_type == AgentType.GENERAL


def test_agent_selection_doubt(tier2_orchestrator):
    """Test agent selection for DOUBT intent."""
    classification = ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.85,
        intent=Intent.DOUBT,
        intent_confidence=0.9,
        difficulty=Difficulty.MEDIUM,
        focus_area="problem_solving",
        language="english",
        overall_confidence=0.87
    )
    
    agent_type = tier2_orchestrator._select_agent(classification)
    assert agent_type == AgentType.DOUBT_SOLVER


def test_agent_selection_mentor(tier2_orchestrator):
    """Test agent selection for MENTOR intent."""
    classification = ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.7,
        intent=Intent.MENTOR,
        intent_confidence=0.85,
        difficulty=Difficulty.MEDIUM,
        focus_area="exam_preparation",
        language="english",
        overall_confidence=0.78
    )
    
    agent_type = tier2_orchestrator._select_agent(classification)
    assert agent_type == AgentType.MENTOR


# ============================================================================
# Test: Context Building
# ============================================================================

def test_context_building(
    tier2_orchestrator,
    physics_teach_classification,
    high_quality_tier1_result,
    user_profile
):
    """Test context building with all components."""
    context = tier2_orchestrator._build_context(
        classification=physics_teach_classification,
        retrieved_docs=high_quality_tier1_result,
        query="Explain Newton's Second Law",
        user_profile=user_profile
    )
    
    assert context.query == "Explain Newton's Second Law"
    assert context.classification == physics_teach_classification
    assert context.user_id == "student123"
    assert context.learning_level == "intermediate"
    assert context.language == "english"
    assert len(context.retrieved_documents) == 3
    assert context.retrieval_quality == 0.90
    assert context.retrieval_stage == 0
    assert context.user_accuracy == 0.75


# ============================================================================
# Test: Context Validation
# ============================================================================

def test_context_validation_teacher_sufficient(tier2_orchestrator):
    """Test validation for teacher with sufficient docs (≥1)."""
    context = AgentContext(
        query="Test",
        classification=Mock(),
        user_id="test",
        learning_level="intermediate",
        language="english",
        retrieved_documents=[
            RetrievedDocument(
                id="doc1",
                content="...",
                subject="physics",
                content_type="explanation",
                difficulty="easy",
                quality_score=0.9,
                relevance_score=0.9,
                is_relevant=True
            )
        ],
        retrieval_quality=0.9,
        retrieval_stage=0
    )
    
    is_valid, msg = tier2_orchestrator._validate_context(AgentType.TEACHER, context)
    
    assert is_valid is True
    assert "1/1" in msg


def test_context_validation_trainer_insufficient(tier2_orchestrator):
    """Test validation for trainer with insufficient docs (<3)."""
    context = AgentContext(
        query="Test",
        classification=Mock(),
        user_id="test",
        learning_level="intermediate",
        language="english",
        retrieved_documents=[
            RetrievedDocument(
                id="doc1",
                content="...",
                subject="chemistry",
                content_type="question",
                difficulty="hard",
                quality_score=0.85,
                relevance_score=0.8,
                is_relevant=True
            )
        ],
        retrieval_quality=0.8,
        retrieval_stage=0
    )
    
    is_valid, msg = tier2_orchestrator._validate_context(AgentType.TRAINER, context)
    
    assert is_valid is False
    assert "1/3" in msg


def test_context_validation_doubt_solver_no_requirement(tier2_orchestrator):
    """Test validation for doubt solver (no docs required)."""
    context = AgentContext(
        query="Test",
        classification=Mock(),
        user_id="test",
        learning_level="intermediate",
        language="english",
        retrieved_documents=[],
        retrieval_quality=0.0,
        retrieval_stage=0
    )
    
    is_valid, msg = tier2_orchestrator._validate_context(AgentType.DOUBT_SOLVER, context)
    
    assert is_valid is True  # No docs required


# ============================================================================
# Test: Confidence Calculation
# ============================================================================

def test_confidence_crag_stage1_high_quality(tier2_orchestrator):
    """Test confidence for C-RAG Stage 1 with high quality."""
    confidence = tier2_orchestrator._calculate_confidence(
        retrieval_method=RetrievalMethod.CRAG,
        retrieval_stage=0,
        retrieval_quality=0.90
    )
    
    assert confidence == 0.94


def test_confidence_crag_stage2_good_quality(tier2_orchestrator):
    """Test confidence for C-RAG Stage 2 with good quality."""
    confidence = tier2_orchestrator._calculate_confidence(
        retrieval_method=RetrievalMethod.CRAG,
        retrieval_stage=1,
        retrieval_quality=0.75
    )
    
    assert confidence == 0.87


def test_confidence_zero_shot(tier2_orchestrator):
    """Test confidence for zero-shot mode."""
    confidence = tier2_orchestrator._calculate_confidence(
        retrieval_method=RetrievalMethod.ZERO_SHOT,
        retrieval_stage=None,
        retrieval_quality=0.0
    )
    
    assert confidence == 0.75


def test_confidence_fallback(tier2_orchestrator):
    """Test confidence for fallback mode."""
    confidence = tier2_orchestrator._calculate_confidence(
        retrieval_method=RetrievalMethod.FALLBACK,
        retrieval_stage=None,
        retrieval_quality=0.0
    )
    
    assert confidence == 0.70


# ============================================================================
# Test: Full Orchestration
# ============================================================================

@pytest.mark.asyncio
async def test_full_orchestration_teacher(
    tier2_orchestrator,
    physics_teach_classification,
    high_quality_tier1_result,
    user_profile,
    mock_llm
):
    """Test full orchestration for teacher agent."""
    # Mock LLM response
    mock_response = Mock()
    mock_response.content = "Newton's Second Law states that F = ma. This fundamental law..."
    mock_llm.invoke.return_value = mock_response
    
    # Execute
    response = await tier2_orchestrator.execute_agent(
        classification=physics_teach_classification,
        retrieved_docs=high_quality_tier1_result,
        query="Explain Newton's Second Law",
        user_profile=user_profile
    )
    
    # Verify response structure
    assert response.success is True
    assert 'text' in response.content
    assert response.metadata['agent_used'] == 'teacher'
    assert response.metadata['confidence_score'] == 0.94  # High quality C-RAG
    assert response.metadata['retrieval_method'] == 'C-RAG'
    assert response.metadata['retrieval_stage'] == 0
    assert len(response.metadata['retrieval_sources']) > 0


@pytest.mark.asyncio
async def test_full_orchestration_general(
    tier2_orchestrator,
    general_classification,
    empty_tier1_result,
    user_profile,
    mock_llm
):
    """Test full orchestration for general agent."""
    # Mock LLM response
    mock_response = Mock()
    mock_response.content = "Hello! I'm here to help you with your NEET preparation."
    mock_llm.invoke.return_value = mock_response
    
    # Execute
    response = await tier2_orchestrator.execute_agent(
        classification=general_classification,
        retrieved_docs=empty_tier1_result,
        query="Hello, how are you?",
        user_profile=user_profile
    )
    
    # Verify response
    assert response.success is True
    assert 'text' in response.content
    assert response.metadata['agent_used'] == 'general'
    assert response.metadata['confidence_score'] == 0.94  # No retrieval needed, threshold met


@pytest.mark.asyncio
async def test_orchestration_with_fallback(
    tier2_orchestrator,
    chemistry_train_classification,
    low_quality_tier1_result,
    user_profile,
    mock_llm
):
    """Test orchestration triggering fallback mode."""
    # Mock LLM response
    mock_response = Mock()
    mock_response.content = '{"question": "Test question", "options": {"A": "Opt A", "B": "Opt B", "C": "Opt C", "D": "Opt D"}, "correct_answer": "A", "explanation": "Test explanation"}'
    mock_llm.invoke.return_value = mock_response
    
    # Execute (should trigger fallback due to insufficient docs)
    response = await tier2_orchestrator.execute_agent(
        classification=chemistry_train_classification,
        retrieved_docs=low_quality_tier1_result,
        query="Give me practice questions",
        user_profile=user_profile
    )
    
    # Verify fallback was used
    assert response.success is True
    assert response.metadata['agent_used'] == 'trainer'
    assert response.metadata['retrieval_method'] == 'zero-shot'  # Fallback mode


# ============================================================================
# Test: Agent Implementations
# ============================================================================

@pytest.mark.asyncio
async def test_teacher_agent_execution(mock_llm):
    """Test TeacherAgent execution."""
    teacher = TeacherAgent(llm=mock_llm)
    
    # Mock LLM response
    mock_response = Mock()
    mock_response.content = "Detailed explanation of the concept..."
    mock_llm.invoke.return_value = mock_response
    
    # Create context
    context = AgentContext(
        query="Explain this concept",
        classification=Mock(subject=Subject.PHYSICS, focus_area="test", difficulty=Difficulty.MEDIUM),
        user_id="test",
        learning_level="intermediate",
        language="english",
        retrieved_documents=[],
        retrieval_quality=0.0,
        retrieval_stage=0
    )
    
    # Execute
    result = await teacher.execute(context)
    
    # Verify
    assert 'text' in result
    assert 'learning_objectives' in result
    assert 'related_topics' in result


@pytest.mark.asyncio
async def test_trainer_agent_execution(mock_llm):
    """Test TrainerAgent execution."""
    trainer = TrainerAgent(llm=mock_llm)
    
    # Mock LLM response with valid JSON
    mock_response = Mock()
    mock_response.content = '''
    {
        "question": "What is F = ma?",
        "options": {
            "A": "Force equals mass times acceleration",
            "B": "Force equals mass plus acceleration",
            "C": "Force equals mass divided by acceleration",
            "D": "Force equals mass minus acceleration"
        },
        "correct_answer": "A",
        "explanation": "Newton's Second Law states F = ma"
    }
    '''
    mock_llm.invoke.return_value = mock_response
    
    # Create context
    context = AgentContext(
        query="Generate a question",
        classification=Mock(subject=Subject.PHYSICS, focus_area="test", difficulty=Difficulty.MEDIUM),
        user_id="test",
        learning_level="intermediate",
        language="english",
        retrieved_documents=[],
        retrieval_quality=0.0,
        retrieval_stage=0
    )
    
    # Execute
    result = await trainer.execute(context)
    
    # Verify
    assert 'text' in result
    assert 'options' in result
    assert 'correct_answer' in result
    assert 'explanation' in result


@pytest.mark.asyncio
async def test_doubt_solver_agent_execution(mock_llm):
    """Test DoubtSolverAgent execution."""
    doubt_solver = DoubtSolverAgent(llm=mock_llm)
    
    # Mock LLM response
    mock_response = Mock()
    mock_response.content = "Step 1: Identify the forces...\nStep 2: Apply Newton's law..."
    mock_llm.invoke.return_value = mock_response
    
    # Create context
    context = AgentContext(
        query="How do I solve this problem?",
        classification=Mock(subject=Subject.PHYSICS, focus_area="test", difficulty=Difficulty.MEDIUM),
        user_id="test",
        learning_level="intermediate",
        language="english",
        retrieved_documents=[],
        retrieval_quality=0.0,
        retrieval_stage=0
    )
    
    # Execute
    result = await doubt_solver.execute(context)
    
    # Verify
    assert 'text' in result
    assert 'Step' in result['text']  # Should have step-by-step solution


# ============================================================================
# Test: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_orchestration_handles_missing_agent(user_profile):
    """Test that orchestration handles missing agent gracefully."""
    # Create orchestrator with missing agent
    orchestrator = Tier2Orchestrator(agents={
        # Teacher agent missing
        AgentType.TRAINER: Mock(),
        AgentType.GENERAL: Mock()
    })
    
    classification = ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.9,
        intent=Intent.TEACH,  # Will select teacher (missing)
        intent_confidence=0.85,
        difficulty=Difficulty.MEDIUM,
        focus_area="test",
        language="english",
        overall_confidence=0.88
    )
    
    tier1_result = Tier1Result(
        retrieved_documents=[],
        retrieval_stage=RetrievalStage.INITIAL,
        retrieval_quality=1.0,
        metadata=Mock()
    )
    
    # Execute
    response = await orchestrator.execute_agent(
        classification=classification,
        retrieved_docs=tier1_result,
        query="Test",
        user_profile=user_profile
    )
    
    # Should return error response
    assert response.success is False
    assert 'error' in response.metadata


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
