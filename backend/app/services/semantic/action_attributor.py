from app.schemas.semantic import (
    ActionAttribution,
    CharacterRecord,
    CharacterResolutionCandidate,
    EnrichedMention,
    ResolvedCharacterRef,
)


class ActionAttributor:
    def attribute(
        self,
        mentions: list[EnrichedMention],
        character_map: dict[str, CharacterRecord],
    ) -> ActionAttribution:
        explicit_resolved = [
            mention
            for mention in mentions
            if mention.mention_type in {"name", "alias"} and mention.resolution_status == "resolved"
        ]
        if explicit_resolved:
            chosen = explicit_resolved[0]
            character = character_map[chosen.canonical_character_id]
            return ActionAttribution(
                canonical_character_id=character.canonical_character_id,
                resolved_character=ResolvedCharacterRef(
                    canonical_character_id=character.canonical_character_id,
                    canonical_name=character.canonical_name,
                ),
                attribution_confidence=0.9,
                resolution_status="resolved",
                rationale="explicit character mention in action text",
            )

        pronoun_resolved = [
            mention for mention in mentions if mention.mention_type == "pronoun" and mention.resolution_status == "resolved"
        ]
        if pronoun_resolved:
            chosen = pronoun_resolved[0]
            character = character_map[chosen.canonical_character_id]
            return ActionAttribution(
                canonical_character_id=character.canonical_character_id,
                resolved_character=ResolvedCharacterRef(
                    canonical_character_id=character.canonical_character_id,
                    canonical_name=character.canonical_name,
                ),
                attribution_confidence=0.6,
                resolution_status="resolved",
                rationale="pronoun resolved from recent scene-local context",
            )

        ambiguous_candidates: list[CharacterResolutionCandidate] = []
        for mention in mentions:
            if mention.resolution_status == "ambiguous" and mention.resolved_character_candidates:
                ambiguous_candidates = mention.resolved_character_candidates
                break

        if ambiguous_candidates:
            return ActionAttribution(
                resolved_character_candidates=ambiguous_candidates,
                attribution_confidence=ambiguous_candidates[0].score,
                resolution_status="ambiguous",
                rationale="multiple plausible characters for this action",
            )

        return ActionAttribution(
            attribution_confidence=0.0,
            resolution_status="unresolved",
            rationale="no sufficiently strong character evidence in this action block",
        )
