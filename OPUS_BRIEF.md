# Arezzo — Opus Brief

> Strategic briefing for Opus (claude.ai) planning sessions.
> CC updates this at the end of every execution session.
> Will uploads this when starting a new Opus chat.

## Project Summary

Arezzo is a deterministic compiler for Google Docs API operations. It compiles semantic agent-intent operations ("insert a paragraph after the Budget heading") into correct `batchUpdate` request sequences with proper UTF-16 index arithmetic, element address resolution, and OT-compatible mutation ordering. Named after Guido d'Arezzo, the monk who standardized music notation. Same Convergent Methods thesis as Boyce: cheap deterministic layer consumed by expensive agents.

**One-sentence thesis:** Deterministic layers turn silent wrongness into loud correctness failures.

## Current State
- **Phase:** Phases 4+5 complete. Awaiting HITL review.
- **Status:** Phases 1–5 all done (2026-03-27). 210 tests passing. 6/6 live MCP validations. Full distribution package ready. PyPI publish deferred (name conflict). MCP directory submissions Will-controlled.
- **Key deliverables:**
  - `arezzo/server.py` — MCP server with 3 tools, behavioral advertising framework
  - `arezzo/cli.py` — CLI entry point (serve/init/version)
  - `arezzo/setup.py` — arezzo init wizard + platform config generation
  - `arezzo/auth.py` — package-level auth (config dir + env var + dev fallback)
  - `arezzo/compiler.py` — `compile_operations()` entry point
  - `arezzo/parser.py` — ParsedDocument with pre-built indexes
  - `arezzo/address.py` — 6 address modes
  - `arezzo/index.py` — UTF-16 arithmetic, surrogate pair handling
  - `arezzo/operations/` — 5 operation compiler modules
  - `arezzo/tests/` — 210 tests across 11 test files
  - `README.md` — dual-optimized, MCP tool docs, architecture
  - `LICENSE` — MIT
- **Review artifacts (for Opus):**
  - `_strategy/OPUS_SOURCE_REVIEW.md` — all 9 source files + review response (single doc for Opus)
  - `_strategy/OPUS_REVIEW_RESPONSE.md` — tool descriptions, validations, corruption tests, auth flow

## Recent Decisions
- 2026-03-27: Will authorized CC to build through Phase 5 before HITL review. Gates preserved, not removed.
- 2026-03-27: Phase 4 MCP server design: 3 tools (read_document, edit_document, validate_operations). Behavioral advertising framework transferred from Boyce.
- 2026-03-24: Architecture locked: two-phase compilation, pure function compiler, 6 address modes, UTF-16 internally, reverse index order, always emit tabId.
- 2026-03-24: Boyce shipped to PyPI. Arezzo build gate cleared.

## Open Questions
- PyPI name `arezzo` is available. Ready to publish when Opus review approves.
- MCP directory submission timing: Will's call.

## Blocked Items
- PyPI publish — awaiting Opus code review completion before publication.
- MCP directory submissions — Will-controlled.

## Cross-Project Dependencies
- Boyce shipped. No remaining Boyce blocker.
- Behavioral advertising framework (from Boyce) applies to Arezzo MCP tool descriptions in Phase 4.
- Product line positioning: Boyce (database formalism) + Arezzo (document formalism).

## HITL Queue
- **Phases 4+5 joint review (NOW ACTIVE):** Build phases complete. Will reviews: cross-platform MCP client testing, compiler output for 3 representative operations (async), PyPI naming decision, MCP directory submission timing.
- **Phase 2 async review:** Will catches up on compiler output for 3 representative operations (deferred, not blocking).
