from pydantic import BaseModel
from typing import Optional


class WorkflowStatus(BaseModel):
    status: str  # idle | running | completed | failed
    run_id: Optional[str] = None
    total: int = 0
    success: int = 0
    failed: int = 0


class LogEvent(BaseModel):
    id: int
    level: str
    message: str
    ts: str
