"""
Agent Implementations for Tier-2 Orchestration
==============================================

Concrete implementations of all agents that work with Tier-2 orchestrator.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import logging
from typing import Dict, Any, List
import json

from .tier2_orchestrator import BaseAgent, AgentContext
from ..routing.tier0_classifier import Subject, Difficulty

logger = logging.getLogger(__name__)


class TeacherAgent(BaseAgent):
    """
    Teacher Agent - Explains concepts using C-RAG (Corrective RAG).
    
    Strategy:
    - Uses retrieved documents as authoritative sources
    - Generates detailed explanations at appropriate level
    - Provides learning objectives and related topics
    - High confidence when retrieval quality is high
    """
    
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute teaching strategy with retrieved documents.
        
        Args:
            context: AgentContext with classification and documents
            
        Returns:
            Dictionary with explanation and metadata
        """
        logger.info(f"TeacherAgent executing for: {context.query}")
        
        # Extract relevant content
        content = self._extract_relevant_content(
            context.retrieved_documents,
            top_k=3
        )
        
        # Build teaching prompt
        if content:
            # C-RAG mode - use retrieved sources
            prompt = f"""You are an expert tutor explaining {context.classification.subject.value} to a {context.learning_level} level student.

Focus Area: {context.classification.focus_area or 'general concept'}

Use the following authoritative sources to explain the concept:

{content}

Student's Question: {context.query}

Instructions:
1. Provide a clear, detailed explanation using the sources
2. Use simple language appropriate for {context.learning_level} level
3. Include examples where relevant
4. Cite which source you're using (Source 1, Source 2, etc.)
5. Respond in {context.language}

Explanation:"""
        else:
            # Fallback mode - zero-shot
            prompt = f"""You are an expert tutor explaining {context.classification.subject.value} to a {context.learning_level} level student.

Student's Question: {context.query}

Instructions:
1. Provide a clear, detailed explanation from your knowledge
2. Use simple language appropriate for {context.learning_level} level
3. Include examples where relevant
4. Respond in {context.language}
5. Note: You're working from base knowledge (no specific sources available)

Explanation:"""
        
        # Get explanation from LLM
        response = self.llm.invoke(prompt)
        explanation_text = response.content if hasattr(response, 'content') else str(response)
        
        # Extract learning objectives
        learning_objectives = self._extract_learning_objectives(
            context.classification.focus_area,
            context.classification.subject
        )
        
        # Suggest related topics
        related_topics = self._suggest_related_topics(
            context.classification.focus_area,
            context.classification.subject
        )
        
        return {
            'text': explanation_text.strip(),
            'learning_objectives': learning_objectives,
            'related_topics': related_topics,
            'difficulty_feedback': f"Explained at {context.learning_level} level",
            'next_steps': [
                'Practice problems on this topic',
                'Review related concepts',
                'Ask follow-up questions if needed'
            ]
        }
    
    def _extract_learning_objectives(
        self,
        focus_area: str,
        subject: Subject
    ) -> List[str]:
        """Extract learning objectives for the topic."""
        # Simplified - in production, this could use LLM or knowledge base
        objectives_map = {
            'newtons_second_law': [
                'Understand the relationship F = ma',
                'Apply Newton\'s Second Law to problems',
                'Calculate force, mass, or acceleration'
            ],
            'organic_reactions': [
                'Identify reaction mechanisms',
                'Predict reaction products',
                'Understand reaction conditions'
            ],
            'photosynthesis': [
                'Understand light and dark reactions',
                'Explain the role of chlorophyll',
                'Describe energy conversion in plants'
            ]
        }
        
        return objectives_map.get(focus_area, [
            f'Understand {focus_area}',
            f'Apply {focus_area} concepts',
            f'Solve problems related to {focus_area}'
        ])
    
    def _suggest_related_topics(
        self,
        focus_area: str,
        subject: Subject
    ) -> List[str]:
        """Suggest related topics for further study."""
        related_map = {
            'newtons_second_law': [
                'Newton\'s First Law',
                'Newton\'s Third Law',
                'Forces and Motion'
            ],
            'organic_reactions': [
                'Reaction Mechanisms',
                'Functional Groups',
                'Stereochemistry'
            ],
            'photosynthesis': [
                'Cellular Respiration',
                'Plant Structure',
                'Energy Flow in Ecosystems'
            ]
        }
        
        return related_map.get(focus_area, [])


