# ScriptSense Backend

Minimal FastAPI backend for Phase 1 of ScriptSense.

## What This MVP Does

- accepts pasted screenplay text
- accepts uploaded plaintext screenplay files
- parses scripts into scenes, action blocks, dialogue blocks, speakers, and parentheticals
- stores raw scripts and parsed outputs with SQLAlchemy
- enriches parsed output with a semantic attribution layer
- returns structured JSON
- includes parser unit tests and API smoke tests

## Tech Stack

- Python 3.9+
- FastAPI
- Pydantic
- pytest
- SQLAlchemy
- PostgreSQL
- heuristic semantic enrichment modules

## Run Locally

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements-dev.txt
```

### 3. Configure the database

For local persistence, set `DATABASE_URL`.

PostgreSQL example:

```bash
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/scriptsense"
```

SQLite fallback for quick local testing:

```bash
export DATABASE_URL="sqlite:///./scriptsense.db"
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Run Tests

```bash
pytest
```

## Example Request

### Parse pasted script text

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sample Screenplay",
    "raw_text": "INT. ROOM - DAY\n\nMIA\n(whispering)\nHello.\n"
  }'
```

### Create and store a parsed script

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/scripts" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sample Screenplay",
    "raw_text": "INT. ROOM - DAY\n\nMIA\nHello.\n"
  }'
```

### Parse a plaintext file

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/parse-file" \
  -F "title=Sample Upload" \
  -F "script_file=@tests/fixtures/sample_screenplay.txt;type=text/plain"
```

### Create and store from a plaintext file

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/scripts/file" \
  -F "title=Sample Upload" \
  -F "script_file=@tests/fixtures/sample_screenplay.txt;type=text/plain"
```

### List stored scripts

```bash
curl "http://127.0.0.1:8000/api/v1/scripts"
```

### Fetch one stored script

```bash
curl "http://127.0.0.1:8000/api/v1/scripts/<script-id>"
```

## Example Response

```json
{
  "title": "Sample Screenplay",
  "total_scenes": 1,
  "total_elements": 3,
  "scenes": [
    {
      "scene_number": 1,
      "heading": "INT. ROOM - DAY",
      "start_line": 1,
      "end_line": 5,
      "elements": [
        {
          "element_index": 1,
          "element_type": "scene_heading",
          "text": "INT. ROOM - DAY",
          "start_line": 1,
          "end_line": 1,
          "speaker": null
        },
        {
          "element_index": 2,
          "element_type": "parenthetical",
          "text": "(whispering)",
          "start_line": 4,
          "end_line": 4,
          "speaker": "MIA"
        },
        {
          "element_index": 3,
          "element_type": "dialogue",
          "text": "Hello.",
          "start_line": 5,
          "end_line": 5,
          "speaker": "MIA"
        }
      ]
    }
  ],
  "warnings": [],
  "characters": [
    {
      "canonical_character_id": "char_001",
      "canonical_name": "MIA",
      "aliases": [
        {
          "alias_text": "MIA",
          "normalized_alias": "MIA",
          "alias_type": "speaker",
          "confidence": 1.0
        }
      ],
      "source_types": ["speaker"],
      "dialogue_block_count": 1,
      "mention_count": 0
    }
  ]
}
```

## Semantic Enrichment Layer

The backend now applies a semantic enrichment pass after the rules-based parser finishes. The parser remains the baseline structural system; enrichment is layered on top of the parsed scene and block stream.

Current enrichment behavior:

- builds a canonical character registry from speaker cues and action mentions
- normalizes simple alias variants such as title-stripped names
- extracts mentions from action and description blocks
- attempts scene-local pronoun and reference resolution when there is enough evidence
- attributes action blocks to likely characters
- preserves ambiguity with candidate lists and explicit resolution status fields

Key enriched fields include:

- `speaker_character_id`
- `characters`
- `mentions`
- `canonical_character_id`
- `mention_text`
- `mention_type`
- `resolved_character`
- `resolved_character_candidates`
- `attribution_confidence`
- `resolution_status`
- `action_attribution`

Example enriched action block fragment:

```json
{
  "element_type": "action",
  "text": "Jonah enters with a torn envelope. He drops it on the table.",
  "mentions": [
    {
      "canonical_character_id": "char_002",
      "mention_text": "Jonah",
      "mention_type": "name",
      "resolved_character": {
        "canonical_character_id": "char_002",
        "canonical_name": "JONAH"
      },
      "resolved_character_candidates": [],
      "attribution_confidence": 0.78,
      "resolution_status": "resolved"
    },
    {
      "canonical_character_id": "char_002",
      "mention_text": "He",
      "mention_type": "pronoun",
      "resolved_character": {
        "canonical_character_id": "char_002",
        "canonical_name": "JONAH"
      },
      "resolved_character_candidates": [],
      "attribution_confidence": 0.58,
      "resolution_status": "resolved"
    }
  ],
  "action_attribution": {
    "canonical_character_id": "char_002",
    "resolved_character": {
      "canonical_character_id": "char_002",
      "canonical_name": "JONAH"
    },
    "resolved_character_candidates": [],
    "attribution_confidence": 0.9,
    "resolution_status": "resolved",
    "rationale": "explicit character mention in action text"
  }
}
```

## Project Layout

```text
backend/
  alembic/
  app/
    api/routes/
    db/
    repositories/
    schemas/
    services/parsing/
    services/persistence/
    main.py
  tests/
    fixtures/
  pyproject.toml
```
