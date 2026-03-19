from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.correction import CreateCorrectionRequest
from app.schemas.parse import ParseRequest
from app.schemas.script import StoredScriptResponse, StoredScriptSummary
from app.services.corrections.correction_service import CorrectionService
from app.services.persistence.script_service import ScriptService

router = APIRouter(prefix="/scripts", tags=["scripts"])

service = ScriptService()
correction_service = CorrectionService()


@router.post("", response_model=StoredScriptResponse, status_code=status.HTTP_201_CREATED)
def create_script(
    request: ParseRequest,
    session: Session = Depends(get_db),
) -> StoredScriptResponse:
    return service.create_and_parse(session, request)


@router.post("/file", response_model=StoredScriptResponse, status_code=status.HTTP_201_CREATED)
async def create_script_from_file(
    script_file: Optional[UploadFile] = File(default=None),
    title: Optional[str] = Form(default=None),
    session: Session = Depends(get_db),
) -> StoredScriptResponse:
    if script_file is None:
        raise HTTPException(status_code=400, detail="script_file is required")

    raw_bytes = await script_file.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Only UTF-8 plaintext screenplay files are supported.",
        ) from exc

    return service.create_and_parse_file(
        session=session,
        raw_text=raw_text,
        filename=script_file.filename,
        content_type=script_file.content_type,
        title=title,
    )


@router.get("", response_model=list[StoredScriptSummary])
def list_scripts(session: Session = Depends(get_db)) -> list[StoredScriptSummary]:
    return service.list_scripts(session)


@router.get("/{script_id}", response_model=StoredScriptResponse)
def get_script(script_id: str, session: Session = Depends(get_db)) -> StoredScriptResponse:
    script = service.get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.post("/{script_id}/corrections", response_model=StoredScriptResponse)
def create_correction(
    script_id: str,
    request: CreateCorrectionRequest,
    session: Session = Depends(get_db),
) -> StoredScriptResponse:
    try:
        updated = correction_service.create_correction(session, script_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return updated
