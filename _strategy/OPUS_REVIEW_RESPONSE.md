# Opus Review Response — Arezzo Phases 4+5

> Strategic briefing document for Opus code review.
> Covers MCP tool descriptions, live validation details, corruption detection test coverage, and auth flow.

---

## MCP Tool Descriptions

### read_document

**Name:** read_document

**Input:** `document_id` (string) — The Google Docs document ID from the URL.

**Output:** Dictionary with:
- `next_step`: Behavioral guidance for next action
- `document_reality`: Structural map showing headings, named ranges, tables, bookmarks, metadata

**Description from server.py:**

> See what the document contains before you edit it. Returns the document's structural map — headings with hierarchy, named ranges with boundaries, tables with dimensions, inline objects, and section boundaries. Without this, you're editing blind: you don't know what headings exist, where sections start, or what named ranges are available for targeting. **Call this before edit_document.** The structural map shows what addresses are available (heading names, named range names) so your edit operations target the right locations.

**Behavioral Layer:** The `next_step` includes affordance summary ("Document has N headings, M named ranges, K table(s)") to signal what operations are available. The `document_reality` field serves as the "ground truth" about document structure for the agent to reason over.

---

### edit_document

**Name:** edit_document

**Input:**
- `document_id` (string)
- `operations` (list of operation dicts)

Each operation has:
- `type`: operation name (insert_text, update_text_style, insert_table, etc.)
- `address`: target location ({heading: "name"}, {named_range: "name"}, {start: true}, {end: true}, {index: N})
- `params`: operation-specific parameters

**Output:** Dictionary with:
- `next_step`: Behavioral guidance
- `operations_compiled`: count of operations
- `requests_emitted`: count of API requests generated
- `document_id`: the document that was modified
- `present_to_user` (optional): guidance for compound operations or named range mutations
- Error responses if compilation or execution fails

**Description from server.py:**

> Make changes to a Google Doc with correct index arithmetic. You cannot safely modify a Google Doc by constructing batchUpdate requests yourself. The API uses UTF-16 code units with cascading index shifts — insert 10 characters at position 50, and every subsequent index in your batch is wrong. A single miscalculation silently corrupts the document with no error message. This tool compiles your semantic intent into a correct request sequence. **Recommended flow:** call read_document first, then describe your changes using heading names or named ranges as addresses. Supports: text insertion/deletion/replacement, formatting (bold, italic, headings, links), tables, lists, images, headers/footers, footnotes, named ranges.

**Behavioral Layer:** For compound operations (insert_table, create_header, etc.), `present_to_user` signals that new element indices must be re-read. For named range mutations, `present_to_user` warns that boundaries may have shifted. The response always includes `next_step` directing the agent to either call `read_document` again or proceed to the next task.

---

### validate_operations

**Name:** validate_operations

**Input:** Same as edit_document — `document_id` and `operations` list.

**Output:** Dictionary with:
- `validation`: "passed" or "failed"
- `operations_compiled`: count
- `requests_emitted`: count
- `content_mutations`: count of content-modifying requests
- `format_mutations`: count of formatting requests
- `compiled_requests`: the full batchUpdate body (for inspection)
- `next_step`: guidance
- Error fields if validation fails

**Description from server.py:**

> Check whether edit operations would succeed without executing them. Returns the compiled batchUpdate requests plus validation status. Use this when you want to inspect the exact API calls before they execute, or when debugging why an edit might fail. Catches address resolution errors, ambiguous headings, out-of-bounds indices, and invalid operation parameters. **Use this before edit_document when uncertain.** Shows exactly what Arezzo would send to the Google Docs API.

**Behavioral Layer:** Returns the compiled request body so the agent can inspect the exact API mutations before execution. Separates content mutations from format mutations so the agent understands the two-phase ordering.

---

## Live Validation Details

### Phase 3 Live API Validations (via validate_live.py)

Each test creates a real Google Doc, applies operations via the Arezzo compiler, executes the batchUpdate, and verifies the mutation via document read-back.

1. **insert_text_after_heading**
   - Operation: Insert paragraph after "Revenue Analysis" heading
   - Assertion: Inserted text appears in document body, positioned after heading start index
   - What's tested: Address resolution (heading → endIndex), text insertion, cascading index handling

2. **replace_all_text**
   - Operation: Replace all instances of "revenue" (case-insensitive) with "REVENUE"
   - Assertion: All lowercase "revenue" replaced; no unreplaced instances found
   - What's tested: replaceAllText operation (index-independent), case-insensitive matching

3. **apply_bold_and_insert**
   - Operations: (1) Insert text at document end, (2) Apply bold to "15%"
   - Assertion: Text appended to document; "15%" element has `bold: true` in textStyle
   - What's tested: Two-phase compilation (content ops before format ops), format state verification

