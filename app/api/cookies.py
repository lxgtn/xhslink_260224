import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.services import xhs_scraper

router = APIRouter()


class CookiePayload(BaseModel):
    cookie_string: Optional[str] = None


@router.get("/cookies/status")
async def cookie_status():
    return xhs_scraper.get_cookie_status()


@router.post("/cookies/capture")
async def capture_cookies(background_tasks: BackgroundTasks):
    if xhs_scraper.is_capturing():
        return {"status": "capturing", "message": "已在获取中，请等待浏览器窗口出现"}
    background_tasks.add_task(xhs_scraper.capture_cookies_async)
    return {
        "status": "capturing",
        "message": "已打开浏览器，请在弹出的窗口中登录小红书，登录完成后系统自动保存",
    }


@router.post("/cookies/import")
async def import_cookies(payload: CookiePayload):
    """
    Import cookies from browser console.
    Accepts either:
    1. document.cookie string (key=value; key2=value2)
    2. JSON array from Application > Cookies > Copy as cURL
    """
    if not payload.cookie_string or not payload.cookie_string.strip():
        return {"status": "error", "message": "Cookie 内容不能为空"}

    result = xhs_scraper.import_cookies_from_string(payload.cookie_string.strip())
    return result


@router.post("/cookies/cancel")
async def cancel_capture():
    await xhs_scraper.cancel_capture()
    return {"status": "cancelled"}


@router.get("/cookies/raw")
async def get_cookie_raw():
    """Get saved raw cookie string for auto-fill."""
    return {"cookie_string": xhs_scraper.get_cookie_raw_string()}
