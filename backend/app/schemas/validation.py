from typing import Literal, Optional

from pydantic import BaseModel, Field


SupportedInputType = Literal["text_input", "txt", "pdf", "docx", "unknown"]


class ValidationSignal(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float
    note: str


class InputValidationResult(BaseModel):
    source_type: SupportedInputType
    is_supported_file_type: bool
    is_likely_screenplay: bool
    screenplay_confidence: float
    rejection_reason: Optional[str] = None
    validation_signals: list[ValidationSignal] = Field(default_factory=list)
