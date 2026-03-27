# Arezzo Operation Catalog

> Derived empirically from Google Docs API fixture data (Phase 1).
> Each operation maps agent intent → prerequisites → API call sequence → index arithmetic.
> Fixture references point to `fixtures/` JSON files for verification.

## Index Model (empirical)

All observations below are derived from fixture JSON, not Google documentation.

- Body content starts at index 1. Index 0 is consumed by an implicit sectionBreak.
- Every document ends with a trailing empty paragraph (`"\n"` at endIndex-1).
- Paragraph endIndex **includes** the trailing `\n` character.
- Text runs split at style boundaries — each contiguous run of identical formatting is one `textRun` element.
- Proto3 default omission: `startIndex: 0` is **omitted** from JSON in all segments (headers, footers, footnotes). The compiler must default missing `startIndex` to 0.
- Insert operations at the body's final index are invalid. `insertTable` at index N fails if N equals the segment endIndex. Insert at N-1 (before the final `\n`).
- Table structural markers each consume 1 index: table start (+1), row start (+1), cell start (+1). A 3×3 table with 4-char cell text ("R1C1") consumes 60 indices total (table:19–78 in fixture 05).

## Segment Model

The document has multiple independent index spaces (segments):

| Segment | Location in JSON | Index start | Notes |
|---------|-----------------|-------------|-------|
| Body | `tabs[N].documentTab.body.content` | 1 | Main content |
| Header | `tabs[N].documentTab.headers[id].content` | 0 (omitted) | Per-section, keyed by headerId |
| Footer | `tabs[N].documentTab.footers[id].content` | 0 (omitted) | Per-section, keyed by footerId |
| Footnote | `tabs[N].documentTab.footnotes[id].content` | 0 (omitted) | Per-footnote, keyed by footnoteId |

All `batchUpdate` requests that reference a segment must include `segmentId` (header/footer/footnote ID) or omit it (body). The `tabId` field is required for multi-tab documents.

---

## Text Operations

### T1: Insert text at beginning of document

**Agent intent:** "Add a paragraph at the top of the document."

**Prerequisites:** None — index 1 is always the first insertable position.

**API call sequence:**
```json
{"insertText": {"location": {"index": 1}, "text": "New first paragraph.\n"}}
```

**Index arithmetic:** All existing content shifts forward by `len(text)`. If text is 22 chars, every startIndex and endIndex in the body increases by 22.

**Fixture reference:** 01_plain_text.json — first paragraph starts at index 1.

---

### T2: Insert text at end of document

**Agent intent:** "Add a paragraph at the end of the document."

**Prerequisites:** Must read body to find the endIndex of the last content paragraph (NOT the trailing empty paragraph).

**API call sequence:**
```json
{"insertText": {"location": {"index": LAST_PARA_END_INDEX}, "text": "New last paragraph.\n"}}
```

Where `LAST_PARA_END_INDEX` is the startIndex of the trailing empty paragraph (or equivalently, the endIndex of the last real paragraph).

**Index arithmetic:** Only the trailing empty paragraph shifts. No impact on existing content.

**Fixture reference:** 01_plain_text.json — trailing paragraph at index 519-520. Insert at 519.

---

### T3: Insert text after a specific heading

**Agent intent:** "Insert a paragraph after the 'Section One' heading."

**Prerequisites:**
1. Walk body content to find a paragraph where `paragraphStyle.namedStyleType` starts with `HEADING_` AND a textRun contains the target heading text.
2. Record the heading paragraph's `endIndex`.

**API call sequence:**
```json
{"insertText": {"location": {"index": HEADING_END_INDEX}, "text": "Inserted paragraph.\n"}}
```

**Index arithmetic:** All content after `HEADING_END_INDEX` shifts by `len(text)`.

**Fixture reference:** 02_heading_hierarchy.json — "Section One" heading at 68-80. Insert at index 80.

**Address resolution complexity:** MEDIUM. Heading text matching is straightforward but heading text may not be unique (two sections could be named identically). The `headingId` field (e.g., `h.ior4rtyaon1h`) is unique and machine-generated.

---

### T4: Insert text between two existing paragraphs

**Agent intent:** "Insert a paragraph between the second and third paragraphs."

**Prerequisites:** Walk body content, count paragraphs (skip sectionBreak), find the endIndex of paragraph N.

**API call sequence:**
```json
{"insertText": {"location": {"index": PARA_N_END_INDEX}, "text": "Inserted paragraph.\n"}}
```

