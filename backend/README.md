# ScriptSense Backend

Minimal FastAPI backend for Phase 1 of ScriptSense.

## What This MVP Does

- accepts pasted screenplay text
- accepts uploaded plaintext screenplay files
- parses scripts into scenes, action blocks, dialogue blocks, speakers, and parentheticals
- stores raw scripts and parsed outputs with SQLAlchemy
- enriches parsed output with a semantic attribution layer
- stores append-only manual correction records for review and audit
- returns structured JSON
- includes parser unit tests and API smoke tests
- includes parser evaluation using corrected review data

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

## Run Parser Evaluation

The backend now includes a structural parser evaluation track that compares:

- `raw_parser`: direct rules-based parser output
- `corrected_output`: the corrected review data itself, used as a sanity-check ceiling

### Gold / Corrected Data Format

Evaluation files live in `evaluation_data/parser_gold/` and contain:

- `raw_text`: the original screenplay text
- `corrected_scenes`: manually reviewed scene and block structure
- scene boundaries with `scene_number`, `heading`, `start_line`, `end_line`
- corrected blocks with `element_type`, `text`, `speaker`, `start_line`, `end_line`

This format is intentionally close to the platform's reviewed output so corrected data can later be exported into evaluation directly.

### Run the evaluator

```bash
python3 -m app.evaluation.parser_runner \
  --data-dir evaluation_data/parser_gold \
  --output-dir evaluation_data/parser_output \
  --modes raw_parser corrected_output
```

### What it measures

- `scene_detection`
  - exact match requires heading and line boundaries to match corrected output
- `speaker_attribution`
  - evaluated on dialogue blocks aligned by scene number and line span
- `block_type_classification`
  - evaluated on non-heading blocks aligned by scene number and line span

### Output

The runner writes:

- per-script JSON reports under `evaluation_data/parser_output/<mode>/`
- a combined summary report at `evaluation_data/parser_output/combined_report.json`

Example checked-in outputs:

- `evaluation_data/examples/parser_combined_report.json`
- `evaluation_data/examples/parser_mixed_case_error_report.json`

The error analysis output is intentionally inspectable. Each error includes:

- task name
- outcome (`missing`, `extra`, or `incorrect`)
- scene number / block span
- text excerpt when relevant
- corrected value vs predicted value
- a short explanation

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

### Save a manual correction

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/scripts/<script-id>/corrections" \
  -H "Content-Type: application/json" \
  -d '{
    "target_type": "block",
    "target_id": "<block-id>",
    "corrected_field": "text",
    "new_value": "Corrected dialogue line."
  }'
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

## Review And Correction Workflow

Stored script reads now preserve both:

- the original parsed structure stored in the database
- the latest corrected values produced by replaying append-only correction records

Each corrected scene or block includes:

- original values such as `original_heading`, `original_text`, and `original_speaker`
- `is_corrected`
- per-item `corrections`

The top-level stored script response also includes a full `corrections` audit list with:

- `corrected_field`
- `old_value`
- `new_value`
- `timestamp`

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

## Evaluation Framework

ScriptSense now includes a small but realistic local evaluation pipeline for speaker attribution, mention resolution, and action attribution.

### Gold annotation format

Gold examples live in `evaluation_data/gold/*.json`.

Each file contains:

- `script_id`
- `title`
- `raw_text`
- `speaker_attribution`
- `mention_resolution`
- `action_attribution`

Each annotation target is identified by:

- `scene_number`
- `element_index`
- optional `mention_text`
- optional `mention_occurrence`
- `resolution_status`
- `acceptable_characters`

This format keeps annotations explicit and easy to extend by hand.

### Evaluation modes

- `baseline`
  - parser-only output
  - dialogue speaker strings from the structural parser
  - no semantic mention or action attribution
- `heuristic`
  - semantic registry, mention extraction, pronoun resolution, and action attribution
- `heuristic_llm_fallback`
  - heuristic semantic layer plus an offline pluggable fallback resolver
  - this repo ships a deterministic local fallback so evaluation runs offline
  - it is the integration seam for a future real LLM-backed resolver

### Metrics

Each task reports:

- `exact_match`
- `ambiguous_match`
- `unresolved`
- `incorrect`
- `exact_match_rate`
- `ambiguity_aware_rate`
- `unresolved_rate`

The evaluation intentionally separates exact resolution from ambiguity-preserving partial success.

### Run evaluation

```bash
python3 -m app.evaluation.runner \
  --data-dir evaluation_data/gold \
  --output-dir evaluation_data/output \
  --modes baseline heuristic heuristic_llm_fallback
```

### Outputs

The runner prints summary metrics to stdout and writes JSON reports to `evaluation_data/output/`.

You will get:

- per-mode report files
- a combined report file
- inspectable non-exact cases for error analysis

Example error analysis fields include:

- task
- scene number
- element index
- mention text
- gold status
- predicted status
- gold characters
- predicted character
- predicted candidates
- outcome
- confidence

## Parser Assumptions And Limits

The structural parser is intentionally rules-based and optimized for readability and debuggability rather than full screenplay-format coverage.

Current assumptions:

- scene headings are typically uppercase and begin with `INT.`, `EXT.`, `INT/EXT.`, `EXT/INT.`, `I/E.`, or `EST.`
- dialogue cues are uppercase character lines followed by dialogue-like content
- short parenthetical lines inside dialogue are treated as parentheticals
- action blocks are grouped until a scene heading, transition, or dialogue cue interrupts them
- speaker suffixes such as `(V.O.)`, `(O.S.)`, and `CONT'D` are normalized for attribution

Realistic cases currently covered by tests:

- numbered scene headings such as `.INT. LAB - NIGHT #12#`
- voice-over speaker cues such as `JONAH (V.O.)`
- dialogue continuation with `MIA (CONT'D)`
- interleaved dialogue parentheticals such as `(beat)` and `(whispering)`
- uppercase action lines that should not be misread as character cues

Known limitations:

- screenplay formatting that depends heavily on indentation is not modeled yet
- centered text conventions are not explicitly detected
- dual dialogue is not supported
- highly nonstandard scene heading formats may still be missed
- parentheticals outside dialogue are treated conservatively as action text
- imported PDFs are not parsed directly yet; use extracted plaintext `.txt` screenplay files

## Input Validation Layer

Before parsing, ScriptSense now runs a rules-based validation step that answers two questions:

1. is this input type supported right now?
2. does the extracted text look enough like a screenplay to parse honestly?

Structured validation fields exposed in parse and stored-script responses:

- `is_supported_file_type`
- `is_likely_screenplay`
- `screenplay_confidence`
- `rejection_reason`
- `validation_signals`

Current supported input types:

- pasted text input
- plaintext `.txt` screenplay files

Currently rejected explicitly:

- PDF
- DOCX
- unknown file types

The validator looks for transparent structural screenplay cues such as:

- scene headings like `INT.` and `EXT.`
- uppercase character cue lines
- dialogue-like blocks
- parentheticals
- dialogue/action alternation
- screenplay transitions

If the confidence is too low, the backend returns a clear validation error instead of pretending to parse arbitrary text.

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
