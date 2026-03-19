from typing import Literal, Optional

from pydantic import BaseModel, Field


SystemMode = Literal["baseline", "heuristic", "heuristic_llm_fallback"]
ResolutionStatus = Literal["resolved", "ambiguous", "unresolved"]
TaskName = Literal["speaker_attribution", "mention_resolution", "action_attribution"]
OutcomeLabel = Literal["exact_match", "ambiguous_match", "unresolved", "incorrect"]


class GoldTarget(BaseModel):
    scene_number: int
    element_index: int
    resolution_status: ResolutionStatus
    acceptable_characters: list[str] = Field(default_factory=list)
    mention_text: Optional[str] = None
    mention_occurrence: int = 1


class GoldScriptAnnotation(BaseModel):
    script_id: str
    title: str
    raw_text: str
    speaker_attribution: list[GoldTarget] = Field(default_factory=list)
    mention_resolution: list[GoldTarget] = Field(default_factory=list)
    action_attribution: list[GoldTarget] = Field(default_factory=list)


class TaskPrediction(BaseModel):
    scene_number: int
    element_index: int
    resolution_status: ResolutionStatus
    predicted_character: Optional[str] = None
    candidate_characters: list[str] = Field(default_factory=list)
    mention_text: Optional[str] = None
    attribution_confidence: float = 0.0


class EvaluationCaseResult(BaseModel):
    script_id: str
    task: TaskName
    scene_number: int
    element_index: int
    mention_text: Optional[str] = None
    gold_status: ResolutionStatus
    predicted_status: ResolutionStatus
    gold_characters: list[str] = Field(default_factory=list)
    predicted_character: Optional[str] = None
    predicted_candidates: list[str] = Field(default_factory=list)
    outcome: OutcomeLabel
    confidence: float = 0.0


class TaskMetrics(BaseModel):
    task: TaskName
    total: int
    exact_match: int
    ambiguous_match: int
    unresolved: int
    incorrect: int
    exact_match_rate: float
    ambiguity_aware_rate: float
    unresolved_rate: float


class ModeEvaluationReport(BaseModel):
    script_id: str
    mode: SystemMode
    summary: list[TaskMetrics]
    errors: list[EvaluationCaseResult]
