from collections import defaultdict
from typing import Optional

from app.schemas.parse import ParsedScriptResponse
from app.schemas.semantic import CharacterRecord
from app.services.semantic.action_attributor import ActionAttributor
from app.services.semantic.character_registry import CharacterRegistryBuilder
from app.services.semantic.mention_extractor import MentionExtractor
from app.services.semantic.normalization import normalize_character_name
from app.services.semantic.resolver import MentionResolver


class SemanticEnricher:
    def __init__(
        self,
        registry_builder: Optional[CharacterRegistryBuilder] = None,
        mention_extractor: Optional[MentionExtractor] = None,
        mention_resolver: Optional[MentionResolver] = None,
        action_attributor: Optional[ActionAttributor] = None,
    ) -> None:
        self.registry_builder = registry_builder or CharacterRegistryBuilder()
        self.mention_extractor = mention_extractor or MentionExtractor()
        self.mention_resolver = mention_resolver or MentionResolver()
        self.action_attributor = action_attributor or ActionAttributor()

    def enrich(self, parsed: ParsedScriptResponse) -> ParsedScriptResponse:
        characters, alias_index = self.registry_builder.build(parsed)
        character_map: dict[str, CharacterRecord] = {
            character.canonical_character_id: character for character in characters
        }
        recent_scene_references: dict[int, list[str]] = defaultdict(list)

        for scene in parsed.scenes:
            for element in scene.elements:
                if element.speaker:
                    speaker_alias = normalize_character_name(element.speaker)
                    speaker_ids = alias_index.get(speaker_alias, [])
                    if len(speaker_ids) == 1:
                        element.speaker_character_id = speaker_ids[0]
                        recent_scene_references[scene.scene_number].insert(0, speaker_ids[0])

                if element.element_type != "action":
                    continue

                mentions = self.mention_extractor.extract(element, set(alias_index.keys()))
                resolved_mentions = []
                element_recent_character_ids: list[str] = []
                for mention in mentions:
                    resolved = self.mention_resolver.resolve(
                        mention=mention,
                        alias_index=alias_index,
                        character_map=character_map,
                        element_recent_character_ids=element_recent_character_ids,
                        recent_character_ids=recent_scene_references[scene.scene_number],
                    )
                    if resolved.canonical_character_id:
                        element_recent_character_ids.insert(0, resolved.canonical_character_id)
                        recent_scene_references[scene.scene_number].insert(0, resolved.canonical_character_id)
                        character_map[resolved.canonical_character_id].mention_count += 1
                    resolved_mentions.append(resolved)

                element.mentions = resolved_mentions
                element.action_attribution = self.action_attributor.attribute(
                    mentions=resolved_mentions,
                    character_map=character_map,
                )

        parsed.characters = sorted(
            character_map.values(),
            key=lambda item: (-item.dialogue_block_count, -item.mention_count, item.canonical_name),
        )
        return parsed
