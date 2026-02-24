from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db import models as db
from app.services import workflow_service

router = APIRouter()


@router.post("/workflow/start")
async def start_workflow():
    try:
        run_id = await workflow_service.start_workflow()
        return {"run_id": run_id}
    except RuntimeError as e:
        return JSONResponse(status_code=409, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/workflow/status")
async def get_status():
    current = await db.get_current_run()
    if current:
        return {
            "status": "running",
            "run_id": current["id"],
            "total": current["total"],
            "success": current["success"],
            "failed": current["failed"],
        }
    return {"status": "idle"}
