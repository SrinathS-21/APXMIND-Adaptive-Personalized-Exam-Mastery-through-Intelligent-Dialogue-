"""
Query Router
=============

POST /api/query — process user queries through the intelligence layer.
"""

import time
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from ...api.schemas import QueryRequest, QueryResponse, QueryMetadata, ErrorResponse
from ...core.dependencies import get_llm, get_vectorstore
from ...core.language import resolve_request_language

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=QueryResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Process user query through intelligence layer",
)
async def process_query(request: QueryRequest, http_request: Request):
    """
    Process a user query through the 3-tier intelligence system.

    - Tier-0: Intent classification & subject detection
    - Tier-1: Retrieval-based QA (RAG)
    - Tier-2: Multi-agent orchestration for complex queries
    """
    start_time = time.time()

    try:
        query = request.query.strip()
        subject = request.subject.value if request.subject else ""
        selected_language = resolve_request_language(
            explicit=request.language,
            context=request.context,
            header=http_request.headers.get("X-APXMIND-Language"),
        )

        logger.info(
            f"Processing query: {query[:100]}... "
            f"(subject: {subject or 'auto'}, language: {selected_language})"
        )

        # Import intelligence components (lazy to avoid circular deps)
        from ...api.agents import classify_intent, retriever_agent, orchestrator_agent

        llm = get_llm()

        # TIER-0: Classify intent
        tier0_start = time.time()
        intent_result = classify_intent(query, subject)
        tier0_latency = (time.time() - tier0_start) * 1000

        intent = intent_result.get("intent", "complex")
        detected_subject = intent_result.get("subject", subject)

        logger.info(f"Tier-0: {intent} (subject={detected_subject}, {tier0_latency:.0f}ms)")

        if intent in ("simple", "retrieval"):
            # TIER-1: Retrieval-based QA
            tier1_start = time.time()
            vectorstore = (
                get_vectorstore(detected_subject)
                or get_vectorstore(subject)
                or get_vectorstore("question_bank")
            )

            result = retriever_agent(
                query=query,
                vectorstore=vectorstore,
                llm=llm,
                subject=detected_subject,
                language=selected_language,
            )
            tier1_latency = (time.time() - tier1_start) * 1000
            total_latency = (time.time() - start_time) * 1000

            return QueryResponse(
                success=True,
                answer=result.get("answer", ""),
                metadata=QueryMetadata(
                    tier="tier1",
                    agent="retriever",
                    intent=intent,
                    subject=detected_subject,
                    confidence=result.get("confidence", 0.0),
                    sources=result.get("sources", []),
                    tier0_latency_ms=round(tier0_latency, 2),
                    tier1_latency_ms=round(tier1_latency, 2),
                    total_latency_ms=round(total_latency, 2),
                    timestamp=datetime.utcnow().isoformat(),
                ),
            )
        else:
            # TIER-2: Advanced orchestration
            tier2_start = time.time()
            vectorstores = {
                "biology": get_vectorstore("biology"),
                "chemistry": get_vectorstore("chemistry"),
                "physics": get_vectorstore("physics"),
            }

            result = orchestrator_agent(
                query=query,
                vectorstores=vectorstores,
                llm=llm,
                subject=detected_subject,
                language=selected_language,
            )
            tier2_latency = (time.time() - tier2_start) * 1000
            total_latency = (time.time() - start_time) * 1000

            return QueryResponse(
                success=True,
                answer=result.get("answer", ""),
                metadata=QueryMetadata(
                    tier="tier2",
                    agent="orchestrator",
                    intent=intent,
                    subject=detected_subject,
                    confidence=result.get("confidence", 0.0),
                    sources=result.get("sources", []),
                    tier0_latency_ms=round(tier0_latency, 2),
                    tier2_latency_ms=round(tier2_latency, 2),
                    total_latency_ms=round(total_latency, 2),
                    timestamp=datetime.utcnow().isoformat(),
                ),
            )

    except Exception as e:
        latency = (time.time() - start_time) * 1000
        logger.error(f"Query failed after {latency:.0f}ms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")
