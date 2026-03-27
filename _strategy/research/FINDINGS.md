# Arezzo Phase 1 Findings

> Empirical findings from Google Docs API problem cartography.
> For Will and Opus to review before Phase 2 architecture design.
> Date: 2026-03-24

## 1. Surprises

### Proto3 default value omission
`startIndex: 0` is **silently omitted** from all JSON responses for headers, footers, and footnotes. This is standard proto3 behavior (zero-valued fields are omitted) but is underdocumented in Google's API docs. The compiler must `dict.get("startIndex", 0)` everywhere — a `KeyError` on this cost us time during fixture creation.

### Links auto-apply visual styles
Setting `textStyle.link.url` causes Google to automatically apply underline and blue foreground color (`rgb(0.067, 0.333, 0.8)`). The compiler should NOT apply these manually — doing so would double-apply and potentially conflict. When removing a link, the compiler may need to explicitly clear the underline and color.

### Table index arithmetic is non-trivial
Tables consume indices for **every structural boundary**: table start (+1), row start (+1), cell start (+1), plus cell content. A 3×3 table with 4-character cell text occupies 60 index positions (fixture 05: indices 19-78). Empty tables still consume `1 + rows + rows × columns` structural indices plus one `\n` per cell.

### Footnote references occupy exactly 1 index
A `footnoteReference` element in the body is a single index position (fixture 07: index 114-115). But this one position shifts everything after it and creates an entirely new segment with its own index space. Compact representation, large side effect.

### Rate limiting is aggressive
Google Docs API enforces 60 write operations per minute per user. Each `batchUpdate` counts as one write, but `documents.create` also counts. Creating a test document + formatting it + mutating it = 3-4 writes. At scale, the compiler must batch operations into fewer `batchUpdate` calls rather than many small ones. This is a natural optimization — a compiler should emit one large batch, not many small ones.

### Page breaks create a two-element paragraph
`insertPageBreak` creates a paragraph with two elements: a `pageBreak` element and a trailing `textRun` containing `"\n"`. This consumes 2 index positions. The paragraph contains both the break marker and the text continuation — they can't be separated.

### Comments live in a completely different API
Comments and replies are created via the Google Drive API, not the Docs API `batchUpdate`. The Docs API `documents.get` does NOT return comments at all — they are metadata attached to the file, not document structure. This means the compiler's scope can exclude comments entirely for v1 (they're not part of the document model it compiles).

### Google re-hosts all images
Images inserted via `insertInlineImage` are re-hosted by Google. The `sourceUri` in the JSON matches the original URL, but `contentUri` is a Google-served URL. The image occupies exactly 1 index position regardless of file size. This is clean for the compiler — images are opaque objects that consume one slot.

---

## 2. Patterns

### The document is a flat list with nesting illusions
Despite the visual hierarchy of headings, sections, lists, and tables, the Google Docs body is fundamentally a **flat array** of structural elements. Paragraphs, tables, and section breaks are siblings at the same level. The only true nesting is:
- Tables → rows → cells → content (paragraphs)
- Paragraphs → elements (textRuns, inlineObjects, footnoteRefs)

There is no semantic "section" concept in the JSON. Sections are implied by the sequence of heading paragraphs. The compiler must build the section abstraction from heading positions.

### Text runs split exactly at style boundaries
A paragraph with mixed formatting has multiple `textRun` elements, one per contiguous region of identical style. "This has **bold** and *italic*" becomes 5 textRun elements. The splits are deterministic and lossless — concatenating all textRun.content values recreates the full paragraph text.

### Lists are paragraphs with a `bullet` property
There is no "list" structural element. Lists are regular paragraphs that happen to have a `bullet` field containing a `listId` (referencing definitions in `documentTab.lists`). Nesting depth is determined by `paragraphStyle.indentStart` magnitude, not by any explicit nesting field. The list definition provides glyph types for 9 nesting levels.

### All segments have identical structure
Body, headers, footers, and footnotes all have the same internal structure: an array of content elements (paragraphs, tables, etc.) with `startIndex`/`endIndex` pairs. The only difference is:
- Body starts at index 1 (index 0 is the sectionBreak)
- Other segments start at index 0 (omitted in JSON)
- Each segment has an independent index space

