"""
Flask-Compatible Agent Wrappers
================================

Simplified agent functions that work with Flask without Streamlit dependencies.
"""

import logging
import re
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..core.language import language_name, normalize_language

logger = logging.getLogger(__name__)


def _first_sentences(text: str, max_sentences: int = 2) -> str:
    """Return up to max_sentences from text."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return text.strip()
    return " ".join(sentences[:max_sentences]).strip()


def _looks_already_structured(answer: str) -> bool:
    has_headings = bool(re.search(r"^\s{0,3}#{1,6}\s+", answer, flags=re.MULTILINE))
    labels = ["concept", "explanation", "example", "exam tip", "quick recap"]
    found = sum(1 for label in labels if label in answer.lower())
    return has_headings or found >= 2


def _is_system_or_error_answer(answer: str) -> bool:
    lower = answer.lower()
    markers = [
        "unable to process",
        "encountered an error",
        "please try again",
        "backend is currently unavailable",
        "could not reach the live ai model",
        "i can still help, but the ai model backend is currently unavailable",
    ]
    return any(marker in lower for marker in markers)


def _default_exam_tip(subject: str) -> str:
    tips = {
        "biology": "Focus on NCERT wording and classification terms. In NEET, options often differ by one key biological term.",
        "chemistry": "Write the core equation or trend first, then eliminate options that violate units, periodic trends, or reaction conditions.",
        "physics": "Start from the governing formula, check units at each step, and estimate the expected magnitude before finalizing the answer.",
    }
    return tips.get(
        (subject or "").lower(),
        "Underline the core concept in the question, then eliminate options that directly contradict the governing rule.",
    )


def _format_for_chat_display(answer: str, query: str, subject: str) -> str:
    """Normalize model output into stable markdown sections for chat UI."""
    text = (answer or "").replace("\r\n", "\n").strip()
    if not text or _is_system_or_error_answer(text) or _looks_already_structured(text):
        return text

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paragraphs:
        return text

    example_text = ""
    exam_tip_text = ""
    explanation_parts = []

    example_re = re.compile(
        r"^\s*(example|for example|for instance|consider|suppose|let's say)\s*[:\-]?\s*",
        re.IGNORECASE,
    )
    exam_tip_re = re.compile(
        r"^\s*(exam tip|neet tip|quick tip|remember|pitfall|mnemonic)\s*[:\-]?\s*",
        re.IGNORECASE,
    )

    for paragraph in paragraphs:
        if not exam_tip_text and exam_tip_re.search(paragraph):
            exam_tip_text = re.sub(
                r"^\s*(exam tip|neet tip|quick tip|remember|pitfall|mnemonic)\s*[:\-]?\s*",
                "",
                paragraph,
                flags=re.IGNORECASE,
            ).strip()
            continue

        if not example_text and example_re.search(paragraph):
            example_text = re.sub(
                r"^\s*(example|for example|for instance|consider|suppose|let's say)\s*[:\-]?\s*",
                "",
                paragraph,
                flags=re.IGNORECASE,
            ).strip()
            continue

        explanation_parts.append(paragraph)

    main_text = explanation_parts[0] if explanation_parts else paragraphs[0]
    concept_text = _first_sentences(main_text, max_sentences=2)

    if not explanation_parts:
        explanation_text = main_text
    else:
        explanation_text = "\n\n".join(explanation_parts)

    if not example_text:
        example_text = (
            f"Apply the same idea to this query: \"{query}\". "
            "Identify the governing concept first, then solve step by step."
        )

    if not exam_tip_text:
        exam_tip_text = _default_exam_tip(subject)

    return "\n\n".join([
        f"### Concept\n{concept_text}",
        f"### Explanation\n{explanation_text}",
        f"### Example\n{example_text}",
        f"### Exam Tip\n{exam_tip_text}",
    ]).strip()


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


def _build_excerpt_answer(query: str, retrieved_docs: list[Any], subject: str) -> str:
    """Build a deterministic fallback answer from retrieved context snippets."""
    if not retrieved_docs:
        return (
            f"I could not access the live AI model right now. "
            f"Please retry in a moment, or ask a more specific {subject} question."
        )

    snippets: list[str] = []
    for doc in retrieved_docs[:3]:
        content = (doc.page_content or "").strip().replace("\n", " ")
        if not content:
            continue
        snippets.append(content[:260] + ("..." if len(content) > 260 else ""))

    if not snippets:
        return (
            f"I found related {subject} material but could not generate a full explanation right now. "
            "Please try again shortly."
        )

    joined = "\n\n".join(f"- {snippet}" for snippet in snippets)
    return (
        f"I could not reach the live AI model, but I found relevant {subject} references for your question: \"{query}\".\n\n"
        f"Key points from your study material:\n{joined}\n\n"
        "You can ask again to get a full explained answer once the model backend is available."
    )


def _not_found_in_source(language: str) -> str:
    if normalize_language(language) == "ta":
        return "தேர்ந்தெடுக்கப்பட்ட மூலத்தில் இந்த கேள்விக்கு ஆதாரம் கிடைக்கவில்லை."
    return "Not found in source."


def _source_citation_from_doc(doc: Any, fallback_subject: str, index: int) -> Dict[str, Any]:
    metadata = doc.metadata or {}
    page_raw = metadata.get("page")
    page = int(page_raw) if isinstance(page_raw, int) else None
    content = (doc.page_content or "").strip().replace("\n", " ")
    snippet = content[:260] + ("..." if len(content) > 260 else "")
    title = (
        metadata.get("title")
        or metadata.get("chapter")
        or metadata.get("source")
        or f"Source {index}"
    )
    subject = metadata.get("subject") or fallback_subject
    source_ref = metadata.get("source") or metadata.get("path")
    source_id = f"{title}:{page if page is not None else index}"

    return {
        "source_id": source_id,
        "title": str(title),
        "page": page,
        "subject": str(subject) if subject else None,
        "snippet": snippet,
        "source": str(source_ref) if source_ref else None,
        "relevance": 0.85,
    }


def retriever_agent(
    query: str,
    vectorstore,
    llm,
    subject: str,
    language: str = "en",
    source_locked: bool = False,
) -> Dict[str, Any]:
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
        selected_language_name = language_name(normalize_language(language))

        def _llm_fallback_answer() -> str:
            if llm is None:
                raise RuntimeError("LLM instance unavailable")

            fallback_template = """You are an expert NEET tutor specializing in {subject}.
