from typing import Optional

from app.schemas.parse import ParsedScriptResponse
from app.schemas.validation import InputValidationResult
from app.services.parsing.screenplay_parser import ScreenplayParser
from app.services.semantic.enricher import SemanticEnricher
from app.services.validation.input_validator import InputValidator


class ValidatedParsePipeline:
    def __init__(
        self,
        parser: Optional[ScreenplayParser] = None,
        semantic_enricher: Optional[SemanticEnricher] = None,
        input_validator: Optional[InputValidator] = None,
    ) -> None:
        self.parser = parser or ScreenplayParser()
        self.semantic_enricher = semantic_enricher or SemanticEnricher()
        self.input_validator = input_validator or InputValidator()

    def parse_text(self, raw_text: str, title: Optional[str] = None) -> ParsedScriptResponse:
        validation = self.input_validator.validate_text_input(raw_text)
        self.input_validator.ensure_valid_or_raise(validation)
        return self._parse_and_enrich(raw_text, title, validation)

    def parse_file(
        self,
        raw_text: str,
        filename: Optional[str],
        content_type: Optional[str],
        title: Optional[str] = None,
    ) -> ParsedScriptResponse:
        validation = self.input_validator.validate_file_input(
            filename=filename,
            content_type=content_type,
            raw_text=raw_text,
        )
        self.input_validator.ensure_valid_or_raise(validation)
        return self._parse_and_enrich(raw_text, title or filename, validation)

    def validate_text(self, raw_text: str) -> InputValidationResult:
        return self.input_validator.validate_text_input(raw_text)

    def validate_file(
        self,
        filename: Optional[str],
        content_type: Optional[str],
        raw_text: Optional[str] = None,
    ) -> InputValidationResult:
        return self.input_validator.validate_file_input(
            filename=filename,
            content_type=content_type,
            raw_text=raw_text,
        )

    def _parse_and_enrich(
        self,
        raw_text: str,
        title: Optional[str],
        validation: InputValidationResult,
    ) -> ParsedScriptResponse:
        parsed = self.parser.parse(raw_text=raw_text, title=title)
        enriched = self.semantic_enricher.enrich(parsed)
        enriched.validation = validation
        return enriched
