import json
from pathlib import Path

from app.evaluation.types import GoldScriptAnnotation


def load_gold_annotations(data_dir: Path) -> list[GoldScriptAnnotation]:
    annotations: list[GoldScriptAnnotation] = []
    for path in sorted(data_dir.glob("*.json")):
        annotations.append(GoldScriptAnnotation.model_validate(json.loads(path.read_text())))
    return annotations
