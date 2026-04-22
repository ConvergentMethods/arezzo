# Arezzo

<!-- mcp-name: io.github.ConvergentMethods/arezzo -->

Deterministic compiler for Google Docs API operations.

You cannot safely modify a Google Doc by constructing `batchUpdate` requests yourself. The API uses UTF-16 code units with cascading index shifts — insert 10 characters at position 50, and every subsequent index in your batch is now wrong. A single miscalculation silently corrupts the document with no error message.

Arezzo compiles semantic intent into a correct request sequence. Tell it what you want to do; it handles the index arithmetic.

## For AI agents (MCP tools)

Arezzo exposes three tools via the Model Context Protocol:

```
read_document(document_id)
  → Returns the document's structural map: headings with hierarchy,
    named ranges, tables, section boundaries. Call this before editing
    so you know what addresses are available.

edit_document(document_id, operations)
  → Compiles operations into correct batchUpdate requests and executes
    them. Handles UTF-16 arithmetic, cascading index shifts, and
    OT-compatible request ordering. Supported operations: insert/delete/
    replace text, formatting (bold, italic, headings, links), tables,
    lists, images, headers/footers, footnotes, named ranges.

validate_operations(document_id, operations)
  → Compile-only dry run. Returns the compiled requests for inspection
    without executing. Use before edit_document when uncertain.
```

### Operation format

```json
{
  "type": "insert_text",
  "address": {"heading": "Revenue Analysis"},
  "params": {"text": "New paragraph content.\n"}
}
```

**Address modes:**
- `{"heading": "Section Name"}` — by heading text
- `{"named_range": "range_name"}` — by named range
- `{"bookmark": "bookmark_id"}` — by bookmark ID
- `{"start": true}` — document start
- `{"end": true}` — document end
- `{"index": 42}` — absolute UTF-16 index

**Operation types:**
`insert_text`, `delete_content`, `replace_all_text`, `replace_section`,
`update_text_style`, `update_paragraph_style`, `insert_bullet_list`,
`insert_table`, `insert_table_row`, `insert_table_column`,
`delete_table_row`, `delete_table_column`, `insert_image`,
`create_header`, `create_footer`, `create_footnote`,
`create_named_range`, `replace_named_range_content`, `insert_page_break`

### Recommended workflow

```
read_document → edit_document → (if structural changes) read_document → edit_document
```

Always read before editing. After inserting structural elements (tables, headers, footers),
read again to get the new element indices before adding content inside them.

## Installation

```bash
pip install arezzo
arezzo init
```

`arezzo init` walks through Google OAuth setup and writes platform config files for your MCP client.

## Setup

**Prerequisites:** A Google Cloud project with the Google Docs API enabled and an OAuth 2.0 client ID (Desktop application type).

```bash
arezzo init
```

The wizard:
1. Copies your `credentials.json` to `~/.config/arezzo/`
2. Runs the OAuth consent flow (browser opens once)
3. Generates config files for Claude Code, Cursor, and VS Code

For Claude Desktop, `arezzo init` prints the config block to add manually.

## Platform configs

After `arezzo init`, config files are written to your project directory:

**Claude Code / Cursor** (`.mcp.json`):
```json
{
  "mcpServers": {
    "arezzo": {
      "command": "arezzo"
    }
  }
}
```

**VS Code** (`.vscode/mcp.json`):
```json
{
  "servers": {
    "arezzo": {
      "type": "stdio",
      "command": "arezzo"
    }
  }
}
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):
```json
{
  "mcpServers": {
    "arezzo": {
      "command": "arezzo"
    }
  }
}
```

## Why Arezzo exists

The Google Docs `batchUpdate` API operates on UTF-16 code units with absolute index positions. Every character insertion or deletion shifts all subsequent indices. In a batch with multiple mutations, each request's indices must account for the effect of every prior request in the same batch.

Getting this right requires:
- UTF-16 length calculation (not Python `len()` — surrogate pairs count differently)
- Reverse-order execution for same-type mutations (delete from end to start)
- Two-phase compilation (content mutations before format mutations)
- Cascading offset tracking across multi-step operations

Arezzo handles this deterministically. The same input always produces the same output. No reasoning, no guessing, no "usually works."

## Architecture

```
semantic operation
    ↓
arezzo.parser.parse_document()    — build heading/range/bookmark indexes
    ↓
arezzo.address.resolve_address()  — semantic reference → document index
    ↓
arezzo.operations.*               — operation → batchUpdate request(s)
    ↓
arezzo.index.sort_requests()      — OT-compatible mutation ordering
    ↓
correct batchUpdate request sequence
```

The engine is a pure function: `compile_operations(doc, operations) → requests`. Deterministic. No side effects. No API calls.

The MCP server (`arezzo.server`) wraps the engine with Google Docs API I/O and behavioral guidance fields (`next_step`, `present_to_user`, `document_reality`).

## License

MIT — Convergent Methods, LLC