**Index arithmetic:** Same as T3 — all subsequent content shifts.

---

### T5: Replace text within a section (between two headings)

**Agent intent:** "Replace the body text under 'Section One' with new content."

**Prerequisites:**
1. Find the target heading's endIndex → `section_start`
2. Find the next heading's startIndex (or document end) → `section_end`
3. The range to replace is `section_start` to `section_end`

**API call sequence (2 requests, ordered):**
```json
[
  {"deleteContentRange": {"range": {"startIndex": SECTION_START, "endIndex": SECTION_END}}},
  {"insertText": {"location": {"index": SECTION_START}, "text": "New section content.\n"}}
]
```

**Index arithmetic:** Delete shrinks all subsequent indices by `(SECTION_END - SECTION_START)`. Insert then shifts by `len(new_text)`. Net shift = `len(new_text) - (SECTION_END - SECTION_START)`.

**Fixture reference:** 02_heading_hierarchy.json — body under "Section One" is indices 80-150.

---

### T6: Delete a paragraph

**Agent intent:** "Delete the third paragraph."

**Prerequisites:** Find the target paragraph's startIndex and endIndex.

**API call sequence:**
```json
{"deleteContentRange": {"range": {"startIndex": PARA_START, "endIndex": PARA_END}}}
```

**Index arithmetic:** All subsequent content shifts backward by `(PARA_END - PARA_START)`.

**Caution:** Cannot delete the sectionBreak (index 0-1) or the final trailing paragraph. Attempting to delete content range that includes the very last newline will fail.

---

### T7: Replace all instances of a string

**Agent intent:** "Replace all occurrences of 'old text' with 'new text'."

**Prerequisites:** None — this is a built-in API operation.

**API call sequence:**
```json
{"replaceAllText": {
  "containsText": {"text": "old text", "matchCase": true},
  "replaceText": "new text"
}}
```

**Index arithmetic:** Each replacement shifts subsequent indices by `len(new) - len(old)`. The API handles this internally — no manual index tracking needed.

**This is the simplest operation the compiler will handle.** It's the only text mutation that doesn't require index resolution.

---

## Formatting Operations

### F1: Apply bold/italic/underline to a text range

**Agent intent:** "Bold the phrase 'revenue growth' in the document."

**Prerequisites:**
1. Search body content for the target text string.
2. Find the textRun containing it and compute the exact startIndex and endIndex of the substring within that run.

**API call sequence:**
```json
{"updateTextStyle": {
  "range": {"startIndex": START, "endIndex": END},
  "textStyle": {"bold": true},
  "fields": "bold"
}}
```

**Index arithmetic:** None — formatting operations don't change indices.

**Important:** The `fields` parameter is a field mask. Only specified fields are modified. Omitting `fields` clears all unmentioned style properties. This is a critical compiler requirement.

**Fixture reference:** 03_inline_formatting.json — "bold text" at indices 20-29 with `textStyle: {bold: true}`.

---

### F2: Change paragraph heading level

**Agent intent:** "Make 'Revenue Analysis' a Heading 2."

**Prerequisites:** Find the paragraph containing the target text. Need the paragraph's startIndex and endIndex (including trailing `\n`).

**API call sequence:**
```json
{"updateParagraphStyle": {
  "range": {"startIndex": PARA_START, "endIndex": PARA_END},
  "paragraphStyle": {"namedStyleType": "HEADING_2"},
  "fields": "namedStyleType"
}}
```

**Index arithmetic:** None — style changes don't affect indices.

**Side effect:** Google auto-generates a `headingId` (e.g., `h.jkv9lifaaxhq`). This ID is not predictable and must be re-read from the document if needed for future operations.

**Fixture reference:** 02_heading_hierarchy.json — "Document Title" has headingId auto-assigned.

---

### F3: Apply heading style to text matching a string

**Agent intent:** "Make the line containing 'Summary' a Heading 1."

**Prerequisites:** Same as F2 but with text-based paragraph lookup rather than position-based.

**API call sequence:** Same as F2.

---

### F4: Change font size or font family

**Agent intent:** "Set the first paragraph to 14pt Georgia."

**Prerequisites:** Find the text range.

**API call sequence:**
```json
{"updateTextStyle": {
  "range": {"startIndex": START, "endIndex": END},
  "textStyle": {
    "fontSize": {"magnitude": 14, "unit": "PT"},
    "weightedFontFamily": {"fontFamily": "Georgia", "weight": 400}
  },
  "fields": "fontSize,weightedFontFamily"
}}
```

