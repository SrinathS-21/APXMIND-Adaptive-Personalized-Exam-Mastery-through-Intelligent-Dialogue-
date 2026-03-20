"""Simple test runner for Tier-1 retriever tests."""

import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Add src to path
sys.path.insert(0, 'd:\\APXMIND-main\\APXMIND-main')

from src.apxmind.routing.tier1_retriever import Tier1Retriever, RetrievalStage
from src.apxmind.routing.tier0_classifier import (
    ClassificationResult,
    Intent,
    Subject,
    Difficulty
)

def test_collection_selection():
    """Test collection selection logic."""
    print("\n=== Testing Collection Selection ===")
    
    # Create mocks
    mock_hybrid = Mock()
    mock_chroma = Mock()
    mock_llm = Mock()
    
    retriever = Tier1Retriever(
        hybrid_retriever=mock_hybrid,
        chroma_manager=mock_chroma,
        llm=mock_llm
    )
    
    # Test 1: Physics + Teach → physics collection
    classification = ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.9,
        intent=Intent.TEACH,
        intent_confidence=0.85,
        difficulty=Difficulty.MEDIUM,
        focus_area="newtons_second_law",
        language="english",
        overall_confidence=0.88
    )
    
    collection = retriever._determine_collection(classification)
    print(f"✓ Physics + Teach → '{collection}' (expected: 'physics')")
    assert collection == "physics", f"Expected 'physics', got '{collection}'"
    
    # Test 2: Chemistry + Train → question_bank
    classification.subject = Subject.CHEMISTRY
    classification.intent = Intent.TRAIN
    
    collection = retriever._determine_collection(classification)
    print(f"✓ Chemistry + Train → '{collection}' (expected: 'question_bank')")
    assert collection == "question_bank", f"Expected 'question_bank', got '{collection}'"
    
    # Test 3: Mentor → mentor collection
    classification.intent = Intent.MENTOR
    
    collection = retriever._determine_collection(classification)
    print(f"✓ Mentor → '{collection}' (expected: 'mentor')")
    assert collection == "mentor", f"Expected 'mentor', got '{collection}'"
    
    # Test 4: General → None (no retrieval)
    classification.intent = Intent.GENERAL
    
    collection = retriever._determine_collection(classification)
    print(f"✓ General → '{collection}' (expected: None)")
    assert collection is None, f"Expected None, got '{collection}'"
    
    print("\n✅ All collection selection tests passed!")


def test_filter_building():
    """Test filter building logic."""
    print("\n=== Testing Filter Building ===")
    
    # Create mocks
    mock_hybrid = Mock()
    mock_chroma = Mock()
    mock_llm = Mock()
    
    retriever = Tier1Retriever(
        hybrid_retriever=mock_hybrid,
        chroma_manager=mock_chroma,
        llm=mock_llm
    )
    
    # Test 1: Stage 1 filters (strict)
    classification = ClassificationResult(
        subject=Subject.PHYSICS,
        subject_confidence=0.9,
        intent=Intent.TEACH,
        intent_confidence=0.85,
        difficulty=Difficulty.MEDIUM,
        focus_area="newtons_second_law",
        language="english",
        overall_confidence=0.88
    )
    
    filters_stage1 = retriever._build_filters(classification, stage=1)
    
    # Check quality threshold
    quality_filter = filters_stage1["$and"][0]
    print(f"✓ Stage 1 quality threshold: {quality_filter}")
    assert quality_filter == {"quality_score": {"$gte": 0.85}}
    
    # Test 2: Stage 2 filters (relaxed)
    filters_stage2 = retriever._build_filters(classification, stage=2)
    
    quality_filter_s2 = filters_stage2["$and"][0]
    print(f"✓ Stage 2 quality threshold: {quality_filter_s2}")
    assert quality_filter_s2 == {"quality_score": {"$gte": 0.70}}
    
    # Test 3: Content type for teaching
    has_content_type = any("content_type" in f for f in filters_stage1["$and"])
    print(f"✓ Teaching intent has content_type filter: {has_content_type}")
    assert has_content_type
    
    print("\n✅ All filter building tests passed!")


def test_quality_calculation():
    """Test quality calculation."""
    print("\n=== Testing Quality Calculation ===")
    
    from src.apxmind.routing.tier1_retriever import RetrievedDocument
    
    # Create mocks
    mock_hybrid = Mock()
    mock_chroma = Mock()
    mock_llm = Mock()
    
    retriever = Tier1Retriever(
        hybrid_retriever=mock_hybrid,
        chroma_manager=mock_chroma,
        llm=mock_llm
    )
    
    # Test 1: Calculate quality with relevant docs
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
    
    quality = retriever._calculate_quality(documents)
    expected = (0.95 + 0.88 + 0.82) / 3
    
    print(f"✓ Quality calculation: {quality:.3f} (expected: {expected:.3f})")
    assert abs(quality - expected) < 0.01
    
    # Test 2: No relevant docs
    documents[0].is_relevant = False
    documents[1].is_relevant = False
    documents[2].is_relevant = False
    
    quality = retriever._calculate_quality(documents)
    print(f"✓ No relevant docs quality: {quality:.3f} (expected: 0.0)")
    assert quality == 0.0
    
    print("\n✅ All quality calculation tests passed!")


async def test_empty_result_for_general():
    """Test that general intent returns empty result."""
    print("\n=== Testing Empty Result for General Intent ===")
    
    # Create mocks
    mock_hybrid = Mock()
    mock_chroma = Mock()
    mock_llm = Mock()
    
    retriever = Tier1Retriever(
        hybrid_retriever=mock_hybrid,
        chroma_manager=mock_chroma,
        llm=mock_llm
    )
    
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
    
    result = await retriever.retrieve(
        classification=classification,
        query="Hello, how are you?",
        use_corrective=True
    )
    
    print(f"✓ Retrieved documents: {len(result.retrieved_documents)} (expected: 0)")
    assert len(result.retrieved_documents) == 0
    
    print(f"✓ Retrieval quality: {result.retrieval_quality} (expected: 1.0)")
    assert result.retrieval_quality == 1.0
    
    print(f"✓ Collection searched: '{result.metadata.collection_searched}' (expected: 'none')")
    assert result.metadata.collection_searched == "none"
    
    print("\n✅ General intent test passed!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TIER-1 RETRIEVER TEST SUITE")
    print("="*60)
    
    try:
        # Run synchronous tests
        test_collection_selection()
        test_filter_building()
        test_quality_calculation()
        
        # Run async tests
        asyncio.run(test_empty_result_for_general())
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
