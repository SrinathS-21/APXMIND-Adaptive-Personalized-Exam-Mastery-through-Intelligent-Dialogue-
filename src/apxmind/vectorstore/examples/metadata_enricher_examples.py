"""
MetadataEnricher Usage Examples
================================

Demonstrates how to use the MetadataEnricher to automatically extract
metadata from educational content.

Author: APXMIND Team
Date: 2024
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apxmind.vectorstore.preprocessing import MetadataEnricher
from apxmind.vectorstore.chunking import Chunk


def create_sample_chunk(content: str, subject: str = 'biology') -> Chunk:
    """Helper to create a sample chunk with basic metadata."""
    metadata = {
        'chunk_id': 'sample_001',
        'chunk_index': 0,
        'subject': subject,
        'topic': 'Sample Topic',
        'subtopic': '',
        'content_type': 'explanation',
        'difficulty': 'intermediate',
        'class_level': 11,
        'chapter': 'Sample Chapter',
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
        'source_file': 'sample.pdf',
        'source_path': '/sample/sample.pdf',
        'created_at': datetime.now().isoformat(),
        'embedding_model': 'nomic-embed-text',
        'chunk_method': 'semantic',
        'custom_metadata': {}
    }
    
    return Chunk(
        content=content,
        metadata=metadata,
        chunk_id='sample_001',
        start_pos=0,
        end_pos=len(content),
        quality_score=0.8,
        created_at=datetime.now()
    )


def example_1_biology_enrichment():
    """Example 1: Enrich biology content."""
    print("=" * 70)
    print("EXAMPLE 1: Biology Content Enrichment")
    print("=" * 70)
    
    content = """
    Photosynthesis is the process by which green plants and certain other 
    organisms transform light energy into chemical energy. During photosynthesis 
    in green plants, light energy is captured and used to convert water, carbon 
    dioxide, and minerals into oxygen and energy-rich organic compounds.
    
    The overall chemical equation for photosynthesis is:
    6CO2 + 6H2O + light energy → C6H12O6 + 6O2
    
    This process occurs in the chloroplasts of plant cells, specifically in 
    structures called thylakoids. Chlorophyll, the green pigment, plays a 
    crucial role in capturing light energy. For example, when sunlight hits 
    a leaf, chlorophyll molecules absorb red and blue wavelengths while 
    reflecting green light, which is why plants appear green to our eyes.
    """
    
    # Create chunk and enrich
    chunk = create_sample_chunk(content, 'biology')
    enricher = MetadataEnricher()
    enriched = enricher.enrich(chunk)
    
    # Display results
    print(f"\n📄 Original Content ({len(content)} chars)")
    print("-" * 70)
    print(content[:200] + "...")
    
    print(f"\n📊 Enriched Metadata:")
    print("-" * 70)
    print(f"Subject: {enriched.metadata['subject']}")
    print(f"Difficulty: {enriched.metadata['difficulty']}")
    print(f"\nKey Terms ({len(enriched.metadata['key_terms'])}):")
    print(f"  {', '.join(enriched.metadata['key_terms'][:10])}")
    print(f"\nEntities ({len(enriched.metadata['entities'])}):")
    for entity in enriched.metadata['entities'][:8]:
        print(f"  • {entity}")
    print(f"\nSummary:")
    print(f"  {enriched.metadata['summary']}")
    print(f"\nContent Flags:")
    print(f"  Has Formula: {enriched.metadata['has_formula']}")
    print(f"  Has Equation: {enriched.metadata['has_equation']}")
    print(f"  Has Example: {enriched.metadata['has_example']}")
    print()


def example_2_physics_enrichment():
    """Example 2: Enrich physics content."""
    print("=" * 70)
    print("EXAMPLE 2: Physics Content Enrichment")
    print("=" * 70)
    
    content = """
    Newton's Second Law of Motion states that the acceleration of an object 
    is directly proportional to the net force acting on it and inversely 
    proportional to its mass. This fundamental law can be expressed as:
    
    F = ma
    
    where F is the net force, m is the mass, and a is the acceleration.
    
    Consider this example: When you push a shopping cart with a force of 10 N, 
    and the cart has a mass of 5 kg, the acceleration can be calculated as:
    a = F/m = 10/5 = 2 m/s²
    
    This law has profound implications in mechanics and is essential for 
    understanding motion, momentum, and energy in physical systems.
    """
    
    chunk = create_sample_chunk(content, 'physics')
    enricher = MetadataEnricher()
    enriched = enricher.enrich(chunk)
    
    print(f"\n📄 Original Content ({len(content)} chars)")
    print("-" * 70)
    print(content[:200] + "...")
    
    print(f"\n📊 Enriched Metadata:")
    print("-" * 70)
    print(f"Subject: {enriched.metadata['subject']}")
    print(f"Difficulty: {enriched.metadata['difficulty']}")
    print(f"\nKey Terms ({len(enriched.metadata['key_terms'])}):")
    print(f"  {', '.join(enriched.metadata['key_terms'][:10])}")
    print(f"\nEntities ({len(enriched.metadata['entities'])}):")
    for entity in enriched.metadata['entities'][:8]:
        print(f"  • {entity}")
    print(f"\nSummary:")
    print(f"  {enriched.metadata['summary']}")
    print(f"\nContent Flags:")
    print(f"  Has Formula: {enriched.metadata['has_formula']}")
    print(f"  Has Equation: {enriched.metadata['has_equation']}")
    print(f"  Has Example: {enriched.metadata['has_example']}")
    print()


def example_3_chemistry_enrichment():
    """Example 3: Enrich chemistry content."""
    print("=" * 70)
    print("EXAMPLE 3: Chemistry Content Enrichment")
    print("=" * 70)
    
    content = """
    The periodic table arranges chemical elements in order of increasing atomic 
    number. Elements in the same group have similar chemical properties because 
    they have the same number of valence electrons. For instance, Group 1 elements 
    (lithium, sodium, potassium) are all highly reactive alkali metals.
    
    A chemical reaction occurs when substances interact to form new compounds.
    The reaction between sodium (Na) and chlorine (Cl2) produces sodium chloride:
    2Na + Cl2 → 2NaCl
    
    This is an example of a synthesis reaction where two or more reactants combine 
    to form a single product. The balanced equation shows that two sodium atoms 
    react with one chlorine molecule to produce two formula units of sodium chloride.
    """
    
    chunk = create_sample_chunk(content, 'chemistry')
    enricher = MetadataEnricher()
    enriched = enricher.enrich(chunk)
    
    print(f"\n📄 Original Content ({len(content)} chars)")
    print("-" * 70)
    print(content[:200] + "...")
    
    print(f"\n📊 Enriched Metadata:")
    print("-" * 70)
    print(f"Subject: {enriched.metadata['subject']}")
    print(f"Difficulty: {enriched.metadata['difficulty']}")
    print(f"\nKey Terms ({len(enriched.metadata['key_terms'])}):")
    print(f"  {', '.join(enriched.metadata['key_terms'][:10])}")
    print(f"\nEntities ({len(enriched.metadata['entities'])}):")
    for entity in enriched.metadata['entities'][:8]:
        print(f"  • {entity}")
    print(f"\nSummary:")
    print(f"  {enriched.metadata['summary']}")
    print(f"\nContent Flags:")
    print(f"  Has Formula: {enriched.metadata['has_formula']}")
    print(f"  Has Equation: {enriched.metadata['has_equation']}")
    print(f"  Has Example: {enriched.metadata['has_example']}")
    print()


def example_4_difficulty_comparison():
    """Example 4: Compare difficulty levels."""
    print("=" * 70)
    print("EXAMPLE 4: Difficulty Level Comparison")
    print("=" * 70)
    
    texts = {
        'Basic': """
        A cell is the smallest unit of life. All living things are made of cells.
        Some organisms have one cell, while others have many cells. This is a 
        fundamental concept in biology that is easy to understand.
        """,
        
        'Advanced': """
        The eukaryotic cell exhibits remarkable compartmentalization through 
        membrane-bound organelles. The endoplasmic reticulum facilitates protein 
        synthesis and lipid metabolism, while mitochondria orchestrate ATP production 
        through oxidative phosphorylation. This sophisticated organization demonstrates 
        the complex evolutionary adaptations of multicellular organisms.
        """,
        
        'NEET-Level': """
        NEET exam question: Which assertion is correct regarding competitive 
        inhibition? A) The inhibitor resembles substrate structurally. B) Km value 
        increases with inhibitor. Previous year papers show this MCQ pattern frequently.
        Reasoning questions require understanding both assertion and reason statements.
        """
    }
    
    enricher = MetadataEnricher()
    
    print("\n📊 Difficulty Analysis:")
    print("-" * 70)
    
    for level, text in texts.items():
        chunk = create_sample_chunk(text)
        enriched = enricher.enrich(chunk)
        
        print(f"\n{level} Text:")
        print(f"  Detected Difficulty: {enriched.metadata['difficulty']}")
        print(f"  Key Terms: {', '.join(enriched.metadata['key_terms'][:5])}")
        print(f"  Content Length: {len(text)} chars")
    
    print()


def example_5_batch_enrichment():
    """Example 5: Batch enrichment of multiple chunks."""
    print("=" * 70)
    print("EXAMPLE 5: Batch Enrichment")
    print("=" * 70)
    
    chunks_data = [
        ("Cells are the basic building blocks of life.", "biology"),
        ("Force equals mass times acceleration: F = ma", "physics"),
        ("Water is H2O, composed of hydrogen and oxygen.", "chemistry"),
    ]
    
    enricher = MetadataEnricher()
    enriched_chunks = []
    
    print("\n⚙️  Processing batch of 3 chunks...")
    print("-" * 70)
    
    for i, (content, subject) in enumerate(chunks_data, 1):
        chunk = create_sample_chunk(content, subject)
        enriched = enricher.enrich(chunk)
        enriched_chunks.append(enriched)
        
        print(f"\nChunk {i}/{len(chunks_data)}:")
        print(f"  Subject: {enriched.metadata['subject']}")
        print(f"  Key Terms: {', '.join(enriched.metadata['key_terms'][:5])}")
        print(f"  Entities: {len(enriched.metadata['entities'])}")
        print(f"  Has Formula: {enriched.metadata['has_formula']}")
    
    print(f"\n✅ Successfully enriched {len(enriched_chunks)} chunks")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("METADATA ENRICHER - USAGE EXAMPLES")
    print("=" * 70 + "\n")
    
    example_1_biology_enrichment()
    example_2_physics_enrichment()
    example_3_chemistry_enrichment()
    example_4_difficulty_comparison()
    example_5_batch_enrichment()
    
    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