**Index arithmetic:** None.

---

### F5: Add a hyperlink to text

**Agent intent:** "Link the word 'example' to https://example.com."

**Prerequisites:** Find the text range of "example".

**API call sequence:**
```json
{"updateTextStyle": {
  "range": {"startIndex": START, "endIndex": END},
  "textStyle": {"link": {"url": "https://example.com"}},
  "fields": "link"
}}
```

**Side effect:** Google auto-applies underline and blue foreground color (rgb 0.067, 0.333, 0.8). The compiler should NOT apply these manually — the API does it.

**Fixture reference:** 03_inline_formatting.json — "a hyperlink" at 70-81 shows the auto-applied styles.

---

## Structural Operations

### S1: Insert a table at a specific location

**Agent intent:** "Insert a 3×3 table after the 'Revenue Analysis' heading."

**Prerequisites:**
1. Find the target location (heading endIndex, paragraph endIndex, etc.).
2. **Critical:** The insert index must be strictly less than the segment's endIndex.

**API call sequence:**
```json
{"insertTable": {"location": {"index": INSERT_INDEX}, "rows": 3, "columns": 3}}
```

**Index arithmetic:** A table consumes significant index space. For a 3×3 table:
- 1 index for table start
- Per row: 1 for row start + (per cell: 1 for cell start + cell content length + 1 for cell paragraph \n)
- Empirical: 3×3 table with empty cells = 40 indices. With 4-char text per cell = 60 indices.

**Formula for empty N×M table:** `1 + N × (1 + M × (1 + 1))` = `1 + N × (1 + 2M)` = `1 + N + 2NM`
- 3×3: `1 + 3 + 18 = 22` structural + `9` cell newlines = varies

**Fixture reference:** 05_tables.json — 3×3 table at indices 19-78.

**Hard edge:** Cannot insert table at the document's final index. Must read the document to find a safe insertion point.

---

### S2: Add a row to an existing table

**Agent intent:** "Add a row to the bottom of the table."

**Prerequisites:**
1. Find the table element in body content.
2. Find the endIndex of the last tableRow.

**API call sequence:**
```json
{"insertTableRow": {"tableCellLocation": {
  "tableStartLocation": {"index": TABLE_START_INDEX},
  "rowIndex": ROW_INDEX, "columnIndex": 0
}, "insertBelow": true}}
```

**Index arithmetic:** New row consumes `1 + cols × 2` indices (row marker + cell marker + cell \n per cell).

**Fixture reference:** 05_tables.json — table starts at index 19. Row indices: 20, 39, 58.

---

### S3: Add a column to an existing table

**Agent intent:** "Add a column to the right of the table."

**API call sequence:**
```json
{"insertTableColumn": {"tableCellLocation": {
  "tableStartLocation": {"index": TABLE_START_INDEX},
  "rowIndex": 0, "columnIndex": COL_INDEX
}, "insertRight": true}}
```

**Index arithmetic:** Each row gets `2` additional indices (cell marker + cell \n). Total shift = `rows × 2`.

---

### S4: Delete a table row or column

**API call sequence:**
```json
{"deleteTableRow": {"tableCellLocation": {
  "tableStartLocation": {"index": TABLE_START_INDEX},
  "rowIndex": ROW_INDEX, "columnIndex": 0
}}}
```

Or:
```json
{"deleteTableColumn": {"tableCellLocation": {
  "tableStartLocation": {"index": TABLE_START_INDEX},
  "rowIndex": 0, "columnIndex": COL_INDEX
}}}
```

**Index arithmetic:** Row delete removes `1 + cols × (1 + cell_content_len)` indices. Column delete removes `1 + cell_content_len` per row.

---

### S5: Insert a bullet list

**Agent intent:** "Create a bullet list with these items after the heading."

**Prerequisites:** Insert the text first (as regular paragraphs), then apply bullet formatting.

**API call sequence (2 steps):**
```json
[
  {"insertText": {"location": {"index": INSERT_INDEX}, "text": "Item one\nItem two\nItem three\n"}},
  {"createParagraphBullets": {
    "range": {"startIndex": INSERT_INDEX, "endIndex": INSERT_INDEX + 30},
    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
  }}
]
```

**Index arithmetic:** Text insertion shifts indices normally. `createParagraphBullets` does NOT change indices — it modifies paragraph properties in place.

