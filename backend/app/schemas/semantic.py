from typing import Literal, Optional

from pydantic import BaseModel, Field


ResolutionStatus = Literal["resolved", "ambiguous", "unresolved"]
MentionType = Literal["name", "alias", "pronoun"]


class ResolvedCharacterRef(BaseModel):
    canonical_character_id: str
    canonical_name: str


class CharacterResolutionCandidate(BaseModel):
    canonical_character_id: str
    canonical_name: str
    score: float
    rationale: str


class CharacterAliasRecord(BaseModel):
    alias_text: str
    normalized_alias: str
    alias_type: Literal["speaker", "derived", "action_mention"]
    confidence: float


class CharacterRecord(BaseModel):
    canonical_character_id: str
    canonical_name: str
    aliases: list[CharacterAliasRecord] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    dialogue_block_count: int = 0
    mention_count: int = 0


class EnrichedMention(BaseModel):
    canonical_character_id: Optional[str] = None
    mention_text: str
    mention_type: MentionType
    resolved_character: Optional[ResolvedCharacterRef] = None
    resolved_character_candidates: list[CharacterResolutionCandidate] = Field(default_factory=list)
    attribution_confidence: float = 0.0
    resolution_status: ResolutionStatus = "unresolved"


class ActionAttribution(BaseModel):
    canonical_character_id: Optional[str] = None
    resolved_character: Optional[ResolvedCharacterRef] = None
    resolved_character_candidates: list[CharacterResolutionCandidate] = Field(default_factory=list)
    attribution_confidence: float = 0.0
    resolution_status: ResolutionStatus = "unresolved"
    rationale: str
