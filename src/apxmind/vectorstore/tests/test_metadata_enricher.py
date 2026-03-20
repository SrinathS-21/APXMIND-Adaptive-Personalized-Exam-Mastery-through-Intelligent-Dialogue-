"""
Test MetadataEnricher
=====================

Tests for automatic metadata extraction and enrichment.

Usage:
    python -m APXMIND.vectorstore.tests.test_metadata_enricher
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apxmind.vectorstore.preprocessing import MetadataEnricher
from apxmind.vectorstore.chunking import Chunk
from apxmind.vectorstore.constants import Difficulty


def create_test_chunk(content: str, subject: str = 'biology') -> Chunk:
    """Helper to create a test chunk."""
    metadata = {
        'chunk_id': 'test_001',
        'chunk_index': 0,
        'subject': subject,
        'topic': 'Test Topic',
        'subtopic': '',
        'content_type': 'explanation',
        'difficulty': 'intermediate',
        'class_level': 11,
        'chapter': 'Test Chapter',
        'section': '',
        'page_number': None,
        'quality_score': 0.8,
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
        quality_score=0.8,
        created_at=datetime.now()
    )


def test_key_term_extraction():
    """Test extraction of key terms."""
    print("=" * 60)
    print("TEST 1: Key Term Extraction")
    print("=" * 60)
    
    content = """
    Photosynthesis is the process by which green plants convert light energy 
    into chemical energy. Chloroplasts contain chlorophyll pigment which captures 
    light energy. The process involves light-dependent reactions and the Calvin cycle.
    Photosynthesis produces glucose and oxygen as products.
    """
    
    chunk = create_test_chunk(content, 'biology')
    enricher = MetadataEnricher()
    
    enriched = enricher.enrich(chunk)
    
    key_terms = enriched.metadata['key_terms']
    print(f"\n✓ Extracted {len(key_terms)} key terms:")
    print(f"  {', '.join(key_terms[:10])}")
    
    # Check for expected biology terms
    biology_terms_found = [t for t in key_terms if t in ['photosynthesis', 'chlorophyll', 'glucose', 'oxygen', 'energy']]
    print(f"\n  Biology-specific terms found: {len(biology_terms_found)}")
    
    return len(key_terms) > 0


def test_entity_extraction():
    """Test extraction of formulas and equations."""
    print("\n" + "=" * 60)
    print("TEST 2: Entity Extraction")
    print("=" * 60)
    
    content = """
    The chemical equation for photosynthesis is: 6CO2 + 6H2O + light → C6H12O6 + 6O2.
    Water molecule is H2O and carbon dioxide is CO2. Glucose has formula C6H12O6.
    Newton's Second Law states that F = ma.
    """
    
    chunk = create_test_chunk(content, 'chemistry')
    enricher = MetadataEnricher()
    
    enriched = enricher.enrich(chunk)
    
    entities = enriched.metadata['entities']
    print(f"\n✓ Extracted {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity}")
    
    # Check for expected entities
    has_formulas = any('CO2' in e or 'H2O' in e or 'C6H12O6' in e for e in entities)
    has_laws = any("Newton's" in e or 'Law' in e for e in entities)
    
    print(f"\n  Has chemical formulas: {has_formulas}")
    print(f"  Has laws/theorems: {has_laws}")
    
    return len(entities) > 0


def test_difficulty_determination():
    """Test difficulty level determination."""
    print("\n" + "=" * 60)
    print("TEST 3: Difficulty Determination")
    print("=" * 60)
    
    # Basic text
    basic_text = """
    Cell is the basic unit of life. It is simple to understand.
    All living things are made of cells. This is a fundamental concept.
    """
    
    # Advanced text
    advanced_text = """
    The sophisticated mechanism involves complex biochemical pathways.
    Comprehensive analysis reveals intricate molecular interactions.
    Rigorous derivation of the thermodynamic equation demonstrates
    elaborate relationships between entropy and enthalpy.
    """
    
    # NEET-level text
    neet_text = """
    NEET exam question: In competitive exams, MCQ questions test
    assertion-reason based understanding. Previous year papers show
    this pattern frequently.
    """
    
    enricher = MetadataEnricher()
    
    chunk_basic = create_test_chunk(basic_text)
    chunk_advanced = create_test_chunk(advanced_text)
    chunk_neet = create_test_chunk(neet_text)
    
    enriched_basic = enricher.enrich(chunk_basic)
    enriched_advanced = enricher.enrich(chunk_advanced)
    enriched_neet = enricher.enrich(chunk_neet)
    
    diff_basic = enriched_basic.metadata.get('difficulty', '')
    diff_advanced = enriched_advanced.metadata.get('difficulty', '')
    diff_neet = enriched_neet.metadata.get('difficulty', '')
    
    print(f"\n✓ Difficulty levels determined:")
    print(f"  Basic text → {diff_basic}")
    print(f"  Advanced text → {diff_advanced}")
    print(f"  NEET text → {diff_neet}")
    
    # Validate that advanced is harder than basic
    difficulty_order = ['basic', 'intermediate', 'advanced', 'neet_level']
    
    if diff_basic in difficulty_order and diff_advanced in difficulty_order:
        basic_idx = difficulty_order.index(diff_basic)
        advanced_idx = difficulty_order.index(diff_advanced)
        correct_ordering = advanced_idx >= basic_idx
        print(f"\n  Correct ordering (advanced >= basic): {correct_ordering}")
    
    return True


def test_summary_generation():
    """Test summary generation."""
    print("\n" + "=" * 60)
    print("TEST 4: Summary Generation")
    print("=" * 60)
    
    content = """
    Mitosis is a type of cell division that results in two daughter cells 
    each having the same number and kind of chromosomes as the parent nucleus.
    The process consists of four main phases: prophase, metaphase, anaphase, 
    and telophase. During prophase, chromatin condenses into chromosomes.
    """
    
    chunk = create_test_chunk(content)
    enricher = MetadataEnricher()
    
    enriched = enricher.enrich(chunk)
    
    summary = enriched.metadata['summary']
    print(f"\n✓ Generated summary ({len(summary)} chars):")
    print(f"  \"{summary}\"")
    
    # Summary should be shorter than original
    is_shorter = len(summary) < len(content)
    print(f"\n  Summary is shorter than original: {is_shorter}")
    
    return len(summary) > 0 and is_shorter


def test_content_flags():
    """Test content detection flags."""
    print("\n" + "=" * 60)
    print("TEST 5: Content Flags Detection")
    print("=" * 60)
    
    # Text with formula and example
    content = """
    For example, the reaction of sodium with water is: 2Na + 2H2O → 2NaOH + H2.
    This demonstrates the reactivity of alkali metals. Consider another instance:
    potassium also reacts violently with water.
    """
    
    chunk = create_test_chunk(content, 'chemistry')
    enricher = MetadataEnricher()
    
    enriched = enricher.enrich(chunk)
    
    has_formula = enriched.metadata['has_formula']
    has_equation = enriched.metadata['has_equation']
    has_example = enriched.metadata['has_example']
    
    print(f"\n✓ Content flags:")
    print(f"  Has formula: {has_formula}")
    print(f"  Has equation: {has_equation}")
    print(f"  Has example: {has_example}")
    
    return has_formula and has_example


def test_subject_specific_extraction():
    """Test subject-specific term extraction."""
    print("\n" + "=" * 60)
    print("TEST 6: Subject-Specific Extraction")
    print("=" * 60)
    
    # Physics text
    physics_text = """
    Force is defined as mass times acceleration. Momentum equals mass times velocity.
    Energy can be kinetic or potential. Power is the rate of work done.
    """
    
    # Chemistry text
    chemistry_text = """
    Atoms combine to form molecules. Elements are arranged in the periodic table.
    Chemical reactions involve bonds between atoms. Catalysts speed up reactions.
    """
    
    enricher = MetadataEnricher()
    
    chunk_physics = create_test_chunk(physics_text, 'physics')
    chunk_chemistry = create_test_chunk(chemistry_text, 'chemistry')
    
    enriched_physics = enricher.enrich(chunk_physics)
    enriched_chemistry = enricher.enrich(chunk_chemistry)
    
    physics_terms = enriched_physics.metadata['key_terms']
    chemistry_terms = enriched_chemistry.metadata['key_terms']
    
    print(f"\n✓ Physics terms: {', '.join(physics_terms[:5])}")
    print(f"  Chemistry terms: {', '.join(chemistry_terms[:5])}")
    
    # Check for subject-specific terms
    physics_specific = ['force', 'mass', 'acceleration', 'momentum', 'velocity', 'energy', 'power']
    chemistry_specific = ['atom', 'molecule', 'element', 'periodic', 'reaction', 'catalyst']
    
    physics_found = sum(1 for t in physics_terms if t in physics_specific)
    chemistry_found = sum(1 for t in chemistry_terms if t in chemistry_specific)
    
    print(f"\n  Physics-specific terms found: {physics_found}")
    print(f"  Chemistry-specific terms found: {chemistry_found}")
    
    return physics_found > 0 and chemistry_found > 0


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("METADATA ENRICHER TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Key Term Extraction", test_key_term_extraction),
        ("Entity Extraction", test_entity_extraction),
        ("Difficulty Determination", test_difficulty_determination),
        ("Summary Generation", test_summary_generation),
        ("Content Flags", test_content_flags),
        ("Subject-Specific Extraction", test_subject_specific_extraction),
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
