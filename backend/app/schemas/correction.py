from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

CorrectionTargetType = Literal["scene", "block"]
CorrectionField = Literal["heading", "element_type", "speaker", "text"]


class CreateCorrectionRequest(BaseModel):
    target_type: CorrectionTargetType
    target_id: str = Field(min_length=1)
    corrected_field: CorrectionField
    new_value: Optional[str] = None


class CorrectionRecordResponse(BaseModel):
    id: str
    target_type: CorrectionTargetType
    target_id: str
    corrected_field: CorrectionField
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime
