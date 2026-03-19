import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status

from app.schemas.validation import InputValidationResult, ValidationSignal

SCENE_HEADING_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|EXT/INT\.|INT\./EXT\.|EXT\./INT\.|I/E\.|EST\.)")
UPPERCASE_CUE_RE = re.compile(r"^[A-Z0-9 .'\-()]{2,40}$")
PARENTHETICAL_RE = re.compile(r"^\([^)]{1,38}\)$")
TRANSITION_RE = re.compile(r"^[A-Z0-9 .'()\-]+:$")


class InputValidator:
    def __init__(self, screenplay_threshold: float = 0.45) -> None:
        self.screenplay_threshold = screenplay_threshold

    def validate_text_input(self, raw_text: str) -> InputValidationResult:
        return self._score_text(raw_text=raw_text, source_type="text_input", supported=True)

    def validate_file_input(
        self,
        filename: Optional[str],
        content_type: Optional[str],
        raw_text: Optional[str] = None,
    ) -> InputValidationResult:
        source_type, supported = self._detect_source_type(filename, content_type)
        if not supported:
            return InputValidationResult(
                source_type=source_type,
                is_supported_file_type=False,
                is_likely_screenplay=False,
                screenplay_confidence=0.0,
                rejection_reason="Only plaintext .txt screenplay files are supported right now.",
                validation_signals=[],
            )

        return self._score_text(raw_text=raw_text or "", source_type=source_type, supported=True)

    def ensure_valid_or_raise(self, result: InputValidationResult) -> None:
        if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT"):
            unprocessable_status = status.HTTP_422_UNPROCESSABLE_CONTENT
        else:
            unprocessable_status = 422
        if not result.is_supported_file_type:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "message": result.rejection_reason,
                    "validation": result.model_dump(),
                },
            )

        if not result.is_likely_screenplay:
            raise HTTPException(
                status_code=unprocessable_status,
                detail={
                    "message": result.rejection_reason or "The input does not appear to be a screenplay.",
                    "validation": result.model_dump(),
                },
            )

    def _detect_source_type(
        self,
        filename: Optional[str],
        content_type: Optional[str],
    ) -> tuple[str, bool]:
        suffix = Path(filename or "").suffix.lower()
        normalized_content_type = (content_type or "").lower()

        if suffix == ".txt" or normalized_content_type == "text/plain":
            return "txt", True
        if suffix == ".pdf" or normalized_content_type == "application/pdf":
            return "pdf", False
        if suffix == ".docx" or normalized_content_type in {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }:
            return "docx", False
        return "unknown", False

    def _score_text(self, raw_text: str, source_type: str, supported: bool) -> InputValidationResult:
        lines = [line.rstrip() for line in raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        non_empty_lines = [line.strip() for line in lines if line.strip()]

        scene_heading_count = sum(self._is_scene_heading(line) for line in non_empty_lines)
        uppercase_cue_count = sum(self._looks_like_character_cue(non_empty_lines, index) for index in range(len(non_empty_lines)))
        parenthetical_count = sum(PARENTHETICAL_RE.match(line) is not None for line in non_empty_lines)
        transition_count = sum(TRANSITION_RE.match(line) is not None for line in non_empty_lines)
        dialogue_like_count = self._count_dialogue_like_blocks(non_empty_lines)
        alternation_score = self._count_dialogue_action_alternation(non_empty_lines)

        signals = [
            self._build_signal(
                "scene_headings",
                value=float(scene_heading_count),
                weight=0.35,
                contribution=1.0 if scene_heading_count > 0 else 0.0,
                note="Scene headings such as INT. or EXT. are strong screenplay cues.",
            ),
            self._build_signal(
                "character_cues",
                value=float(uppercase_cue_count),
                weight=0.25,
                contribution=1.0 if uppercase_cue_count > 0 else 0.0,
                note="Uppercase character cue lines followed by dialogue-like text.",
            ),
            self._build_signal(
                "dialogue_blocks",
                value=float(dialogue_like_count),
                weight=0.2,
                contribution=1.0 if dialogue_like_count > 0 else 0.0,
                note="Dialogue structure separated from action is a screenplay signal.",
            ),
            self._build_signal(
                "parentheticals",
                value=float(parenthetical_count),
                weight=0.05,
                contribution=1.0 if parenthetical_count > 0 else 0.0,
                note="Parenthetical dialogue directions increase screenplay confidence.",
            ),
            self._build_signal(
                "transitions",
                value=float(transition_count),
                weight=0.05,
                contribution=1.0 if transition_count > 0 else 0.0,
                note="Transitions like CUT TO: are screenplay-specific cues.",
            ),
            self._build_signal(
                "dialogue_action_alternation",
                value=float(alternation_score),
                weight=0.1,
                contribution=min(alternation_score, 2) / 2,
                note="Alternation between narrative and dialogue supports screenplay structure.",
            ),
        ]

        confidence = round(sum(signal.weight * signal.contribution for signal in signals), 3)
        is_likely = confidence >= self.screenplay_threshold
        rejection_reason = None

        if not supported:
            rejection_reason = "Only plaintext .txt screenplay files are supported right now."
        elif not is_likely:
            rejection_reason = (
                "This input does not look enough like a screenplay yet. "
                "Expected structural cues such as scene headings, speaker cues, or dialogue/action formatting."
            )

        return InputValidationResult(
            source_type=source_type,
            is_supported_file_type=supported,
            is_likely_screenplay=is_likely,
            screenplay_confidence=confidence,
            rejection_reason=rejection_reason,
            validation_signals=signals,
        )

    def _build_signal(
        self,
        name: str,
        value: float,
        weight: float,
        contribution: float,
        note: str,
    ) -> ValidationSignal:
        return ValidationSignal(
            name=name,
            value=value,
            weight=weight,
            contribution=round(contribution, 3),
            note=note,
        )

    def _is_scene_heading(self, line: str) -> bool:
        return line == line.upper() and bool(SCENE_HEADING_RE.match(line))

    def _looks_like_character_cue(self, lines: list[str], index: int) -> bool:
        line = lines[index]
        if not UPPERCASE_CUE_RE.match(line):
            return False
        if self._is_scene_heading(line) or TRANSITION_RE.match(line) or PARENTHETICAL_RE.match(line):
            return False
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if not next_line:
            return False
        if next_line == next_line.upper() and not PARENTHETICAL_RE.match(next_line):
            return False
        return True

    def _count_dialogue_like_blocks(self, lines: list[str]) -> int:
        count = 0
        for index, line in enumerate(lines[:-1]):
            if not self._looks_like_character_cue(lines, index):
                continue
            next_line = lines[index + 1]
            if PARENTHETICAL_RE.match(next_line):
                count += 1
            elif next_line and next_line != next_line.upper():
                count += 1
        return count

    def _count_dialogue_action_alternation(self, lines: list[str]) -> int:
        alternation = 0
        last_kind: Optional[str] = None
        for index, line in enumerate(lines):
            if self._is_scene_heading(line) or TRANSITION_RE.match(line):
                continue
            if self._looks_like_character_cue(lines, index):
                current = "dialogue"
            elif PARENTHETICAL_RE.match(line):
                current = "parenthetical"
            else:
                current = "action"
            if last_kind == "action" and current == "dialogue":
                alternation += 1
            last_kind = current
        return alternation
