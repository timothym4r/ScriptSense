from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.parse import ParsedScene


class StoredScriptSummary(BaseModel):
    id: str
    title: Optional[str] = None
    total_scenes: int
    total_elements: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StoredScriptResponse(BaseModel):
    id: str
    title: Optional[str] = None
    raw_text: str
    total_scenes: int
    total_elements: int
    scenes: list[ParsedScene]
    warnings: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
