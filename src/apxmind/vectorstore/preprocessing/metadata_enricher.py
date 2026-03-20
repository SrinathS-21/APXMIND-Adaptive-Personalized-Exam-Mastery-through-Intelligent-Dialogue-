"""
Metadata Enricher
=================

Automatically extracts and populates metadata fields from chunk content.
Enriches chunks with key terms, entities, concepts, difficulty levels, etc.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import re
from typing import List, Set, Dict, Any, Optional
from collections import Counter
import string

from ..chunking.base_chunker import Chunk, BaseChunkEnricher
from ..constants import Difficulty, ContentType
from ..monitoring import get_logger

logger = get_logger(__name__)


class MetadataEnricher(BaseChunkEnricher):
    """
    Enriches chunks with automatically extracted metadata.
    
    Features:
    - Extract key terms using TF-IDF-like scoring
    - Identify entities (formulas, reactions, equations, theorems)
    - Determine difficulty level based on vocabulary complexity
    - Extract concepts and topics
    - Identify prerequisites
    - Detect related topics
    - Generate concise summaries
    
    Usage:
        enricher = MetadataEnricher()
        enriched_chunk = enricher.enrich(chunk)
    """
    
    # Subject-specific terminology
    BIOLOGY_TERMS = {
        'cell', 'dna', 'rna', 'protein', 'enzyme', 'mitosis', 'meiosis',
        'photosynthesis', 'respiration', 'metabolism', 'gene', 'chromosome',
        'evolution', 'ecology', 'organism', 'tissue', 'organ', 'system',
        'membrane', 'nucleus', 'chloroplast', 'mitochondria', 'bacteria',
        'virus', 'plant', 'animal', 'species', 'adaptation', 'heredity'
    }
    
    CHEMISTRY_TERMS = {
        'atom', 'molecule', 'element', 'compound', 'reaction', 'bond',
        'electron', 'proton', 'neutron', 'ion', 'acid', 'base', 'salt',
        'oxidation', 'reduction', 'catalyst', 'equilibrium', 'solution',
        'solvent', 'solute', 'periodic', 'valency', 'isotope', 'organic',
        'inorganic', 'alkane', 'alkene', 'alcohol', 'ester', 'polymer'
    }
    
    PHYSICS_TERMS = {
        'force', 'mass', 'acceleration', 'velocity', 'momentum', 'energy',
        'work', 'power', 'friction', 'gravity', 'motion', 'wave', 'light',
        'electricity', 'magnetism', 'current', 'voltage', 'resistance',
        'circuit', 'heat', 'temperature', 'pressure', 'density', 'optics',
        'mechanics', 'thermodynamics', 'quantum', 'relativity', 'atom'
    }
    
    # Difficulty indicators
    BASIC_INDICATORS = {
        'simple', 'basic', 'introduction', 'fundamental', 'what is',
        'definition', 'meaning', 'overview', 'understand', 'learn'
    }
    
    ADVANCED_INDICATORS = {
        'complex', 'advanced', 'detailed', 'mechanism', 'derive',
        'proof', 'theorem', 'analysis', 'comprehensive', 'intricate',
        'sophisticated', 'elaborate', 'rigorous', 'precise'
    }
    
    # NEET-specific patterns
    NEET_INDICATORS = {
        'neet', 'exam', 'mcq', 'assertion', 'reason', 'competitive',
        'previous year', 'practice', 'test', 'objective'
    }
    
    def __init__(self):
        """Initialize metadata enricher."""
        # Compile regex patterns
        self._formula_pattern = re.compile(
            r'\b[A-Z][a-z]?\d*(?:[\+\-]?\d*)*\b|'  # Chemical formulas
            r'[A-Z]\d+|'  # Simple formulas
            r'\\[a-z]+\{[^}]+\}'  # LaTeX
        )
        
        self._equation_pattern = re.compile(
            r'[a-zA-Z]\s*=\s*[^,\.]+|'  # Equations
            r'\\frac\{[^}]+\}\{[^}]+\}|'  # LaTeX fractions
            r'F\s*=\s*ma|E\s*=\s*mc'  # Famous equations
        )
        
        self._number_pattern = re.compile(r'\d+\.?\d*')
        
        logger.info("Initialized MetadataEnricher")
    
    def enrich(self, chunk: Chunk) -> Chunk:
        """
        Enrich chunk with extracted metadata.
        
        Args:
            chunk: Chunk to enrich
            
        Returns:
            Enriched chunk with populated metadata fields
        """
        try:
            content = chunk.content
            subject = chunk.metadata.get('subject', '').lower()
            
            # Extract key terms
            chunk.metadata['key_terms'] = self.extract_key_terms(content, subject)
            
            # Extract entities
            chunk.metadata['entities'] = self.extract_entities(content)
            
            # Extract concepts
            chunk.metadata['concepts'] = self._extract_concepts(content, subject)
            
            # Determine difficulty
            difficulty = self.determine_difficulty(content)
            if difficulty:
                chunk.metadata['difficulty'] = difficulty.value
            
            # Generate summary
            chunk.metadata['summary'] = self._generate_summary(content)
            
            # Extract prerequisites (basic implementation)
            chunk.metadata['prerequisites'] = self._extract_prerequisites(content, subject)
            
            # Extract related topics
            chunk.metadata['related_topics'] = self._extract_related_topics(content, subject)
            
            # Update content flags
            chunk.metadata['has_formula'] = self._has_formula(content)
            chunk.metadata['has_equation'] = self._has_equation(content)
            chunk.metadata['has_example'] = self._has_example(content)
            
            logger.debug(
                f"Enriched chunk {chunk.chunk_id}",
                extra={
                    'key_terms_count': len(chunk.metadata['key_terms']),
                    'entities_count': len(chunk.metadata['entities']),
                    'difficulty': chunk.metadata.get('difficulty')
                }
            )
            
            return chunk
            
        except Exception as e:
            logger.error(
                f"Failed to enrich chunk {chunk.chunk_id}: {e}",
                exc_info=True
            )
            return chunk
    
    def extract_key_terms(self, text: str, subject: str = '') -> List[str]:
        """
        Extract key terms from text using frequency and relevance.
        
        Args:
            text: Text to analyze
            subject: Subject area (biology, chemistry, physics)
            
        Returns:
            List of key terms
        """
        # Normalize text
        text_lower = text.lower()
        
        # Remove punctuation and split into words
        words = re.findall(r'\b[a-z]{3,}\b', text_lower)
        
        # Common stop words to exclude
        stop_words = {
            'the', 'and', 'this', 'that', 'with', 'from', 'have', 'has',
            'was', 'were', 'been', 'are', 'for', 'not', 'but', 'can',
            'will', 'also', 'which', 'when', 'where', 'how', 'what',
            'there', 'their', 'these', 'those', 'such', 'some', 'many'
        }
        
        # Filter stop words
        words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Get subject-specific terms
        subject_terms = self._get_subject_terms(subject)
        
        # Score words
        word_freq = Counter(words)
        scored_words = []
        
        for word, freq in word_freq.items():
            score = freq
            
            # Boost subject-specific terms
            if word in subject_terms:
                score *= 3
            
            # Boost capitalized terms (likely important)
            if any(word.capitalize() in text for _ in range(freq)):
                score *= 1.5
            
            scored_words.append((word, score))
        
        # Sort by score and take top terms
        scored_words.sort(key=lambda x: x[1], reverse=True)
        key_terms = [word for word, _ in scored_words[:10]]
        
        return key_terms
    
    def extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities (formulas, reactions, theorems, laws).
        
        Args:
            text: Text to analyze
            
        Returns:
            List of entities
        """
        entities = []
        
        # Extract chemical formulas
        formulas = self._formula_pattern.findall(text)
        entities.extend([f for f in formulas if len(f) > 1 and len(f) < 20])
        
        # Extract equations
        equations = self._equation_pattern.findall(text)
        entities.extend([eq.strip() for eq in equations if len(eq.strip()) > 2])
        
        # Extract named laws/theorems
        law_pattern = re.compile(
            r"(?:Newton's|Ohm's|Boyle's|Charles'|Mendel's|Darwin's)\s+[Ll]aw|"
            r"(?:Pythagorean|Binomial)\s+[Tt]heorem|"
            r"[A-Z][a-z]+(?:'s)?\s+(?:Law|Theorem|Principle|Rule|Effect)"
        )
        laws = law_pattern.findall(text)
        entities.extend(laws)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            entity_clean = entity.strip()
            if entity_clean and entity_clean not in seen:
                seen.add(entity_clean)
                unique_entities.append(entity_clean)
        
        return unique_entities[:15]  # Limit to 15 entities
    
    def determine_difficulty(self, text: str) -> Optional[Difficulty]:
        """
        Determine content difficulty level.
        
        Factors:
        - Vocabulary complexity (word length, rare words)
        - Sentence complexity (avg sentence length)
        - Presence of mathematical content
        - Difficulty indicators
        
        Args:
            text: Text to analyze
            
        Returns:
            Difficulty level enum
        """
        text_lower = text.lower()
        
        # Check for NEET-specific content
        neet_score = sum(1 for indicator in self.NEET_INDICATORS if indicator in text_lower)
        if neet_score >= 2:
            return Difficulty.NEET_LEVEL
        
        # Count basic vs advanced indicators
        basic_score = sum(1 for indicator in self.BASIC_INDICATORS if indicator in text_lower)
        advanced_score = sum(1 for indicator in self.ADVANCED_INDICATORS if indicator in text_lower)
        
        # Calculate vocabulary complexity
        words = re.findall(r'\b[a-z]+\b', text_lower)
        if not words:
            return Difficulty.INTERMEDIATE
        
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        # Calculate sentence complexity
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_sentence_length = len(text) / len(sentences)
        else:
            avg_sentence_length = 0
        
        # Count mathematical content
        math_content = len(self._formula_pattern.findall(text)) + len(self._equation_pattern.findall(text))
        
        # Scoring
        difficulty_score = 0
        
        # Vocabulary complexity
        if avg_word_length > 6:
            difficulty_score += 2
        elif avg_word_length > 5:
            difficulty_score += 1
        
        # Sentence complexity
        if avg_sentence_length > 100:
            difficulty_score += 2
        elif avg_sentence_length > 70:
            difficulty_score += 1
        
        # Mathematical content
        if math_content > 3:
            difficulty_score += 2
        elif math_content > 0:
            difficulty_score += 1
        
        # Indicator-based adjustment
        if advanced_score > basic_score:
            difficulty_score += 2
        elif basic_score > advanced_score:
            difficulty_score -= 1
        
        # Map score to difficulty level
        if difficulty_score <= 1:
            return Difficulty.BASIC
        elif difficulty_score <= 3:
            return Difficulty.INTERMEDIATE
        elif difficulty_score <= 5:
            return Difficulty.ADVANCED
        else:
            return Difficulty.NEET_LEVEL
    
    def _extract_concepts(self, text: str, subject: str) -> List[str]:
        """Extract main concepts from text."""
        concepts = []
        
        # Get subject-specific terms that appear in text
        subject_terms = self._get_subject_terms(subject)
        text_lower = text.lower()
        
        for term in subject_terms:
            if term in text_lower:
                concepts.append(term)
        
        # Extract capitalized terms (likely concepts)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        concepts.extend([c for c in capitalized if len(c) > 3])
        
        # Remove duplicates and limit
        return list(set(concepts))[:10]
    
    def _extract_prerequisites(self, text: str, subject: str) -> List[str]:
        """Extract prerequisite concepts."""
        prerequisites = []
        
        # Look for prerequisite indicators
        prereq_patterns = [
            r'(?:requires?|needs?|assumes?)\s+(?:knowledge of|understanding of)?\s*([^,.]+)',
            r'(?:based on|builds? on|depends? on)\s+([^,.]+)',
            r'(?:before|prior to)\s+(?:this|studying|learning)\s*,?\s*([^,.]+)'
        ]
        
        for pattern in prereq_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prerequisites.extend([m.strip() for m in matches])
        
        return prerequisites[:5]
    
    def _extract_related_topics(self, text: str, subject: str) -> List[str]:
        """Extract related topics."""
        related = []
        
        # Look for "related to", "see also", etc.
        relation_patterns = [
            r'(?:related to|similar to|see also)\s+([^,.]+)',
            r'(?:other|another)\s+(?:topic|concept|example)\s+is\s+([^,.]+)',
            r'(?:compared to|contrast with)\s+([^,.]+)'
        ]
        
        for pattern in relation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            related.extend([m.strip() for m in matches])
        
        # Extract topics from same subject area
        subject_terms = self._get_subject_terms(subject)
        text_lower = text.lower()
        
        for term in subject_terms:
            if term in text_lower and term not in related:
                related.append(term)
        
        return related[:8]
    
    def _generate_summary(self, text: str, max_length: int = 150) -> str:
        """Generate concise summary of text."""
        # Get first sentence or first max_length chars
        sentences = re.split(r'[.!?]+', text)
        first_sentence = sentences[0].strip() if sentences else text
        
        if len(first_sentence) <= max_length:
            return first_sentence
        else:
            # Truncate at word boundary
            truncated = first_sentence[:max_length]
            last_space = truncated.rfind(' ')
            if last_space > 0:
                truncated = truncated[:last_space]
            return truncated + '...'
    
    def _get_subject_terms(self, subject: str) -> Set[str]:
        """Get subject-specific terminology."""
        subject = subject.lower()
        if 'bio' in subject:
            return self.BIOLOGY_TERMS
        elif 'chem' in subject:
            return self.CHEMISTRY_TERMS
        elif 'phy' in subject:
            return self.PHYSICS_TERMS
        else:
            return self.BIOLOGY_TERMS | self.CHEMISTRY_TERMS | self.PHYSICS_TERMS
    
    def _has_formula(self, text: str) -> bool:
        """Check if text contains formulas."""
        return len(self._formula_pattern.findall(text)) > 0
    
    def _has_equation(self, text: str) -> bool:
        """Check if text contains equations."""
        return len(self._equation_pattern.findall(text)) > 0
    
    def _has_example(self, text: str) -> bool:
        """Check if text contains examples."""
        example_keywords = [
            'example', 'for instance', 'for example', 'e.g.',
            'such as', 'let us consider', 'consider',
            'उदाहरण', 'जैसे'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in example_keywords)


# Export
__all__ = ['MetadataEnricher']
