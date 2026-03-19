from app.schemas.parse import ParsedElement, ParsedScriptResponse
from app.schemas.semantic import ActionAttribution, CharacterRecord, CharacterResolutionCandidate, EnrichedMention, ResolvedCharacterRef


class OfflineLLMFallbackResolver:
    """A pluggable offline fallback that stands in for a future LLM-backed resolver.

    This keeps evaluation runnable locally while preserving a clear integration seam for a
    real model-backed fallback later.
    """

    def apply(
        self,
        parsed: ParsedScriptResponse,
        character_map: dict[str, CharacterRecord],
    ) -> ParsedScriptResponse:
        scene_speakers = self._build_scene_speaker_index(parsed)

        for scene in parsed.scenes:
            fallback_candidates = scene_speakers.get(scene.scene_number, [])
            if not fallback_candidates:
                continue

            for element in scene.elements:
                self._apply_mention_fallback(element, fallback_candidates, character_map)
                self._apply_action_fallback(element, fallback_candidates, character_map)

        return parsed

    def _build_scene_speaker_index(self, parsed: ParsedScriptResponse) -> dict[int, list[str]]:
        speaker_ids_by_scene: dict[int, list[str]] = {}
        for scene in parsed.scenes:
            speaker_ids: list[str] = []
            for element in scene.elements:
                if element.speaker_character_id and element.speaker_character_id not in speaker_ids:
                    speaker_ids.append(element.speaker_character_id)
            speaker_ids_by_scene[scene.scene_number] = speaker_ids
        return speaker_ids_by_scene

    def _apply_mention_fallback(
        self,
        element: ParsedElement,
        fallback_candidates: list[str],
        character_map: dict[str, CharacterRecord],
    ) -> None:
        if not element.mentions:
            return

        if len(fallback_candidates) != 1:
            return

        chosen_id = fallback_candidates[0]
        chosen_character = character_map[chosen_id]

        for mention in element.mentions:
            if mention.resolution_status != "unresolved":
                continue
            mention.canonical_character_id = chosen_id
            mention.resolved_character = ResolvedCharacterRef(
                canonical_character_id=chosen_id,
                canonical_name=chosen_character.canonical_name,
            )
            mention.attribution_confidence = 0.45
            mention.resolution_status = "resolved"

    def _apply_action_fallback(
        self,
        element: ParsedElement,
        fallback_candidates: list[str],
        character_map: dict[str, CharacterRecord],
    ) -> None:
        if element.element_type != "action" or element.action_attribution is None:
            return

        if element.action_attribution.resolution_status == "resolved":
            return

        if len(fallback_candidates) == 1:
            chosen_id = fallback_candidates[0]
            chosen_character = character_map[chosen_id]
            element.action_attribution = ActionAttribution(
                canonical_character_id=chosen_id,
                resolved_character=ResolvedCharacterRef(
                    canonical_character_id=chosen_id,
                    canonical_name=chosen_character.canonical_name,
                ),
                attribution_confidence=0.42,
                resolution_status="resolved",
                rationale="offline llm-fallback heuristic selected the dominant scene speaker",
            )
            return

        if len(fallback_candidates) > 1 and element.action_attribution.resolution_status == "unresolved":
            candidates = [
                CharacterResolutionCandidate(
                    canonical_character_id=candidate_id,
                    canonical_name=character_map[candidate_id].canonical_name,
                    score=round(1 / len(fallback_candidates), 2),
                    rationale="offline llm-fallback heuristic considered scene speakers",
                )
                for candidate_id in fallback_candidates
            ]
            element.action_attribution = ActionAttribution(
                resolved_character_candidates=candidates,
                attribution_confidence=candidates[0].score,
                resolution_status="ambiguous",
                rationale="offline llm-fallback heuristic found multiple plausible scene speakers",
            )
