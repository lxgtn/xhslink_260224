from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services import sse_manager

router = APIRouter()


@router.get("/logs/stream")
async def stream_logs(run_id: str, after_id: int = 0):
    async def generate():
        async for chunk in sse_manager.stream_events(run_id, after_id):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
