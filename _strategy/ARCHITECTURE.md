# Arezzo Architecture

> Deterministic layers turn silent wrongness into loud correctness failures.
>
> Locked by Will + Opus on 2026-03-24. CC executes. Do not reopen
> architecture decisions without a HITL gate.

## Scope Decisions (LOCKED)

| Feature | Decision | Rationale |
|---------|----------|-----------|
| Tabs | OUT | No tab-awareness. Always emit `tabId` (first tab) in Location/Range for future-proofing. |
| Comments | OUT | Drive API, not Docs API. No Drive integration path. |
| Bookmarks | READ-ONLY | Address resolver can resolve "at bookmark X" to an index. Cannot create bookmarks. |
| Cell merging | OUT (v2) | Adds complexity to table index arithmetic with limited agent use. |
| Horizontal rules | OUT (v2) | No `insertHorizontalRule` request exists. |
| Suggestions | OUT (v2) | UI-only or special auth scopes. |

## Two-Phase Compilation

Formatting operations are index-neutral (confirmed empirically in Phase 1).
The compiler emits requests in two phases within a single batchUpdate array:

**Phase 1 — Content mutations:** All insertions, deletions, structural
operations (tables, headers, footers). These shift indices. Emitted in
reverse index order to eliminate cascading index recalculation.

**Phase 2 — Format mutations:** All style operations (updateTextStyle,
updateParagraphStyle, createParagraphBullets). Index-neutral. Reference
final post-content-mutation positions. Appended after all content mutations.

## Compiler Is a Pure Function

Stateless: **document state in → request array out.**

Compound operations requiring intermediate document reads (create table →
read new doc → fill cells) are the CALLER's responsibility. The MCP tool
layer (Phase 4) handles orchestration.

**Exception:** If a compound operation fits in one atomic batchUpdate
(e.g., delete + insert at same index = replace), the compiler emits it
as one array.

## Address Resolution Model

Six address modes:

| Mode | Input | Resolution |
|------|-------|------------|
| Heading | `{"heading": "Budget"}` | endIndex of paragraph with that heading text |
| Named range | `{"named_range": "summary"}` | range's startIndex/endIndex |
| Bookmark | `{"bookmark": "insertion_point"}` | bookmark's index |
| End of document | `{"end": true}` | endOfSegmentLocation |
| Start of document | `{"start": true}` | index 1 |
| Absolute index | `{"index": 847}` | pass-through |

**Rules:**
- All resolution requires a current document snapshot as input.
- Heading match: exact, case-sensitive against HEADING_* paragraphs.
  Multiple matches → error with list of matches and indices. Never guess.
- Unresolvable address → `ArezzoAddressError`. Never fall back.

## Index Representation — UTF-16 Internally

No character-offset abstraction. The API speaks UTF-16 code units. The
compiler speaks UTF-16 code units. Surrogate pairs (emoji, CJK
supplementary) consume two index positions.

Handle proto3 default omission: treat missing `startIndex` as 0.

## WriteControl

Default: `targetRevisionId` (OT merge — API resolves conflicts).
Optional: `requiredRevisionId` (optimistic locking — 400 on conflict).

Revision ID from input document's `revisionId` field.

## Request Emission

- **Reverse index order** for content mutations within a batchUpdate.
- **`endOfSegmentLocation`** for append operations.
- **Always emit `tabId`** in every Location and Range. Obtained from
  `document['tabs'][0]['tabProperties']['tabId']`. If absent (pre-tabs
  docs), omit — don't fail.
- **Atomic correctness** — if any request would be invalid, the compiler
  raises an error. Partial correctness is total failure.

## Compiler Interface

```python
def compile_operations(
    document: dict,           # Full documents.get response (includeTabsContent=true)
    operations: list[dict],   # List of agent-intent operations
    write_control: str = "target",  # "target" | "required"
) -> dict:
    """
    Returns a dict ready to POST as batchUpdate request body:
    {
        "requests": [...],
        "writeControl": {"targetRevisionId": "..."}
    }

    Raises:
        ArezzoCompileError     — base class
        ArezzoAddressError     — unresolvable or ambiguous address
        ArezzoOperationError   — invalid operation type or params
        ArezzoIndexError       — UTF-16 index arithmetic failure
    """
```

### Operation Format

```python
{
    "type": "insert_text",              # snake_case from OPERATION_CATALOG
    "address": {"heading": "Budget"},   # address mode
    "position": "after",                # "before" | "after" | "within"
    "params": {                         # operation-specific
        "text": "New paragraph content\n"
    }
}
```

## Internal Representation

The parser produces a `ParsedDocument` — a thin wrapper around the raw
JSON with pre-built lookup indexes. Not a translation layer.

