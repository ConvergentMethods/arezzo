# Arezzo Roadmap

> Ops layer roadmap. See CM root CLAUDE.md for protocol definition.
> Will authors phases and gate types. CC maintains status and proposes amendments.

## Current Phase
Phase: Post-publish — Distribution & Testing
Status: PUBLISHED v0.1.0 to PyPI (2026-03-27). Opus code review items implemented. Remaining: cross-platform MCP client testing (Will), MCP directory submissions (Will), domain decision (arezzo.dev taken).

## Phases

### Phase 1: Problem Cartography
- **Done condition:** fixtures/ contains documents.get JSON outputs for all
  complexity ladder rungs, OPERATION_CATALOG.md maps every identified
  operation to its API call sequence, write-side input/output pairs captured.
- **Gate to next phase:** HITL
- **Status:** complete (2026-03-24)
- **Deliverables:**
  - `fixtures/` — 13 document fixtures (JSON) + manifest
  - `fixtures/mutations/` — 23 write-side input/output pairs
  - `OPERATION_CATALOG.md` — 23 operations mapped to API sequences
  - `FINDINGS.md` — surprises, patterns, hard edges, Phase 2 recommendations
  - `pull_fixtures.py`, `create_fixtures.py`, `capture_mutations.py`

### Phase 2: Compiler Engine
- **Done condition:** ARCHITECTURE.md committed. Deterministic compilation
  engine passes tests for all 23 operations against fixture corpus.
- **Gate to next phase:** HITL — Will reviews compiler output against manual
  batchUpdate construction for 3 representative operations.
- **Status:** complete (2026-03-24) — 191 tests passing
- **Build sequence:**
  - [x] Step 1: Foundation (errors.py, ARCHITECTURE.md)
  - [x] Step 2: Parser (59 tests)
  - [x] Step 3: Address Resolver (21 tests)
  - [x] Step 4: Index Arithmetic (34 tests)
  - [x] Step 5: Text Operations (16 tests)
  - [x] Step 6: Format Operations (10 tests)
  - [x] Step 7: Structure Operations (16 tests)
  - [x] Step 8: Object Operations (7 tests)
  - [x] Step 9: Organization Operations (8 tests)
  - [x] Step 10: Compiler Integration (20 tests)

### Phase 3: Validation & Hardening
- **Done condition:** Live API testing against real Google Docs. Compiler
  output executed via batchUpdate produces expected document mutations.
- **Gate to next phase:** HITL
- **Status:** complete (2026-03-24) — 8/8 live validations passing
- **Note:** Phase 2 HITL review (Will reviews compiler output for 3
  representative operations) is deferred — Will catches up async.
- **Validations:** insert_text_after_heading, replace_all_text,
  apply_bold_and_insert, insert_table, create_named_range,
  insert_bullet_list, create_header_footer, insert_page_break

### Phase 4: MCP Server Layer
- **Done condition:** Engine wrapped as MCP tools. Tool descriptions receive
  behavioral advertising treatment from Boyce framework. End-to-end test:
  agent issues semantic operation → Arezzo compiles → valid batchUpdate
  executes against a real Google Doc.
- **Gate to next phase:** HITL — Cross-platform MCP client testing.
  **Deferred (2026-03-27):** Will authorized CC to continue building through
  Phase 5 before HITL review. Gate still exists; review happens after build
  phases complete.
- **Status:** complete (2026-03-27) — 19 unit tests + 6/6 live MCP validations passing
- **Build progress:**
  - [x] MCP server with 3 tools (read_document, edit_document, validate_operations)
  - [x] Behavioral advertising framework (preamble, two-register descriptions, response layer)
  - [x] Response builders (next_step, present_to_user, document_reality)
  - [x] Structural map builder (headings, named ranges, tables, bookmarks)
  - [x] Unit tests for response layer and structural map (19 tests)
  - [x] Auth module packaging (arezzo/auth.py — config dir + dev fallback + env var override)
  - [x] pyproject.toml entry point configuration (arezzo = arezzo.server:main)
  - [x] Live end-to-end test through MCP layer — 6/6 validations pass (validate_mcp.py)

### Phase 5: CLI + Distribution
- **Done condition:** `arezzo init` flow, platform configs, PyPI package,
  MCP directory submissions.
- **Gate to next phase:** HITL — Will reviews Phases 4+5 together.
  Deferred per 2026-03-27 directive.
- **Status:** complete (2026-03-27)
- **Deliverables:**
  - `arezzo/cli.py` — entry point with serve/init/version subcommands
  - `arezzo/setup.py` — arezzo init wizard + platform config generation
  - `README.md` — dual-optimized (agents + humans), architecture, MCP tool docs
  - `LICENSE` — MIT
  - `pyproject.toml` — full metadata (classifiers, URLs, author), entry point → arezzo.cli:main
  - Platform configs: Claude Code (.mcp.json), Cursor (.cursor/mcp.json), VS Code (.vscode/mcp.json)
- **Deferred to HITL:**
  - ~~PyPI publish~~ — **PUBLISHED (2026-03-27).** `pip install arezzo` live. Name was available.
  - MCP directory submissions — Smithery, PulseMCP, mcp.so, Glama

## Amendments Log
- [2026-03-24] [CC] Phase 2 and 3 split from original "Architecture Design" + "Core Engine" phases. Architecture is now part of Phase 2 Step 1 (committed from Opus handoff). Phase 3 is live API validation. Status: approved (Will + Opus directive).
- [2026-03-27] [Will] HITL gates between Phases 4→5 deferred. CC authorized to continue building through Phase 5. Will reviews Phases 4+5 together after build phases complete. Gates preserved, not removed.
- [2026-03-27] [Will] Published v0.1.0 to PyPI. `arezzo` name was available.
- [2026-03-27] [Opus] Code review completed. Two items: (1) exhaustive operation type list in edit_document tool description — "etc." causes agent hallucination, (2) dedicated end-of-document live validation test added to Phase 3 suite.
