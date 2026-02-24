from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db import models as db

router = APIRouter()


@router.get("/history")
async def list_history():
    runs = await db.get_runs(30)
    return {"runs": runs}


@router.get("/history/{run_id}")
async def get_run_detail(run_id: str):
    run = await db.get_run(run_id)
    if not run:
        return JSONResponse(status_code=404, content={"error": "not found"})
    events = await db.get_events(run_id)
    return {"run": run, "events": events}
