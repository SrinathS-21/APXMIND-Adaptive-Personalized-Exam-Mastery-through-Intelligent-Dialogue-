"""
WebSocket Streaming Router
============================

WS /ws/chat — real-time token streaming for chat responses.
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.dependencies import get_llm, get_vectorstore
from ...core.language import language_name, normalize_language

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.

    Client sends:
        {"question": "What is photosynthesis?", "subject": "biology"}

    Server sends (multiple messages):
        {"type": "token", "content": "Photo"}
        {"type": "token", "content": "synthesis"}
        ...
        {"type": "done", "metadata": {"tier": "tier1", "agent": "retriever"}}
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_json()
            question = data.get("question", "").strip()

            if not question:
                await websocket.send_json({"type": "error", "content": "Empty question"})
                continue

            subject = data.get("subject", "")

            try:
                # Use the new Agentic Tool Runner instead of forced RAG
                from ...core.dependencies import get_llm
                from ...core.tool_runner import AgenticToolRunner
                
                llm = get_llm()
                # We need the pure llama_cpp instance
                native_llama_client = llm.client
                runner = AgenticToolRunner(native_llama_client)
                
                selected_language_name = language_name(normalize_language(data.get("language")))
                
                system_prompt = (
                    f"You are a NEET Medical tutor. You MUST use your search tools if the user asks a factual "
                    f"science question about Biology, Chemistry, or Physics. DO NOT guess the curriculum facts. "
                    f"Explain the answer in {selected_language_name}. Do NOT mention 'NEET aspirant'."
                )

                # Execute the dynamic Tool-Calling Stream
                stream = runner.chat_with_tools_stream(user_query=question, system_prompt=system_prompt)
                
                for chunk in stream:
                    # Check if the chunk is JSON (tool status update)
                    if chunk.startswith('{"status":'):
                        import json
                        status_data = json.loads(chunk)
                        await websocket.send_json({"type": "status", "content": status_data["message"]})
                    else:
                        # Standard text token
                        await websocket.send_json({"type": "token", "content": chunk})

                await websocket.send_json(
                    {
                        "type": "done",
                        "metadata": {
                            "tier": "agentic",
                            "agent": "tool_runner",
                            "subject": subject,
                            "intent": "dynamic",
                        },
                    }
                )

            except Exception as e:
                logger.error(f"WebSocket query error: {e}", exc_info=True)
                await websocket.send_json(
                    {"type": "error", "content": f"Error processing query: {str(e)}"}
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
