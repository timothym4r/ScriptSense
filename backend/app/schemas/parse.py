from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.semantic import ActionAttribution, CharacterRecord, EnrichedMention

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
    element_index: int
    element_type: ElementType
    text: str
    start_line: int
    end_line: int
    speaker: Optional[str] = None
    speaker_character_id: Optional[str] = None
    mentions: list[EnrichedMention] = Field(default_factory=list)
    action_attribution: Optional[ActionAttribution] = None


class ParsedScene(BaseModel):
    scene_number: int
    heading: Optional[str] = None
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
