from copy import deepcopy

from app.evaluation.llm_fallback import OfflineLLMFallbackResolver
from app.evaluation.types import GoldScriptAnnotation, SystemMode, TaskPrediction
from app.schemas.parse import ParsedElement
from app.services.parsing.screenplay_parser import ScreenplayParser
from app.services.semantic.enricher import SemanticEnricher


class PredictionRunner:
    def __init__(self) -> None:
        self.parser = ScreenplayParser()
        self.semantic_enricher = SemanticEnricher()
        self.fallback = OfflineLLMFallbackResolver()

    def predict(self, annotation: GoldScriptAnnotation, mode: SystemMode) -> dict[str, list[TaskPrediction]]:
        parsed = self.parser.parse(annotation.raw_text, title=annotation.title)

        if mode in {"heuristic", "heuristic_llm_fallback"}:
            parsed = self.semantic_enricher.enrich(deepcopy(parsed))

        if mode == "heuristic_llm_fallback":
            character_map = {
                character.canonical_character_id: character
                for character in parsed.characters
            }
            parsed = self.fallback.apply(parsed, character_map)

        return {
            "speaker_attribution": self._collect_speaker_predictions(parsed),
            "mention_resolution": self._collect_mention_predictions(parsed),
            "action_attribution": self._collect_action_predictions(parsed),
        }

    def _collect_speaker_predictions(self, parsed) -> list[TaskPrediction]:
        predictions: list[TaskPrediction] = []
        for scene in parsed.scenes:
            for element in scene.elements:
                if element.element_type != "dialogue":
                    continue

                predicted_character = None
                candidates: list[str] = []
                status = "unresolved"
                confidence = 0.0

                if element.speaker_character_id and parsed.characters:
                    character = next(
                        (
                            item
                            for item in parsed.characters
                            if item.canonical_character_id == element.speaker_character_id
                        ),
                        None,
                    )
                    if character is not None:
                        predicted_character = character.canonical_name
                        status = "resolved"
                        confidence = 1.0
                elif element.speaker:
                    predicted_character = element.speaker.upper()
                    status = "resolved"
                    confidence = 0.8

                predictions.append(
                    TaskPrediction(
                        scene_number=scene.scene_number,
                        element_index=element.element_index,
                        resolution_status=status,
                        predicted_character=predicted_character,
                        candidate_characters=candidates,
                        attribution_confidence=confidence,
                    )
                )
        return predictions

    def _collect_mention_predictions(self, parsed) -> list[TaskPrediction]:
        predictions: list[TaskPrediction] = []
        for scene in parsed.scenes:
            for element in scene.elements:
                for mention in element.mentions:
                    candidate_names = [
                        candidate.canonical_name for candidate in mention.resolved_character_candidates
                    ]
                    predictions.append(
                        TaskPrediction(
                            scene_number=scene.scene_number,
                            element_index=element.element_index,
                            resolution_status=mention.resolution_status,
                            predicted_character=(
                                mention.resolved_character.canonical_name
                                if mention.resolved_character
                                else None
                            ),
                            candidate_characters=candidate_names,
                            mention_text=mention.mention_text,
                            attribution_confidence=mention.attribution_confidence,
                        )
                    )
        return predictions

    def _collect_action_predictions(self, parsed) -> list[TaskPrediction]:
        predictions: list[TaskPrediction] = []
        for scene in parsed.scenes:
            for element in scene.elements:
                if element.element_type != "action" or element.action_attribution is None:
                    continue
                candidate_names = [
                    candidate.canonical_name
                    for candidate in element.action_attribution.resolved_character_candidates
                ]
                predictions.append(
                    TaskPrediction(
                        scene_number=scene.scene_number,
                        element_index=element.element_index,
                        resolution_status=element.action_attribution.resolution_status,
                        predicted_character=(
                            element.action_attribution.resolved_character.canonical_name
                            if element.action_attribution.resolved_character
                            else None
                        ),
                        candidate_characters=candidate_names,
                        attribution_confidence=element.action_attribution.attribution_confidence,
                    )
                )
        return predictions
