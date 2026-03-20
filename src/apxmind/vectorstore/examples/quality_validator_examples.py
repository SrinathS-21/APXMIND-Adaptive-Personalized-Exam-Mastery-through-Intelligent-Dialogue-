"""
QualityValidator Usage Examples
================================

Demonstrates how to use the QualityValidator to validate chunk quality.

Author: APXMIND Team
Date: November 2024
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apxmind.vectorstore.preprocessing import QualityValidator
from apxmind.vectorstore.chunking import Chunk


def create_sample_chunk(content: str, metadata: dict = None) -> Chunk:
    """Helper to create a sample chunk."""
    if metadata is None:
        metadata = {
            'chunk_id': 'sample_001',
            'chunk_index': 0,
            'subject': 'biology',
            'topic': 'Sample Topic',
            'key_terms': [],
            'has_formula': False,
            'has_example': False,
            'has_equation': False,
        }
    
    return Chunk(
        content=content,
        metadata=metadata,
        chunk_id='sample_001',
        start_pos=0,
        end_pos=len(content),
        quality_score=0.0,
        created_at=datetime.now()
    )


def example_1_validate_good_chunk():
    """Example 1: Validate a high-quality chunk."""
    print("=" * 70)
    print("EXAMPLE 1: High-Quality Chunk Validation")
    print("=" * 70)
    
    content = """
    Photosynthesis is the fundamental process by which plants convert light 
    energy into chemical energy. During this process, chloroplasts capture 
    light through chlorophyll molecules. The light energy then drives the 
    conversion of carbon dioxide and water into glucose and oxygen.
    
    For example, when sunlight strikes a leaf, photons are absorbed by 
    chlorophyll. This energy splits water molecules, releasing oxygen as 
    a byproduct. The chemical equation for photosynthesis is:
    6CO2 + 6H2O + light → C6H12O6 + 6O2
    
    Therefore, photosynthesis not only produces food for plants but also 
    generates the oxygen that supports most life on Earth.
    """
    
    metadata = {
        'chunk_id': 'bio_001',
        'subject': 'biology',
        'topic': 'Photosynthesis',
        'key_terms': ['photosynthesis', 'chlorophyll', 'glucose', 'oxygen', 'energy'],
        'has_formula': True,
        'has_example': True,
        'has_equation': True,
    }
    
    chunk = create_sample_chunk(content, metadata)
    validator = QualityValidator()
    result = validator.validate(chunk)
    
    print(f"\n📄 Content Preview:")
    print("-" * 70)
    print(content[:200] + "...")
    
    print(f"\n📊 Validation Results:")
    print("-" * 70)
    print(f"✓ Valid: {result.valid}")
    print(f"  Overall Quality Score: {result.score:.2f}")
    print(f"\n  Component Scores:")
    print(f"    Completeness: {result.metrics['completeness_score']:.2f}")
    print(f"    Readability:  {result.metrics['readability_score']:.2f}")
    print(f"    Coherence:    {result.metrics['coherence_score']:.2f}")
    print(f"    Educational:  {result.metrics['educational_score']:.2f}")
    
    print(f"\n  Metrics:")
    print(f"    Flesch Reading Ease: {result.metrics['flesch_reading_ease']:.1f}")
    print(f"    Sentence Count: {result.metrics['sentence_count']}")
    print(f"    Word Count: {result.metrics['word_count']}")
    print(f"    Avg Sentence Length: {result.metrics['avg_sentence_length']:.1f} words")
    print(f"    Transition Words: {result.metrics['transition_word_count']}")
    
    errors = [i for i in result.issues if i.level.value == 'error']
    warnings = [i for i in result.issues if i.level.value == 'warning']
    suggestions = [i for i in result.issues if i.level.value == 'info']
    
    print(f"\n  Issues: {len(errors)} errors, {len(warnings)} warnings")
    if suggestions:
        print(f"  Suggestions ({len(suggestions)}):")
        for s in suggestions[:3]:
            print(f"    • {s.message}")
    
    print()


def example_2_validate_poor_chunk():
    """Example 2: Validate a poor-quality chunk."""
    print("=" * 70)
    print("EXAMPLE 2: Poor-Quality Chunk Validation")
    print("=" * 70)
    
    content = "plants make food using sun"
    
    metadata = {
        'chunk_id': 'bio_002',
        'subject': 'biology',
        'topic': 'Plants',
        'key_terms': ['plants'],
        'has_formula': False,
        'has_example': False,
        'has_equation': False,
    }
    
    chunk = create_sample_chunk(content, metadata)
    validator = QualityValidator()
    result = validator.validate(chunk)
    
    print(f"\n📄 Content: \"{content}\"")
    
    print(f"\n📊 Validation Results:")
    print("-" * 70)
    print(f"✗ Valid: {result.valid}")
    print(f"  Overall Quality Score: {result.score:.2f}")
    print(f"\n  Component Scores:")
    print(f"    Completeness: {result.metrics['completeness_score']:.2f}")
    print(f"    Readability:  {result.metrics['readability_score']:.2f}")
    print(f"    Coherence:    {result.metrics['coherence_score']:.2f}")
    print(f"    Educational:  {result.metrics['educational_score']:.2f}")
    
    errors = [i for i in result.issues if i.level.value == 'error']
    warnings = [i for i in result.issues if i.level.value == 'warning']
    suggestions = [i for i in result.issues if i.level.value == 'info']
    
    print(f"\n  Critical Issues ({len(errors)}):")
    for e in errors:
        print(f"    ✗ {e.message}")
    
    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings[:3]:
            print(f"    ⚠ {w.message}")
    
    if suggestions:
        print(f"\n  Suggestions for Improvement ({len(suggestions)}):")
        for s in suggestions[:3]:
            print(f"    💡 {s.message}")
    
    print()


def example_3_readability_comparison():
    """Example 3: Compare readability levels."""
    print("=" * 70)
    print("EXAMPLE 3: Readability Level Comparison")
    print("=" * 70)
    
    texts = {
        'Simple (Easy to read)': """
        A cell is the smallest unit of life. All living things have cells.
        Some organisms have just one cell. Others have many cells working
        together. You can see cells using a microscope. They are very small
        but very important.
        """,
        
        'Moderate (Grade level)': """
        Cells are the fundamental units of biological organization. Every
        organism consists of one or more cells that perform essential life
        functions. Single-celled organisms complete all processes within
        one cell, while multicellular organisms distribute tasks among
        specialized cells.
        """,
        
        'Complex (Advanced)': """
        Cellular architecture demonstrates remarkable compartmentalization
        through sophisticated membrane-bound organelles. The endoplasmic
        reticulum facilitates protein synthesis and lipid metabolism, while
        mitochondria orchestrate ATP production through oxidative
        phosphorylation in the electron transport chain.
        """
    }
    
    validator = QualityValidator()
    
    print("\n📊 Readability Analysis:")
    print("-" * 70)
    
    for level, text in texts.items():
        chunk = create_sample_chunk(text)
        result = validator.validate(chunk)
        
        print(f"\n{level}:")
        print(f"  Flesch Score: {result.metrics['flesch_reading_ease']:.1f}/100")
        print(f"  Readability Score: {result.metrics['readability_score']:.2f}")
        print(f"  Avg Sentence Length: {result.metrics['avg_sentence_length']:.1f} words")
        print(f"  Overall Quality: {result.score:.2f}")
    
    print()


def example_4_batch_validation():
    """Example 4: Validate multiple chunks."""
    print("=" * 70)
    print("EXAMPLE 4: Batch Validation")
    print("=" * 70)
    
    chunks = [
        create_sample_chunk(
            "Newton's law states that force equals mass times acceleration. "
            "Therefore, F = ma. This fundamental principle explains motion.",
            {'key_terms': ['force', 'mass', 'acceleration'], 'has_formula': True,
             'has_example': False, 'has_equation': True}
        ),
        create_sample_chunk(
            "too short",
            {'key_terms': [], 'has_formula': False, 'has_example': False, 'has_equation': False}
        ),
        create_sample_chunk(
            "Chemical reactions involve bonds between atoms. For example, "
            "sodium reacts with chlorine to form salt: 2Na + Cl2 → 2NaCl. "
            "This demonstrates synthesis reactions.",
            {'key_terms': ['reaction', 'atoms', 'bonds'], 'has_formula': True,
             'has_example': True, 'has_equation': True}
        ),
        create_sample_chunk(
            "Incomplete sentence without",
            {'key_terms': [], 'has_formula': False, 'has_example': False, 'has_equation': False}
        ),
        create_sample_chunk(
            "Mitosis is cell division that produces two identical daughter cells. "
            "The process includes prophase, metaphase, anaphase, and telophase. "
            "During prophase, chromosomes condense. Subsequently, in metaphase, "
            "they align at the center.",
            {'key_terms': ['mitosis', 'cell', 'division', 'chromosomes'], 
             'has_formula': False, 'has_example': False, 'has_equation': False}
        ),
    ]
    
    validator = QualityValidator()
    summary = validator.validate_batch(chunks)
    
    print(f"\n📊 Batch Validation Summary:")
    print("-" * 70)
    print(f"Total Chunks: {summary['total_chunks']}")
    print(f"Valid Chunks: {summary['valid_chunks']} ({summary['validation_rate']:.1%})")
    print(f"Invalid Chunks: {summary['invalid_chunks']}")
    print(f"Average Quality: {summary['average_quality']:.2f}")
    
    print(f"\n🔍 Most Common Issues:")
    for issue, count in summary['common_issues'][:5]:
        print(f"  • {issue} ({count} occurrences)")
    
    print(f"\n📋 Individual Results:")
    for i, result in enumerate(summary['results'], 1):
        status = "✓" if result.valid else "✗"
        print(f"  Chunk {i}: {status} Score: {result.score:.2f}")
    
    print()


def example_5_custom_thresholds():
    """Example 5: Use custom validation thresholds."""
    print("=" * 70)
    print("EXAMPLE 5: Custom Validation Thresholds")
    print("=" * 70)
    
    content = """
    Energy is the ability to do work. It exists in many forms such as
    kinetic energy and potential energy. Energy cannot be created or
    destroyed, only transformed from one form to another.
    """
    
    metadata = {
        'key_terms': ['energy', 'work', 'kinetic', 'potential'],
        'has_formula': False,
        'has_example': True,
        'has_equation': False,
    }
    
    chunk = create_sample_chunk(content, metadata)
    
    # Strict validator
    strict_validator = QualityValidator(
        min_quality_score=0.8,
        min_readability=50.0,
        min_coherence_score=0.7,
        min_completeness_score=0.9
    )
    
    # Lenient validator
    lenient_validator = QualityValidator(
        min_quality_score=0.4,
        min_readability=20.0,
        min_coherence_score=0.3,
        min_completeness_score=0.5
    )
    
    result_strict = strict_validator.validate(chunk)
    result_lenient = lenient_validator.validate(chunk)
    
    print(f"\n📄 Content: \"{content[:100]}...\"")
    
    print(f"\n📊 Validation with Different Thresholds:")
    print("-" * 70)
    
    print(f"\nStrict Validator (min_quality=0.8):")
    print(f"  Valid: {result_strict.valid}")
    print(f"  Score: {result_strict.score:.2f}")
    print(f"  Issues: {len([i for i in result_strict.issues if i.level.value == 'error'])}")
    
    print(f"\nLenient Validator (min_quality=0.4):")
    print(f"  Valid: {result_lenient.valid}")
    print(f"  Score: {result_lenient.score:.2f}")
    print(f"  Issues: {len([i for i in result_lenient.issues if i.level.value == 'error'])}")
    
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("QUALITY VALIDATOR - USAGE EXAMPLES")
    print("=" * 70 + "\n")
    
    example_1_validate_good_chunk()
    example_2_validate_poor_chunk()
    example_3_readability_comparison()
    example_4_batch_validation()
    example_5_custom_thresholds()
    
    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