**JSON representation:** Bulleted paragraphs have a `bullet` field with `listId` (referencing `documentTab.lists`). List definitions have 9 nesting levels with glyph types (●○■ for bullets, DECIMAL/ALPHA/ROMAN for numbered).

**Fixture reference:** 04_lists.json — three separate list IDs for bullet, numbered, and nested lists.

---

### S6: Insert a numbered list

**Agent intent:** "Create a numbered list."

Same as S5 but with preset `"NUMBERED_DECIMAL_ALPHA_ROMAN"`.

---

### S7: Convert existing paragraphs to a list

**Agent intent:** "Convert paragraphs 3-5 into a bullet list."

**Prerequisites:** Find the startIndex of the first target paragraph and endIndex of the last.

**API call sequence:**
```json
{"createParagraphBullets": {
  "range": {"startIndex": FIRST_PARA_START, "endIndex": LAST_PARA_END},
  "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
}}
```

**Index arithmetic:** None — in-place paragraph property modification.

---

### S8: Insert a page break

**Agent intent:** "Insert a page break before this section."

**Prerequisites:** Find the insertion index.

**API call sequence:**
```json
{"insertPageBreak": {"location": {"index": INSERT_INDEX}}}
```

**Index arithmetic:** Page break inserts a `pageBreak` element + trailing `textRun` element within a new paragraph. Total: 2 index positions.

**Fixture reference:** 12_horizontal_rules_page_breaks.json — page break paragraph at indices 89-91, with elements: pageBreak + textRun("\n").

---

## Object Operations

### O1: Insert an inline image

**Agent intent:** "Insert an image at this location."

**Prerequisites:** Image must be accessible via public URL.

**API call sequence:**
```json
{"insertInlineImage": {
  "location": {"index": INSERT_INDEX},
  "uri": "https://example.com/image.png",
  "objectSize": {
    "width": {"magnitude": 200, "unit": "PT"},
    "height": {"magnitude": 100, "unit": "PT"}
  }
}}
```

**Index arithmetic:** Inline image consumes exactly 1 index position (the `inlineObjectElement`). Image data is stored in `documentTab.inlineObjects` keyed by auto-generated ID.

**Side effect:** Google re-hosts the image. The `sourceUri` in the JSON will be the original URL; `contentUri` will be a Google-hosted URL. The image occupies one index position in the body regardless of file size.

**Fixture reference:** 06_images.json — inlineObjectElement at index 38-39 (1 position). Image properties in `documentTab.inlineObjects`.

---

### O2: Create a header or footer

**Agent intent:** "Add a page header to the document."

**API call sequence:**
```json
{"createHeader": {"type": "DEFAULT"}}
```
or
```json
{"createFooter": {"type": "DEFAULT"}}
```

**Index arithmetic:** None in the body. Creates a new segment with its own index space starting at 0.

**Side effect:** Registers the header/footer ID in `documentStyle.defaultHeaderId` / `defaultFooterId`. Content must be inserted into the header segment using `segmentId` in subsequent requests.

**Fixture reference:** 07_headers_footers_footnotes.json — header `kix.nznd4d573jt5` with content starting at index 0 (omitted), footer `kix.ile5r52vq0s4`.

---

### O3: Insert text into a header or footer

**Agent intent:** "Set the header text to 'Company Report'."

**Prerequisites:** Must know the header/footer segment ID (from documentStyle or previous `createHeader` response).

**API call sequence:**
```json
{"insertText": {
  "location": {"segmentId": "kix.nznd4d573jt5", "index": 0},
  "text": "Company Report"
}}
```

**Index arithmetic:** Same as body text insertion, but within the header/footer's own index space.

---

### O4: Insert a footnote

**Agent intent:** "Add a footnote after 'customer retention'."

**Prerequisites:** Find the index position in the body where the footnote reference should appear.

**API call sequence:**
```json
{"createFootnote": {"location": {"index": BODY_INDEX}}}
```

**Index arithmetic:** Inserts a `footnoteReference` element consuming 1 index in the body. Creates a new footnote segment with its own index space. Footnote content must be inserted via separate request using `segmentId`.

**Side effect:** Auto-numbers the footnote. Content within the footnote segment auto-styles to 10pt font, 100% line spacing.

**Fixture reference:** 07_headers_footers_footnotes.json — footnoteReference at body index 114-115. Footnote content in `documentTab.footnotes["kix.tij8sy2iesex"]`.

