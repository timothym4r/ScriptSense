from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.block import ScriptBlock
from app.db.models.correction import CorrectionRecord
from app.db.models.scene import Scene
from app.db.models.script import Script
from app.repositories.script_repository import ScriptRepository
from app.schemas.parse import ParsedScriptResponse, ParseRequest
from app.schemas.correction import CorrectionRecordResponse
from app.schemas.script import StoredScriptResponse, StoredScriptSummary
from app.services.validation.parse_pipeline import ValidatedParsePipeline


class ScriptService:
    def __init__(
        self,
        repository: Optional[ScriptRepository] = None,
        parse_pipeline: Optional[ValidatedParsePipeline] = None,
    ) -> None:
        self.repository = repository or ScriptRepository()
        self.parse_pipeline = parse_pipeline or ValidatedParsePipeline()

    def create_and_parse(self, session: Session, request: ParseRequest) -> StoredScriptResponse:
        parsed = self.parse_pipeline.parse_text(raw_text=request.raw_text, title=request.title)
        script_model = self._build_script_model(request.raw_text, parsed)
        created = self.repository.create(session, script_model)
        session.commit()
        stored = self.repository.get(session, created.id)
        return self._to_stored_response(stored)

    def create_and_parse_file(
        self,
        session: Session,
        raw_text: str,
        filename: Optional[str],
        content_type: Optional[str],
        title: Optional[str],
    ) -> StoredScriptResponse:
        parsed = self.parse_pipeline.parse_file(
            raw_text=raw_text,
            filename=filename,
            content_type=content_type,
            title=title or filename,
        )
        script_model = self._build_script_model(raw_text, parsed)
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
        enriched = self.parse_pipeline.parse_text(raw_text=script.raw_text, title=script.title)
        correction_responses = [self._to_correction_response(correction) for correction in script.corrections]

        scene_corrections: dict[str, list[CorrectionRecord]] = {}
        block_corrections: dict[str, list[CorrectionRecord]] = {}
        for correction in script.corrections:
            if correction.scene_id is not None:
                scene_corrections.setdefault(correction.scene_id, []).append(correction)
            if correction.block_id is not None:
                block_corrections.setdefault(correction.block_id, []).append(correction)

        ordered_scenes = sorted(script.scenes, key=lambda item: item.scene_number)
        for scene_payload, scene_model in zip(enriched.scenes, ordered_scenes):
            scene_payload.scene_id = scene_model.id
            scene_payload.original_heading = scene_model.heading
            scene_payload.heading = self._apply_corrections(scene_model.heading, scene_corrections.get(scene_model.id, []))
            scene_payload.corrections = [
                self._to_correction_response(correction) for correction in scene_corrections.get(scene_model.id, [])
            ]
            scene_payload.is_corrected = bool(scene_payload.corrections)

            ordered_blocks = sorted(scene_model.blocks, key=lambda item: item.element_index)
            for element_payload, block_model in zip(scene_payload.elements, ordered_blocks):
                block_history = block_corrections.get(block_model.id, [])
                element_payload.block_id = block_model.id
                element_payload.original_element_type = block_model.element_type
                element_payload.original_text = block_model.text
                element_payload.original_speaker = block_model.speaker
                element_payload.element_type = self._apply_corrections(
                    block_model.element_type,
                    [correction for correction in block_history if correction.corrected_field == "element_type"],
                )
                element_payload.text = self._apply_corrections(
                    block_model.text,
                    [correction for correction in block_history if correction.corrected_field == "text"],
                )
                element_payload.speaker = self._apply_corrections(
                    block_model.speaker,
                    [correction for correction in block_history if correction.corrected_field == "speaker"],
                )
                element_payload.corrections = [
                    self._to_correction_response(correction) for correction in block_history
                ]
                element_payload.is_corrected = bool(block_history)

        return StoredScriptResponse(
            id=script.id,
            title=script.title,
            raw_text=script.raw_text,
            total_scenes=enriched.total_scenes,
            total_elements=enriched.total_elements,
            scenes=enriched.scenes,
            warnings=enriched.warnings,
            characters=enriched.characters,
            validation=enriched.validation,
            corrections=correction_responses,
            created_at=script.created_at,
        )

    def _to_correction_response(self, correction: CorrectionRecord) -> CorrectionRecordResponse:
        target_id = correction.scene_id if correction.target_type == "scene" else correction.block_id
        return CorrectionRecordResponse(
            id=correction.id,
            target_type=correction.target_type,
            target_id=target_id or "",
            corrected_field=correction.corrected_field,
            old_value=correction.old_value,
            new_value=correction.new_value,
            timestamp=correction.created_at,
        )

    def _apply_corrections(
        self,
        original_value: Optional[str],
        corrections: list[CorrectionRecord],
    ) -> Optional[str]:
        current_value = original_value
        for correction in corrections:
            current_value = correction.new_value
        return current_value
