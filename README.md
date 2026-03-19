# ScriptSense

ScriptSense is a portfolio-quality ML Engineering + NLP project focused on turning raw movie scripts into structured, queryable data.

The platform is designed to:

- ingest messy screenplay text
- segment scripts into scenes
- classify screenplay elements such as scene headings, action, dialogue, parentheticals, and transitions
- identify speakers for dialogue when possible
- extract character mentions, aliases, and action links
- preserve ambiguity with confidence scores and provenance
- expose the output through a production-style API

## Product Direction

The project follows a rules-first, ML-second strategy:

- use deterministic screenplay parsing for document structure
- use NLP/ML only where language ambiguity justifies it
- keep pipeline stages modular so rule-based and ML-assisted components can be compared

This is intentionally a monolithic, production-style system rather than a hackathon prototype or microservice-heavy architecture.

## MVP Scope

The MVP should:

- upload and store raw screenplay text
- normalize and parse screenplay structure
- persist scripts, scenes, elements, characters, and aliases
- expose query APIs for scripts, scenes, elements, and characters
- export structured JSON

The MVP should not attempt:

- robust global coreference resolution
- advanced semantic search
- background worker orchestration
- heavy model training infrastructure

## Core Tech Stack

- Backend: Python, FastAPI, Pydantic
- NLP/ML: spaCy, Hugging Face Transformers, sentence-transformers, PyTorch if needed
- Database: PostgreSQL
- Frontend: Next.js, TypeScript, Tailwind CSS
- Infra: Docker

## Repo Guide

- [Architecture](./docs/architecture.md)
- [Backend Structure](./docs/backend-structure.md)
- [Database Schema](./docs/schema.md)
- [API Design](./docs/api.md)
- [Roadmap](./docs/roadmap.md)
- [Task Board](./docs/task-board.md)
- [Agent Working Rules](./AGENTS.md)

## Best First Build Step

Start by defining the canonical intermediate representation and building a pure Python structural parser:

`parse_script(raw_text: str) -> ParsedScript`

That parser should produce:

- script metadata
- ordered scenes
- ordered elements
- parser warnings
- confidence and provenance for inferred fields

Do this before wiring FastAPI, PostgreSQL, or ML components. Everything else depends on it.

## Current Backend MVP

The Phase 1 backend now lives in [backend/README.md](./backend/README.md).

It includes:

- a FastAPI app with health and parsing endpoints
- a rules-based screenplay parser
- Pydantic response models
- sample screenplay fixtures
- parser and API tests

## Frontend Explorer

A lightweight Next.js inspector now lives in [frontend/README.md](./frontend/README.md).

It includes:

- a screenplay upload and paste flow
- a stored scripts list view
- a script detail explorer with scenes, blocks, raw text, and a simple character sidebar
- typed API integration with the FastAPI backend
