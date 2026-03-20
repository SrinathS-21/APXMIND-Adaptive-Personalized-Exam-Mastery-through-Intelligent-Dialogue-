"""
Tier-2 Agent Selection & Orchestration System
==============================================

Intelligent agent selection and orchestration using Tier-0 classification
and Tier-1 retrieval results.

This is the third layer of the hierarchical routing system that:
1. Selects appropriate agent based on intent classification
2. Builds comprehensive context for agent execution
3. Validates context sufficiency
4. Handles fallback strategies when context is insufficient
5. Orchestrates agent execution
6. Formats responses with rich metadata

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .tier0_classifier import ClassificationResult, Intent
from .tier1_retriever import Tier1Result, RetrievedDocument

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Available agent types."""
    TEACHER = "teacher"
    TRAINER = "trainer"
    DOUBT_SOLVER = "doubt_solver"
    MENTOR = "mentor"
    GENERAL = "general"


class RetrievalMethod(str, Enum):
    """Method used for response generation."""
    CRAG = "C-RAG"  # Corrective RAG (with retrieval)
    FEW_SHOT = "few-shot"  # Few-shot learning
    ZERO_SHOT = "zero-shot"  # No retrieval
    FALLBACK = "fallback"  # Fallback mode


@dataclass
class AgentContext:
    """Complete context for agent execution."""
    # Essential
    query: str
    classification: ClassificationResult
    user_id: str
    learning_level: str
    language: str
    
    # Retrieved information
    retrieved_documents: List[RetrievedDocument]
    retrieval_quality: float
    retrieval_stage: int
    
    # Additional context
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    user_accuracy: float = 0.5
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query': self.query,
            'classification': self.classification.to_dict(),
            'user_id': self.user_id,
            'learning_level': self.learning_level,
            'language': self.language,
            'retrieved_documents': [doc.to_dict() for doc in self.retrieved_documents],
            'retrieval_quality': self.retrieval_quality,
            'retrieval_stage': self.retrieval_stage,
            'conversation_history': self.conversation_history,
            'user_accuracy': self.user_accuracy,
            'preferences': self.preferences
        }


@dataclass
class AgentResponse:
    """Standardized agent response."""
    success: bool
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    enrichment: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'content': self.content,
            'metadata': self.metadata,
            'enrichment': self.enrichment,
            'performance': self.performance
        }


