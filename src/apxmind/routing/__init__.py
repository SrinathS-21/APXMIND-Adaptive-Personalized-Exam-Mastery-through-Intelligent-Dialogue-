"""
Routing Package
===============

Hierarchical routing system for intelligent query handling.

Architecture:
- Tier-0: Query Classification (subject, intent, difficulty)
- Tier-1: Optimized Retrieval (filtered vector search)
- Tier-2: Agent Selection (route to appropriate agent)

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

from .tier0_classifier import (
    Tier0Classifier,
    ClassificationResult,
    UserProfile,
    Intent,
    Subject,
    Difficulty,
    LearningLevel
)

from .tier1_retriever import (
    Tier1Retriever,
    Tier1Result,
    RetrievedDocument,
    RetrievalStage
)

from .tier2_orchestrator import (
    Tier2Orchestrator,
    AgentType,
    AgentContext,
    AgentResponse,
    RetrievalMethod,
    BaseAgent
)

from .agents import (
    TeacherAgent,
    TrainerAgent,
    DoubtSolverAgent,
    MentorAgent,
    GeneralAgent
)

__all__ = [
    # Tier-0
    'Tier0Classifier',
    'ClassificationResult',
    'UserProfile',
    'Intent',
    'Subject',
    'Difficulty',
    'LearningLevel',
    # Tier-1
    'Tier1Retriever',
    'Tier1Result',
    'RetrievedDocument',
    'RetrievalStage',
    # Tier-2
    'Tier2Orchestrator',
    'AgentType',
    'AgentContext',
    'AgentResponse',
    'RetrievalMethod',
    'BaseAgent',
    # Agents
    'TeacherAgent',
    'TrainerAgent',
    'DoubtSolverAgent',
    'MentorAgent',
    'GeneralAgent',
]
