"""
SSE Manager – broadcasts workflow log events to connected clients in real-time.

Strategy:
  - Each run has an asyncio.Queue registered in _queues while clients listen.
  - emit() saves the event to the DB (for history) AND pushes to live queue.
  - stream_events() first replays historical events from DB, then reads from queue.
    This prevents event loss when the client connects after the run starts.
"""

import asyncio
import json
from typing import AsyncGenerator

from app.db import models as db


_queues: dict[str, asyncio.Queue] = {}


async def emit(run_id: str, level: str, message: str) -> int:
    """Save event to DB and push to live SSE queue. Returns inserted event id."""
    event_id = await db.insert_event(run_id, level, message)
    event = {"id": event_id, "level": level, "message": message}
    q = _queues.get(run_id)
    if q:
        await q.put(event)
    return event_id


async def close_stream(run_id: str):
    """Send sentinel to end the SSE stream for this run."""
    q = _queues.get(run_id)
    if q:
        await q.put(None)


async def stream_events(run_id: str, after_id: int = 0) -> AsyncGenerator[str, None]:
    """
    SSE async generator.
    1. Registers the live queue FIRST (so no new events are missed).
    2. Replays historical events from DB with id > after_id.
    3. Yields live events from queue, skipping any already replayed.
    """
    q: asyncio.Queue = asyncio.Queue()
    _queues[run_id] = q

    try:
        # Replay historical events
        historical = await db.get_events_after(run_id, after_id)
        last_sent_id = after_id
        for event in historical:
            data = {
                "id": event["id"],
                "level": event["level"],
                "message": event["message"],
                "ts": event["ts"],
            }
            yield f"id: {event['id']}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            last_sent_id = event["id"]

        # Check if run is already completed (nothing more to stream)
        run = await db.get_run(run_id)
        if run and run["status"] != "running":
            yield "event: done\ndata: {}\n\n"
            return

        # Stream live events
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=25)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue

            if event is None:  # sentinel – workflow finished
                yield "event: done\ndata: {}\n\n"
                break

            # Skip if already sent via historical replay
            if event["id"] <= last_sent_id:
                continue

            # Fetch ts from DB (not stored in queue payload for simplicity)
            db_events = await db.get_events_after(run_id, event["id"] - 1)
            ts = db_events[0]["ts"] if db_events else ""

            data = {
                "id": event["id"],
                "level": event["level"],
                "message": event["message"],
                "ts": ts,
            }
            yield f"id: {event['id']}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            last_sent_id = event["id"]

    finally:
        _queues.pop(run_id, None)
