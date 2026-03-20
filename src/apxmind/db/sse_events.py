"""
SSE Event Queue
===============
In-process asyncio queue per user for real-time push events.
Imported by gamification.py to emit XP/badge events.
"""

import asyncio
from typing import Dict

_queues: Dict[int, asyncio.Queue] = {}


def get_user_queue(user_id: int) -> asyncio.Queue:
    if user_id not in _queues:
        _queues[user_id] = asyncio.Queue(maxsize=50)
    return _queues[user_id]


async def push(user_id: int, event_type: str, data: dict) -> None:
    """Push an event to the user's SSE queue. Drops oldest event if full."""
    q = get_user_queue(user_id)
    try:
        q.put_nowait({"type": event_type, "data": data})
    except asyncio.QueueFull:
        try:
            q.get_nowait()  # drop oldest to make room
            q.put_nowait({"type": event_type, "data": data})
        except Exception:
            pass
