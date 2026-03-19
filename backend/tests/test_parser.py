from pathlib import Path

from app.services.parsing.screenplay_parser import ScreenplayParser


def test_parser_extracts_scenes_dialogue_and_action(fixture_dir: Path) -> None:
    raw_text = (fixture_dir / "sample_screenplay.txt").read_text()
    parser = ScreenplayParser()

    result = parser.parse(raw_text=raw_text, title="Sample Screenplay")

    assert result.total_scenes == 2
    assert result.title == "Sample Screenplay"

    first_scene = result.scenes[0]
    assert first_scene.heading == "INT. COFFEE SHOP - DAY"

    dialogue_elements = [e for e in first_scene.elements if e.element_type == "dialogue"]
    assert len(dialogue_elements) == 2
    assert dialogue_elements[0].speaker == "MIA"
    assert "I should have called him back." in dialogue_elements[0].text
    assert dialogue_elements[1].speaker == "JONAH"

    action_elements = [e for e in first_scene.elements if e.element_type == "action"]
    assert len(action_elements) >= 2
    assert "Rain taps against the front window." in action_elements[0].text


def test_parser_normalizes_speaker_suffixes() -> None:
    raw_text = """EXT. CITY STREET - NIGHT

JONAH (V.O.)
Some nights never really end.
"""
    parser = ScreenplayParser()

    result = parser.parse(raw_text=raw_text)
    dialogue = next(e for e in result.scenes[0].elements if e.element_type == "dialogue")

    assert dialogue.speaker == "JONAH"


def test_parser_creates_single_inferred_scene_without_headings() -> None:
    raw_text = """A man waits by the train tracks.

SARAH
It's late.
"""
    parser = ScreenplayParser()

    result = parser.parse(raw_text=raw_text)

    assert result.total_scenes == 1
    assert result.scenes[0].heading is None
    assert result.warnings == ["No explicit scene headings found; returned a single inferred scene."]


def test_parser_recognizes_numbered_and_prefixed_scene_headings() -> None:
    raw_text = """.INT. LAB - NIGHT #12#

DR. MAYA
We're running out of time.
"""
    parser = ScreenplayParser()

    result = parser.parse(raw_text=raw_text)

    assert result.total_scenes == 1
    assert result.scenes[0].heading == ".INT. LAB - NIGHT #12#"
    assert result.scenes[0].elements[1].speaker == "DR. MAYA"


def test_uppercase_action_line_is_not_misclassified_as_character_cue() -> None:
    raw_text = """INT. WAREHOUSE - NIGHT

THE DOOR BURSTS OPEN.
Dust falls from the rafters.
"""
    parser = ScreenplayParser()

    result = parser.parse(raw_text=raw_text)

    elements = result.scenes[0].elements
    assert [element.element_type for element in elements] == ["scene_heading", "action"]
    assert "THE DOOR BURSTS OPEN." in elements[1].text


def test_parser_supports_interleaved_parentheticals_and_multiline_dialogue() -> None:
    raw_text = """INT. APARTMENT - NIGHT

MIA
(whispering)
I heard something.
(beat)
Did you hear it too?
It's coming from the hall.
"""
    parser = ScreenplayParser()

    result = parser.parse(raw_text=raw_text)

    scene_elements = result.scenes[0].elements
    assert [element.element_type for element in scene_elements] == [
        "scene_heading",
        "parenthetical",
        "dialogue",
        "parenthetical",
        "dialogue",
    ]
    assert scene_elements[2].text == "I heard something."
    assert scene_elements[4].text == "Did you hear it too?\nIt's coming from the hall."
    assert scene_elements[4].speaker == "MIA"


def test_parenthetical_outside_dialogue_stays_in_action_block() -> None:
    raw_text = """INT. STAGE - NIGHT

(A long beat.)
The audience waits in silence.
"""
    parser = ScreenplayParser()

    result = parser.parse(raw_text=raw_text)

    action = next(element for element in result.scenes[0].elements if element.element_type == "action")
    assert "(A long beat.)" in action.text
    assert "The audience waits in silence." in action.text


def test_character_cue_requires_following_dialogue_context() -> None:
    raw_text = """INT. OFFICE - DAY

MIA

The printer jams again.
"""
    parser = ScreenplayParser()

    result = parser.parse(raw_text=raw_text)

    action = next(element for element in result.scenes[0].elements if element.element_type == "action")
    assert "MIA" in action.text
    assert "The printer jams again." in action.text


def test_realistic_continued_dialogue_fixture_is_grouped_cleanly(fixture_dir: Path) -> None:
    raw_text = (fixture_dir / "continued_dialogue_screenplay.txt").read_text()

    result = ScreenplayParser().parse(raw_text=raw_text, title="Continued Dialogue")

    elements = result.scenes[0].elements
    assert [element.element_type for element in elements] == [
        "scene_heading",
        "dialogue",
        "parenthetical",
        "dialogue",
    ]
    assert elements[2].speaker == "MIA"
    assert elements[3].speaker == "MIA"
    assert elements[3].text == "Then again, maybe I can."


def test_realistic_numbered_scene_fixture_detects_multiple_scenes(fixture_dir: Path) -> None:
    raw_text = (fixture_dir / "numbered_scene_screenplay.txt").read_text()

    result = ScreenplayParser().parse(raw_text=raw_text, title="Numbered Scene")

    assert result.total_scenes == 2
    assert result.scenes[0].heading == ".INT. LAB - NIGHT #12#"
    assert result.scenes[1].heading == "EXT. ROOFTOP - CONTINUOUS"
    assert any(element.speaker == "DR. MAYA" for element in result.scenes[0].elements)


def test_realistic_voiceover_fixture_keeps_transition_outside_scene_count(fixture_dir: Path) -> None:
    raw_text = (fixture_dir / "voiceover_screenplay.txt").read_text()

    result = ScreenplayParser().parse(raw_text=raw_text, title="Voiceover")

    assert result.total_scenes == 1
    dialogue = next(element for element in result.scenes[0].elements if element.element_type == "dialogue")
    transition = next(element for element in result.scenes[0].elements if element.element_type == "transition")
    assert dialogue.speaker == "JONAH"
    assert transition.text == "CUT TO:"