4. **insert_table**
   - Operation: Insert 2×3 table after "Revenue Analysis" heading
   - Assertion: Document contains table element with rows=2, columns=3
   - What's tested: Table structure creation, index arithmetic for structural elements

5. **create_named_range**
   - Operation: Create named range over "Executive Summary" heading bounds
   - Assertion: Named range appears in documentTab.namedRanges with expected name
   - What's tested: Named range creation, heading-as-range address resolution

6. **insert_bullet_list**
   - Operation: Insert 3-item bullet list at document end
   - Assertion: Document contains 3+ bullet paragraphs
   - What's tested: List creation with preset bullets, paragraph mutation detection

7. **create_header_footer**
   - Operations: Create default header, create default footer
   - Assertion: documentTab.headers and documentTab.footers are non-empty
   - What's tested: Structural element creation (header/footer), multi-operation batching

8. **insert_page_break**
   - Operation: Insert page break before "Conclusion" heading
   - Assertion: Document contains pageBreak element in body paragraph.elements
   - What's tested: Page break element insertion, structural integrity

### Phase 4 Live MCP Server Validations (via validate_mcp.py)

Tests exercise the server tool functions directly (not compiler.py), validating the full MCP integration.

1. **test_read_document**
   - Call: `read_document(doc_id)`
   - Assertion: Response contains `next_step` and `document_reality`. Structural map shows 5 headings with correct levels (HEADING_1, HEADING_2). Heading names match document (Report Title, Revenue Analysis, etc.)
   - What's tested: Structural map builder, heading extraction, level detection, behavioral next_step text

2. **test_edit_document_insert**
   - Call: `edit_document(doc_id, [insert_text after "Revenue Analysis"])`
   - Assertion: No error in response. operations_compiled=1, requests_emitted=1. Live document contains inserted text positioned after heading.
   - What's tested: Full MCP tool stack (server → compiler → auth → API execution), live state verification

3. **test_edit_document_compound**
   - Call: `edit_document(doc_id, [insert_table after "Key Metrics"])`
   - Assertion: No error. `present_to_user` field is present (signaling compound operation). `next_step` mentions read_document. Live document contains new table.
   - What's tested: Compound operation detection, behavioral response building, structural element creation

4. **test_validate_operations**
   - Call: `validate_operations(doc_id, [insert_text before "Conclusion"])`
   - Assertion: validation="passed". operations_compiled=1, requests_emitted=1. content_mutations=1. compiled_requests is populated.
   - What's tested: Compile-only path, request categorization (content vs format), no API execution

5. **test_error_invalid_address**
   - Call: `edit_document(doc_id, [insert_text with heading="NO_SUCH_HEADING_XYZ"])`
   - Assertion: Response error="address_resolution_failed". next_step directs to read_document.
   - What's tested: Address resolution error handling, error recovery guidance

6. **test_error_invalid_operation**
   - Call: `edit_document(doc_id, [operation with type="not_a_real_operation"])`
   - Assertion: Response error in ("invalid_operation", "compilation_failed"). next_step present.
   - What's tested: Operation type validation, structured error response

---

## Corruption Detection Test Coverage

### Test Categories

Corruption detection tests verify that the compiler catches errors that would silently corrupt a document if not caught. The categories:

1. **Structural Boundary Corruption** — Operations that would produce invalid indices or break document structure
   - `test_index.py::TestValidateIndex` (5 tests): negative indices, out-of-bounds indices, boundary conditions
   - `test_index.py::TestValidateRange` (3 tests): invalid ranges (end < start), negative bounds, segment overflow
   - `test_address.py::TestAddressResolution`: ambiguous headings, missing headings, out-of-bounds absolute indices

2. **Overflow & Cascading Shifts** — Operations that trigger cascading index shifts and must be ordered correctly
   - `test_compiler.py::TestTwoPhaseOrdering` (1 test): content operations must precede format operations
   - `test_index.py::sort_requests_reverse_index` (implicit via compiler tests): requests sorted descending by index to avoid cascading
   - Multiple operation tests in `test_text_ops.py`, `test_structure_ops.py`: verify each operation's mutation doesn't corrupt subsequent indices

3. **Structural Overlap & Element Boundary** — Operations that would corrupt table structure, list nesting, element markers
   - `test_structure_ops.py`: table row/column insertion, structural validity
   - `test_organization_ops.py`: named range mutation, boundary shifts

4. **Surrogate Pair Corruption** — UTF-16 specific: operations that land indices inside emoji/supplementary character pairs
   - `test_index.py::TestValidateNotInSurrogate` (4 tests): emoji, musical symbols, verify offset doesn't split surrogate pair
   - `test_index.py::TestUtf16Length` (8 tests): emoji, CJK, mixed content UTF-16 counting
   - Implicit: all index validation passes through utf16_length and validate_not_in_surrogate

### Coverage Summary

