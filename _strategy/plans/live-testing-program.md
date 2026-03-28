# Plan: Live Testing Program — Real-World Document Validation
**Status:** Planned
**Created:** 2026-03-28
**Depends on:** PyPI publish (COMPLETE), Opus code review (COMPLETE)
**Model:** Sonnet · high (implementation), Opus · max (test document design)

## Goal

Heavy-test Arezzo against real-world Google Docs that represent the distribution
of what users actually have in the wild, plus deliberate corner cases that pressure
test the compiler's correctness guarantees. This is the Arezzo equivalent of Boyce's
benchmark program + test warehouse tiers.

**The bar:** If a user points Arezzo at any real Google Doc and issues any valid
operation, the compiler MUST either produce correct output or raise a clear error.
Silent corruption is total failure.

---

## Test Document Tiers

### Tier 1 — Fixture Corpus (EXISTS)
- **What:** 13 Phase 1 fixtures (plain text through kitchen sink), 23 mutation pairs
- **Where:** `fixtures/`, `fixtures/mutations/`
- **Use:** Unit tests, regression, deterministic compilation verification
- **Status:** OPERATIONAL — 210 tests, all passing

### Tier 2 — Real-World Representative Set (TO BUILD)
- **What:** 15-25 Google Docs that represent what users actually have
- **Where:** Created in Google Docs, pulled via API, stored in `fixtures/tier2/`
- **Use:** Live API validation, behavioral verification, edge case discovery
- **Priority:** HIGH — this is the confidence foundation

**Document distribution (what people actually have):**

| Category | Count | Rationale |
|----------|-------|-----------|
| Meeting notes (short, flat) | 2-3 | Most common doc type. Light formatting, no structure. |
| Technical spec (deep headings) | 2-3 | Heading hierarchy 3+ levels, named ranges, bookmarks. |
| Report with tables | 2-3 | Complex tables, merged concepts, data-heavy. |
| Shared collaborative doc | 2-3 | Comments, suggestions, multiple editors, revision churn. |
| Template-generated doc | 1-2 | Resume, invoice, letter — structured layout, unusual elements. |
| Long-form document (20+ pages) | 1-2 | Large body_end_index, many elements, performance test. |
| Multi-language content | 1-2 | CJK, Arabic, emoji-heavy — UTF-16 surrogate pair stress. |
| Mixed media | 1-2 | Inline images, drawings, embedded charts. |

### Tier 3 — Corner Case Pressure Tests (TO BUILD)
- **What:** Docs specifically designed to break the compiler
- **Where:** Created via API, stored in `fixtures/tier3/`
- **Use:** Boundary testing, corruption detection, error path validation

**Corner cases to construct:**

| Case | What breaks | How to test |
|------|-------------|-------------|
| Empty document | body has only trailing newline | All address modes against empty body |
| Single character | body_end_index is 2 | Insert at start, end, absolute 1 |
| Maximum nesting | 6-level heading hierarchy | Address resolution at every level |
| Duplicate headings | Same heading text appears 3+ times | Ambiguity error fires correctly |
| Emoji-heavy content | Every paragraph has emoji | UTF-16 surrogate pair arithmetic |
| 10,000+ character paragraph | Single massive paragraph | Large index values, end-of-doc resolution |
| 100+ headings | Large heading_index | Performance + address resolution at scale |
| Deeply nested tables | Table inside table (if API allows) | Structural boundary detection |
| Named range spanning structural boundary | Range starts in one heading section, ends in another | Range resolution correctness |
| Right-to-left text | Arabic/Hebrew content | Index arithmetic with RTL characters |
| Zero-width characters | ZWJ, ZWNJ, combining marks | UTF-16 length calculation |
| Mixed tab document | Multi-tab document | Tab isolation (Arezzo uses first tab) |
| Document with only inline objects | Images only, no text | Parser handles empty text runs |
| Rapidly mutated document | Apply 50+ operations in one batch | Reverse-index sort correctness at scale |

---

## Test Harness Design

Modeled on Boyce's benchmark harness — plug-and-play, adding a new test document
is adding a fixture, not writing new test code.

```
fixtures/
├── tier1/                    # (existing fixtures, moved)
│   ├── 01_plain_text.json
│   └── ...
├── tier2/                    # Real-world representative
│   ├── manifest.json         # Document IDs + descriptions
│   ├── meeting_notes_01.json
│   ├── tech_spec_01.json
│   └── ...
├── tier3/                    # Corner case pressure tests
│   ├── manifest.json
│   ├── empty_doc.json
│   ├── emoji_heavy.json
│   └── ...
├── mutations/                # (existing, Phase 1)
└── validation/               # (existing, Phase 3)
```

### Validation Script Design

```
scripts/
├── validate_tier2.py         # Run all Tier 2 validations
├── validate_tier3.py         # Run all Tier 3 validations
└── validate_live.py          # (existing, Phase 3 — becomes Tier 1 live)
```

Each validation:
1. Reads the fixture (or pulls live via API)
2. Applies a predefined set of operations
3. Verifies the compiled output against expected behavior
4. Reports pass/fail with details on what was asserted

### Operation Coverage Matrix

Every Tier 2 document should be tested with at minimum:
- `read_document` → structural map accuracy
- `insert_text` at heading, start, end
- `replace_all_text` with a known string
- `update_text_style` on a known range
- `validate_operations` dry run

Tier 3 documents get operation-specific tests based on the corner case.

---

## Platform Integration Testing

Modeled on Boyce's platform integration tests. Tests the full MCP stack, not
just the compiler.

| Platform | Config | Test |
|----------|--------|------|
| Claude Code | `.mcp.json` | `arezzo init` → read_document → edit_document |
| Cursor | `.cursor/mcp.json` | Same |
| Claude Desktop | Manual config | Same |
| VS Code | `.vscode/mcp.json` | Same |

**Test script:** Automated where possible, HITL where MCP client requires
manual interaction. Minimum acceptance: all four platforms can call all three
tools against a live Google Doc.

---

## Acceptance Criteria

- [ ] Tier 2: 15+ real-world documents pulled and stored as fixtures
- [ ] Tier 2: validate_tier2.py passes all documents with standard operation set
- [ ] Tier 3: 10+ corner case documents created and stored as fixtures
- [ ] Tier 3: validate_tier3.py passes all corner cases (or raises expected errors)
- [ ] UTF-16: At least 3 documents with non-BMP content (emoji, CJK supplementary)
- [ ] Scale: At least 1 document with 100+ structural elements
- [ ] Platform: All 4 MCP platforms tested end-to-end
- [ ] No silent corruption in any test — every failure is a raised error, never wrong output

---

## Sequencing

This plan runs in parallel with distribution. It doesn't block MCP directory
submissions but SHOULD complete before any significant marketing push, because
the marketing claim is "correct index arithmetic" and this plan proves it.

1. **Sprint 0:** Create Tier 2 documents in Google Docs (manual + API)
2. **Sprint 1:** Pull fixtures, build validate_tier2.py, run
3. **Sprint 2:** Create Tier 3 corner cases, build validate_tier3.py, run
4. **Sprint 3:** Platform integration testing (HITL — Will runs MCP clients)
5. **Sprint 4:** Fix any issues found, update tests, publish results

**Estimated effort:** 2-3 sessions (Sonnet · high for implementation)
