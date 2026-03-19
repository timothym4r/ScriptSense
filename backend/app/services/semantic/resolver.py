from app.schemas.semantic import (
    CharacterRecord,
    CharacterResolutionCandidate,
    EnrichedMention,
    ResolvedCharacterRef,
)
from app.services.semantic.normalization import normalize_character_name


class MentionResolver:
    def resolve(
        self,
        mention: EnrichedMention,
        alias_index: dict[str, list[str]],
        character_map: dict[str, CharacterRecord],
        element_recent_character_ids: list[str],
        recent_character_ids: list[str],
    ) -> EnrichedMention:
        if mention.mention_type in {"name", "alias"}:
            return self._resolve_explicit(mention, alias_index, character_map)
        return self._resolve_pronoun(
            mention,
            character_map,
            element_recent_character_ids,
            recent_character_ids,
        )

    def _resolve_explicit(
        self,
        mention: EnrichedMention,
        alias_index: dict[str, list[str]],
        character_map: dict[str, CharacterRecord],
    ) -> EnrichedMention:
        normalized = normalize_character_name(mention.mention_text)
        candidate_ids = alias_index.get(normalized, [])
        if len(candidate_ids) == 1:
            character = character_map[candidate_ids[0]]
            mention.canonical_character_id = character.canonical_character_id
            mention.resolved_character = ResolvedCharacterRef(
                canonical_character_id=character.canonical_character_id,
                canonical_name=character.canonical_name,
            )
            mention.attribution_confidence = 0.95 if "speaker" in character.source_types else 0.78
            mention.resolution_status = "resolved"
            return mention

        if len(candidate_ids) > 1:
            mention.resolved_character_candidates = [
                CharacterResolutionCandidate(
                    canonical_character_id=candidate_id,
                    canonical_name=character_map[candidate_id].canonical_name,
                    score=round(1 / len(candidate_ids), 2),
                    rationale="multiple alias matches",
                )
                for candidate_id in candidate_ids
            ]
            mention.attribution_confidence = 0.4
            mention.resolution_status = "ambiguous"
        return mention

    def _resolve_pronoun(
        self,
        mention: EnrichedMention,
        character_map: dict[str, CharacterRecord],
        element_recent_character_ids: list[str],
        recent_character_ids: list[str],
    ) -> EnrichedMention:
        local_unique_recent = []
        for candidate_id in element_recent_character_ids:
            if candidate_id not in local_unique_recent:
                local_unique_recent.append(candidate_id)

        if len(local_unique_recent) == 1:
            character = character_map[local_unique_recent[0]]
            mention.canonical_character_id = character.canonical_character_id
            mention.resolved_character = ResolvedCharacterRef(
                canonical_character_id=character.canonical_character_id,
                canonical_name=character.canonical_name,
            )
            mention.attribution_confidence = 0.72
            mention.resolution_status = "resolved"
            return mention

        if len(local_unique_recent) > 1:
            mention.resolved_character_candidates = [
                CharacterResolutionCandidate(
                    canonical_character_id=candidate_id,
                    canonical_name=character_map[candidate_id].canonical_name,
                    score=round(1 / len(local_unique_recent), 2),
                    rationale="multiple explicit character mentions in the same action block",
                )
                for candidate_id in local_unique_recent
            ]
            mention.attribution_confidence = mention.resolved_character_candidates[0].score
            mention.resolution_status = "ambiguous"
            return mention

        unique_recent = []
        for candidate_id in recent_character_ids:
            if candidate_id not in unique_recent:
                unique_recent.append(candidate_id)

        if len(unique_recent) == 1:
            character = character_map[unique_recent[0]]
            mention.canonical_character_id = character.canonical_character_id
            mention.resolved_character = ResolvedCharacterRef(
                canonical_character_id=character.canonical_character_id,
                canonical_name=character.canonical_name,
            )
            mention.attribution_confidence = 0.58
            mention.resolution_status = "resolved"
            return mention

        if len(unique_recent) > 1:
            scored = []
            for index, candidate_id in enumerate(unique_recent[:3]):
                score = round(max(0.2, 0.6 - (index * 0.15)), 2)
                scored.append(
                    CharacterResolutionCandidate(
                        canonical_character_id=candidate_id,
                        canonical_name=character_map[candidate_id].canonical_name,
                        score=score,
                        rationale="scene-local pronoun context",
                    )
                )
            mention.resolved_character_candidates = scored
            mention.attribution_confidence = scored[0].score
            mention.resolution_status = "ambiguous"
        return mention
