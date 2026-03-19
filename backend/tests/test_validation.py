from app.services.validation.input_validator import InputValidator


def test_validator_accepts_screenplay_like_text() -> None:
    raw_text = """INT. KITCHEN - DAY

MIA
Where is Jonah?

JONAH
Right behind you.
"""
    result = InputValidator().validate_text_input(raw_text)

    assert result.is_supported_file_type is True
    assert result.is_likely_screenplay is True
    assert result.screenplay_confidence >= 0.45


def test_validator_rejects_non_screenplay_text() -> None:
    raw_text = """Meeting notes:

Quarterly revenue grew by 14 percent.
Action items:
- finalize hiring plan
- update the product roadmap
"""
    result = InputValidator().validate_text_input(raw_text)

    assert result.is_likely_screenplay is False
    assert result.rejection_reason is not None


def test_validator_marks_borderline_text_without_scene_headings() -> None:
    raw_text = """MIA
I don't know.

JONAH
Maybe we wait.
"""
    result = InputValidator().validate_text_input(raw_text)

    assert result.screenplay_confidence > 0.0
    assert result.screenplay_confidence < 0.6


def test_validator_rejects_unsupported_pdf_type_for_now() -> None:
    result = InputValidator().validate_file_input(
        filename="script.pdf",
        content_type="application/pdf",
        raw_text="INT. ROOM - DAY",
    )

    assert result.is_supported_file_type is False
    assert result.source_type == "pdf"
