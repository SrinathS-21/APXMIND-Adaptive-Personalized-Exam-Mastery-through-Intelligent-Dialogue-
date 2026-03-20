"""
Server-Sent Events Router
==========================

GET /api/events/stream — real-time push stream for the authenticated user.

Events pushed:
  connected   — on initial connect (includes user_id)
  xp_awarded  — after any XP-bearing action  {xp, total_xp, level, streak}
  badge_earned — when a badge is unlocked    {badge_id, badge_name}
  heartbeat   — every 30 s to keep proxy connections alive
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ...api.middleware.auth import get_current_user
from ...db.models import User
from ...db.sse_events import get_user_queue

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stream", summary="SSE event stream", tags=["Events"])
async def event_stream(user: User = Depends(get_current_user)):
    """
    Open a Server-Sent Events stream.
    The client must send the JWT in the Authorization header
    (or via ?token= query param if EventSource doesn't support headers).
    """
    queue = get_user_queue(user.id)

    async def generator():
        # initial handshake
        yield f"data: {json.dumps({'type': 'connected', 'data': {'user_id': user.id}})}\n\n"
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield 'data: {"type":"heartbeat"}\n\n'
            except asyncio.CancelledError:
                break

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
