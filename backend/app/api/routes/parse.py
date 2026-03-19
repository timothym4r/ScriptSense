from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.parse import ParseRequest, ParsedScriptResponse
from app.services.validation.parse_pipeline import ValidatedParsePipeline

router = APIRouter(tags=["parse"])

pipeline = ValidatedParsePipeline()


@router.post("/parse", response_model=ParsedScriptResponse)
def parse_script(request: ParseRequest) -> ParsedScriptResponse:
    parsed = pipeline.parse_text(raw_text=request.raw_text, title=request.title)
    return ParsedScriptResponse.model_validate(parsed)


@router.post("/parse-file", response_model=ParsedScriptResponse)
async def parse_script_file(
    script_file: Optional[UploadFile] = File(default=None),
    title: Optional[str] = Form(default=None),
) -> ParsedScriptResponse:
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

    parsed = pipeline.parse_file(
        raw_text=raw_text,
        filename=script_file.filename,
        content_type=script_file.content_type,
        title=title or script_file.filename,
    )
    return ParsedScriptResponse.model_validate(parsed)