Answer the student's question clearly and concisely.
When possible, include key definitions, one short example, and a quick exam tip.
Write the full answer in {language_name}.

Question: {question}

Answer:"""

            fallback_chain = PromptTemplate.from_template(fallback_template) | llm | StrOutputParser()
            return fallback_chain.invoke(
                {
                    "subject": subject,
                    "question": query,
                    "language_name": selected_language_name,
                }
            )

        if vectorstore is None:
            if source_locked:
                return {
                    'answer': _not_found_in_source(language),
                    'confidence': 0.95,
                    'sources': [],
                    'method': 'source_locked_no_vectorstore',
                    'warning': 'Vectorstore not available',
                }
            try:
                answer = _llm_fallback_answer()
            except Exception as llm_exc:
                logger.warning(f"LLM fallback without vectorstore failed: {llm_exc}")
                answer = (
                    "I can still help, but the AI model backend is currently unavailable. "
                    "Please retry shortly, or ask a specific concept and I will return available reference snippets."
                )

            return {
                'answer': _format_for_chat_display(answer, query, subject),
                'confidence': 0.45,
                'sources': [],
                'method': 'fallback_no_vectorstore',
                'warning': 'Vectorstore not available'
            }
        
        # Retrieve relevant documents (best-effort; embeddings backend may be unavailable).
        retrieval_warning = None
        try:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            retrieved_docs = retriever.invoke(query)
        except Exception as retrieval_exc:
            retrieval_warning = str(retrieval_exc)
            logger.warning(f"Retriever invoke failed, falling back without RAG: {retrieval_exc}")
            retrieved_docs = []
        
        if not retrieved_docs:
            if source_locked:
                return {
                    'answer': _not_found_in_source(language),
                    'confidence': 0.98,
                    'sources': [],
                    'method': 'source_locked_no_match',
                    'warning': retrieval_warning,
                }
            # Fallback: Direct LLM response (if available), else deterministic guidance.
            try:
                answer = _llm_fallback_answer()
                confidence = 0.6
            except Exception as llm_exc:
                logger.warning(f"LLM fallback with empty retrieval failed: {llm_exc}")
                answer = _build_excerpt_answer(query=query, retrieved_docs=[], subject=subject)
                confidence = 0.3
            
            return {
                'answer': _format_for_chat_display(answer, query, subject),
                'confidence': confidence,
                'sources': [],
                'method': 'fallback',
                'warning': retrieval_warning,
            }
        
        # Build a bounded context to keep local Ollama inference stable on low-RAM machines.
        max_doc_chars = 1200
        max_context_chars = 3200
        context_parts = []
        for doc in retrieved_docs:
            text = (doc.page_content or "").strip()
            if not text:
                continue
            context_parts.append(text[:max_doc_chars])

        context_str = "\n\n".join(context_parts)[:max_context_chars]
        
        # Generate answer using RAG
        rag_template = """Answer the question based on the following context from NEET study materials.