class TrainerAgent(BaseAgent):
    """
    Trainer Agent - Generates practice questions using few-shot learning.
    
    Strategy:
    - Uses retrieved questions as examples
    - Analyzes structure and format
    - Generates new, similar questions
    - Ensures appropriate difficulty level
    """
    
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute training strategy with example questions.
        
        Args:
            context: AgentContext with classification and examples
            
        Returns:
            Dictionary with generated question
        """
        logger.info(f"TrainerAgent executing for: {context.query}")
        
        # Extract example questions
        examples = self._extract_relevant_content(
            context.retrieved_documents,
            top_k=5
        )
        
        difficulty = context.classification.difficulty.value if context.classification.difficulty else 'medium'
        
        if examples:
            # Few-shot mode - use examples
            prompt = f"""You are an expert question generator for {context.classification.subject.value}.

Here are example questions from the question bank:

{examples}

Now, generate a NEW, UNIQUE multiple-choice question about: {context.classification.focus_area or context.query}

Requirements:
1. Difficulty: {difficulty}
2. Format: 4 options (A, B, C, D)
3. Similar style to examples above
4. Must be different from all examples
5. Include explanation for correct answer
6. Respond in {context.language}

Generate the question in JSON format:
{{
    "question": "Your question here",
    "options": {{
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
    }},
    "correct_answer": "A",
    "explanation": "Why this is correct"
}}

JSON:"""
        else:
            # Zero-shot mode
            prompt = f"""You are an expert question generator for {context.classification.subject.value}.

Generate a multiple-choice question about: {context.query}

Requirements:
1. Difficulty: {difficulty}
2. Format: 4 options (A, B, C, D)
3. Test conceptual understanding
4. Include explanation for correct answer
5. Respond in {context.language}

Generate the question in JSON format:
{{
    "question": "Your question here",
    "options": {{
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
    }},
    "correct_answer": "A",
    "explanation": "Why this is correct"
}}

JSON:"""
        
        # Get question from LLM
        response = self.llm.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                question_data = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
            
            return {
                'text': question_data.get('question', ''),
                'options': question_data.get('options', {}),
                'correct_answer': question_data.get('correct_answer', 'A'),
                'explanation': question_data.get('explanation', ''),
                'learning_objectives': [
                    f'Test understanding of {context.classification.focus_area}',
                    f'Apply {context.classification.subject.value} concepts'
                ],
                'related_topics': [],
                'difficulty_feedback': f'Question at {difficulty} level',
                'next_steps': [
                    'Attempt the question',
                    'Review explanation if incorrect',
                    'Try more practice questions'
                ]
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse question JSON: {e}")
            # Fallback: return response as-is
            return {
                'text': response_text.strip(),
                'options': {},
                'correct_answer': '',
                'explanation': '',
                'learning_objectives': [],
                'related_topics': [],
                'difficulty_feedback': '',
                'next_steps': []
            }


class DoubtSolverAgent(BaseAgent):
    """
    Doubt Solver Agent - Solves problems using zero-shot reasoning.
    
    Strategy:
    - Direct problem-solving approach
    - Step-by-step reasoning
    - No retrieval needed (uses LLM reasoning)
    - Clear explanations for each step
    """
    
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute doubt-solving strategy.
        
        Args:
            context: AgentContext with student's doubt/problem
            
        Returns:
            Dictionary with solution and explanation
        """
        logger.info(f"DoubtSolverAgent executing for: {context.query}")
        
        prompt = f"""You are an expert tutor solving a student's doubt in {context.classification.subject.value}.

Student's Question/Problem: {context.query}

Instructions:
1. Understand the problem or doubt
2. Provide a step-by-step solution
3. Explain the reasoning for each step
4. Use simple language for {context.learning_level} level
5. Respond in {context.language}

Solution:"""
        
        # Get solution from LLM
        response = self.llm.invoke(prompt)
        solution_text = response.content if hasattr(response, 'content') else str(response)
        
        return {
            'text': solution_text.strip(),
            'learning_objectives': [
                'Understand the problem-solving approach',
                'Apply similar methods to related problems'
            ],
            'related_topics': [],
            'difficulty_feedback': 'Step-by-step solution provided',
            'next_steps': [
                'Try solving similar problems',
                'Review the steps if unclear',
                'Ask follow-up questions'
            ]
        }


