# Arezzo — Opus Brief

> Strategic briefing for Opus (claude.ai) planning sessions.
> CC updates this at the end of every execution session.
> Will uploads this when starting a new Opus chat.

## Project Summary

Arezzo is a deterministic compiler for Google Docs API operations. It compiles semantic agent-intent operations ("insert a paragraph after the Budget heading") into correct `batchUpdate` request sequences with proper UTF-16 index arithmetic, element address resolution, and OT-compatible mutation ordering. Named after Guido d'Arezzo, the monk who standardized music notation. Same Convergent Methods thesis as Boyce: cheap deterministic layer consumed by expensive agents.

**One-sentence thesis:** Deterministic layers turn silent wrongness into loud correctness failures.

## Current State
- **Phase:** PUBLISHED v0.1.0 to PyPI (2026-03-27). Post-publish review + distribution.
- **Status:** `pip install arezzo` live. 210 unit tests, 9/9 live validations (8 Phase 3 + 1 end-of-doc added per Opus review). 6/6 live MCP validations. Opus code review items implemented. No domain yet (arezzo.dev is taken).
- **Key deliverables:**
  - `arezzo/server.py` — MCP server with 3 tools, behavioral advertising framework, full operation type list in tool description (Opus review item)
  - `arezzo/cli.py` — CLI entry point (serve/init/version)
  - `arezzo/setup.py` — arezzo init wizard + platform config generation
  - `arezzo/auth.py` — package-level auth (config dir + env var + dev fallback)
  - `arezzo/compiler.py` — `compile_operations()` entry point
  - `arezzo/parser.py` — ParsedDocument with pre-built indexes
  - `arezzo/address.py` — 6 address modes
  - `arezzo/index.py` — UTF-16 arithmetic, surrogate pair handling
  - `arezzo/operations/` — 5 operation compiler modules
  - `arezzo/tests/` — 210 tests across 11 test files
  - `README.md` — dual-optimized, MCP tool docs, architecture (renders on PyPI)
  - `LICENSE` — MIT
- **Project structure:** Reorganized to match Boyce paradigm. `_strategy/` for internal planning/research, `scripts/` for dev utilities.

## Recent Decisions
- 2026-03-27: **PUBLISHED to PyPI.** `pip install arezzo` live. v0.1.0.
- 2026-03-27: Domain search: arezzo.dev is taken (Porkbun). Need alternative.
- 2026-03-27: Opus code review completed. Two items implemented: (1) exhaustive operation type list in edit_document tool description, (2) dedicated end-of-document live validation test.
- 2026-03-27: Project directory reorganized to match Boyce paradigm (_strategy/, scripts/).
- 2026-03-27: Will authorized CC to build through Phase 5 before HITL review.
- 2026-03-24: Architecture locked: two-phase compilation, pure function compiler, 6 address modes.

## Open Questions
- Domain: arezzo.dev is taken (Porkbun registrant, not ours). Alternatives: arezzo.tools, arezzo.io, or host under convergentmethods.com/arezzo/. Will decides.
- MCP directory submission timing: Will's call.
- Cross-platform MCP client testing: Claude Desktop, Cursor, Claude Code — Will tests.

## Blocked Items
- MCP directory submissions — Will-controlled.
- Product site — needs domain decision first.

## Cross-Project Dependencies
- Boyce shipped. No remaining Boyce blocker.
- Behavioral advertising framework (from Boyce) applies to Arezzo MCP tool descriptions.
- Product line positioning: Boyce (database formalism) + Arezzo (document formalism).
- LLM SEO study can reference Arezzo as second case study alongside Boyce.

## HITL Queue
- **Cross-platform MCP client testing (NOW DUE):** Will tests arezzo serve with Claude Desktop, Cursor, Claude Code. This is the primary remaining validation before distribution.
- **MCP directory submissions:** Smithery, PulseMCP, mcp.so, Glama. Will-controlled timing.
- **Phase 2 async review:** Will catches up on compiler output for 3 representative operations (deferred, not blocking — publish already happened).
