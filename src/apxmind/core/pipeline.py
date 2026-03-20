"""
APXMIND Pipeline
================

End-to-end query processing pipeline that connects
Tier-0 → Tier-1 → Tier-2 → Agent response.

This will be the primary entry point once the full
routing system is wired up (Phase 4).
"""

import logging
from typing import Optional, AsyncIterator

logger = logging.getLogger(__name__)


class APXMINDPipeline:
    """
    End-to-end query processing orchestrator.
    
    For now this wraps the existing simplified agents.
    In Phase 4, it will wire up the full Tier-0/1/2 system.
    """

    def __init__(self, llm, vectorstores: dict):
        self.llm = llm
        self.vectorstores = vectorstores

    async def process(
        self, question: str, subject: Optional[str] = None
    ) -> dict:
        """
        Process a query through the intelligence pipeline.
        
        Returns dict with keys: answer, agent, confidence, sources, tier_path
        """
        from ..api.agents import classify_intent, retriever_agent, orchestrator_agent

        # Step 1: Tier-0 classification
        intent_result = classify_intent(question, subject)
        intent = intent_result.get("intent", "retrieval")
        detected_subject = intent_result.get("subject", subject or "biology")

        # Step 2 & 3: Route to appropriate tier
        if intent in ("simple", "retrieval"):
            vectorstore = self.vectorstores.get(detected_subject)
            result = retriever_agent(
                query=question,
                vectorstore=vectorstore,
                llm=self.llm,
                subject=detected_subject,
            )
            result["tier_path"] = f"T0({intent})→T1:retriever"
        else:
            result = orchestrator_agent(
                query=question,
                vectorstores=self.vectorstores,
                llm=self.llm,
                subject=detected_subject,
            )
            result["tier_path"] = f"T0({intent})→T2:orchestrator"

        result["subject"] = detected_subject
        return result

    async def stream(
        self, question: str, subject: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Streaming version — yields tokens for WebSocket.
        
        This is a placeholder that processes the full response then streams it.
        In Phase 2 (llama.cpp), this will yield actual tokens from the LLM.
        """
        result = await self.process(question, subject)
        answer = result.get("answer", "")

        # Simulate token streaming by yielding word groups
        words = answer.split(" ")
        for i in range(0, len(words), 2):
            chunk = " ".join(words[i : i + 2])
            yield chunk + " "