---

## Named Range Operations

### N1: Create a named range

**Agent intent:** "Create a named range called 'introduction' covering the first two paragraphs."

**Prerequisites:** Determine the startIndex and endIndex of the range.

**API call sequence:**
```json
{"createNamedRange": {
  "name": "introduction_section",
  "range": {"startIndex": 1, "endIndex": 84}
}}
```

**Index arithmetic:** None — named ranges are metadata, not content.

**Fixture reference:** 08_named_ranges.json — `namedRanges` in documentTab with `introduction_section` (1-84) and `conclusion_section` (84-157).

---

### N2: Replace content within a named range

**Agent intent:** "Replace the content of the 'introduction' named range with new text."

**Prerequisites:**
1. Read `documentTab.namedRanges` to find the range by name.
2. Get the `ranges[0].startIndex` and `ranges[0].endIndex`.

**API call sequence (2 requests):**
```json
[
  {"deleteContentRange": {"range": {"startIndex": RANGE_START, "endIndex": RANGE_END}}},
  {"insertText": {"location": {"index": RANGE_START}, "text": "New introduction content.\n"}}
]
```

**Index arithmetic:** Same as section replacement (T5). Named range boundaries are invalidated after content modification — must be re-created.

**Caution:** Named ranges reference **index positions**, not content. If content before the named range shifts, the range's indices become stale. The compiler must either: (a) process named range operations first, or (b) re-read the document to get current range positions.

---

### N3: Delete a named range

**API call sequence:**
```json
{"deleteNamedRange": {"namedRangeId": "kix.puzvmyfvu64d"}}
```

Or by name:
```json
{"deleteNamedRange": {"name": "introduction_section"}}
```

**Index arithmetic:** None — metadata only.

---

## API Limitations Discovered

These are operations that **cannot** be performed via `batchUpdate`:

| Operation | Status | Alternative |
|-----------|--------|-------------|
| Create document tabs | NOT SUPPORTED | UI only. `addTab` is not a valid request. |
| Create bookmarks | NOT SUPPORTED | UI only. `createBookmark` is not a valid request. |
| Insert horizontal rules | NOT VERIFIED | No `insertHorizontalRule` request observed. May require workaround. |
| Create comments | DIFFERENT API | Use Drive API `comments().create()` with `quotedFileContent` anchoring. |
| Create comment replies | DIFFERENT API | Use Drive API `replies().create()`. |
| Create suggested edits | NOT SUPPORTED | Suggestion mode is UI-only or requires special auth scopes. |

---

## Batch Ordering Rules

The Google Docs API processes `batchUpdate` requests sequentially. Each request can shift indices for subsequent requests. Critical ordering rules:

1. **Delete before insert at same location.** A delete + insert at the same index is a replace operation.
2. **Process from end to start** when multiple independent insertions are needed. Inserting at later indices first avoids shifting earlier insertion points.
3. **Format after insert.** Text must exist before styles can be applied. Insert text first, then apply formatting in a separate request (or later in the same batch, using the post-insertion indices).
4. **Tables require safe index.** `insertTable` index must be strictly less than the segment endIndex. Read the document to verify.
5. **Named range operations first** if the range boundaries must be stable. Or re-read after prior mutations.

---

## Address Resolution Patterns

The compiler needs to resolve semantic references to index positions. Common patterns:

| Semantic reference | Resolution strategy |
|---|---|
| "the Budget heading" | Walk body paragraphs, match `namedStyleType` starts with `HEADING_` AND textRun content contains target text |
| "paragraph 3" | Walk body paragraphs (skip sectionBreak), count to N |
| "after the table" | Walk body content, find element with `table` key, use its endIndex |
| "in cell R2C3" | Find table element, navigate `tableRows[1].tableCells[2].content[0].startIndex` |
| "the introduction section" (named range) | Read `namedRanges["introduction_section"].namedRanges[0].ranges[0]` |
| "in the header" | Read `documentStyle.defaultHeaderId`, use as segmentId |
| "between sections X and Y" | Find heading X's endIndex and heading Y's startIndex |

---

## Operations NOT cataloged (out of scope for v1)

- Table cell merging/splitting
- Column/section layout
- Equation insertion
- Drawing insertion
- Smart chips / @mentions
- Suggestion mode / tracked changes
- Document-level style changes (margins, page size)
- Tab navigation / cross-tab operations
- Table of contents generation
