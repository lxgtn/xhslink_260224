from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.db import models as db

router = APIRouter()


class ConfigPayload(BaseModel):
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_api_key: Optional[str] = None
    sheets_id: Optional[str] = None
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


@router.get("/config")
async def get_config():
    cfg = await db.get_all_config()
    raw_key = cfg.get("ai_api_key", "")
    raw_secret = cfg.get("feishu_app_secret", "")
    cfg["ai_api_key"] = ""  # never send raw key
    cfg["ai_api_key_masked"] = _mask_key(raw_key)
    cfg["ai_api_key_set"] = bool(raw_key)
    # Return raw secret for auto-fill (different security model than API key)
    cfg["feishu_app_secret"] = raw_secret  # return raw for auto-fill
    cfg["feishu_app_secret_masked"] = _mask_key(raw_secret)
    cfg["feishu_app_secret_set"] = bool(raw_secret)
    return cfg


@router.post("/config")
async def save_config(payload: ConfigPayload):
    fields = payload.model_dump(exclude_none=True)
    for k, v in fields.items():
        if v is not None:
            await db.set_config(k, str(v))
    return {"status": "saved"}