- **Total unit tests:** 191 (across 10 test files)
- **Structural boundary:** ~40 tests (validation, address resolution, bounds checking)
- **Cascading shifts:** ~50 tests (two-phase ordering, reverse index sort, multi-operation batching)
- **Structural overlap:** ~40 tests (table, list, element operations)
- **Surrogate pair:** ~12 tests (UTF-16 arithmetic, emoji handling)
- **Gap:** Very large documents (>1M characters) not tested in unit suite; live API tests validate against real documents

---

## Auth Flow

### User Journey: pip install → Working MCP Connection

**Step 0: Install Arezzo**
```
pip install arezzo
# Or: uv tool install arezzo
```

**Step 1: Run arezzo init**
```
arezzo init
```

This launches an interactive setup wizard:

#### 1a. Credential Discovery
- Wizard checks if `~/.config/arezzo/credentials.json` exists
  - **If yes:** Prints "credentials.json found at ~/.config/arezzo/credentials.json" and skips to Step 1b
  - **If no:** Prompts user for path to credentials.json
    - User obtains credentials.json from Google Cloud Console (OAuth 2.0 Desktop App)
    - User enters path (e.g., `~/Downloads/client_secret_*.json`)
    - Wizard validates file exists, copies to `~/.config/arezzo/credentials.json`
    - Creates parent directory if needed

**Credential resolution order in code (auth.py):**
1. `AREZZO_CREDENTIALS_FILE` environment variable (if set)
2. `~/.config/arezzo/credentials.json` (installed location)
3. `<repo-root>/credentials.json` (dev fallback, if running from source)

#### 1b. OAuth Token Flow
- Wizard checks if `~/.config/arezzo/token.json` exists
  - **If yes:** Prints "OAuth token already present — skipping authorization flow"
  - **If no:** Launches browser for OAuth consent
    - User sees Google sign-in + Arezzo permission request ("access your Google Docs and Drive")
    - User grants permission
    - Browser redirects to localhost; token extracted and saved to `~/.config/arezzo/token.json`
    - Wizard prints "Token saved to ~/.config/arezzo/token.json"

**Token refresh logic (auth.py):**
- Token loaded from `~/.config/arezzo/token.json` on each MCP server start
- If token expired and refresh_token present: automatic refresh
- If token invalid or no refresh_token: re-run OAuth flow

#### 1c. Platform Config Generation
- Wizard asks: "Generate platform config files in [current_directory]? [Y/n]"
  - **If yes:** Generates 3 platform-specific configs:
    - `.mcp.json` for Claude Code
    - `.cursor/mcp.json` for Cursor
    - `.vscode/mcp.json` for VS Code
  - Prints instructions for Claude Desktop (cannot auto-write to `~/Library/Application Support/Claude/`):
    ```
    For Claude Desktop, add this to:
    ~/Library/Application Support/Claude/claude_desktop_config.json

    "mcpServers": {
      "arezzo": {
        "command": "arezzo"
      }
    }
    ```

**Step 2: Test Connection**
```
arezzo
# or
arezzo serve
```

Starts MCP server on stdio. Client (Claude Code, Cursor, Claude Desktop) can now:
1. Call `read_document(document_id)`
2. Call `edit_document(document_id, operations)`
3. Call `validate_operations(document_id, operations)`

### Error Scenarios

**Missing credentials.json:**
```
FileNotFoundError: No credentials.json found.
Run `arezzo init` to set up authentication,
or set AREZZO_CREDENTIALS_FILE to the path of your OAuth client secret.
```

**Expired token, no refresh_token:**
- OAuth flow re-runs automatically
- User sees browser popup for re-consent (rare; Google usually extends tokens)

**Invalid OAuth scope:**
- Arezzo requests `https://www.googleapis.com/auth/documents` and `https://www.googleapis.com/auth/drive`
- If user revokes Drive scope, Arezzo will fail on document access
- Solution: Delete `~/.config/arezzo/token.json` and re-run `arezzo init`

**Document access denied:**
- User attempts to edit a document they don't have edit permission on
- Google Docs API returns 403 Forbidden
- edit_document returns error response with next_step guidance

### Environment Variable Override

For CI/CD or containerized setups:
```
export AREZZO_CREDENTIALS_FILE=/path/to/service/account/credentials.json
arezzo serve
```

Arezzo will use the specified credentials file, bypassing the default lookup order.

### Summary

| Phase | File | User Action |
|-------|------|-------------|
| Install | pyproject.toml | `pip install arezzo` |
| Discovery | auth.py + setup.py | `arezzo init` → prompt for credentials path |
| OAuth | auth.py + browser | Google consent flow, token saved to ~/.config/arezzo/ |
| Platform Config | setup.py | Generate .mcp.json files, print Claude Desktop instructions |
| Connect | cli.py + server.py | `arezzo serve` or MCP client calls server tools |
| Operation | server.py | Call read_document, edit_document, validate_operations |