class Tier2Orchestrator:
    """
    Tier-2 Agent Selection & Orchestration System.
    
    Routes classified queries with retrieved documents to appropriate agents:
    - Selects agent based on intent
    - Builds comprehensive context
    - Validates context sufficiency
    - Handles fallbacks gracefully
    - Orchestrates agent execution
    - Formats rich responses
    
    Usage:
        orchestrator = Tier2Orchestrator(agents={
            AgentType.TEACHER: teacher_agent,
            AgentType.TRAINER: trainer_agent,
            AgentType.DOUBT_SOLVER: doubt_agent,
            AgentType.MENTOR: mentor_agent,
            AgentType.GENERAL: general_agent
        })
        
        response = await orchestrator.execute_agent(
            classification=tier0_result,
            retrieved_docs=tier1_result,
            query=user_query,
            user_profile=profile
        )
        
        print(f"Agent: {response.metadata['agent_used']}")
        print(f"Response: {response.content['text']}")
    """
    
    # Intent to Agent mapping
    AGENT_MAP = {
        Intent.TEACH: AgentType.TEACHER,
        Intent.TRAIN: AgentType.TRAINER,
        Intent.DOUBT: AgentType.DOUBT_SOLVER,
        Intent.MENTOR: AgentType.MENTOR,
        Intent.GENERAL: AgentType.GENERAL
    }
    
    # Context validation thresholds (minimum relevant docs needed)
    VALIDATION_THRESHOLDS = {
        AgentType.TEACHER: 1,  # Need at least 1 explanation
        AgentType.TRAINER: 3,  # Need at least 3 practice examples
        AgentType.MENTOR: 2,   # Need at least 2 guidance sources
        AgentType.DOUBT_SOLVER: 0,  # Zero-shot reasoning
        AgentType.GENERAL: 0   # No retrieval needed
    }
    
    # Confidence scores by retrieval method
    CONFIDENCE_SCORES = {
        (RetrievalMethod.CRAG, 0, 0.85): 0.94,  # Stage 1, high quality
        (RetrievalMethod.CRAG, 1, 0.70): 0.87,  # Stage 2, good quality
        (RetrievalMethod.FEW_SHOT, 0, 0.80): 0.90,  # Few-shot with examples
        (RetrievalMethod.ZERO_SHOT, None, None): 0.75,  # No retrieval
        (RetrievalMethod.FALLBACK, None, None): 0.70   # Fallback mode
    }
    
    def __init__(
        self,
        agents: Dict[AgentType, Any],
        tier1_retriever: Optional[Any] = None
    ):
        """
        Initialize Tier-2 orchestrator.
        
        Args:
            agents: Dictionary mapping AgentType to agent instances
            tier1_retriever: Optional Tier1Retriever for corrective retrieval
        """
        self.agents = agents
        self.tier1_retriever = tier1_retriever
        
        # Validate all required agents are present
        required_agents = [
            AgentType.TEACHER,
            AgentType.TRAINER,
            AgentType.DOUBT_SOLVER,
            AgentType.MENTOR,
            AgentType.GENERAL
        ]
        
        missing = [agent for agent in required_agents if agent not in agents]
        if missing:
            logger.warning(f"Missing agents: {missing}")
        
        logger.info(f"Initialized Tier2Orchestrator with {len(agents)} agents")
    
    async def execute_agent(
        self,
        classification: ClassificationResult,
        retrieved_docs: Tier1Result,
        query: str,
        user_profile: Dict[str, Any]
    ) -> AgentResponse:
        """
        Execute appropriate agent with full orchestration.
        
        Args:
            classification: Tier-0 classification result
            retrieved_docs: Tier-1 retrieval result
            query: Original user query
            user_profile: User profile information
            
        Returns:
            AgentResponse with content, metadata, enrichment, performance
        """
        start_time = time.time()
        
        try:
            # Step 1: Agent selection
            agent_type = self._select_agent(classification)
            
            logger.info(
                f"Selected agent: {agent_type.value} "
                f"(intent: {classification.intent.value})"
            )
            
            # Step 2: Context building
            context = self._build_context(
                classification=classification,
                retrieved_docs=retrieved_docs,
                query=query,
                user_profile=user_profile
            )
            
            # Step 3: Context validation
            is_valid, validation_msg = self._validate_context(agent_type, context)
            
            logger.info(
                f"Context validation: {is_valid} - {validation_msg}"
            )
            
            # Step 4: Fallback handling
            retrieval_method = RetrievalMethod.CRAG
            
            if not is_valid:
                context, retrieval_method = await self._handle_fallback(
                    agent_type=agent_type,
                    context=context,
                    classification=classification,
                    query=query
                )
            
            # Step 5: Agent execution
            agent = self.agents.get(agent_type)
            
            if not agent:
                logger.error(f"Agent {agent_type.value} not found!")
                return self._error_response(
                    f"Agent {agent_type.value} not available"
                )
            
            # Execute agent
            agent_result = await agent.execute(context)
            
            # Step 6: Response formatting
            response = self._format_response(
                agent_result=agent_result,
                context=context,
                agent_type=agent_type,
                retrieval_method=retrieval_method,
                start_time=start_time
            )
            
            logger.info(
                f"Agent execution complete: {agent_type.value}, "
                f"confidence: {response.metadata.get('confidence_score', 0):.2f}, "
                f"latency: {response.performance.get('total_latency_ms', 0):.0f}ms"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            return self._error_response(str(e))
    
    def _select_agent(self, classification: ClassificationResult) -> AgentType:
        """
        Select appropriate agent based on intent.
        
        Args:
            classification: Tier-0 classification result
            
        Returns:
            AgentType for the selected agent
        """
        agent_type = self.AGENT_MAP.get(
            classification.intent,
            AgentType.GENERAL  # Default fallback
        )
        
        return agent_type
    
    def _build_context(
        self,
        classification: ClassificationResult,
        retrieved_docs: Tier1Result,
        query: str,
        user_profile: Dict[str, Any]
    ) -> AgentContext:
        """
        Build comprehensive context for agent execution.
        
        Args:
            classification: Tier-0 classification result
            retrieved_docs: Tier-1 retrieval result
            query: Original query
            user_profile: User profile data
            
        Returns:
            AgentContext with all necessary information
        """
        context = AgentContext(
            query=query,
            classification=classification,
            user_id=user_profile.get('user_id', 'anonymous'),
            learning_level=user_profile.get('learning_level', 'intermediate'),
            language=classification.language,
            retrieved_documents=retrieved_docs.retrieved_documents,
            retrieval_quality=retrieved_docs.retrieval_quality,
            retrieval_stage=retrieved_docs.retrieval_stage.value,
            conversation_history=user_profile.get('conversation_history', []),
            user_accuracy=user_profile.get('recent_accuracy', 0.5),
            preferences=user_profile.get('preferences', {})
        )
        
        return context
    
    def _validate_context(
        self,
        agent_type: AgentType,
        context: AgentContext
    ) -> Tuple[bool, str]:
        """
        Validate if context is sufficient for agent execution.
        
        Args:
            agent_type: Type of agent to validate for
            context: Agent context to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        # Get relevant documents (high relevance only)
        relevant_docs = [
            doc for doc in context.retrieved_documents
            if doc.is_relevant and doc.relevance_score > 0.7
        ]
        
        # Get threshold for this agent
        required_count = self.VALIDATION_THRESHOLDS.get(agent_type, 0)
        
        # Check if threshold met
        if len(relevant_docs) >= required_count:
            return True, f"Context valid: {len(relevant_docs)}/{required_count} docs"
        else:
            return False, f"Insufficient context: {len(relevant_docs)}/{required_count} docs"
    
    async def _handle_fallback(
        self,
        agent_type: AgentType,
        context: AgentContext,
        classification: ClassificationResult,
        query: str
    ) -> Tuple[AgentContext, RetrievalMethod]:
        """
        Handle fallback strategy when context is insufficient.
        
        Args:
            agent_type: Type of agent
            context: Current context
            classification: Classification result
            query: Original query
            
        Returns:
            Tuple of (updated_context, retrieval_method)
        """
        logger.warning(
            f"Context insufficient for {agent_type.value}, applying fallback"
        )
        
        # Level 1: Try corrective retrieval for TRAINER
        if agent_type == AgentType.TRAINER and self.tier1_retriever:
            logger.info("Attempting Stage 2 corrective retrieval for trainer...")
            
            try:
                # Force Stage 2 retrieval
                corrective_result = await self.tier1_retriever.retrieve(
                    classification=classification,
                    query=query,
                    use_corrective=True
                )
                
                # Check if we now have enough docs
                relevant_docs = [
                    doc for doc in corrective_result.retrieved_documents
                    if doc.is_relevant and doc.relevance_score > 0.7
                ]
                
                if len(relevant_docs) >= 3:
                    logger.info(
                        f"Corrective retrieval successful: {len(relevant_docs)} docs"
                    )
                    # Update context with new documents
                    context.retrieved_documents = corrective_result.retrieved_documents
                    context.retrieval_quality = corrective_result.retrieval_quality
                    context.retrieval_stage = corrective_result.retrieval_stage.value
                    
                    return context, RetrievalMethod.CRAG
                else:
                    logger.warning("Corrective retrieval still insufficient")
            
            except Exception as e:
                logger.error(f"Corrective retrieval failed: {e}")
        
        # Level 2: Fallback to zero-shot LLM
        logger.info(f"Using zero-shot fallback for {agent_type.value}")
        
        # Clear retrieved documents (agent will use LLM base knowledge)
        context.retrieved_documents = []
        context.retrieval_quality = 0.0
        
        return context, RetrievalMethod.ZERO_SHOT
    
    def _format_response(
        self,
        agent_result: Dict[str, Any],
        context: AgentContext,
        agent_type: AgentType,
        retrieval_method: RetrievalMethod,
        start_time: float
    ) -> AgentResponse:
        """
        Format agent result into standardized response.
        
        Args:
            agent_result: Raw agent execution result
            context: Agent context used
            agent_type: Type of agent that executed
            retrieval_method: Method used for generation
            start_time: Execution start time
            
        Returns:
            Formatted AgentResponse
        """
        # Calculate total latency
        total_latency = (time.time() - start_time) * 1000
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            retrieval_method=retrieval_method,
            retrieval_stage=context.retrieval_stage,
            retrieval_quality=context.retrieval_quality
        )
        
        # Extract retrieval sources
        retrieval_sources = [
            doc.id for doc in context.retrieved_documents
            if doc.is_relevant
        ]
        
        # Build metadata
        metadata = {
            'agent_used': agent_type.value,
            'confidence_score': confidence,
            'retrieval_method': retrieval_method.value,
            'retrieval_stage': context.retrieval_stage,
            'retrieval_sources': retrieval_sources[:5],  # Top 5 sources
            'retrieval_quality': context.retrieval_quality,
            'subject': context.classification.subject.value,
            'intent': context.classification.intent.value,
            'difficulty': context.classification.difficulty.value if context.classification.difficulty else None,
            'focus_area': context.classification.focus_area
        }
        
        # Extract content from agent result
        content = {
            'text': agent_result.get('text', ''),
            'language': context.language
        }
        
        # Add additional content fields if present
        if 'options' in agent_result:  # For MCQs
            content['options'] = agent_result['options']
        if 'correct_answer' in agent_result:
            content['correct_answer'] = agent_result['correct_answer']
        if 'explanation' in agent_result:
            content['explanation'] = agent_result['explanation']
        
        # Build enrichment
        enrichment = {
            'learning_objectives': agent_result.get('learning_objectives', []),
            'related_topics': agent_result.get('related_topics', []),
            'difficulty_feedback': agent_result.get('difficulty_feedback', ''),
            'next_steps': agent_result.get('next_steps', [])
        }
        
        # Build performance metrics
        performance = {
            'total_latency_ms': round(total_latency, 2),
            'tier0_latency_ms': agent_result.get('tier0_latency_ms', 0),
            'tier1_latency_ms': agent_result.get('tier1_latency_ms', 0),
            'tier2_latency_ms': agent_result.get('tier2_latency_ms', 0),
            'agent_execution_ms': agent_result.get('execution_time_ms', 0)
        }
        
        return AgentResponse(
            success=True,
            content=content,
            metadata=metadata,
            enrichment=enrichment,
            performance=performance
        )
    
    def _calculate_confidence(
        self,
        retrieval_method: RetrievalMethod,
        retrieval_stage: Optional[int],
        retrieval_quality: float
    ) -> float:
        """
        Calculate confidence score based on retrieval method and quality.
        
        Args:
            retrieval_method: Method used for generation
            retrieval_stage: Retrieval stage (0=initial, 1=corrective)
            retrieval_quality: Quality score from retrieval
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Zero-shot and fallback have fixed scores
        if retrieval_method == RetrievalMethod.ZERO_SHOT:
            return 0.75
        elif retrieval_method == RetrievalMethod.FALLBACK:
            return 0.70
        
        # C-RAG confidence based on stage and quality
        if retrieval_method == RetrievalMethod.CRAG:
            if retrieval_stage == 0 and retrieval_quality >= 0.85:
                return 0.94
            elif retrieval_stage == 1 and retrieval_quality >= 0.70:
                return 0.87
            elif retrieval_quality >= 0.60:
                return 0.80
            else:
                return 0.75
        
        # Few-shot confidence
        if retrieval_method == RetrievalMethod.FEW_SHOT:
            if retrieval_quality >= 0.80:
                return 0.90
            else:
                return 0.85
        
        # Default
        return 0.75
    
    def _error_response(self, error_message: str) -> AgentResponse:
        """
        Create error response for graceful failure.
        
        Args:
            error_message: Error description
            
        Returns:
            AgentResponse with error information
        """
        return AgentResponse(
            success=False,
            content={
                'text': (
                    "I apologize, but I'm having trouble processing your request. "
                    "Could you please try rephrasing your question?"
                ),
                'language': 'english'
            },
            metadata={
                'agent_used': 'error_handler',
                'confidence_score': 0.0,
                'retrieval_method': 'none',
                'retrieval_stage': None,
                'error': error_message
            },
            enrichment={
                'learning_objectives': [],
                'related_topics': [],
                'difficulty_feedback': '',
                'next_steps': ['Try rephrasing your question', 'Ask about a specific topic']
            },
            performance={
                'total_latency_ms': 0.0
            }
        )


class BaseAgent:
    """
    Base class for all agents.
    
    Provides common functionality and interface that all agents must implement.
    """
    
    def __init__(self, llm=None):
        """
        Initialize base agent.
        
        Args:
            llm: Language model instance
        """
        from ..llm.llm import get_llm
        self.llm = llm or get_llm()
    
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute agent with given context.
        
        Args:
            context: AgentContext with all necessary information
            
        Returns:
            Dictionary with agent response
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    async def execute_fallback(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute agent in fallback mode (zero-shot).
        
        Args:
            context: AgentContext (may have no retrieved documents)
            
        Returns:
            Dictionary with agent response
        """
        # Default: same as execute
        return await self.execute(context)
    
    def _extract_relevant_content(
        self,
        documents: List[RetrievedDocument],
        top_k: int = 3
    ) -> str:
        """
        Extract relevant content from documents.
        
        Args:
            documents: List of retrieved documents
            top_k: Number of top documents to use
            
        Returns:
            Formatted content string
        """
        relevant_docs = [
            doc for doc in documents
            if doc.is_relevant and doc.relevance_score > 0.7
        ][:top_k]
        
        if not relevant_docs:
            return ""
        
        content_parts = []
        for i, doc in enumerate(relevant_docs, 1):
            content_parts.append(
                f"Source {i} (Quality: {doc.quality_score:.2f}):\n{doc.content}\n"
            )
        
        return "\n".join(content_parts)