Be clear, concise, and accurate. Use student-friendly wording.
Write the final answer in {language_name}.

Context:
{context}

Question: {question}

Answer:"""
        
        try:
            if llm is None:
                raise RuntimeError("LLM instance unavailable")
            rag_chain = PromptTemplate.from_template(rag_template) | llm | StrOutputParser()
            answer = rag_chain.invoke(
                {
                    "context": context_str,
                    "question": query,
                    "language_name": selected_language_name,
                }
            )
            method = 'rag'
            confidence = 0.9
        except Exception as llm_exc:
            logger.warning(f"RAG synthesis failed, using excerpt fallback: {llm_exc}")
            answer = _build_excerpt_answer(query=query, retrieved_docs=retrieved_docs, subject=subject)
            method = 'retrieval_excerpt_fallback'
            confidence = 0.5
        
        # Extract source metadata
        sources = []
        for index, doc in enumerate(retrieved_docs[:4], start=1):
            sources.append(_source_citation_from_doc(doc, subject, index))
        
        return {
            'answer': _format_for_chat_display(answer, query, subject),
            'confidence': confidence,
            'sources': sources,
            'method': method,
            'documents_retrieved': len(retrieved_docs)
        }
        
    except Exception as e:
        logger.error(f"Retriever agent failed: {e}", exc_info=True)
        return {
            'answer': _format_for_chat_display(
                "I encountered an error while processing your question. Please try again.",
                query,
                subject,
            ),
            'confidence': 0.0,
            'sources': [],
            'error': str(e)
        }


def orchestrator_agent(
    query: str,
    vectorstores: Dict[str, Any],
    llm,
    subject: str,
    language: str = "en",
) -> Dict[str, Any]:
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
        selected_language_name = language_name(normalize_language(language))
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
            if store is not None:
                try:
                    retriever = store.as_retriever(search_kwargs={"k": 2})
                    docs = retriever.invoke(query)
                    
                    if docs:
                        context_parts.append(f"=== From {subj.upper()} ===\n" + "\n".join([d.page_content for d in docs]))
                        
                        for index, doc in enumerate(docs, start=1):
                            source_row = _source_citation_from_doc(doc, subj, index)
                            source_row['relevance'] = 0.75
                            all_sources.append(source_row)
                except Exception as e:
                    logger.warning(f"Failed to retrieve from {subj}: {e}")
        
        # Step 3: Synthesize answer
        if context_parts:
            context_str = "\n\n".join(context_parts)
            
            synthesis_template = """You are an expert NEET tutor. Answer this complex question by synthesizing information from multiple sources.
Write the full answer in {language_name}.

Context from study materials:
{context}

Question: {query}

Provide a comprehensive answer that:
1. Directly answers the question
2. Explains key concepts
3. Shows connections between topics if relevant

Answer:"""
            
            synthesis_chain = PromptTemplate.from_template(synthesis_template) | llm | StrOutputParser()
            answer = synthesis_chain.invoke(
                {
                    "context": context_str,
                    "query": query,
                    "language_name": selected_language_name,
                }
            )
            
            return {
                'answer': _format_for_chat_display(answer, query, subject),
                'confidence': 0.85,
                'sources': all_sources[:5],  # Top 5 sources
                'reasoning': analysis,
                'method': 'orchestration',
                'subjects_consulted': list(vectorstores.keys())
            }
        else:
            # Fallback to direct LLM
            fallback_template = """You are an expert NEET tutor. Answer this question comprehensively.
Write the full answer in {language_name}.

Question: {query}

Answer:"""
            
            fallback_chain = PromptTemplate.from_template(fallback_template) | llm | StrOutputParser()
            answer = fallback_chain.invoke(
                {
                    "query": query,
                    "language_name": selected_language_name,
                }
            )
            
            return {
                'answer': _format_for_chat_display(answer, query, subject),
                'confidence': 0.6,
                'sources': [],
                'reasoning': analysis,
                'method': 'fallback'
            }
        
    except Exception as e:
        logger.error(f"Orchestrator agent failed: {e}", exc_info=True)
        return {
            'answer': _format_for_chat_display(
                "I encountered an error while processing your complex question. Please try simplifying it or try again.",
                query,
                subject,
            ),
            'confidence': 0.0,
            'sources': [],
            'error': str(e)
        }
