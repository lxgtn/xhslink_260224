from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.services import sheets_service
from config import CREDENTIALS_PATH

router = APIRouter()


@router.get("/auth/google")
async def google_auth(request: Request):
    if not CREDENTIALS_PATH.exists():
        return {
            "error": (
                "未找到 credentials.json，"
                "请将 Google OAuth2 客户端凭据文件放入 data/ 目录后重试"
            )
        }
    redirect_uri = str(request.base_url).rstrip("/") + "/api/auth/google/callback"
    try:
        auth_url = sheets_service.get_auth_url(redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        return {"error": str(e)}


@router.get("/auth/google/callback")
async def google_callback(request: Request, code: str = None, error: str = None):
    if error:
        return RedirectResponse(f"/?auth_error={error}")
    if not code:
        return RedirectResponse("/?auth_error=no_code")

    redirect_uri = str(request.base_url).rstrip("/") + "/api/auth/google/callback"
    try:
        sheets_service.exchange_code(code, redirect_uri)
    except Exception as e:
        return RedirectResponse(f"/?auth_error={str(e)[:200]}")

    return RedirectResponse("/?auth_success=1")


@router.get("/auth/google/status")
async def google_status():
    return sheets_service.get_auth_status()
