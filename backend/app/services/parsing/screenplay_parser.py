import re
from dataclasses import dataclass
from typing import Optional

from app.schemas.parse import ParsedElement, ParsedScene, ParsedScriptResponse

SCENE_HEADING_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|EXT/INT\.|I/E\.|EST\.)")
CHARACTER_CUE_SUFFIX_RE = re.compile(r"\s*\(([^)]+)\)\s*$")
TRANSITION_RE = re.compile(r"^[A-Z0-9 .'()\-]+:$")
SCENE_NUMBER_SUFFIX_RE = re.compile(r"\s+#\d+[A-Z]?#\s*$")


@dataclass(frozen=True)
class ClassifiedLine:
    number: int
    text: str


class ScreenplayParser:
    def parse(self, raw_text: str, title: Optional[str] = None) -> ParsedScriptResponse:
        normalized_lines = self._normalize(raw_text)
        classified_lines = [
            ClassifiedLine(number=index, text=line)
            for index, line in enumerate(normalized_lines, start=1)
        ]

        scenes: list[ParsedScene] = []
        warnings: list[str] = []
        current_scene_lines: list[ClassifiedLine] = []
        pending_preamble: list[ClassifiedLine] = []

        for line in classified_lines:
            if self._is_scene_heading(line.text):
                if current_scene_lines:
                    scenes.append(self._build_scene(len(scenes) + 1, current_scene_lines))
                    current_scene_lines = []
                elif pending_preamble and not self._is_ignorable_preamble(pending_preamble):
                    scenes.append(self._build_scene(len(scenes) + 1, pending_preamble, heading=None))
                    pending_preamble = []
                else:
                    pending_preamble = []
                current_scene_lines.append(line)
                continue

            if current_scene_lines:
                current_scene_lines.append(line)
            else:
                pending_preamble.append(line)

        if current_scene_lines:
            scenes.append(self._build_scene(len(scenes) + 1, current_scene_lines))
        elif pending_preamble:
            warnings.append("No explicit scene headings found; returned a single inferred scene.")
            scenes.append(self._build_scene(1, pending_preamble, heading=None))

        total_elements = sum(len(scene.elements) for scene in scenes)
        return ParsedScriptResponse(
            title=title,
            total_scenes=len(scenes),
            total_elements=total_elements,
            scenes=scenes,
            warnings=warnings,
        )

    def _normalize(self, raw_text: str) -> list[str]:
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
        return [line.rstrip() for line in text.split("\n")]

    def _build_scene(
        self,
        scene_number: int,
        lines: list[ClassifiedLine],
        heading: Optional[str] = None,
    ) -> ParsedScene:
        elements: list[ParsedElement] = []
        index = 1
        pointer = 0
        resolved_heading = heading

        if lines and self._is_scene_heading(lines[0].text):
            resolved_heading = lines[0].text.strip()
            elements.append(
                ParsedElement(
                    element_index=index,
                    element_type="scene_heading",
                    text=resolved_heading,
                    start_line=lines[0].number,
                    end_line=lines[0].number,
                )
            )
            index += 1
            pointer = 1

        while pointer < len(lines):
            line = lines[pointer]

            if self._is_blank(line.text):
                pointer += 1
                continue

            if self._is_transition(line.text):
                elements.append(
                    ParsedElement(
                        element_index=index,
                        element_type="transition",
                        text=line.text.strip(),
                        start_line=line.number,
                        end_line=line.number,
                    )
                )
                index += 1
                pointer += 1
                continue

            if self._is_character_cue(lines, pointer):
                element, next_pointer = self._consume_dialogue(index, lines, pointer)
                elements.extend(element)
                index = len(elements) + 1
                pointer = next_pointer
                continue

            element, next_pointer = self._consume_action(index, lines, pointer)
            elements.append(element)
            index += 1
            pointer = next_pointer

        start_line = lines[0].number if lines else 1
        end_line = lines[-1].number if lines else start_line
        return ParsedScene(
            scene_number=scene_number,
            heading=resolved_heading,
            start_line=start_line,
            end_line=end_line,
            elements=elements,
        )

    def _consume_dialogue(
        self,
        element_index: int,
        lines: list[ClassifiedLine],
        pointer: int,
    ) -> tuple[list[ParsedElement], int]:
        cue_line = lines[pointer]
        speaker = self._normalize_speaker(cue_line.text)
        elements: list[ParsedElement] = []
        dialogue_lines: list[ClassifiedLine] = []
        local_index = element_index
        pointer += 1

        while pointer < len(lines):
            line = lines[pointer]
            if self._is_blank(line.text):
                break
            if self._is_scene_heading(line.text) or self._is_character_cue(lines, pointer):
                break
            if self._is_transition(line.text):
                break
            if self._is_parenthetical(line.text):
                if dialogue_lines:
                    elements.append(
                        ParsedElement(
                            element_index=local_index,
                            element_type="dialogue",
                            text="\n".join(item.text.strip() for item in dialogue_lines),
                            start_line=dialogue_lines[0].number,
                            end_line=dialogue_lines[-1].number,
                            speaker=speaker,
                        )
                    )
                    local_index += 1
                    dialogue_lines = []
                elements.append(
                    ParsedElement(
                        element_index=local_index,
                        element_type="parenthetical",
                        text=line.text.strip(),
                        start_line=line.number,
                        end_line=line.number,
                        speaker=speaker,
                    )
                )
                local_index += 1
                pointer += 1
                continue
            dialogue_lines.append(line)
            pointer += 1

        if dialogue_lines:
            elements.append(
                ParsedElement(
                    element_index=local_index,
                    element_type="dialogue",
                    text="\n".join(item.text.strip() for item in dialogue_lines),
                    start_line=dialogue_lines[0].number,
                    end_line=dialogue_lines[-1].number,
                    speaker=speaker,
                )
            )

        return elements, pointer

    def _consume_action(
        self,
        element_index: int,
        lines: list[ClassifiedLine],
        pointer: int,
    ) -> tuple[ParsedElement, int]:
        action_lines: list[ClassifiedLine] = []

        while pointer < len(lines):
            line = lines[pointer]
            if self._is_blank(line.text):
                if action_lines:
                    next_index = self._next_meaningful_index(lines, pointer + 1)
                    if (
                        next_index is not None
                        and len(action_lines) == 1
                        and self._looks_like_character_cue(action_lines[0].text)
                        and not self._is_dialogue_break(lines, next_index)
                    ):
                        pointer += 1
                        continue
                    break
                pointer += 1
                continue
            if self._is_scene_heading(line.text) or self._is_character_cue(lines, pointer):
                break
            if self._is_transition(line.text):
                break
            action_lines.append(line)
            pointer += 1

        if not action_lines:
            line = lines[pointer]
            return (
                ParsedElement(
                    element_index=element_index,
                    element_type="action",
                    text=line.text.strip(),
                    start_line=line.number,
                    end_line=line.number,
                ),
                pointer + 1,
            )

        return (
            ParsedElement(
                element_index=element_index,
                element_type="action",
                text="\n".join(item.text.strip() for item in action_lines),
                start_line=action_lines[0].number,
                end_line=action_lines[-1].number,
            ),
            pointer,
        )

    def _is_blank(self, text: str) -> bool:
        return not text.strip()

    def _is_scene_heading(self, text: str) -> bool:
        stripped = self._normalize_scene_heading_candidate(text)
        return bool(stripped) and bool(SCENE_HEADING_RE.match(stripped))

    def _is_transition(self, text: str) -> bool:
        stripped = text.strip()
        return bool(stripped) and stripped == stripped.upper() and bool(TRANSITION_RE.match(stripped))

    def _is_parenthetical(self, text: str) -> bool:
        stripped = text.strip()
        return stripped.startswith("(") and stripped.endswith(")") and len(stripped) <= 40

    def _is_ignorable_preamble(self, lines: list[ClassifiedLine]) -> bool:
        meaningful_lines = [line for line in lines if not self._is_blank(line.text)]
        if not meaningful_lines:
            return True
        return all(self._is_transition(line.text) for line in meaningful_lines)

    def _is_character_cue(self, lines: list[ClassifiedLine], pointer: int) -> bool:
        text = lines[pointer].text
        if not self._looks_like_character_cue(text):
            return False
        if pointer + 1 < len(lines) and self._is_blank(lines[pointer + 1].text):
            return False
        next_index = self._next_meaningful_index(lines, pointer + 1)
        if next_index is None:
            return False
        next_line = lines[next_index]
        if self._is_scene_heading(next_line.text) or self._is_transition(next_line.text):
            return False
        if self._looks_like_character_cue(next_line.text):
            return False
        return True

    def _looks_like_character_cue(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped or stripped != stripped.upper():
            return False
        if self._is_scene_heading(stripped) or self._is_transition(stripped):
            return False
        if len(stripped) > 40:
            return False
        if stripped.endswith(":"):
            return False
        if stripped.endswith((".", "!", "?")):
            return False
        has_alpha = any(char.isalpha() for char in stripped)
        if not has_alpha:
            return False
        normalized = self._normalize_speaker(stripped)
        return len(normalized.split()) <= 5

    def _normalize_speaker(self, text: str) -> str:
        stripped = text.strip()
        while True:
            updated = CHARACTER_CUE_SUFFIX_RE.sub("", stripped)
            if updated == stripped:
                break
            stripped = updated.strip()
        stripped = stripped.removesuffix(" (CONT'D)").removesuffix(" (CONT’D)")
        stripped = stripped.removesuffix(" CONT'D").removesuffix(" CONT’D")
        return stripped.strip()

    def _normalize_scene_heading_candidate(self, text: str) -> str:
        stripped = text.strip().lstrip(".")
        stripped = SCENE_NUMBER_SUFFIX_RE.sub("", stripped).strip()
        if not stripped:
            return ""
        return stripped if stripped == stripped.upper() else ""

    def _next_meaningful_index(
        self,
        lines: list[ClassifiedLine],
        start: int,
    ) -> Optional[int]:
        for index in range(start, len(lines)):
            if not self._is_blank(lines[index].text):
                return index
        return None

    def _is_dialogue_break(self, lines: list[ClassifiedLine], pointer: int) -> bool:
        line = lines[pointer]
        if self._is_scene_heading(line.text) or self._is_transition(line.text):
            return True
        if self._is_character_cue(lines, pointer):
            return True
        return False
