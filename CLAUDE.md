# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

---

## Role

CTO / Architect. Follows the four-phase protocol defined in `~/.claude/CLAUDE.md`: Assess & Plan → Build → Verify → Ship.

## Session Protocol
1. Read `ROADMAP.md` for current phase and status
2. Read `SESSION_LOG.md` (most recent entry) for temporal continuity
3. Check for active plans in `_strategy/plans/`
4. If session is getting long (>30 messages): *"Run `/compact` to preserve context."*

### Model Tiering
Follows the Mandatory Model Gate defined in `~/.claude/CLAUDE.md`.

---

## What is this?

Arezzo is a deterministic compiler for Google Docs API operations, built by
Convergent Methods, LLC. It compiles semantic agent-intent operations into
correct Google Docs API `batchUpdate` request sequences with proper UTF-16
index arithmetic, element address resolution, and OT-compatible mutation
ordering.

Named after Guido d'Arezzo (~991–1033), the monk who standardized music
notation — turning vague melodic intent into precise, portable notation.
Arezzo does the same for document operations.

**One-sentence thesis:** Deterministic layers turn silent wrongness into
loud correctness failures.

---

## Architectural Principles

1. Arezzo NEVER reasons. The host LLM reasons. Arezzo compiles.
2. All compilation is deterministic — same input always produces same output.
3. The engine modules (`compiler.py`, `parser.py`, `address.py`, `index.py`)
   are the deterministic core. They must never import from the MCP layer.
4. The MCP layer (`server.py`) is a thin wrapper that calls into the engine.
5. Arezzo sits BETWEEN the agent and the Google Docs API. It is a compiler,
   not a plugin.
6. Two-phase compilation: content mutations first (reverse index order),
   then format mutations (index-neutral, appended after content).

---

## Master Planning Document

`_strategy/ARCHITECTURE.md` is the locked architecture document (from Will + Opus).
`ROADMAP.md` is the ops layer roadmap. `_strategy/plans/` holds phase-level
execution plans when they exist.

---

## Ops Layer

This project uses the Convergent Methods ops layer protocol. The canonical
protocol definition lives in the CM root CLAUDE.md
(`/Users/willwright/ConvergentMethods/CLAUDE.md`). Follow all ops layer
behaviors defined there: session boot sequence, session end protocol,
amendment protocol, session log rotation, status bar, and directory scope
rules.

On session boot, read `ROADMAP.md` and `SESSION_LOG.md` at the repo root
before doing any work. These files govern phase sequencing and session
continuity.

**Upward propagation paths:** When a propagation event occurs (phase
completion, external publish, blocking status change, HITL gate
reached/cleared — see CM root CLAUDE.md for full list), update these
CEO-level docs before the session ends:
- `/Users/willwright/ConvergentMethods/MASTER.md` — this project's workstream entry
- `/Users/willwright/ConvergentMethods/OPUS_BRIEF.md` — this project's portfolio brief entry

**Status bar:** Every response footer must include, alongside existing lines
(docs updated, persistence receipts, timestamp):
```
Project: Arezzo | Phase: [current phase from ROADMAP.md]
```

---

## Repo Folder Visibility Convention

Every top-level folder signals its audience by its prefix:

| Prefix | Audience | Examples |
|---|---|---|
| `_name/` | **Internal only** — planning, strategy, research, review artifacts. Never referenced in public docs. | `_strategy/` |
| `name/` (no prefix) | **Public / contributor-visible** — source, tests, docs, fixtures. What a user sees on GitHub. | `arezzo/`, `fixtures/`, `scripts/` |
| `.name/` | **Runtime / tooling** — config files, generated data, IDE/tool artifacts. Usually gitignored or system-managed. | `.venv/`, `.pytest_cache/` |

---

## Key Directories

```
arezzo/                    # Project root
├── arezzo/                # Python package (source code)
│   ├── server.py          # MCP server — 3 tools
│   ├── compiler.py        # compile_operations() entry point
│   ├── parser.py          # ParsedDocument with pre-built indexes
│   ├── address.py         # 6 address resolution modes
│   ├── index.py           # UTF-16 arithmetic, surrogate pair handling
│   ├── errors.py          # Error hierarchy
│   ├── auth.py            # OAuth2 credential management
│   ├── cli.py             # CLI entry point (serve/init/version)
│   ├── setup.py           # arezzo init wizard + platform configs
│   ├── operations/        # Operation compiler modules
│   │   ├── text.py        # insert, delete, replace_all, replace_section
│   │   ├── format.py      # text style, paragraph style, bullets
│   │   ├── structure.py   # tables, lists, page breaks
│   │   ├── objects.py     # images, headers, footers, footnotes
│   │   └── organization.py # named ranges
│   └── tests/             # 210 unit tests
├── _strategy/             # Internal planning & review docs
│   ├── ARCHITECTURE.md    # Locked architecture (Will + Opus)
│   ├── OPUS_REVIEW_RESPONSE.md   # Code review for Opus
│   ├── OPUS_SOURCE_REVIEW.md     # Source code package for Opus review
│   ├── plans/             # Phase-level execution plans
│   ├── research/          # Phase 1 findings & operation catalog
│   │   ├── FINDINGS.md
│   │   └── OPERATION_CATALOG.md
│   └── history/           # Historical logs (future rotation)
├── fixtures/              # Phase 1 test fixtures (documents.get JSON)
├── scripts/               # Dev utilities (not part of package)
│   ├── auth.py            # Standalone auth for scripts
│   ├── create_fixtures.py
│   ├── pull_fixtures.py
│   ├── capture_mutations.py
│   ├── validate_live.py   # Phase 3 live API validation
│   └── validate_mcp.py    # Phase 4 live MCP validation
├── CLAUDE.md              # CC behavioral protocol (this file)
├── ROADMAP.md             # Ops layer roadmap
├── SESSION_LOG.md         # Ops layer session log
├── OPUS_BRIEF.md          # Strategic briefing for Opus
├── README.md              # Public-facing
├── LICENSE                # MIT
└── pyproject.toml         # Package metadata + deps
```

---

## Tech Stack
- Python 3.12+, uv for environment management
- Google Docs API v1
- MCP SDK (`mcp>=1.26.0`) for the server layer
- Google auth libraries (`google-auth`, `google-auth-oauthlib`, `google-api-python-client`)

## Key Commands
```bash
uv run pytest                              # Run all 210 tests
uv run pytest arezzo/tests/test_server.py  # MCP server tests only
uv run python scripts/validate_live.py     # Phase 3 live API validation (needs creds)
uv run python scripts/validate_mcp.py      # Phase 4 live MCP validation (needs creds)
```

## Scope
- Google Docs is the sole target for the initial product
- Google Slides, Forms, and other Workspace products are validated
  future expansions, not current scope

## Conventions
- Vim references in all instructions, never nano
- Ruff for linting/formatting
- All commits should be atomic and descriptive

## Owner
Will — will@convergentmethods.com
Convergent Methods, LLC
