import json
from pathlib import Path

from app.evaluation.parser_types import CorrectedScriptAnnotation


def load_corrected_annotations(data_dir: Path) -> list[CorrectedScriptAnnotation]:
    annotations: list[CorrectedScriptAnnotation] = []
    for path in sorted(data_dir.glob("*.json")):
        annotations.append(CorrectedScriptAnnotation.model_validate(json.loads(path.read_text())))
    return annotations
