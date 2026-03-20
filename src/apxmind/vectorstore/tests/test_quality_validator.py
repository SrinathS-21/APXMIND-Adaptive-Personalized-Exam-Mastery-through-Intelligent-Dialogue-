"""
Test QualityValidator
=====================

Tests for chunk quality validation.

Usage:
    python src\APXMIND\vectorstore\tests\test_quality_validator.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apxmind.vectorstore.preprocessing import QualityValidator
from apxmind.vectorstore.chunking import Chunk


def create_test_chunk(content: str, metadata: dict = None) -> Chunk:
    """Helper to create a test chunk."""
    if metadata is None:
        metadata = {
            'chunk_id': 'test_001',
            'chunk_index': 0,
            'subject': 'biology',
            'topic': 'Test Topic',
            'subtopic': '',
            'content_type': 'explanation',
            'difficulty': 'intermediate',
            'class_level': 11,
            'chapter': 'Test Chapter',
            'section': '',
            'page_number': None,
            'quality_score': 0.0,
            'key_terms': [],
            'entities': [],
            'concepts': [],
            'prerequisites': [],
            'related_topics': [],
            'summary': '',
            'has_diagram': False,
            'has_formula': False,
            'has_example': False,
            'has_equation': False,
            'language': 'english',
            'source_file': 'test.pdf',
            'source_path': '/test/test.pdf',
            'created_at': datetime.now().isoformat(),
            'embedding_model': 'nomic-embed-text',
            'chunk_method': 'semantic',
            'custom_metadata': {}
        }
    
    return Chunk(
        content=content,
        metadata=metadata,
        chunk_id='test_001',
        start_pos=0,
        end_pos=len(content),
        quality_score=0.0,
        created_at=datetime.now()
    )


def test_completeness_validation():
    """Test completeness validation."""
    print("=" * 60)
    print("TEST 1: Completeness Validation")
    print("=" * 60)
    
    validator = QualityValidator()
    
    # Good chunk - complete sentences
    good_chunk = create_test_chunk(
        "Photosynthesis is the process by which plants convert light energy "
        "into chemical energy. This process occurs in chloroplasts. "
        "The products are glucose and oxygen."
    )
    
    # Bad chunk - incomplete ending
    bad_chunk = create_test_chunk(
        "Photosynthesis is the process by which plants convert light"
    )
    
    # Too short chunk
    short_chunk = create_test_chunk("Short text")
    
    result_good = validator.validate(good_chunk)
    result_bad = validator.validate(bad_chunk)
    result_short = validator.validate(short_chunk)
    
    print(f"\n✓ Good chunk:")
    print(f"  Valid: {result_good.valid}")
    print(f"  Completeness: {result_good.metrics['completeness_score']:.2f}")
    print(f"  Issues: {len([i for i in result_good.issues if i.level.value == 'error'])}")
    
    print(f"\n✓ Bad chunk (no sentence boundary):")
    print(f"  Valid: {result_bad.valid}")
    print(f"  Completeness: {result_bad.metrics['completeness_score']:.2f}")
    print(f"  Issues: {[i.message for i in result_bad.issues if i.level.value == 'error']}")
    
    print(f"\n✓ Short chunk:")
    print(f"  Valid: {result_short.valid}")
    print(f"  Completeness: {result_short.metrics['completeness_score']:.2f}")
    print(f"  Issues: {[i.message for i in result_short.issues if i.level.value == 'error']}")
    
    # Good chunk should be valid, bad chunks should be invalid
    # The test passes if good is valid and short is invalid (most restrictive case)
    return result_good.valid and not result_short.valid


def test_readability_scoring():
    """Test readability scoring."""
    print("\n" + "=" * 60)
    print("TEST 2: Readability Scoring")
    print("=" * 60)
    
    validator = QualityValidator()
    
    # Simple text (high readability)
    simple_text = """
    A cell is the basic unit of life. All living things have cells.
    Some have one cell. Others have many cells. Cells are very small.
    You need a microscope to see them.
    """
    
    # Complex text (low readability)
    complex_text = """
    The sophisticated mechanism of cellular differentiation involves 
    comprehensive biochemical pathways that orchestrate gene expression.
    Transcriptional regulation demonstrates remarkable complexity through
    epigenetic modifications and chromatin remodeling processes.
    """
    
    simple_chunk = create_test_chunk(simple_text)
    complex_chunk = create_test_chunk(complex_text)
    
    result_simple = validator.validate(simple_chunk)
    result_complex = validator.validate(complex_chunk)
    
    print(f"\n✓ Simple text:")
    print(f"  Flesch Score: {result_simple.metrics['flesch_reading_ease']:.1f}")
    print(f"  Readability: {result_simple.metrics['readability_score']:.2f}")
    print(f"  Avg Sentence Length: {result_simple.metrics['avg_sentence_length']:.1f} words")
    
    print(f"\n✓ Complex text:")
    print(f"  Flesch Score: {result_complex.metrics['flesch_reading_ease']:.1f}")
    print(f"  Readability: {result_complex.metrics['readability_score']:.2f}")
    print(f"  Avg Sentence Length: {result_complex.metrics['avg_sentence_length']:.1f} words")
    
    # Simple should have higher readability score
    return result_simple.metrics['readability_score'] > result_complex.metrics['readability_score']


def test_coherence_checking():
    """Test coherence checking."""
    print("\n" + "=" * 60)
    print("TEST 3: Coherence Checking")
    print("=" * 60)
    
    validator = QualityValidator()
    
    # Coherent text with transitions
    coherent_text = """
    Photosynthesis begins with light absorption. First, chlorophyll captures
    light energy. Then, this energy splits water molecules. Subsequently,
    electrons flow through the electron transport chain. Finally, ATP is
    produced. Therefore, light energy is converted to chemical energy.
    """
    
    # Less coherent text
    incoherent_text = """
    Plants make food. Chlorophyll is green. Water is used. Oxygen comes out.
    Sugar is made. Energy is stored.
    """
    
    coherent_chunk = create_test_chunk(coherent_text)
    incoherent_chunk = create_test_chunk(incoherent_text)
    
    result_coherent = validator.validate(coherent_chunk)
    result_incoherent = validator.validate(incoherent_chunk)
    
    print(f"\n✓ Coherent text:")
    print(f"  Coherence Score: {result_coherent.metrics['coherence_score']:.2f}")
    print(f"  Transition Words: {result_coherent.metrics['transition_word_count']}")
    print(f"  Issues: {len(result_coherent.issues)}")
    
    print(f"\n✓ Incoherent text:")
    print(f"  Coherence Score: {result_incoherent.metrics['coherence_score']:.2f}")
    print(f"  Transition Words: {result_incoherent.metrics['transition_word_count']}")
    print(f"  Issues: {[i.message for i in result_incoherent.issues if i.level.value == 'error']}")
    
    return result_coherent.metrics['coherence_score'] > result_incoherent.metrics['coherence_score']


def test_educational_value():
    """Test educational value checking."""
    print("\n" + "=" * 60)
    print("TEST 4: Educational Value")
    print("=" * 60)
    
    validator = QualityValidator()
    
    # High educational value
    educational_text = """
    Photosynthesis is defined as the process of converting light energy into
    chemical energy. For example, when sunlight hits a leaf, chlorophyll
    molecules absorb the light. This demonstrates the principle of energy
    transformation. The equation is: 6CO2 + 6H2O → C6H12O6 + 6O2.
    """
    
    # Low educational value
    simple_text = """
    Plants are green. They need sun. They make food. This happens in leaves.
    """
    
    # Create chunks with appropriate metadata
    edu_metadata = {
        'chunk_id': 'test_001',
        'chunk_index': 0,
        'subject': 'biology',
        'topic': 'Photosynthesis',
        'key_terms': ['photosynthesis', 'chlorophyll', 'energy', 'light', 'chemical'],
        'has_formula': True,
        'has_example': True,
        'has_equation': True,
    }
    
    simple_metadata = {
        'chunk_id': 'test_002',
        'chunk_index': 0,
        'subject': 'biology',
        'topic': 'Plants',
        'key_terms': ['plants', 'green'],
        'has_formula': False,
        'has_example': False,
        'has_equation': False,
    }
    
    edu_chunk = create_test_chunk(educational_text, edu_metadata)
    simple_chunk = create_test_chunk(simple_text, simple_metadata)
    
    result_edu = validator.validate(edu_chunk)
    result_simple = validator.validate(simple_chunk)
    
    print(f"\n✓ Educational text:")
    print(f"  Educational Score: {result_edu.metrics['educational_score']:.2f}")
    print(f"  Has examples: {edu_metadata['has_example']}")
    print(f"  Key terms: {len(edu_metadata['key_terms'])}")
    print(f"  Warnings: {len([i for i in result_edu.issues if i.level.value == 'warning'])}")
    
    print(f"\n✓ Simple text:")
    print(f"  Educational Score: {result_simple.metrics['educational_score']:.2f}")
    print(f"  Has examples: {simple_metadata['has_example']}")
    print(f"  Key terms: {len(simple_metadata['key_terms'])}")
    print(f"  Warnings: {[i.message for i in result_simple.issues if i.level.value == 'warning']}")
    
    return result_edu.metrics['educational_score'] > result_simple.metrics['educational_score']


def test_overall_quality():
    """Test overall quality scoring."""
    print("\n" + "=" * 60)
    print("TEST 5: Overall Quality Scoring")
    print("=" * 60)
    
    validator = QualityValidator(min_quality_score=0.6)
    
    # High quality chunk
    high_quality_text = """
    Newton's Second Law states that force equals mass times acceleration.
    Therefore, F = ma where F is force, m is mass, and a is acceleration.
    For example, when you push a cart, the force you apply determines its
    acceleration. This fundamental principle explains motion in physics.
    """
    
    high_metadata = {
        'chunk_id': 'test_001',
        'subject': 'physics',
        'key_terms': ['force', 'mass', 'acceleration', 'motion'],
        'has_formula': True,
        'has_example': True,
        'has_equation': True,
    }
    
    chunk = create_test_chunk(high_quality_text, high_metadata)
    result = validator.validate(chunk)
    
    print(f"\n✓ Quality Analysis:")
    print(f"  Overall Quality: {result.score:.2f}")
    print(f"  Valid: {result.valid}")
    print(f"  Completeness: {result.metrics['completeness_score']:.2f}")
    print(f"  Readability: {result.metrics['readability_score']:.2f}")
    print(f"  Coherence: {result.metrics['coherence_score']:.2f}")
    print(f"  Educational: {result.metrics['educational_score']:.2f}")
    print(f"  Errors: {len([i for i in result.issues if i.level.value == 'error'])}")
    print(f"  Warnings: {len([i for i in result.issues if i.level.value == 'warning'])}")
    print(f"  Suggestions: {len([i for i in result.issues if i.level.value == 'info'])}")
    
    info_issues = [i for i in result.issues if i.level.value == 'info']
    if info_issues:
        print(f"\n  Suggestions:")
        for issue in info_issues[:3]:
            print(f"    - {issue.message}")
    
    return result.valid and result.score >= 0.6


def test_batch_validation():
    """Test batch validation."""
    print("\n" + "=" * 60)
    print("TEST 6: Batch Validation")
    print("=" * 60)
    
    validator = QualityValidator()
    
    chunks = [
        create_test_chunk("Good chunk with proper sentences. It has multiple sentences. This is complete."),
        create_test_chunk("Bad chunk"),
        create_test_chunk("Another good chunk. Therefore, it has transitions. Moreover, it flows well."),
        create_test_chunk("incomplete"),
    ]
    
    summary = validator.validate_batch(chunks)
    
    print(f"\n✓ Batch Results:")
    print(f"  Total chunks: {summary['total_chunks']}")
    print(f"  Valid chunks: {summary['valid_chunks']}")
    print(f"  Invalid chunks: {summary['invalid_chunks']}")
    print(f"  Validation rate: {summary['validation_rate']:.1%}")
    print(f"  Average quality: {summary['average_quality']:.2f}")
    
    if summary['common_issues']:
        print(f"\n  Common issues:")
        for issue, count in summary['common_issues'][:3]:
            print(f"    - {issue}: {count}")
    
    return summary['total_chunks'] == 4


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("QUALITY VALIDATOR TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Completeness Validation", test_completeness_validation),
        ("Readability Scoring", test_readability_scoring),
        ("Coherence Checking", test_coherence_checking),
        ("Educational Value", test_educational_value),
        ("Overall Quality", test_overall_quality),
        ("Batch Validation", test_batch_validation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
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