```python
@dataclass
class ParsedDocument:
    raw: dict                                # Full documents.get response
    tab_id: str | None                       # First tab's tabId (None for pre-tabs docs)
    revision_id: str                         # For WriteControl
    body: list[dict]                         # tabs[0].documentTab.body.content
    body_end_index: int                      # Last element's endIndex
    heading_index: dict[str, list[tuple]]    # text → [(startIndex, endIndex, headingId)]
    named_range_index: dict[str, list[tuple]]# name → [(startIndex, endIndex, rangeId)]
    bookmark_index: dict[str, int]           # bookmarkId → index
    headers: dict[str, dict]                 # headerId → header segment
    footers: dict[str, dict]                 # footerId → footer segment
    footnotes: dict[str, dict]               # footnoteId → footnote segment
    lists: dict[str, dict]                   # listId → list properties
    inline_objects: dict[str, dict]          # objectId → object properties
```

Indexes are built in a single pass during parse. Raw JSON stays available
for anything the indexes don't cover.

## Module Structure

```
arezzo/
├── __init__.py
├── compiler.py          # compile_operations() — entry point
├── parser.py            # Document JSON → ParsedDocument
├── address.py           # Address resolution (6 modes)
├── index.py             # UTF-16 index arithmetic
├── errors.py            # ArezzoCompileError hierarchy
├── operations/
│   ├── __init__.py
│   ├── text.py          # insert_text, delete_content, replace_all_text
│   ├── format.py        # update_text_style, update_paragraph_style, create_paragraph_bullets
│   ├── structure.py     # insert_table, insert_table_row/column, delete_table_row/column
│   ├── objects.py       # insert_inline_image, create_header/footer, create_footnote, insert_page_break
│   └── organization.py  # create_named_range, delete_named_range, replace_named_range_content
└── tests/
    ├── conftest.py      # Shared fixtures — load Phase 1 JSON
    ├── test_parser.py
    ├── test_address.py
    ├── test_index.py
    ├── test_text_ops.py
    ├── test_format_ops.py
    ├── test_structure_ops.py
    ├── test_objects_ops.py
    ├── test_organization_ops.py
    └── test_compiler.py # End-to-end integration
```

## Single-Batch vs. Multi-Round Classification

Derived from Phase 1 mutation pairs. Every captured operation is single-batch.
Multi-round cases are compound operations that create new structures then
write content into them.

| Operation | Catalog | Classification | Notes |
|-----------|---------|---------------|-------|
| insert_text (start) | T1 | Single-batch | 1 request |
| insert_text (end) | T2 | Single-batch | 1 request |
| insert_text (after heading) | T3 | Single-batch | 1 request |
| insert_text (between paras) | T4 | Single-batch | 1 request |
| replace_section | T5 | Single-batch | 2 requests (delete + insert) in one batch |
| delete_paragraph | T6 | Single-batch | 1 request |
| replace_all_text | T7 | Single-batch | 1 request |
| apply_text_style | F1 | Single-batch | 1 request |
| change_heading_level | F2 | Single-batch | 1 request |
| change_font | F4 | Single-batch | 1 request |
| add_hyperlink | F5 | Single-batch | 1 request |
| insert_table (empty) | S1 | Single-batch | 1 request |
| add_table_row | S2 | Single-batch | 1 request |
| insert_bullet_list | S5 | Single-batch | 2 requests (insert text + create bullets) |
| insert_numbered_list | S6 | Single-batch | 2 requests (insert text + create bullets) |
| convert_to_list | S7 | Single-batch | 1 request |
| insert_page_break | S8 | Single-batch | 1 request |
| insert_inline_image | O1 | Single-batch | 1 request |
| create_header_footer | O2 | Single-batch | 2 requests (create header + create footer) |
| create_footnote | O4 | Single-batch | 1 request |
| create_named_range | N1 | Single-batch | 1 request |
| replace_named_range | N2 | Single-batch | 2 requests (delete + insert) |
| delete_named_range | N3 | Single-batch | 1 request |

**Multi-round (caller orchestrates):**

| Compound operation | Why multi-round |
|---|---|
| Create table + fill cells with data | Cell indices only exist after table creation |
| Create header/footer + write content | Segment ID only exists after creation |
| Create footnote + write content | Footnote segment ID only exists after creation |

## Corruption Detection Tests

The compiler's core value proposition: convert silent data corruption into
loud compile errors. Every operation compiler includes tests that verify
rejection of intentionally wrong inputs:

- Address resolving to inside a structural element boundary (e.g., inside
  a table cell marker) → must error
- Insert whose text length would push subsequent indices past document end
  → must error
- Delete range overlapping structural element boundary (deleting half a
  table) → must error
- Index falling on second code unit of a surrogate pair → must error

**Principle:** If the compiler emits a request, that request MUST be valid.
If there is any doubt, raise `ArezzoCompileError`.
