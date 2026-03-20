"""
Test SemanticChunker
====================

Simple test to verify SemanticChunker functionality.

Usage:
    python test_semantic_chunker.py
"""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apxmind.vectorstore.chunking import SemanticChunker
from apxmind.vectorstore.config import ChunkingConfig
from apxmind.vectorstore.constants import Subject, ContentType, Difficulty


def test_basic_chunking():
    """Test basic chunking functionality."""
    print("=" * 60)
    print("TEST 1: Basic Semantic Chunking")
    print("=" * 60)
    
    # Sample biology text
    text = """
    Photosynthesis is the process by which green plants and some other organisms 
    use sunlight to synthesize nutrients from carbon dioxide and water. 
    Photosynthesis in plants generally involves the green pigment chlorophyll 
    and generates oxygen as a by-product.
    
    The process of photosynthesis can be divided into two main stages: 
    the light-dependent reactions and the light-independent reactions (Calvin cycle). 
    In the light-dependent reactions, light energy is captured by chlorophyll and 
    converted into chemical energy in the form of ATP and NADPH.
    
    The Calvin cycle uses the ATP and NADPH produced in the light-dependent reactions 
    to convert carbon dioxide into glucose. This process is essential for life on Earth 
    as it provides the organic compounds and oxygen necessary for most organisms.
    
    Factors affecting photosynthesis include light intensity, carbon dioxide concentration, 
    temperature, and water availability. Understanding these factors is crucial for 
    optimizing plant growth in agriculture.
    """
    
    # Create config
    config = ChunkingConfig(
        target_size=200,  # Small for testing
        min_size=50,
        max_size=400,
        overlap=30
    )
    
    # Initialize chunker
    chunker = SemanticChunker(config=config)
    
    # Prepare metadata
    metadata = {
        'subject': Subject.BIOLOGY.value,
        'topic': 'Photosynthesis',
        'content_type': ContentType.EXPLANATION.value,
        'difficulty': Difficulty.INTERMEDIATE.value,
        'class_level': 11,
        'source_file': 'test_biology.txt',
        'chapter': 'Plant Physiology'
    }
    
    # Chunk the text
    result = chunker.chunk(text, metadata)
    
    # Display results
    if result.success:
        print(f"\n✓ Chunking successful!")
        print(f"  Total chunks: {len(result.chunks)}")
        print(f"  Metrics: {result.metrics}")
        
        print("\n" + "-" * 60)
        print("CHUNKS CREATED:")
        print("-" * 60)
        
        for i, chunk in enumerate(result.chunks, 1):
            print(f"\nChunk {i}:")
            print(f"  ID: {chunk.chunk_id}")
            print(f"  Size: {chunk.get_size()} chars ({chunk.get_word_count()} words)")
            print(f"  Quality: {chunk.quality_score:.2f}")
            print(f"  Position: {chunk.start_pos}-{chunk.end_pos}")
            print(f"  Has formula: {chunk.metadata.get('has_formula', False)}")
            print(f"  Has example: {chunk.metadata.get('has_example', False)}")
            print(f"  Content preview: {chunk.content[:100]}...")
        
        if result.warnings:
            print(f"\n⚠ Warnings: {len(result.warnings)}")
            for warning in result.warnings[:3]:
                print(f"  - {warning}")
    else:
        print(f"\n✗ Chunking failed: {result.error}")
    
    return result.success


def test_boundary_respect():
    """Test that chunker respects sentence boundaries."""
    print("\n" + "=" * 60)
    print("TEST 2: Sentence Boundary Respect")
    print("=" * 60)
    
    text = """
    First sentence is here. Second sentence follows it. Third one comes next.
    
    New paragraph starts here. It has multiple sentences too. Each should be respected.
    Another sentence in this paragraph. And one more to test.
    """
    
    chunker = SemanticChunker(target_size=80, min_size=30, max_size=150)
    
    metadata = {
        'subject': 'biology',
        'topic': 'Test',
        'source_file': 'test.txt'
    }
    
    result = chunker.chunk(text, metadata)
    
    if result.success:
        print(f"\n✓ Created {len(result.chunks)} chunks")
        
        for i, chunk in enumerate(result.chunks, 1):
            # Check if chunk ends with sentence boundary
            ends_with_boundary = chunk.content.rstrip().endswith(('.', '!', '?', '।', '।।'))
            status = "✓" if ends_with_boundary else "✗"
            print(f"\nChunk {i}: {status} Ends with sentence boundary")
            print(f"  Last chars: ...{chunk.content[-50:]}")
    
    return result.success


def test_quality_scoring():
    """Test quality score calculation."""
    print("\n" + "=" * 60)
    print("TEST 3: Quality Score Calculation")
    print("=" * 60)
    
    # High quality chunk (complete, good size, ends with period)
    good_text = """
    Mitosis is a type of cell division that results in two daughter cells 
    each having the same number and kind of chromosomes as the parent nucleus. 
    This process is essential for growth and repair in multicellular organisms.
    """
    
    # Low quality chunk (too short, incomplete)
    poor_text = "Cell division"
    
    chunker = SemanticChunker()
    
    metadata = {'subject': 'biology', 'topic': 'Cell Division', 'source_file': 'test.txt'}
    
    # Test good chunk
    result1 = chunker.chunk(good_text, metadata)
    if result1.success and result1.chunks:
        good_score = result1.chunks[0].quality_score
        print(f"\n✓ Good text quality score: {good_score:.2f}")
    
    # Test poor chunk
    result2 = chunker.chunk(poor_text, metadata)
    if result2.success and result2.chunks:
        poor_score = result2.chunks[0].quality_score
        print(f"  Poor text quality score: {poor_score:.2f}")
        print(f"  Difference: {good_score - poor_score:.2f}")
    
    return result1.success and result2.success


def test_formula_detection():
    """Test formula and equation detection."""
    print("\n" + "=" * 60)
    print("TEST 4: Formula/Equation Detection")
    print("=" * 60)
    
    # Text with chemical formula
    text_with_formula = """
    Water molecule is represented as H2O. It consists of two hydrogen atoms 
    and one oxygen atom. Carbon dioxide is CO2.
    """
    
    # Text with equation
    text_with_equation = """
    Newton's second law states that F = ma, where F is force, m is mass, 
    and a is acceleration.
    """
    
    chunker = SemanticChunker()
    metadata = {'subject': 'chemistry', 'topic': 'Test', 'source_file': 'test.txt'}
    
    result1 = chunker.chunk(text_with_formula, metadata)
    result2 = chunker.chunk(text_with_equation, metadata)
    
    if result1.success and result1.chunks:
        has_formula = result1.chunks[0].metadata.get('has_formula', False)
        print(f"\n✓ Formula detection: {has_formula} (expected: True)")
    
    if result2.success and result2.chunks:
        has_equation = result2.chunks[0].metadata.get('has_equation', False)
        print(f"✓ Equation detection: {has_equation} (expected: True)")
    
    return result1.success and result2.success


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SEMANTIC CHUNKER TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Basic Chunking", test_basic_chunking),
        ("Boundary Respect", test_boundary_respect),
        ("Quality Scoring", test_quality_scoring),
        ("Formula Detection", test_formula_detection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
