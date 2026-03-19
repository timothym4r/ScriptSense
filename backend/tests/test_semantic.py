from app.services.parsing.screenplay_parser import ScreenplayParser
from app.services.semantic.enricher import SemanticEnricher


def test_semantic_enrichment_builds_character_registry_and_action_mentions() -> None:
    raw_text = """INT. KITCHEN - DAY

MIA
Where is Jonah?

Jonah enters with a torn envelope.
He drops it on the table.
"""
    parsed = ScreenplayParser().parse(raw_text=raw_text, title="Semantic Sample")
    enriched = SemanticEnricher().enrich(parsed)

    characters = {character.canonical_name: character for character in enriched.characters}
    assert "MIA" in characters
    assert "JONAH" in characters

    action_elements = [element for element in enriched.scenes[0].elements if element.element_type == "action"]
    assert len(action_elements) == 1
    mentions = action_elements[0].mentions
    assert [mention.mention_text for mention in mentions] == ["Jonah", "He"]
    assert mentions[0].resolution_status == "resolved"
    assert mentions[0].resolved_character.canonical_name == "JONAH"
    assert mentions[1].resolution_status == "resolved"
    assert action_elements[0].action_attribution.resolution_status == "resolved"
    assert action_elements[0].action_attribution.resolved_character.canonical_name == "JONAH"


def test_semantic_enrichment_preserves_ambiguity_for_pronouns() -> None:
    raw_text = """INT. OFFICE - NIGHT

MIA
Jonah is late.

JONAH
I'm here.

He closes the folder.
"""
    parsed = ScreenplayParser().parse(raw_text=raw_text)
    enriched = SemanticEnricher().enrich(parsed)

    action = next(element for element in enriched.scenes[0].elements if element.element_type == "action")
    pronoun = next(mention for mention in action.mentions if mention.mention_type == "pronoun")

    assert pronoun.resolution_status == "ambiguous"
    assert len(pronoun.resolved_character_candidates) >= 2
    assert action.action_attribution.resolution_status == "ambiguous"


def test_semantic_enrichment_links_speaker_to_canonical_character() -> None:
    raw_text = """INT. HALLWAY - NIGHT

DR. MAYA
Stay behind me.
"""
    parsed = ScreenplayParser().parse(raw_text=raw_text)
    enriched = SemanticEnricher().enrich(parsed)

    dialogue = next(element for element in enriched.scenes[0].elements if element.element_type == "dialogue")
    assert dialogue.speaker_character_id is not None
    character = next(
        character
        for character in enriched.characters
        if character.canonical_character_id == dialogue.speaker_character_id
    )
    assert character.canonical_name == "DR. MAYA"
    assert any(alias.normalized_alias == "MAYA" for alias in character.aliases)
