"""
Flask-Compatible Agent Wrappers
================================

Simplified agent functions that work with Flask without Streamlit dependencies.
"""

import logging
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


def classify_intent(query: str, subject: Optional[str] = None) -> Dict[str, Any]:
    """
    Classify user query intent (Tier-0 routing).
    
    Args:
        query: User's question
        subject: Optional subject hint
    
    Returns:
        Dict with intent classification and confidence
    """
    try:
        from ..llm.llm import get_llm
        llm = get_llm()
        
        system_prompt = """You are an expert at classifying student queries. Analyze the query and respond with:
1. 'simple' - Direct factual questions that can be answered with retrieval
2. 'retrieval' - Questions needing context from documents
3. 'complex' - Multi-step reasoning, comparisons, or analysis questions
4. 'quiz' - Requests for practice questions or quizzes

Examples:
- "What is photosynthesis?" -> simple
- "Explain the Krebs cycle" -> retrieval  
- "Compare mitosis and meiosis" -> complex
- "Give me 5 questions on thermodynamics" -> quiz
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Classify this query: {query}\n\nRespond with only: simple, retrieval, complex, or quiz")
        ])
        
        chain = prompt | llm | StrOutputParser()
        intent = chain.invoke({"query": query}).strip().lower()
        
        # Detect subject if not provided
        if not subject:
            subject = detect_subject(query, llm)
        
        return {
            'intent': intent,
            'subject': subject,
            'confidence': 0.85,  # Placeholder
            'tier': 'tier0'
        }
        
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return {
            'intent': 'retrieval',  # Default to retrieval
            'subject': subject or 'biology',
            'confidence': 0.5,
            'tier': 'tier0',
            'error': str(e)
        }


def detect_subject(query: str, llm) -> str:
    """
    Detect subject from query.
    
    Args:
        query: User's question
        llm: LLM instance
    
    Returns:
        Subject name (biology, chemistry, or physics)
    """
    try:
        system_prompt = """You are an expert at identifying the subject of NEET questions.
Respond with ONLY: biology, chemistry, or physics

Examples:
- "What is photosynthesis?" -> biology
- "Explain atomic structure" -> chemistry
- "What is Newton's first law?" -> physics
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{query}")
        ])
        
        chain = prompt | llm | StrOutputParser()
        subject = chain.invoke({"query": query}).strip().lower()
        
        # Validate subject
        if subject not in ['biology', 'chemistry', 'physics']:
            subject = 'biology'  # Default
        
        return subject
        
    except Exception as e:
        logger.error(f"Subject detection failed: {e}")
        return 'biology'  # Default fallback


def retriever_agent(query: str, vectorstore, llm, subject: str) -> Dict[str, Any]:
    """
    Retrieval-based QA agent (Tier-1).
    
    Args:
        query: User's question
        vectorstore: Subject-specific vectorstore
        llm: LLM instance
        subject: Subject name
    
    Returns:
        Dict with answer, confidence, and sources
    """
    try:
        if not vectorstore:
            return {
                'answer': "I apologize, but I don't have access to the study materials right now.",
                'confidence': 0.0,
                'sources': [],
                'error': 'Vectorstore not available'
            }
        
        # Retrieve relevant documents
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        retrieved_docs = retriever.invoke(query)
        
        if not retrieved_docs:
            # Fallback: Direct LLM response
            fallback_template = """You are an expert NEET tutor specializing in {subject}.
Answer the question clearly and concisely for a NEET student.

Question: {question}

Answer:"""
            
            fallback_chain = PromptTemplate.from_template(fallback_template) | llm | StrOutputParser()
            answer = fallback_chain.invoke({"subject": subject, "question": query})
            
            return {
                'answer': answer,
                'confidence': 0.6,
                'sources': [],
                'method': 'fallback'
            }
        
        # Build context from retrieved documents
        context_str = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
        # Generate answer using RAG
        rag_template = """Answer the question based on the following context from NEET study materials.
Be clear, concise, and accurate. Use simple English suitable for students.

Context:
{context}

Question: {question}

Answer:"""
        
        rag_chain = PromptTemplate.from_template(rag_template) | llm | StrOutputParser()
        answer = rag_chain.invoke({"context": context_str, "question": query})
        
        # Extract source metadata
        sources = []
        for doc in retrieved_docs[:3]:  # Top 3 sources
            metadata = doc.metadata or {}
            sources.append({
                'title': metadata.get('title', 'Unknown'),
                'page': metadata.get('page', 0),
                'subject': metadata.get('subject', subject),
                'relevance': 0.85  # Placeholder
            })
        
        return {
            'answer': answer,
            'confidence': 0.9,
            'sources': sources,
            'method': 'rag',
            'documents_retrieved': len(retrieved_docs)
        }
        
    except Exception as e:
        logger.error(f"Retriever agent failed: {e}", exc_info=True)
        return {
            'answer': "I encountered an error while processing your question. Please try again.",
            'confidence': 0.0,
            'sources': [],
            'error': str(e)
        }


