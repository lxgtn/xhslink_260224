from pydantic import BaseModel
from typing import Optional


class AIConfig(BaseModel):
    provider: str = ""
    model: str = ""
    api_base_url: str = ""
    api_key: str = ""


class AppConfig(BaseModel):
    ai: AIConfig = AIConfig()
    sheets_id: str = ""
