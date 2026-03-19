from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.correction import CorrectionRecordResponse
from app.schemas.parse import ParsedScene
from app.schemas.semantic import CharacterRecord
from app.schemas.validation import InputValidationResult


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
    characters: list[CharacterRecord]
    validation: Optional[InputValidationResult] = None
    corrections: list[CorrectionRecordResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
