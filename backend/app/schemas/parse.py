from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.correction import CorrectionRecordResponse
from app.schemas.semantic import ActionAttribution, CharacterRecord, EnrichedMention
from app.schemas.validation import InputValidationResult

ElementType = Literal[
    "scene_heading",
    "action",
    "dialogue",
    "parenthetical",
    "transition",
]


class ParseRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="Optional title for the script.")
    raw_text: str = Field(min_length=1, description="Raw screenplay text.")


class ParsedElement(BaseModel):
    block_id: Optional[str] = None
    element_index: int
    element_type: ElementType
    text: str
    start_line: int
    end_line: int
    speaker: Optional[str] = None
    original_element_type: Optional[ElementType] = None
    original_text: Optional[str] = None
    original_speaker: Optional[str] = None
    is_corrected: bool = False
    corrections: list[CorrectionRecordResponse] = Field(default_factory=list)
    speaker_character_id: Optional[str] = None
    mentions: list[EnrichedMention] = Field(default_factory=list)
    action_attribution: Optional[ActionAttribution] = None


class ParsedScene(BaseModel):
    scene_id: Optional[str] = None
    scene_number: int
    heading: Optional[str] = None
    original_heading: Optional[str] = None
    is_corrected: bool = False
    corrections: list[CorrectionRecordResponse] = Field(default_factory=list)
    start_line: int
    end_line: int
    elements: list[ParsedElement]


class ParsedScriptResponse(BaseModel):
    title: Optional[str] = None
    total_scenes: int
    total_elements: int
    scenes: list[ParsedScene]
    warnings: list[str] = Field(default_factory=list)
    characters: list[CharacterRecord] = Field(default_factory=list)
    validation: Optional[InputValidationResult] = None