class MentorAgent(BaseAgent):
    """
    Mentor Agent - Provides guidance using two-stage C-RAG.
    
    Strategy:
    - Retrieves guidance from mentor documents
    - Validates across multiple sources
    - Synthesizes personalized advice
    - Focuses on study strategies and motivation
    """
    
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute mentoring strategy.
        
        Args:
            context: AgentContext with student's guidance request
            
        Returns:
            Dictionary with guidance and advice
        """
        logger.info(f"MentorAgent executing for: {context.query}")
        
        # Extract guidance content
        content = self._extract_relevant_content(
            context.retrieved_documents,
            top_k=3
        )
        
        if content:
            # C-RAG mode
            prompt = f"""You are an experienced NEET exam mentor providing guidance to a {context.learning_level} level student.

Here is guidance from expert sources:

{content}

Student's Question: {context.query}

Instructions:
1. Use the guidance sources to provide personalized advice
2. Be encouraging and motivational
3. Provide practical, actionable steps
4. Consider student's level: {context.learning_level}
5. Respond in {context.language}

Guidance:"""
        else:
            # Zero-shot mode
            prompt = f"""You are an experienced NEET exam mentor providing guidance to a {context.learning_level} level student.

Student's Question: {context.query}

Instructions:
1. Provide personalized, encouraging advice
2. Be practical and actionable
3. Consider student's level: {context.learning_level}
4. Respond in {context.language}

Guidance:"""
        
        # Get guidance from LLM
        response = self.llm.invoke(prompt)
        guidance_text = response.content if hasattr(response, 'content') else str(response)
        
        return {
            'text': guidance_text.strip(),
            'learning_objectives': [
                'Develop effective study strategies',
                'Build confidence and motivation',
                'Plan preparation effectively'
            ],
            'related_topics': [
                'Time Management',
                'Exam Strategy',
                'Stress Management'
            ],
            'difficulty_feedback': 'Personalized guidance provided',
            'next_steps': [
                'Implement the suggested strategies',
                'Track your progress',
                'Reach out for more guidance as needed'
            ]
        }


class GeneralAgent(BaseAgent):
    """
    General Agent - Handles general conversation.
    
    Strategy:
    - Simple conversational responses
    - No retrieval needed
    - Friendly and helpful tone
    - Redirects to learning when appropriate
    """
    
    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """
        Execute general conversation.
        
        Args:
            context: AgentContext with user message
            
        Returns:
            Dictionary with conversational response
        """
        logger.info(f"GeneralAgent executing for: {context.query}")
        
        prompt = f"""You are APXMIND, a friendly AI tutor for NEET exam preparation.

Student says: {context.query}

Instructions:
1. Respond naturally and helpfully
2. Be encouraging and supportive
3. If relevant, guide them toward learning
4. Keep response concise
5. Respond in {context.language}

Response:"""
        
        # Get response from LLM
        response = self.llm.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        return {
            'text': response_text.strip(),
            'learning_objectives': [],
            'related_topics': [],
            'difficulty_feedback': '',
            'next_steps': [
                'Ask me to explain a concept',
                'Request practice questions',
                'Get study guidance'
            ]
        }
