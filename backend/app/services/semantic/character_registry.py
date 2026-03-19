import re
from dataclasses import dataclass, field

from app.schemas.parse import ParsedScriptResponse
from app.schemas.semantic import CharacterAliasRecord, CharacterRecord
from app.services.semantic.normalization import derive_alias_variants, normalize_character_name

PRONOUN_BLOCKLIST = {"HE", "HIM", "HIS", "SHE", "HER", "HERS", "THEY", "THEM", "THEIR", "THEIRS"}


@dataclass
class RegistryCharacter:
    canonical_character_id: str
    canonical_name: str
    aliases: dict[str, CharacterAliasRecord] = field(default_factory=dict)
    source_types: set[str] = field(default_factory=set)
    dialogue_block_count: int = 0
    mention_count: int = 0


class CharacterRegistryBuilder:
    def build(self, parsed: ParsedScriptResponse) -> tuple[list[CharacterRecord], dict[str, list[str]]]:
        registry: dict[str, RegistryCharacter] = {}
        alias_index: dict[str, list[str]] = {}
        next_id = 1

        def get_or_create_character(name: str, source_type: str, confidence: float, alias_type: str) -> str:
            nonlocal next_id
            normalized = normalize_character_name(name)
            if not normalized:
                return ""

            matched_id = alias_index.get(normalized, [None])[0]
            if matched_id is None:
                matched_id = f"char_{next_id:03d}"
                next_id += 1
                registry[matched_id] = RegistryCharacter(
                    canonical_character_id=matched_id,
                    canonical_name=normalized,
                )

            character = registry[matched_id]
            character.source_types.add(source_type)
            for alias in derive_alias_variants(name):
                existing = character.aliases.get(alias)
                if existing is None or existing.confidence < confidence:
                    character.aliases[alias] = CharacterAliasRecord(
                        alias_text=alias,
                        normalized_alias=alias,
                        alias_type=alias_type,
                        confidence=confidence,
                    )
                alias_index.setdefault(alias, [])
                if matched_id not in alias_index[alias]:
                    alias_index[alias].append(matched_id)
            return matched_id

        for scene in parsed.scenes:
            for element in scene.elements:
                if element.speaker:
                    character_id = get_or_create_character(
                        element.speaker,
                        source_type="speaker",
                        confidence=1.0,
                        alias_type="speaker",
                    )
                    if character_id:
                        registry[character_id].dialogue_block_count += int(
                            element.element_type == "dialogue"
                        )

        for scene in parsed.scenes:
            for element in scene.elements:
                if element.element_type != "action":
                    continue
                for candidate in self._extract_candidate_action_names(element.text):
                    get_or_create_character(
                        candidate,
                        source_type="action_mention",
                        confidence=0.55,
                        alias_type="action_mention",
                    )

        records = [
            CharacterRecord(
                canonical_character_id=character.canonical_character_id,
                canonical_name=character.canonical_name,
                aliases=sorted(character.aliases.values(), key=lambda item: (-item.confidence, item.alias_text)),
                source_types=sorted(character.source_types),
                dialogue_block_count=character.dialogue_block_count,
                mention_count=character.mention_count,
            )
            for character in registry.values()
        ]
        records.sort(key=lambda item: (item.canonical_name, item.canonical_character_id))
        return records, alias_index

    def _extract_candidate_action_names(self, text: str) -> list[str]:
        candidates: list[str] = []
        blocked = {
            "THE",
            "A",
            "AN",
            "DAY",
            "NIGHT",
            "MORNING",
            "EVENING",
            "NOON",
            "RAIN",
            "CARS",
            "WINDOW",
            "DOOR",
            "ROOM",
            "HALL",
            "CITY",
        }
        for raw in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text):
            normalized = normalize_character_name(raw)
            if normalized in blocked or normalized in PRONOUN_BLOCKLIST:
                continue
            candidates.append(raw)
        return candidates
