from fastapi import APIRouter

from app.services import sheets_service

router = APIRouter()


@router.get("/auth/feishu/status")
async def feishu_status():
    """Check Feishu authentication status."""
    return await sheets_service.get_auth_status()
