import re

from app.schemas.parse import ParsedElement
from app.schemas.semantic import EnrichedMention
from app.services.semantic.normalization import normalize_character_name

PRONOUNS = {
    "he",
    "him",
    "his",
    "she",
    "her",
    "hers",
    "they",
    "them",
    "their",
    "theirs",
}


class MentionExtractor:
    def extract(self, element: ParsedElement, known_aliases: set[str]) -> list[EnrichedMention]:
        if element.element_type != "action":
            return []

        mentions: list[EnrichedMention] = []
        occupied_spans: list[tuple[int, int]] = []

        for alias in sorted(known_aliases, key=len, reverse=True):
            if len(alias) < 2:
                continue
            if alias.lower() in PRONOUNS:
                continue
            pattern = re.compile(rf"\b{re.escape(alias.title())}\b|\b{re.escape(alias)}\b", re.IGNORECASE)
            for match in pattern.finditer(element.text):
                span = match.span()
                if self._overlaps(span, occupied_spans):
                    continue
                occupied_spans.append(span)
                alias_normalized = normalize_character_name(match.group(0))
                mention_type = "alias" if alias_normalized != normalize_character_name(match.group(0).upper()) else "name"
                mentions.append(
                    EnrichedMention(
                        mention_text=match.group(0),
                        mention_type=mention_type,
                    )
                )

        for match in re.finditer(r"\b(he|him|his|she|her|hers|they|them|their|theirs)\b", element.text, re.IGNORECASE):
            if self._overlaps(match.span(), occupied_spans):
                continue
            mentions.append(
                EnrichedMention(
                    mention_text=match.group(0),
                    mention_type="pronoun",
                )
            )

        return mentions

    def _overlaps(self, span: tuple[int, int], existing: list[tuple[int, int]]) -> bool:
        return any(not (span[1] <= other[0] or span[0] >= other[1]) for other in existing)
