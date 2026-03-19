from typing import Any

from app.evaluation.parser_types import CorrectedScriptAnnotation, ParserEvalMode
from app.schemas.parse import ParsedElement, ParsedScene, ParsedScriptResponse
from app.services.parsing.screenplay_parser import ScreenplayParser


class ParserPredictionRunner:
    def __init__(self) -> None:
        self.parser = ScreenplayParser()

    def predict(self, annotation: CorrectedScriptAnnotation, mode: ParserEvalMode) -> ParsedScriptResponse:
        if mode == "raw_parser":
            return self.parser.parse(annotation.raw_text, title=annotation.title)

        scenes = [
            ParsedScene(
                scene_number=scene.scene_number,
                heading=scene.heading,
                start_line=scene.start_line,
                end_line=scene.end_line,
                elements=[
                    ParsedElement(
                        element_index=block.element_index,
                        element_type=block.element_type,
                        text=block.text,
                        start_line=block.start_line,
                        end_line=block.end_line,
                        speaker=block.speaker,
                    )
                    for block in scene.blocks
                ],
            )
            for scene in annotation.corrected_scenes
        ]
        total_elements = sum(len(scene.blocks) for scene in annotation.corrected_scenes)
        return ParsedScriptResponse(
            title=annotation.title,
            total_scenes=len(scenes),
            total_elements=total_elements,
            scenes=scenes,
            warnings=[],
        )
