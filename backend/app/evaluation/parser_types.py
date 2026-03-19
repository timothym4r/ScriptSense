from typing import Literal, Optional

from pydantic import BaseModel, Field


ParserEvalMode = Literal["raw_parser", "corrected_output"]
ParserTaskName = Literal["scene_detection", "speaker_attribution", "block_type_classification"]
ParserOutcomeLabel = Literal["exact_match", "missing", "extra", "incorrect"]
ElementType = Literal[
    "scene_heading",
    "action",
    "dialogue",
    "parenthetical",
    "transition",
]


class CorrectedBlockAnnotation(BaseModel):
    element_index: int
    element_type: ElementType
    text: str
    start_line: int
    end_line: int
    speaker: Optional[str] = None


class CorrectedSceneAnnotation(BaseModel):
    scene_number: int
    heading: Optional[str] = None
    start_line: int
    end_line: int
    blocks: list[CorrectedBlockAnnotation] = Field(default_factory=list)


class CorrectedScriptAnnotation(BaseModel):
    script_id: str
    title: str
    raw_text: str
    corrected_scenes: list[CorrectedSceneAnnotation] = Field(default_factory=list)
    notes: Optional[str] = None


class ParserCaseResult(BaseModel):
    script_id: str
    task: ParserTaskName
    outcome: ParserOutcomeLabel
    scene_number: Optional[int] = None
    block_key: Optional[str] = None
    text_excerpt: Optional[str] = None
    gold_value: Optional[str] = None
    predicted_value: Optional[str] = None
    detail: str


class ParserTaskMetrics(BaseModel):
    task: ParserTaskName
    gold_total: int
    predicted_total: int
    exact_match: int
    missing: int
    extra: int
    incorrect: int
    precision: float
    recall: float
    exact_match_rate: float


class ParserModeEvaluationReport(BaseModel):
    script_id: str
    mode: ParserEvalMode
    summary: list[ParserTaskMetrics]
    errors: list[ParserCaseResult]
