"""
Quality Validator
=================

Concrete implementation of ChunkValidator for validating chunk quality.

Validates:
- Readability (Flesch Reading Ease, sentence complexity)
- Coherence (logical flow, transition words)
- Completeness (sentence boundaries, minimum content)
- Educational value (key terms, concepts, examples)

Author: APXMIND Team
Date: November 2024
"""

import re
from typing import List, Dict, Set
from datetime import datetime

from .base_validator import ChunkValidator, ValidationResult
from ..chunking import Chunk
from ..constants import Difficulty


class QualityValidator(ChunkValidator):
    """
    Validates chunk quality using multiple metrics.
    
    Checks:
    - Readability scores (Flesch Reading Ease)
    - Coherence (transition words, logical flow)
    - Completeness (sentence boundaries, min/max length)
    - Educational value (technical terms, examples)
    """
    
    # Transition words that indicate coherence
    TRANSITION_WORDS = {
        'however', 'therefore', 'thus', 'furthermore', 'moreover',
        'additionally', 'consequently', 'hence', 'nevertheless',
        'although', 'while', 'whereas', 'because', 'since',
        'for example', 'for instance', 'such as', 'namely',
        'first', 'second', 'third', 'finally', 'lastly',
        'next', 'then', 'subsequently', 'previously',
        'similarly', 'likewise', 'conversely', 'in contrast',
        'on the other hand', 'in addition', 'as a result'
    }
    
    # Words indicating examples
    EXAMPLE_INDICATORS = {
        'example', 'instance', 'such as', 'for instance',
        'consider', 'suppose', 'assume', 'let us',
        'imagine', 'demonstration', 'illustration'
    }
    
    # Educational signal words
    EDUCATIONAL_WORDS = {
        'define', 'definition', 'means', 'refers to',
        'called', 'known as', 'termed', 'describes',
        'explains', 'shows', 'demonstrates', 'illustrates',
        'principle', 'theory', 'law', 'rule', 'concept',
        'property', 'characteristic', 'feature', 'process'
    }
    
    def __init__(self, 
                 min_quality_score: float = 0.6,
                 min_readability: float = 30.0,
                 min_coherence_score: float = 0.4,
                 min_completeness_score: float = 0.7):
        """
        Initialize the quality validator.
        
        Args:
            min_quality_score: Minimum overall quality score (0-1)
            min_readability: Minimum Flesch Reading Ease score (0-100)
            min_coherence_score: Minimum coherence score (0-1)
            min_completeness_score: Minimum completeness score (0-1)
        """
        self.min_quality_score = min_quality_score
        self.min_readability = min_readability
        self.min_coherence_score = min_coherence_score
        self.min_completeness_score = min_completeness_score
        
        # Compile regex patterns
        self._sentence_pattern = re.compile(r'[.!?]+\s+')
        self._word_pattern = re.compile(r'\b\w+\b')
        self._syllable_pattern = re.compile(r'[aeiouy]+', re.IGNORECASE)
    
    def validate(self, chunk: Chunk) -> ValidationResult:
        """
        Validate a chunk's quality.
        
        Args:
            chunk: The chunk to validate
            
        Returns:
            ValidationResult with validation status and details
        """
        content = chunk.content.strip()
        
        # Initialize scores
        scores = {}
        issues = []
        warnings = []
        
        # 1. Check completeness
        completeness_score, completeness_issues = self._check_completeness(content)
        scores['completeness'] = completeness_score
        issues.extend(completeness_issues)
        
        # 2. Check readability
        readability_score, readability_issues = self._check_readability(content)
        scores['readability'] = readability_score
        issues.extend(readability_issues)
        
        # 3. Check coherence
        coherence_score, coherence_issues = self._check_coherence(content)
        scores['coherence'] = coherence_score
        issues.extend(coherence_issues)
        
        # 4. Check educational value
        educational_score, educational_warnings = self._check_educational_value(content, chunk.metadata)
        scores['educational_value'] = educational_score
        warnings.extend(educational_warnings)
        
        # Calculate overall quality score (weighted average)
        overall_score = (
            completeness_score * 0.3 +
            readability_score * 0.25 +
            coherence_score * 0.25 +
            educational_score * 0.2
        )
        
        # Determine if chunk passes validation
        is_valid = (
            overall_score >= self.min_quality_score and
            completeness_score >= self.min_completeness_score and
            coherence_score >= self.min_coherence_score
        )
        
        # Create suggestions for improvement
        suggestions = self._generate_suggestions(scores, issues, warnings)
        
        # Convert issues and warnings to ValidationIssue objects
        from .base_validator import ValidationIssue, ValidationLevel
        
        validation_issues = []
        for issue in issues:
            validation_issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=issue,
                suggestion=None
            ))
        
        for warning in warnings:
            validation_issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=warning,
                suggestion=None
            ))
        
        # Add suggestions as info-level issues
        for suggestion in suggestions:
            validation_issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                message=suggestion,
                suggestion=suggestion
            ))
        
        return ValidationResult(
            valid=is_valid,
            issues=validation_issues,
            metrics={
                'completeness_score': completeness_score,
                'readability_score': readability_score,
                'coherence_score': coherence_score,
                'educational_score': educational_score,
                'flesch_reading_ease': scores.get('flesch_reading_ease', 0),
                'sentence_count': scores.get('sentence_count', 0),
                'word_count': scores.get('word_count', 0),
                'avg_sentence_length': scores.get('avg_sentence_length', 0),
                'transition_word_count': scores.get('transition_word_count', 0),
            },
            score=overall_score
        )
    
    def _check_completeness(self, content: str) -> tuple[float, List[str]]:
        """
        Check if chunk is complete (proper boundaries, sufficient content).
        
        Args:
            content: The chunk content
            
        Returns:
            Tuple of (score, issues)
        """
        issues = []
        score = 1.0
        
        # Check minimum length
        if len(content) < 50:
            issues.append("Content too short (< 50 chars)")
            score -= 0.3
        
        # Check maximum length
        if len(content) > 2000:
            issues.append("Content too long (> 2000 chars)")
            score -= 0.2
        
        # Check sentence boundaries
        if not content[-1] in '.!?':
            issues.append("Chunk does not end with sentence boundary")
            score -= 0.2
        
        # Check for incomplete sentences at start
        if content and content[0].islower() and not content.startswith('e.g.'):
            issues.append("Chunk starts with lowercase (may be incomplete)")
            score -= 0.15
        
        # Check for orphaned fragments
        sentences = self._sentence_pattern.split(content)
        if sentences:
            last_sentence = sentences[-1].strip()
            if last_sentence and len(last_sentence) < 10:
                issues.append("Last sentence fragment too short")
                score -= 0.15
        
        return max(0.0, score), issues
    
    def _check_readability(self, content: str) -> tuple[float, List[str]]:
        """
        Check readability using Flesch Reading Ease and other metrics.
        
        Args:
            content: The chunk content
            
        Returns:
            Tuple of (score, issues)
        """
        issues = []
        
        # Count sentences, words, syllables
        sentences = [s.strip() for s in self._sentence_pattern.split(content) if s.strip()]
        words = self._word_pattern.findall(content)
        
        sentence_count = len(sentences)
        word_count = len(words)
        
        if sentence_count == 0 or word_count == 0:
            issues.append("No valid sentences or words found")
            return 0.0, issues
        
        # Count syllables (approximate)
        syllable_count = sum(
            max(1, len(self._syllable_pattern.findall(word)))
            for word in words
        )
        
        # Calculate Flesch Reading Ease
        # Formula: 206.835 - 1.015(words/sentences) - 84.6(syllables/words)
        avg_sentence_length = word_count / sentence_count
        avg_syllables_per_word = syllable_count / word_count
        
        flesch_score = (
            206.835 -
            1.015 * avg_sentence_length -
            84.6 * avg_syllables_per_word
        )
        
        # Normalize to 0-1 range (Flesch is typically 0-100)
        # Higher Flesch = easier to read
        # For educational content, 30-60 is appropriate (college level)
        normalized_score = max(0.0, min(1.0, flesch_score / 100.0))
        
        # Check thresholds
        if flesch_score < 0:
            issues.append("Readability extremely low (very complex text)")
        elif flesch_score < 30:
            issues.append("Readability low (college graduate level)")
        
        if avg_sentence_length > 40:
            issues.append(f"Average sentence too long ({avg_sentence_length:.1f} words)")
        
        # Store metrics for later use
        self._temp_metrics = {
            'flesch_reading_ease': flesch_score,
            'sentence_count': sentence_count,
            'word_count': word_count,
            'avg_sentence_length': avg_sentence_length
        }
        
        return normalized_score, issues
    
    def _check_coherence(self, content: str) -> tuple[float, List[str]]:
        """
        Check logical coherence and flow.
        
        Args:
            content: The chunk content
            
        Returns:
            Tuple of (score, issues)
        """
        issues = []
        score = 0.5  # Base score
        
        content_lower = content.lower()
        
        # Check for transition words
        transition_count = sum(
            1 for word in self.TRANSITION_WORDS
            if word in content_lower
        )
        
        # Normalize by content length (expect ~1 per 100 words)
        word_count = len(self._word_pattern.findall(content))
        expected_transitions = max(1, word_count / 100)
        transition_ratio = transition_count / expected_transitions
        
        # Boost score based on transition words
        if transition_ratio >= 1.0:
            score += 0.3
        elif transition_ratio >= 0.5:
            score += 0.2
        else:
            issues.append("Few transition words (may lack logical flow)")
            score += 0.1
        
        # Check for pronouns indicating continuity
        pronouns = ['this', 'that', 'these', 'those', 'it', 'they', 'its', 'their']
        pronoun_count = sum(1 for p in pronouns if f' {p} ' in content_lower)
        
        if pronoun_count > 0:
            score += 0.1
        
        # Check for repetition (good for educational content)
        words = self._word_pattern.findall(content.lower())
        if len(words) > 0:
            unique_words = set(words)
            repetition_ratio = 1 - (len(unique_words) / len(words))
            
            # Moderate repetition is good (0.3-0.5)
            if 0.3 <= repetition_ratio <= 0.5:
                score += 0.1
            elif repetition_ratio > 0.7:
                issues.append("High word repetition (may be redundant)")
        
        # Store metrics
        self._temp_metrics['transition_word_count'] = transition_count
        
        return min(1.0, score), issues
    
    def _check_educational_value(self, content: str, metadata: Dict) -> tuple[float, List[str]]:
        """
        Check educational value and content richness.
        
        Args:
            content: The chunk content
            metadata: Chunk metadata
            
        Returns:
            Tuple of (score, warnings)
        """
        warnings = []
        score = 0.5  # Base score
        
        content_lower = content.lower()
        
        # Check for examples
        example_count = sum(
            1 for indicator in self.EXAMPLE_INDICATORS
            if indicator in content_lower
        )
        
        if example_count > 0:
            score += 0.2
        else:
            warnings.append("No examples found (may benefit from concrete examples)")
        
        # Check for educational signal words
        educational_count = sum(
            1 for word in self.EDUCATIONAL_WORDS
            if word in content_lower
        )
        
        if educational_count >= 2:
            score += 0.2
        elif educational_count == 1:
            score += 0.1
        
        # Check for formulas/equations (from metadata)
        if metadata.get('has_formula') or metadata.get('has_equation'):
            score += 0.15
        
        # Check for key terms (from metadata)
        key_terms = metadata.get('key_terms', [])
        if len(key_terms) >= 5:
            score += 0.15
        elif len(key_terms) >= 3:
            score += 0.1
        else:
            warnings.append("Few key terms (content may lack technical depth)")
        
        return min(1.0, score), warnings
    
    def _generate_suggestions(self, 
                             scores: Dict[str, float], 
                             issues: List[str], 
                             warnings: List[str]) -> List[str]:
        """
        Generate suggestions for improving chunk quality.
        
        Args:
            scores: Dictionary of quality scores
            issues: List of validation issues
            warnings: List of warnings
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Completeness suggestions
        if scores.get('completeness', 1.0) < 0.7:
            suggestions.append("Ensure chunk ends at sentence boundary")
            suggestions.append("Check for complete sentences at start and end")
        
        # Readability suggestions
        if scores.get('readability', 1.0) < 0.5:
            suggestions.append("Break down complex sentences into simpler ones")
            suggestions.append("Use shorter, clearer sentence structures")
        
        # Coherence suggestions
        if scores.get('coherence', 1.0) < 0.5:
            suggestions.append("Add transition words for better flow")
            suggestions.append("Connect ideas with logical connectives")
        
        # Educational value suggestions
        if scores.get('educational_value', 1.0) < 0.6:
            suggestions.append("Include concrete examples to illustrate concepts")
            suggestions.append("Define key technical terms clearly")
            suggestions.append("Add formulas or equations where relevant")
        
        return suggestions
    
    def validate_batch(self, chunks: List[Chunk]) -> Dict[str, any]:
        """
        Validate a batch of chunks and provide summary statistics.
        
        Args:
            chunks: List of chunks to validate
            
        Returns:
            Dictionary with validation summary
        """
        results = [self.validate(chunk) for chunk in chunks]
        
        valid_count = sum(1 for r in results if r.valid)
        avg_quality = sum(r.score for r in results) / len(results) if results else 0
        
        # Collect all error-level issues
        all_issues = {}
        for result in results:
            for issue in result.issues:
                if issue.level.value == 'error':
                    all_issues[issue.message] = all_issues.get(issue.message, 0) + 1
        
        return {
            'total_chunks': len(chunks),
            'valid_chunks': valid_count,
            'invalid_chunks': len(chunks) - valid_count,
            'validation_rate': valid_count / len(chunks) if chunks else 0,
            'average_quality': avg_quality,
            'common_issues': sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:5],
            'results': results
        }
