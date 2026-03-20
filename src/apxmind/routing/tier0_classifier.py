"""
Tier-0 Query Classifier
=======================

Transforms raw student queries into structured classification data.

This is the first layer of the hierarchical routing system that:
1. Detects subject (physics, chemistry, biology)
2. Identifies intent (teach, train, doubt, mentor, general)
3. Infers difficulty level
4. Extracts focus areas and keywords
5. Detects language
6. Aggregates confidence scores

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Subject(str, Enum):
    """Supported subjects."""
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    GENERAL = "general"


class Intent(str, Enum):
    """Query intents."""
    TEACH = "teach"  # Explanation/concept learning
    TRAIN = "train"  # Practice/quiz generation
    DOUBT = "doubt"  # Problem solving assistance
    MENTOR = "mentor"  # Guidance/strategy/motivation
    GENERAL = "general"  # Off-topic/casual


class Difficulty(str, Enum):
    """Difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class LearningLevel(str, Enum):
    """Student learning levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class UserProfile:
    """User profile for personalization."""
    user_id: str
    learning_level: LearningLevel = LearningLevel.INTERMEDIATE
    language_preference: str = "english"
    recent_accuracy: float = 0.7
    subjects_studied: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'learning_level': self.learning_level.value if isinstance(self.learning_level, LearningLevel) else self.learning_level,
            'language_preference': self.language_preference,
            'recent_accuracy': self.recent_accuracy,
            'subjects_studied': self.subjects_studied
        }


@dataclass
class ClassificationStrategy:
    """Classification strategy metadata."""
    subject_method: str = "keyword_match"
    intent_method: str = "pattern_match"
    difficulty_method: str = "inference"


@dataclass
class ClassificationResult:
    """Result of query classification."""
    
    # Core classification
    subject: Subject
    subject_confidence: float
    
    intent: Intent
    intent_confidence: float
    
    difficulty: Difficulty
    difficulty_confidence: float
    
    # Focus area
    focus_area: Optional[str] = None
    focus_keywords: List[str] = field(default_factory=list)
    focus_confidence: float = 0.0
    
    # Metadata
    language: str = "english"
    overall_confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Strategy used
    strategy: ClassificationStrategy = field(default_factory=ClassificationStrategy)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'subject': self.subject.value if isinstance(self.subject, Subject) else self.subject,
            'subject_confidence': round(self.subject_confidence, 3),
            'intent': self.intent.value if isinstance(self.intent, Intent) else self.intent,
            'intent_confidence': round(self.intent_confidence, 3),
            'difficulty': self.difficulty.value if isinstance(self.difficulty, Difficulty) else self.difficulty,
            'difficulty_confidence': round(self.difficulty_confidence, 3),
            'focus_area': self.focus_area,
            'focus_keywords': self.focus_keywords,
            'focus_confidence': round(self.focus_confidence, 3),
            'language': self.language,
            'overall_confidence': round(self.overall_confidence, 3),
            'timestamp': self.timestamp,
            'strategy': asdict(self.strategy)
        }


class Tier0Classifier:
    """
    Query classification system (Tier-0).
    
    Transforms unstructured queries into structured classification for:
    - Subject detection (physics, chemistry, biology)
    - Intent identification (teach, train, doubt, mentor)
    - Difficulty inference (easy, medium, hard)
    - Focus area extraction with keywords
    - Language detection
    
    Usage:
        classifier = Tier0Classifier()
        
        user_profile = UserProfile(
            user_id="user_123",
            learning_level=LearningLevel.INTERMEDIATE,
            recent_accuracy=0.72
        )
        
        result = classifier.classify_query(
            query="Explain how photosynthesis works",
            user_profile=user_profile
        )
        
        print(f"Subject: {result.subject} ({result.subject_confidence})")
        print(f"Intent: {result.intent} ({result.intent_confidence})")
    """
    
    # Subject keyword database
    SUBJECT_KEYWORDS = {
        Subject.PHYSICS: [
            "force", "velocity", "acceleration", "newton", "energy", "motion",
            "kinematics", "thermodynamics", "light", "electricity", "magnet",
            "momentum", "friction", "gravity", "pressure", "power", "work",
            "wave", "frequency", "wavelength", "amplitude", "optics", "lens",
            "mirror", "reflection", "refraction", "circuit", "current", "voltage",
            "resistance", "capacitor", "inductor", "magnetic", "field", "flux",
            "kinetic", "potential", "mechanics", "dynamics", "electromagnetic",
            "photoelectric", "quantum", "relativity", "nuclear", "radiation",
            "induction", "torque", "oscillation", "pendulum", "displacement"
        ],
        Subject.CHEMISTRY: [
            "atom", "molecule", "reaction", "bond", "compound", "organic",
            "element", "acid", "base", "oxidation", "reduction", "moles",
            "stoichiometry", "equilibrium", "catalyst", "periodic", "table",
            "electron", "proton", "neutron", "ion", "covalent", "ionic",
            "solution", "solvent", "solute", "concentration", "pH", "buffer",
            "redox", "thermochemistry", "kinetics", "chemical", "formula",
            "electrochemistry", "polymer", "hydrocarbon", "alkane", "alkene",
            "isomer", "titration", "molarity", "vsepr", "hybridization",
            "enthalpy", "entropy", "gibbs", "hess", "nomenclature"
        ],
        Subject.BIOLOGY: [
            "cell", "photosynthesis", "respiration", "DNA", "gene", "enzyme",
            "protein", "evolution", "ecology", "reproduction", "organism",
            "mitosis", "meiosis", "chloroplast", "mitochondria", "ribosome",
            "nucleus", "membrane", "plant", "animal", "bacteria", "virus",
            "tissue", "organ", "system", "metabolism", "ATP", "glucose",
            "inheritance", "chromosome", "allele", "genotype", "phenotype",
            "RNA", "replication", "transcription", "translation", "photosynthetic",
            "calvin", "krebs", "glycolysis", "digestive", "circulatory",
            "nervous", "endocrine", "immune", "biodiversity", "ecosystem"
        ]
    }
    
    # Intent pattern database (ordered by priority)
    INTENT_PATTERNS = {
        Intent.DOUBT: [
            r"\b(stuck|confused|struggling|trouble|can't|cannot|unable)\b",
            r"\b(don't understand|not getting|having difficulty)\b",
            r"\b(problem with|issue with|doubt about)\b"
        ],
        Intent.MENTOR: [
            r"\b(strategy|tips|advice|guide|preparation|best way)\b",
            r"\b(should i|recommend|suggest|motivation)\b",
            r"\b(study plan|time management|exam strategy|career|college)\b"
        ],
        Intent.TRAIN: [
            r"\b(generate|create|give|provide).*(quiz|question|mcq|practice|problem|exercise|test)\b",
            r"\b(quiz|exercise|test|worksheet|mcq|mcqs)\b",
            r"\b(practice|exercise).*\b(question|problem)\b",
            r"\b(need|want).*(practice|exercise|question)\b"
        ],
        Intent.TEACH: [
            r"\b(explain|understand|concept|what is|how does|describe|clarify)\b",
            r"\b(definition|meaning|theory|principle|law|process)\b",
            r"\b(help me understand|make sense|learn about|tell me about)\b"
        ]
    }
    
    # Topic mappings by subject
    TOPIC_MAPPINGS = {
        Subject.PHYSICS: {
            "kinematics": ["motion", "velocity", "acceleration", "displacement", "distance", "speed", "equation"],
            "dynamics": ["force", "newton", "mass", "f=ma", "friction", "momentum"],
            "energy": ["work", "power", "kinetic", "potential", "conservation", "energy", "joule"],
            "thermodynamics": ["heat", "temperature", "entropy", "gas", "laws", "thermal"],
            "waves": ["sound", "frequency", "wavelength", "interference", "diffraction", "wave"],
            "optics": ["light", "reflection", "refraction", "lens", "mirror", "spectrum", "ray"],
            "electromagnetism": ["charge", "current", "voltage", "magnetic", "field", "circuit", "electromagnetic", "induction"],
            "modern_physics": ["quantum", "relativity", "photoelectric", "nuclear", "radiation"]
        },
        Subject.CHEMISTRY: {
            "atomic_structure": ["atom", "electron", "proton", "neutron", "orbital", "quantum"],
            "chemical_bonding": ["bond", "covalent", "ionic", "molecular", "structure"],
            "stoichiometry": ["moles", "mass", "limiting", "yield", "ratio", "equation"],
            "thermochemistry": ["enthalpy", "heat", "energy", "exothermic", "endothermic"],
            "equilibrium": ["equilibrium", "constant", "shift", "le chatelier"],
            "acids_bases": ["acid", "base", "pH", "buffer", "titration", "neutralization"],
            "redox": ["oxidation", "reduction", "redox", "electron", "transfer"],
            "organic": ["organic", "carbon", "hydrocarbon", "functional", "group", "reaction"],
            "kinetics": ["rate", "reaction", "catalyst", "activation", "energy"]
        },
        Subject.BIOLOGY: {
            "cell_biology": ["cell", "membrane", "organelle", "nucleus", "cytoplasm", "cellular"],
            "photosynthesis": ["photosynthesis", "light", "dark", "chloroplast", "glucose", "calvin", "thylakoid"],
            "respiration": ["respiration", "atp", "glycolysis", "krebs", "electron", "mitochondria", "nadh"],
            "genetics": ["dna", "gene", "chromosome", "allele", "inheritance", "mendel", "rna", "replication"],
            "evolution": ["evolution", "natural", "selection", "darwin", "adaptation"],
            "ecology": ["ecosystem", "food", "chain", "web", "population", "community"],
            "reproduction": ["reproduction", "sexual", "asexual", "gamete", "fertilization"],
            "plant_biology": ["plant", "tissue", "root", "stem", "leaf", "flower"],
            "human_biology": ["human", "organ", "system", "digestion", "circulation", "nervous", "digestive"]
        }
    }
    
    def __init__(self):
        """Initialize classifier."""
        logger.info("Initialized Tier0Classifier")
    
    def classify_query(
        self,
        query: str,
        user_profile: Optional[UserProfile] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> ClassificationResult:
        """
        Classify a student query.
        
        Args:
            query: Raw query text
            user_profile: User profile for personalization
            conversation_history: Previous conversation for context
            
        Returns:
            ClassificationResult with all classification data
        """
        # Default profile if not provided
        if user_profile is None:
            user_profile = UserProfile(user_id="anonymous")
        
        # Normalize query
        query_lower = query.lower().strip()
        
        try:
            # Step 1: Detect subject
            subject, subject_conf = self._detect_subject(query_lower)
            
            # Step 2: Detect intent
            intent, intent_conf = self._detect_intent(query_lower)
            
            # Step 3: Infer difficulty
            difficulty, difficulty_conf = self._infer_difficulty(
                query_lower, user_profile
            )
            
            # Step 4: Extract focus area
            focus_area, focus_keywords, focus_conf = self._extract_focus_area(
                query_lower, subject
            )
            
            # Step 5: Detect language
            language = self._detect_language(user_profile, query)
            
            # Step 6: Aggregate confidence
            overall_conf = self._aggregate_confidence({
                'subject': subject_conf,
                'intent': intent_conf,
                'focus': focus_conf
            })
            
            result = ClassificationResult(
                subject=subject,
                subject_confidence=subject_conf,
                intent=intent,
                intent_confidence=intent_conf,
                difficulty=difficulty,
                difficulty_confidence=difficulty_conf,
                focus_area=focus_area,
                focus_keywords=focus_keywords,
                focus_confidence=focus_conf,
                language=language,
                overall_confidence=overall_conf
            )
            
            logger.info(
                f"Classified query: {subject.value}/{intent.value} "
                f"(confidence: {overall_conf:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Return safe default
            return self._default_classification()
    
    def _detect_subject(self, query: str) -> Tuple[Subject, float]:
        """
        Detect subject using keyword matching.
        
        Args:
            query: Normalized query text
            
        Returns:
            Tuple of (subject, confidence)
        """
        # Count keyword matches for each subject
        # Use word boundaries to avoid partial matches
        import re
        
        matches = {}
        total_matches = 0
        
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            count = 0
            for keyword in keywords:
                # Use word boundary matching for better precision
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query):
                    count += 1
            matches[subject] = count
            total_matches += count
        
        # Find subject with most matches
        if total_matches == 0:
            return Subject.GENERAL, 0.5
        
        best_subject = max(matches, key=matches.get)
        best_count = matches[best_subject]
        
        if best_count == 0:
            return Subject.GENERAL, 0.5
        
        # Improved confidence calculation:
        # Base: best_count / total_matches (what fraction is this subject)
        # Boost if best_count is significantly higher than second best
        sorted_counts = sorted(matches.values(), reverse=True)
        second_best = sorted_counts[1] if len(sorted_counts) > 1 else 0
        
        # Base confidence from match ratio
        base_confidence = best_count / (total_matches + 1)
        
        # Boost if dominant (best >> second best)
        dominance = (best_count - second_best) / max(1, best_count)
        dominance_boost = dominance * 0.3  # Up to 0.3 boost for clear dominance
        
        # Boost if multiple keywords matched (more signal)
        match_boost = min(0.2, best_count * 0.05)  # Up to 0.2 boost
        
        confidence = min(0.95, base_confidence + dominance_boost + match_boost)
        
        # If confidence too low, return general
        if confidence < 0.3:
            return Subject.GENERAL, confidence
        
        return best_subject, confidence
    
    def _detect_intent(self, query: str) -> Tuple[Intent, float]:
        """
        Detect intent using pattern matching.
        
        Args:
            query: Normalized query text
            
        Returns:
            Tuple of (intent, confidence)
        """
        # Check patterns in priority order
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    # Pattern matched
                    confidence = 0.90  # Pattern matching is reliable
                    return intent, confidence
        
        # No pattern matched - default to teach (most common)
        return Intent.TEACH, 0.6
    
    def _infer_difficulty(
        self,
        query: str,
        user_profile: UserProfile
    ) -> Tuple[Difficulty, float]:
        """
        Infer difficulty level.
        
        Args:
            query: Normalized query text
            user_profile: User profile for personalization
            
        Returns:
            Tuple of (difficulty, confidence)
        """
        score = 0.5  # Start neutral
        
        # Explicit mentions
        if any(word in query for word in ["hard", "difficult", "challenging", "advanced", "complex"]):
            score = 0.8
        elif any(word in query for word in ["easy", "simple", "basic", "fundamental", "beginner"]):
            score = 0.2
        
        # Adjust by learning level
        level = user_profile.learning_level
        if isinstance(level, str):
            level = LearningLevel(level)
        
        if level == LearningLevel.BEGINNER:
            score -= 0.15
        elif level == LearningLevel.ADVANCED:
            score += 0.15
        
        # Adjust by recent performance
        accuracy = user_profile.recent_accuracy
        if accuracy > 0.85:  # Doing well
            score += 0.1
        elif accuracy < 0.60:  # Struggling
            score -= 0.1
        
        # Clamp to valid range
        score = max(0.2, min(0.8, score))
        
        # Convert to category
        if score < 0.35:
            difficulty = Difficulty.EASY
            confidence = (0.35 - score) / 0.35  # Distance from boundary
        elif score < 0.65:
            difficulty = Difficulty.MEDIUM
            # Confidence = distance from both boundaries
            confidence = 1.0 - (abs(0.5 - score) / 0.15)
        else:
            difficulty = Difficulty.HARD
            confidence = (score - 0.65) / 0.35
        
        # Ensure confidence is reasonable
        confidence = max(0.6, min(0.95, confidence))
        
        return difficulty, confidence
    
    def _extract_focus_area(
        self,
        query: str,
        subject: Subject
    ) -> Tuple[Optional[str], List[str], float]:
        """
        Extract focus area and keywords.
        
        Args:
            query: Normalized query text
            subject: Detected subject
            
        Returns:
            Tuple of (focus_area, focus_keywords, confidence)
        """
        if subject not in self.TOPIC_MAPPINGS:
            return None, [], 0.0
        
        topics = self.TOPIC_MAPPINGS[subject]
        
        # Find ALL matching topics (not just best)
        topic_matches = {}
        for topic, keywords in topics.items():
            matched_keywords = [kw for kw in keywords if kw in query]
            if len(matched_keywords) > 0:
                topic_matches[topic] = matched_keywords
        
        if not topic_matches:
            return None, [], 0.0
        
        # Pick topic with most keyword matches
        best_topic = max(topic_matches, key=lambda t: len(topic_matches[t]))
        best_keywords = topic_matches[best_topic]
        best_match_count = len(best_keywords)
        
        # Improved confidence calculation:
        # Not just ratio of keywords matched, but also:
        # - How many keywords matched (absolute)
        # - How dominant this topic is vs others
        
        total_keywords_in_topic = len(topics[best_topic])
        
        # Base confidence from match ratio
        base_confidence = best_match_count / max(1, total_keywords_in_topic)
        
        # Boost for multiple keyword matches (strong signal)
        match_boost = min(0.4, best_match_count * 0.15)
        
        # Boost if this topic dominates (no other close topics)
        second_best_count = 0
        if len(topic_matches) > 1:
            sorted_counts = sorted([len(kws) for kws in topic_matches.values()], reverse=True)
            second_best_count = sorted_counts[1] if len(sorted_counts) > 1 else 0
        
        dominance = (best_match_count - second_best_count) / max(1, best_match_count)
        dominance_boost = dominance * 0.2
        
        confidence = min(0.95, base_confidence + match_boost + dominance_boost)
        
        return best_topic, best_keywords, confidence
    
    def _detect_language(
        self,
        user_profile: UserProfile,
        query: str
    ) -> str:
        """
        Detect query language.
        
        Args:
            user_profile: User profile
            query: Original query text
            
        Returns:
            Language code (english, hindi, tamil, etc.)
        """
        # Use profile preference if available
        if user_profile.language_preference:
            return user_profile.language_preference
        
        # Simple detection: check for non-ASCII characters
        if any(ord(char) > 127 for char in query):
            # Non-ASCII detected, could be regional language
            # Default to hindi (most common)
            return "hindi"
        
        return "english"
    
    def _aggregate_confidence(self, scores: Dict[str, float]) -> float:
        """
        Aggregate component confidences.
        
        Args:
            scores: Dict of component scores
            
        Returns:
            Overall confidence score
        """
        # Weighted average
        overall = (
            scores.get('subject', 0.5) * 0.3 +   # Subject is 30% important
            scores.get('intent', 0.5) * 0.3 +     # Intent is 30% important
            scores.get('focus', 0.5) * 0.4        # Focus is 40% important
        )
        
        return round(overall, 3)
    
    def _default_classification(self) -> ClassificationResult:
        """Return safe default classification."""
        return ClassificationResult(
            subject=Subject.GENERAL,
            subject_confidence=0.5,
            intent=Intent.TEACH,
            intent_confidence=0.5,
            difficulty=Difficulty.MEDIUM,
            difficulty_confidence=0.5,
            language="english",
            overall_confidence=0.5
        )
