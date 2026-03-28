# Arezzo Roadmap

> Ops layer roadmap. See CM root CLAUDE.md for protocol definition.
> Will authors phases and gate types. CC maintains status and proposes amendments.

## Current Phase
Phase: Phase 6 — Live Testing & Distribution
Status: PUBLISHED v0.1.0 to PyPI (2026-03-27). Opus code review complete. Live testing program designed, not yet executed. MCP directory submissions drafted. Distribution plan imported from Boyce.

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
  - `_strategy/research/OPERATION_CATALOG.md` — 23 operations mapped to API sequences
  - `_strategy/research/FINDINGS.md` — surprises, patterns, hard edges, Phase 2 recommendations
  - `scripts/pull_fixtures.py`, `scripts/create_fixtures.py`, `scripts/capture_mutations.py`

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
- **Status:** complete (2026-03-24) — 9/9 live validations passing (8 original + 1 end-of-doc per Opus review)
- **Validations:** insert_text_after_heading, replace_all_text,
  apply_bold_and_insert, insert_table, create_named_range,
  insert_bullet_list, create_header_footer, insert_page_break,
  insert_text_at_end

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

### Phase 5: CLI + Distribution Package
- **Done condition:** `arezzo init` flow, platform configs, PyPI package.
- **Status:** complete (2026-03-27). **PUBLISHED to PyPI (2026-03-27).**
- **Deliverables:**
  - `arezzo/cli.py` — entry point with serve/init/version subcommands
  - `arezzo/setup.py` — arezzo init wizard + platform config generation
  - `README.md` — dual-optimized (agents + humans), architecture, MCP tool docs
  - `LICENSE` — MIT
  - `pyproject.toml` — full metadata, entry point → arezzo.cli:main
  - Platform configs: Claude Code, Cursor, VS Code
  - **PUBLISHED v0.1.0 to PyPI (2026-03-27)**

### Phase 6: Live Testing & Distribution
- **Done condition:** Tier 2 + Tier 3 test documents pass. All 4 MCP platforms
  tested end-to-end. MCP directory submissions complete. Agent docs (llms.txt)
  deployed.
- **Gate to next phase:** HITL — Will controls distribution timing.
- **Status:** in progress (2026-03-28)
- **Plan docs:**
  - `_strategy/plans/live-testing-program.md` — Tier 2/3 test documents, corner cases, platform testing
  - `_strategy/plans/agent-adoption-docs.md` — README audit, llms.txt, llms-full.txt
  - `_strategy/plans/distribution-launch.md` — Registry submissions, content, community posts
  - `_strategy/mcp-directory-submissions.md` — Pre-drafted registry content
- **Build sequence:**
  - [ ] Sprint 0: Create Tier 2 real-world test documents (agent-gated)
  - [ ] Sprint 1: Pull fixtures, build validate_tier2.py, run (agent-gated)
  - [ ] Sprint 2: Create Tier 3 corner cases, validate_tier3.py (agent-gated)
  - [ ] Sprint 3: Cross-platform MCP client testing (**HITL** — Will runs clients)
  - [ ] Sprint 4: Fix issues, publish v0.1.1 with Opus review changes (agent-gated)
  - [ ] Agent docs: README audit, llms.txt, llms-full.txt (agent-gated)
  - [ ] MCP directory submissions (**HITL** — Will submits)
  - [ ] Technical essay: "Why UTF-16 Index Arithmetic Breaks Every Agent" (agent-gated, Will reviews)
  - [ ] Community posts (**HITL** — Will posts)

### Phase 7: Google Workspace Expansion (future)
- **Done condition:** At least one additional Workspace API (Slides, Forms, Sheets)
  supported via the same compilation model.
- **Gate:** HITL — architecture review with Opus
- **Status:** not started
- **Note:** Learnings from Docs propagate. Same compiler architecture, different operation sets.

## Amendments Log
- [2026-03-24] [CC] Phase 2 and 3 split from original phases. Architecture is Phase 2 Step 1.
- [2026-03-27] [Will] HITL gates between Phases 4→5 deferred. CC builds through Phase 5.
- [2026-03-27] [Will] Published v0.1.0 to PyPI. `arezzo` name was available.
- [2026-03-27] [Opus] Code review completed. Two items implemented: exhaustive operation type list, dedicated end-of-doc validation.
- [2026-03-28] [CC] Added Phase 6 (Live Testing & Distribution) and Phase 7 (Workspace Expansion). Imported Boyce's distribution, testing, and adoption patterns. Plans created in `_strategy/plans/`.
