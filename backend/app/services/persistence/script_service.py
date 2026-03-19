from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.block import ScriptBlock
from app.db.models.scene import Scene
from app.db.models.script import Script
from app.repositories.script_repository import ScriptRepository
from app.schemas.parse import ParsedScriptResponse, ParseRequest
from app.schemas.script import StoredScriptResponse, StoredScriptSummary
from app.services.parsing.screenplay_parser import ScreenplayParser
from app.services.semantic.enricher import SemanticEnricher


class ScriptService:
    def __init__(
        self,
        parser: Optional[ScreenplayParser] = None,
        repository: Optional[ScriptRepository] = None,
        semantic_enricher: Optional[SemanticEnricher] = None,
    ) -> None:
        self.parser = parser or ScreenplayParser()
        self.repository = repository or ScriptRepository()
        self.semantic_enricher = semantic_enricher or SemanticEnricher()

    def create_and_parse(self, session: Session, request: ParseRequest) -> StoredScriptResponse:
        parsed = self.parser.parse(raw_text=request.raw_text, title=request.title)
        script_model = self._build_script_model(request.raw_text, parsed)
        created = self.repository.create(session, script_model)
        session.commit()
        stored = self.repository.get(session, created.id)
        return self._to_stored_response(stored)

    def list_scripts(self, session: Session) -> list[StoredScriptSummary]:
        scripts = self.repository.list(session)
        return [
            StoredScriptSummary(
                id=script.id,
                title=script.title,
                total_scenes=script.total_scenes,
                total_elements=script.total_elements,
                created_at=script.created_at,
            )
            for script in scripts
        ]

    def get_script(self, session: Session, script_id: str) -> Optional[StoredScriptResponse]:
        script = self.repository.get(session, script_id)
        if script is None:
            return None
        return self._to_stored_response(script)

    def _build_script_model(self, raw_text: str, parsed: ParsedScriptResponse) -> Script:
        script = Script(
            title=parsed.title,
            raw_text=raw_text,
            total_scenes=parsed.total_scenes,
            total_elements=parsed.total_elements,
            warnings=parsed.warnings,
        )
        global_index = 1

        for parsed_scene in parsed.scenes:
            scene = Scene(
                scene_number=parsed_scene.scene_number,
                heading=parsed_scene.heading,
                start_line=parsed_scene.start_line,
                end_line=parsed_scene.end_line,
            )
            script.scenes.append(scene)
            for parsed_element in parsed_scene.elements:
                block = ScriptBlock(
                    global_element_index=global_index,
                    element_index=parsed_element.element_index,
                    element_type=parsed_element.element_type,
                    text=parsed_element.text,
                    start_line=parsed_element.start_line,
                    end_line=parsed_element.end_line,
                    speaker=parsed_element.speaker,
                )
                block.script = script
                scene.blocks.append(block)
                global_index += 1

        return script

    def _to_stored_response(self, script: Script) -> StoredScriptResponse:
        scenes = []
        total_elements = 0

        ordered_scenes = sorted(script.scenes, key=lambda item: item.scene_number)
        for scene in ordered_scenes:
            ordered_blocks = sorted(scene.blocks, key=lambda item: item.element_index)
            total_elements += len(ordered_blocks)
            scenes.append(
                {
                    "scene_number": scene.scene_number,
                    "heading": scene.heading,
                    "start_line": scene.start_line,
                    "end_line": scene.end_line,
                    "elements": [
                        {
                            "element_index": block.element_index,
                            "element_type": block.element_type,
                            "text": block.text,
                            "start_line": block.start_line,
                            "end_line": block.end_line,
                            "speaker": block.speaker,
                        }
                        for block in ordered_blocks
                    ],
                }
            )

        parsed = ParsedScriptResponse(
            title=script.title,
            total_scenes=script.total_scenes,
            total_elements=total_elements,
            scenes=scenes,
            warnings=script.warnings,
        )
        enriched = self.semantic_enricher.enrich(parsed)

        return StoredScriptResponse(
            id=script.id,
            title=script.title,
            raw_text=script.raw_text,
            total_scenes=enriched.total_scenes,
            total_elements=enriched.total_elements,
            scenes=enriched.scenes,
            warnings=enriched.warnings,
            characters=enriched.characters,
            created_at=script.created_at,
        )