This means the compiler can use a single content walker/resolver for all segment types.

### Formatting operations are index-neutral
All `updateTextStyle` and `updateParagraphStyle` operations leave indices unchanged. This is the cleanest pattern: format operations can be appended to any batch without affecting other operations' index calculations.

### Every document ends with a trailing empty paragraph
All fixtures end with a paragraph containing just `"\n"`. This is an implicit Google Docs invariant. It means `body[-1].endIndex - 1` is always a safe "end of real content" position. The compiler can rely on this.

### Named ranges are pure index metadata
Named ranges are stored outside the body content (in `documentTab.namedRanges`). They don't affect rendering or indices. But they're fragile — any insertion or deletion before a named range invalidates its indices. The compiler must either process named range operations last or re-read the document between mutations that affect named range positions.

---

## 3. Hard Edges

### Table cell index navigation
To write to a specific table cell, the compiler must navigate: `table.tableRows[row].tableCells[col].content[0].startIndex` (plus 1 for the cell's internal paragraph start). Each level has its own start/end indices. Cell operations must be issued in reverse index order within a batch to avoid cascading shift errors.

### Insertion at segment boundaries
`insertTable` at the exact segment endIndex fails with "Index N must be less than the end index of the referenced segment, N." This off-by-one behavior is not documented. The compiler must always insert structural elements before the final `\n`, not at the segment end.

### List nesting is indent-based, not level-based
The API's `createParagraphBullets` doesn't accept a nesting level parameter. Nesting is achieved by manipulating `paragraphStyle.indentStart` — 36pt for level 1, 72pt for level 2. The relationship between indent magnitude and nesting level must be derived (it's 36pt per level based on fixture data). The compiler needs a nesting-level-to-indent mapping.

### batchUpdate request names are not discoverable
Invalid request names (like `addTab`, `createBookmark`, `insertHorizontalRule`) return vague "Unknown name" errors with no suggestion of valid alternatives. The full list of valid request types is only documented, not introspectable via the API. The compiler must maintain a hardcoded allowlist.

### Heading IDs are auto-generated and unstable
When a paragraph's `namedStyleType` is set to any `HEADING_*` value, Google generates a `headingId` (e.g., `h.jkv9lifaaxhq`). This ID changes if the heading is re-applied. It cannot be set by the API. If the compiler needs to reference headings by ID (for TOC, internal links), it must re-read the document after heading creation.

### Multi-step mutations require intermediate document reads
Many compound operations (create table → fill cells, create header → add text, create footnote → add content) require reading the document between steps to get correct indices for the second step. The first step changes the document structure, and the compiler cannot predict the resulting indices without reading. This makes "compile once, execute once" infeasible for compound operations — the compiler needs a "compile-read-compile" pattern for multi-step mutations.

---

## 4. Simplifications

### `replaceAllText` is zero-complexity
The `replaceAllText` request is fully self-contained — no index resolution, no address calculation, no batch ordering concerns. Same-length replacements have zero index shift. This should be the compiler's first optimized path.

### Formatting is completely decoupled from content
Text styling and paragraph styling never affect indices. The compiler can separate the "compute content mutations" phase from the "compute formatting mutations" phase. Format requests can be appended to any batch with no ordering constraints relative to each other (only relative to content insertions/deletions that change what text exists at which indices).

### The segment model is uniform
The same content model (paragraphs, elements, startIndex/endIndex) applies to body, headers, footers, and footnotes. The compiler doesn't need separate code paths for different segment types — just a segment ID parameter.

### Single-index objects simplify arithmetic
Inline images, footnote references, and page breaks all consume a predictable, small number of index positions (1 or 2). This makes their impact on index arithmetic trivially calculable.

### Named ranges provide pre-resolved addresses
When a named range exists, the compiler can skip address resolution entirely for operations targeting that range. This is the "escape hatch" noted in CLAUDE.md — agents can use named ranges to provide pre-resolved addresses to the compiler, bypassing the most complex compilation step.

---

## 5. Recommended Scope for Phase 2

### v1 Must-Have Operations

These cover the core compilation problems and the most common agent intents:

| Category | Operations | Rationale |
|----------|-----------|-----------|
| Text | T1-T7 (all 7) | Core value proposition. Every agent operation involves text mutation. |
| Formatting | F1-F5 (all 5) | Formatting is zero-complexity for indices. High agent value, low implementation cost. |
| Structure | S1 (tables), S5-S7 (lists), S8 (page breaks) | Tables and lists are the most requested structural operations. |
| Objects | O1 (images), O2 (headers/footers), O4 (footnotes) | Complete the document model. |
| Named ranges | N1-N3 (all 3) | Critical escape hatch for address resolution. |

### v1 Should-Have Operations

| Category | Operations | Rationale |
|----------|-----------|-----------|
| Structure | S2-S4 (table row/column add/delete) | Important but secondary to table creation. |

### Scope Decisions Required (flagged for Opus)

These are product scope questions, not engineering recommendations. The
engineering team (CC) provides the data; the CEO layer (Opus + Will)
decides scope.

| Feature | Empirical finding | Question for Opus |
|---------|-------------------|-------------------|
| **Tabs** | Not API-creatable. Zero multi-tab fixture data. | Include tab-aware reads in v1? If yes, CC needs a manual multi-tab fixture. |
| **Comments** | Drive API only. Not in `documents.get` JSON at all. | Is Drive API integration in Arezzo's scope, or comments out entirely? |
| **Bookmarks** | Not API-creatable. But exist in UI-created docs and are readable. | Should compiler reference existing bookmarks for address resolution? |

### CC Recommendation: Defer to v2+

| Feature | Rationale |
|---------|-----------|
| Horizontal rules | No `insertHorizontalRule` request found. May require workaround. |
| Suggestions/tracked changes | UI-only or special auth scopes. |
| Cell merging | Adds complexity to table index arithmetic with limited agent use. |
| Equations/drawings | Niche use cases. |

### Architecture Implications

1. **Two-phase compilation:** Content mutations (which shift indices) should be compiled separately from format mutations (which don't). Format mutations should reference post-content-mutation indices.

2. **Compile-read-compile pattern:** Compound operations (table + fill cells, header + content) need intermediate document reads. The compiler should support multi-round compilation.

3. **Index tracking as core concern:** The central data structure should be an index tracker that accumulates shifts from each operation and adjusts subsequent operations' indices. This is the UTF-16 arithmetic problem stated in CLAUDE.md.

4. **Reverse-order batching for independent operations:** When multiple insertions target different locations, processing from highest index to lowest avoids cascading shifts. This is a solved problem in text editing (Operational Transform).

5. **Named range fast path:** When operations target named ranges, skip address resolution and go straight to index-based compilation. This is the compiler's highest-confidence path.

6. **Hardcoded valid request allowlist:** The batchUpdate API does not self-describe its valid request types. The compiler must maintain an explicit allowlist to give clear errors for unsupported operations.

---

## Fixture Inventory

| Fixture | Elements | Key structures |
|---------|----------|----------------|
| 01_plain_text | 6 | Paragraphs only |
| 02_heading_hierarchy | 12 | HEADING_1/2/3 + headingId |
| 03_inline_formatting | 4 | Bold, italic, underline, link, mixed styles |
| 04_lists | 16 | 3 listIds, bullet/numbered/nested |
| 05_tables | 9 | 3×3 table + 2×2 table, cell content |
| 06_images | 3 | inlineObjectElement + inlineObjects |
| 07_headers_footers_footnotes | 5 | Headers, footers, footnotes as segments |
| 08_named_ranges | 6 | 2 named ranges with index boundaries |
| 09_tabs | 4 | Single tab only (creation not API-supported) |
| 10_comments | 5 | Comments not in Docs JSON (Drive API only) |
| 11_kitchen_sink | 18 | Headings, lists, table, formatting, footnote |
| 12_horizontal_rules_page_breaks | 6 | Page break element structure |
| 13_bookmarks | 5 | Text only (creation not API-supported) |

**Mutation pairs:** 23 operations with before/request/after/description for each.