def orchestrator_agent(query: str, vectorstores: Dict[str, Any], llm, subject: str) -> Dict[str, Any]:
    """
    Advanced orchestration agent for complex queries (Tier-2).
    
    Args:
        query: User's question
        vectorstores: Dict of all vectorstores
        llm: LLM instance
        subject: Primary subject
    
    Returns:
        Dict with answer, reasoning, and sources
    """
    try:
        # For complex queries, we might need to:
        # 1. Break down the question
        # 2. Retrieve from multiple subjects
        # 3. Synthesize information
        
        # Step 1: Analyze query complexity
        analysis_template = """Analyze this NEET question and determine what information is needed.

Question: {query}

Provide:
1. Main topic
2. Sub-topics needed
3. Subjects involved (biology, chemistry, physics)

Response:"""
        
        analysis_chain = PromptTemplate.from_template(analysis_template) | llm | StrOutputParser()
        analysis = analysis_chain.invoke({"query": query})
        
        # Step 2: Retrieve from relevant subjects
        all_sources = []
        context_parts = []
        
        for subj, store in vectorstores.items():
            if store:
                try:
                    retriever = store.as_retriever(search_kwargs={"k": 2})
                    docs = retriever.invoke(query)
                    
                    if docs:
                        context_parts.append(f"=== From {subj.upper()} ===\n" + "\n".join([d.page_content for d in docs]))
                        
                        for doc in docs:
                            metadata = doc.metadata or {}
                            all_sources.append({
                                'title': metadata.get('title', 'Unknown'),
                                'subject': subj,
                                'relevance': 0.75
                            })
                except Exception as e:
                    logger.warning(f"Failed to retrieve from {subj}: {e}")
        
        # Step 3: Synthesize answer
        if context_parts:
            context_str = "\n\n".join(context_parts)
            
            synthesis_template = """You are an expert NEET tutor. Answer this complex question by synthesizing information from multiple sources.

Context from study materials:
{context}

Question: {query}

Provide a comprehensive answer that:
1. Directly answers the question
2. Explains key concepts
3. Shows connections between topics if relevant

Answer:"""
            
            synthesis_chain = PromptTemplate.from_template(synthesis_template) | llm | StrOutputParser()
            answer = synthesis_chain.invoke({"context": context_str, "query": query})
            
            return {
                'answer': answer,
                'confidence': 0.85,
                'sources': all_sources[:5],  # Top 5 sources
                'reasoning': analysis,
                'method': 'orchestration',
                'subjects_consulted': list(vectorstores.keys())
            }
        else:
            # Fallback to direct LLM
            fallback_template = """You are an expert NEET tutor. Answer this question comprehensively.

Question: {query}

Answer:"""
            
            fallback_chain = PromptTemplate.from_template(fallback_template) | llm | StrOutputParser()
            answer = fallback_chain.invoke({"query": query})
            
            return {
                'answer': answer,
                'confidence': 0.6,
                'sources': [],
                'reasoning': analysis,
                'method': 'fallback'
            }
        
    except Exception as e:
        logger.error(f"Orchestrator agent failed: {e}", exc_info=True)
        return {
            'answer': "I encountered an error while processing your complex question. Please try simplifying it or try again.",
            'confidence': 0.0,
            'sources': [],
            'error': str(e)
        }
