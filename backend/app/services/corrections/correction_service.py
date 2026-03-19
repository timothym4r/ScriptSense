from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models.correction import CorrectionRecord
from app.repositories.correction_repository import CorrectionRepository
from app.repositories.script_repository import ScriptRepository
from app.schemas.correction import CreateCorrectionRequest
from app.schemas.script import StoredScriptResponse
from app.services.persistence.script_service import ScriptService

VALID_ELEMENT_TYPES = {
    "scene_heading",
    "action",
    "dialogue",
    "parenthetical",
    "transition",
}


class CorrectionService:
    def __init__(
        self,
        script_repository: Optional[ScriptRepository] = None,
        correction_repository: Optional[CorrectionRepository] = None,
        script_service: Optional[ScriptService] = None,
    ) -> None:
        self.script_repository = script_repository or ScriptRepository()
        self.correction_repository = correction_repository or CorrectionRepository()
        self.script_service = script_service or ScriptService(repository=self.script_repository)

    def create_correction(
        self,
        session: Session,
        script_id: str,
        request: CreateCorrectionRequest,
    ) -> Optional[StoredScriptResponse]:
        script = self.script_repository.get(session, script_id)
        if script is None:
            return None

        self._validate_request(request)
        old_value, scene_id, block_id = self._resolve_target(script, request)
        correction = CorrectionRecord(
            script_id=script.id,
            scene_id=scene_id,
            block_id=block_id,
            target_type=request.target_type,
            corrected_field=request.corrected_field,
            old_value=old_value,
            new_value=request.new_value,
        )
        self.correction_repository.create(session, correction)
        session.commit()
        refreshed = self.script_repository.get(session, script.id)
        return self.script_service._to_stored_response(refreshed)

    def _resolve_target(
        self,
        script,
        request: CreateCorrectionRequest,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        if request.target_type == "scene":
            scene = next((scene for scene in script.scenes if scene.id == request.target_id), None)
            if scene is None:
                raise ValueError("Scene not found for this script.")
            if request.corrected_field != "heading":
                raise ValueError("Scenes only support heading corrections.")
            old_value = self._current_scene_value(script, scene.id, request.corrected_field)
            return old_value, scene.id, None

        block = next((block for block in script.blocks if block.id == request.target_id), None)
        if block is None:
            raise ValueError("Block not found for this script.")
        old_value = self._current_block_value(script, block.id, request.corrected_field)
        return old_value, None, block.id

    def _current_scene_value(self, script, scene_id: str, corrected_field: str) -> Optional[str]:
        scene = next(scene for scene in script.scenes if scene.id == scene_id)
        current_value = getattr(scene, corrected_field)
        for correction in script.corrections:
            if correction.scene_id == scene_id and correction.corrected_field == corrected_field:
                current_value = correction.new_value
        return current_value

    def _current_block_value(self, script, block_id: str, corrected_field: str) -> Optional[str]:
        block = next(block for block in script.blocks if block.id == block_id)
        current_value = getattr(block, corrected_field)
        for correction in script.corrections:
            if correction.block_id == block_id and correction.corrected_field == corrected_field:
                current_value = correction.new_value
        return current_value

    def _validate_request(self, request: CreateCorrectionRequest) -> None:
        if request.corrected_field == "element_type" and request.new_value not in VALID_ELEMENT_TYPES:
            raise ValueError("Invalid block type.")
