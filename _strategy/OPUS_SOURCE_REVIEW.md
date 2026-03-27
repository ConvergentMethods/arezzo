# Arezzo Source Code Review

---

## arezzo/server.py

```python
"""Arezzo MCP Server — deterministic compiler for Google Docs editing.

Three tools:
- read_document: see document structure before editing
- edit_document: compile + execute semantic operations
- validate_operations: compile-only, verify before executing

Behavioral advertising framework transferred from Boyce:
- Preamble: capability + action directive
- Tool descriptions: two-register (uncertain + confident model), loss aversion
- Response layer: next_step (always), present_to_user (risk only), document_reality
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from arezzo.compiler import compile_operations
from arezzo.errors import ArezzoAddressError, ArezzoCompileError, ArezzoOperationError
from arezzo.parser import parse_document

# ── Server ──────────────────────────────────────────────────────────────

mcp = FastMCP(
    "Arezzo",
    json_response=True,
    instructions=(
        "Arezzo is a deterministic compiler for Google Docs editing. Every "
        "document mutation compiled through Arezzo gets correct UTF-16 index "
        "arithmetic, cascading offset resolution, and OT-compatible request "
        "ordering. Start with read_document to see the document structure."
    ),
)


# ── Auth helper ─────────────────────────────────────────────────────────

def _get_docs_service():
    """Lazy import auth to avoid import-time credential requirements."""
    from arezzo.auth import get_docs_service
    return get_docs_service()


def _read_google_doc(document_id: str) -> dict:
    """Read a Google Doc via the API."""
    service = _get_docs_service()
    return service.documents().get(
        documentId=document_id, includeTabsContent=True
    ).execute()


def _execute_batch_update(document_id: str, body: dict) -> dict:
    """Execute a batchUpdate against a Google Doc."""
    service = _get_docs_service()
    return service.documents().batchUpdate(
        documentId=document_id, body=body
    ).execute()


# ── Structural map builder ──────────────────────────────────────────────

def _build_structural_map(parsed) -> dict:
    """Build a human/agent-readable structural map of the document."""
    headings = []
    for text, entries in parsed.heading_index.items():
        for start, end, _heading_id in entries:
            # Determine heading level from the raw body
            level = None
            for el in parsed.body:
                if el.get("startIndex") == start and "paragraph" in el:
                    style = el["paragraph"].get("paragraphStyle", {})
                    named = style.get("namedStyleType", "")
                    if named.startswith("HEADING_"):
                        level = int(named.split("_")[1])
                    break
            headings.append({
                "text": text,
                "level": level,
                "start_index": start,
                "end_index": end,
            })
    headings.sort(key=lambda h: h["start_index"])

    named_ranges = []
    for name, entries in parsed.named_range_index.items():
        for start, end, _range_id in entries:
            named_ranges.append({
                "name": name,
                "start_index": start,
                "end_index": end,
            })

    tables = []
    for el in parsed.body:
        if "table" in el:
            t = el["table"]
            tables.append({
                "start_index": el.get("startIndex", 0),
                "rows": t.get("rows", 0),
                "columns": t.get("columns", 0),
            })

    bookmarks = [
        {"id": bm_id, "index": idx}
        for bm_id, idx in parsed.bookmark_index.items()
    ]

    return {
        "title": parsed.raw.get("title", ""),
        "document_id": parsed.raw.get("documentId", ""),
        "tab_id": parsed.tab_id,
        "body_end_index": parsed.body_end_index,
        "headings": headings,
        "named_ranges": named_ranges,
        "tables": tables,
        "bookmarks": bookmarks,
        "has_header": len(parsed.headers) > 0,
        "has_footer": len(parsed.footers) > 0,
        "footnote_count": len(parsed.footnotes),
        "list_count": len(parsed.lists),
        "inline_object_count": len(parsed.inline_objects),
    }


# ── Response builders ───────────────────────────────────────────────────

def _build_read_response(_parsed, structural_map: dict) -> dict:
    """Build response for read_document with behavioral guidance."""
    heading_count = len(structural_map["headings"])
    nr_count = len(structural_map["named_ranges"])
    table_count = len(structural_map["tables"])

    # Affordance summary for next_step
    affordances = []
    if heading_count > 0:
        affordances.append(f"{heading_count} headings (use as addresses)")
    if nr_count > 0:
        affordances.append(f"{nr_count} named ranges (pre-resolved addresses)")
    if table_count > 0:
        affordances.append(f"{table_count} table(s)")

    next_step = (
        "Use edit_document to make changes. "
        "Target locations by heading name, named range, or absolute index."
    )
    if affordances:
        next_step = (
            f"Document has {', '.join(affordances)}. "
            "Use edit_document to make changes — target locations by heading "
            "name, named range, or absolute index."
        )

    return {
        "next_step": next_step,
        "document_reality": structural_map,
    }


def _build_edit_response(
    document_id: str, operations: list[dict], compiled: dict, after_doc: dict | None
) -> dict:
    """Build response for edit_document with behavioral guidance."""
    op_count = len(operations)
    req_count = len(compiled.get("requests", []))

    response = {
        "next_step": (
            "Document updated. Call read_document if you need the current "
            "structure for further edits."
        ),
        "operations_compiled": op_count,
        "requests_emitted": req_count,
        "document_id": document_id,
    }

    # Check for compound operations that may need follow-up
    op_types = {op.get("type") for op in operations}
    compound_types = {"insert_table", "create_header", "create_footer", "create_footnote"}
    if op_types & compound_types:
        response["present_to_user"] = (
            "Structural elements created. If you need to add content inside "
            "them (table cells, header text, footnote text), call read_document "
            "to get the new element indices, then call edit_document again."
        )
        response["next_step"] = (
            "Structural elements created. Call read_document to see new "
            "indices, then edit_document to add content inside them."
        )

    # Check for named range mutations that invalidate boundaries
    nr_mutating = {"replace_named_range_content", "delete_content", "insert_text", "replace_section"}
    if op_types & nr_mutating:
        parsed_after = parse_document(after_doc) if after_doc else None
        if parsed_after and parsed_after.named_range_index:
            if "present_to_user" not in response:
                response["present_to_user"] = (
                    "Content mutations may have shifted named range boundaries. "
                    "Re-read the document before targeting named ranges again."
                )

    return response


def _build_validate_response(compiled: dict, operations: list[dict]) -> dict:
    """Build response for validate_operations."""
    req_count = len(compiled.get("requests", []))

    # Categorize requests
    content_reqs = 0
    format_reqs = 0
    for req in compiled.get("requests", []):
        key = list(req.keys())[0]
        if key in ("updateTextStyle", "updateParagraphStyle", "createParagraphBullets"):
            format_reqs += 1
        else:
            content_reqs += 1

    return {
        "next_step": (
            "Validation passed. Call edit_document with the same operations "
            "to execute them."
        ),
        "validation": "passed",
        "operations_compiled": len(operations),
        "requests_emitted": req_count,
        "content_mutations": content_reqs,
        "format_mutations": format_reqs,
        "compiled_requests": compiled,
    }


# ── Tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def read_document(document_id: str) -> dict:
    """See what the document contains before you edit it.

    Returns the document's structural map — headings with hierarchy, named
    ranges with boundaries, tables with dimensions, inline objects, and
    section boundaries. Without this, you're editing blind: you don't know
    what headings exist, where sections start, or what named ranges are
    available for targeting.

    **Call this before edit_document.** The structural map shows what
    addresses are available (heading names, named range names) so your edit
    operations target the right locations.

    Args:
        document_id: The Google Docs document ID (from the URL).
    """
    doc = _read_google_doc(document_id)
    parsed = parse_document(doc)
    structural_map = _build_structural_map(parsed)
    return _build_read_response(parsed, structural_map)


@mcp.tool()
def edit_document(document_id: str, operations: list[dict]) -> dict:
    """Make changes to a Google Doc with correct index arithmetic.

    You cannot safely modify a Google Doc by constructing batchUpdate
    requests yourself. The API uses UTF-16 code units with cascading index
    shifts — insert 10 characters at position 50, and every subsequent
    index in your batch is wrong. A single miscalculation silently corrupts
    the document with no error message. This tool compiles your semantic
    intent into a correct request sequence.

    **Recommended flow:** call read_document first, then describe your
    changes using heading names or named ranges as addresses. Supports:
    text insertion/deletion/replacement, formatting (bold, italic, headings,
    links), tables, lists, images, headers/footers, footnotes, named ranges.

    Args:
        document_id: The Google Docs document ID.
        operations: List of operation dicts. Each has:
            - type: operation name (insert_text, update_text_style, etc.)
            - address: target location ({"heading": "Budget"}, {"start": true}, etc.)
            - params: operation-specific parameters
    """
    # Read current document state
    doc = _read_google_doc(document_id)

    # Compile
    try:
        compiled = compile_operations(doc, operations)
    except ArezzoAddressError as e:
        return {
            "error": "address_resolution_failed",
            "message": str(e),
            "next_step": (
                "Call read_document to see available headings and named "
                "ranges, then retry with a valid address."
            ),
        }
    except ArezzoOperationError as e:
        return {
            "error": "invalid_operation",
            "message": str(e),
            "next_step": "Fix the operation type or parameters and retry.",
        }
    except ArezzoCompileError as e:
        return {
            "error": "compilation_failed",
            "message": str(e),
            "next_step": "Check the operation parameters and document state.",
        }

    # Execute
    try:
        _execute_batch_update(document_id, compiled)
    except Exception as e:
        return {
            "error": "execution_failed",
            "message": str(e),
            "next_step": (
                "The compiled request was rejected by the Google Docs API. "
                "Call read_document to check the current document state."
            ),
            "compiled_requests": compiled,
        }

    # Read back for verification and response building
    try:
        after_doc = _read_google_doc(document_id)
    except Exception:
        after_doc = None

    return _build_edit_response(document_id, operations, compiled, after_doc)


@mcp.tool()
def validate_operations(document_id: str, operations: list[dict]) -> dict:
    """Check whether edit operations would succeed without executing them.

    Returns the compiled batchUpdate requests plus validation status. Use
    this when you want to inspect the exact API calls before they execute,
    or when debugging why an edit might fail. Catches address resolution
    errors, ambiguous headings, out-of-bounds indices, and invalid
    operation parameters.

    **Use this before edit_document when uncertain.** Shows exactly what
    Arezzo would send to the Google Docs API.

    Args:
        document_id: The Google Docs document ID.
        operations: List of operation dicts (same format as edit_document).
    """
    doc = _read_google_doc(document_id)

    try:
        compiled = compile_operations(doc, operations)
    except ArezzoAddressError as e:
        return {
            "validation": "failed",
            "error": "address_resolution_failed",
            "message": str(e),
            "next_step": (
                "Call read_document to see available headings and named "
                "ranges, then fix the address."
            ),
        }
    except ArezzoOperationError as e:
        return {
            "validation": "failed",
            "error": "invalid_operation",
            "message": str(e),
            "next_step": "Fix the operation type or parameters.",
        }
    except ArezzoCompileError as e:
        return {
            "validation": "failed",
            "error": "compilation_failed",
            "message": str(e),
            "next_step": "Check the operation parameters.",
        }

    return _build_validate_response(compiled, operations)


# ── Entry point ─────────────────────────────────────────────────────────

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

---

## arezzo/compiler.py

```python
"""Arezzo compiler — compile_operations() entry point.

Stateless pure function: document state in → batchUpdate request body out.
Two-phase compilation: content mutations first (reverse index order),
then format mutations (index-neutral, appended after content).
"""

from __future__ import annotations

from arezzo.address import resolve_address, resolve_address_range
from arezzo.errors import ArezzoCompileError, ArezzoOperationError
from arezzo.index import sort_requests_reverse_index, utf16_length, validate_index
from arezzo.parser import ParsedDocument, parse_document

from arezzo.operations.text import (
    compile_delete_content_range,
    compile_insert_text,
    compile_replace_all_text,
    compile_replace_section,
)
from arezzo.operations.format import (
    compile_create_paragraph_bullets,
    compile_update_paragraph_style,
    compile_update_text_style,
)
from arezzo.operations.structure import (
    compile_delete_table_column,
    compile_delete_table_row,
    compile_insert_bullet_list,
    compile_insert_page_break,
    compile_insert_table,
    compile_insert_table_column,
    compile_insert_table_row,
)
from arezzo.operations.objects import (
    compile_create_footer,
    compile_create_footnote,
    compile_create_header,
    compile_insert_inline_image,
)
from arezzo.operations.organization import (
    compile_create_named_range,
    compile_delete_named_range,
    compile_replace_named_range_content,
)

# Operations that modify content (shift indices) — Phase 1
CONTENT_OPS = {
    "insert_text",
    "delete_content",
    "replace_all_text",
    "replace_section",
    "insert_table",
    "insert_table_row",
    "insert_table_column",
    "delete_table_row",
    "delete_table_column",
    "insert_bullet_list",
    "insert_numbered_list",
    "insert_page_break",
    "insert_inline_image",
    "create_header",
    "create_footer",
    "create_footnote",
    "create_named_range",
    "delete_named_range",
    "replace_named_range_content",
}

# Operations that only modify formatting (index-neutral) — Phase 2
FORMAT_OPS = {
    "update_text_style",
    "update_paragraph_style",
    "create_paragraph_bullets",
    "convert_to_list",
}


def compile_operations(
    document: dict,
    operations: list[dict],
    write_control: str = "target",
) -> dict:
    """Compile agent-intent operations into a batchUpdate request body.

    Args:
        document: Full documents.get response (includeTabsContent=true).
        operations: List of agent-intent operation dicts.
        write_control: "target" (OT merge) or "required" (optimistic lock).

    Returns:
        Dict ready to POST as batchUpdate body:
        {"requests": [...], "writeControl": {...}}

    Raises:
        ArezzoCompileError: Base class for all compilation errors.
        ArezzoAddressError: Unresolvable or ambiguous address.
        ArezzoOperationError: Invalid operation type or params.
        ArezzoIndexError: UTF-16 index arithmetic failure.
    """
    parsed = parse_document(document)

    content_requests: list[dict] = []
    format_requests: list[dict] = []

    for op in operations:
        op_type = op.get("type")
        if not op_type:
            raise ArezzoOperationError("Operation missing 'type' field")

        if op_type in CONTENT_OPS:
            reqs = _compile_content_op(parsed, op)
            if isinstance(reqs, list):
                content_requests.extend(reqs)
            else:
                content_requests.append(reqs)
        elif op_type in FORMAT_OPS:
            reqs = _compile_format_op(parsed, op)
            if isinstance(reqs, list):
                format_requests.extend(reqs)
            else:
                format_requests.append(reqs)
        else:
            raise ArezzoOperationError(
                f"Unknown operation type: '{op_type}'. "
                f"Valid types: {sorted(CONTENT_OPS | FORMAT_OPS)}"
            )

    # Phase 1: content mutations in reverse index order
    sorted_content = sort_requests_reverse_index(content_requests)
    # Phase 2: format mutations appended (order doesn't matter, but keep stable)
    all_requests = sorted_content + format_requests

    # WriteControl
    if write_control == "required":
        wc = {"requiredRevisionId": parsed.revision_id}
    else:
        wc = {"targetRevisionId": parsed.revision_id}

    return {"requests": all_requests, "writeControl": wc}


def _compile_content_op(parsed: ParsedDocument, op: dict) -> dict | list[dict]:
    """Compile a single content operation."""
    op_type = op["type"]
    address = op.get("address", {})
    params = op.get("params", {})
    tab_id = parsed.tab_id

    if op_type == "insert_text":
        idx = resolve_address(parsed, address)
        text = params.get("text", "")
        return compile_insert_text(idx, text, tab_id)

    if op_type == "delete_content":
        if "named_range" in address or "heading" in address:
            start, end = resolve_address_range(parsed, address)
        else:
            start = resolve_address(parsed, address)
            end = start + params.get("length", 0)
        return compile_delete_content_range(start, end, tab_id)

    if op_type == "replace_all_text":
        return compile_replace_all_text(
            params["find_text"],
            params["replace_text"],
            params.get("match_case", True),
        )

    if op_type == "replace_section":
        start, end = resolve_address_range(parsed, address)
        return compile_replace_section(start, end, params["text"], tab_id)

    if op_type == "insert_table":
        idx = resolve_address(parsed, address)
        return compile_insert_table(idx, params["rows"], params["columns"], tab_id)

    if op_type == "insert_table_row":
        return compile_insert_table_row(
            params["table_start_index"],
            params["row_index"],
            params.get("column_index", 0),
            params.get("insert_below", True),
            tab_id,
        )

    if op_type == "insert_table_column":
        return compile_insert_table_column(
            params["table_start_index"],
            params.get("row_index", 0),
            params["column_index"],
            params.get("insert_right", True),
            tab_id,
        )

    if op_type == "delete_table_row":
        return compile_delete_table_row(
            params["table_start_index"],
            params["row_index"],
            params.get("column_index", 0),
            tab_id,
        )

    if op_type == "delete_table_column":
        return compile_delete_table_column(
            params["table_start_index"],
            params.get("row_index", 0),
            params["column_index"],
            tab_id,
        )

    if op_type in ("insert_bullet_list", "insert_numbered_list"):
        idx = resolve_address(parsed, address)
        preset = (
            "NUMBERED_DECIMAL_ALPHA_ROMAN"
            if op_type == "insert_numbered_list"
            else params.get("bullet_preset", "BULLET_DISC_CIRCLE_SQUARE")
        )
        return compile_insert_bullet_list(idx, params["items"], preset, tab_id)

    if op_type == "insert_page_break":
        idx = resolve_address(parsed, address)
        return compile_insert_page_break(idx, tab_id)

    if op_type == "insert_inline_image":
        idx = resolve_address(parsed, address)
        return compile_insert_inline_image(
            idx, params["uri"], params["width_pt"], params["height_pt"], tab_id
        )

    if op_type == "create_header":
        return compile_create_header(params.get("type", "DEFAULT"))

    if op_type == "create_footer":
        return compile_create_footer(params.get("type", "DEFAULT"))

    if op_type == "create_footnote":
        idx = resolve_address(parsed, address)
        return compile_create_footnote(idx, tab_id)

    if op_type == "create_named_range":
        start, end = resolve_address_range(parsed, address)
        return compile_create_named_range(params["name"], start, end, tab_id)

    if op_type == "delete_named_range":
        return compile_delete_named_range(
            named_range_id=params.get("named_range_id"),
            name=params.get("name"),
        )

    if op_type == "replace_named_range_content":
        start, end = resolve_address_range(parsed, address)
        return compile_replace_named_range_content(start, end, params["text"], tab_id)

    raise ArezzoOperationError(f"Unhandled content operation: {op_type}")


def _compile_format_op(parsed: ParsedDocument, op: dict) -> dict | list[dict]:
    """Compile a single format operation."""
    op_type = op["type"]
    address = op.get("address", {})
    params = op.get("params", {})
    tab_id = parsed.tab_id

    if op_type == "update_text_style":
        if "named_range" in address or "heading" in address:
            start, end = resolve_address_range(parsed, address)
        else:
            start = resolve_address(parsed, address)
            end = start + params.get("length", 0)
        return compile_update_text_style(
            start, end, params["text_style"], params["fields"], tab_id
        )

    if op_type == "update_paragraph_style":
        if "named_range" in address or "heading" in address:
            start, end = resolve_address_range(parsed, address)
        else:
            start = resolve_address(parsed, address)
            end = start + params.get("length", 0)
        return compile_update_paragraph_style(
            start, end, params["paragraph_style"], params["fields"], tab_id
        )

    if op_type in ("create_paragraph_bullets", "convert_to_list"):
        if "named_range" in address or "heading" in address:
            start, end = resolve_address_range(parsed, address)
        else:
            start = resolve_address(parsed, address)
            end = start + params.get("length", 0)
        return compile_create_paragraph_bullets(
            start, end, params.get("bullet_preset", "BULLET_DISC_CIRCLE_SQUARE"), tab_id
        )

    raise ArezzoOperationError(f"Unhandled format operation: {op_type}")
```

---

## arezzo/parser.py

```python
"""Parse documents.get JSON into ParsedDocument.

Thin wrapper around the raw Google Docs JSON with pre-built lookup indexes
for address resolution. Single-pass construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    """Parsed Google Docs document with pre-built indexes.

    The raw JSON stays available for anything the indexes don't cover.
    Indexes are built in a single pass during parse.
    """

    raw: dict
    tab_id: str | None
    revision_id: str
    body: list[dict]
    body_end_index: int
    # heading_text → [(start_index, end_index, heading_id)]
    heading_index: dict[str, list[tuple[int, int, str | None]]] = field(
        default_factory=dict
    )
    # range_name → [(start_index, end_index, range_id)]
    named_range_index: dict[str, list[tuple[int, int, str]]] = field(
        default_factory=dict
    )
    # bookmark_id → index
    bookmark_index: dict[str, int] = field(default_factory=dict)
    headers: dict[str, dict] = field(default_factory=dict)
    footers: dict[str, dict] = field(default_factory=dict)
    footnotes: dict[str, dict] = field(default_factory=dict)
    lists: dict[str, dict] = field(default_factory=dict)
    inline_objects: dict[str, dict] = field(default_factory=dict)


def parse_document(doc: dict) -> ParsedDocument:
    """Parse a documents.get response into a ParsedDocument.

    Args:
        doc: Full documents.get response with includeTabsContent=true.

    Returns:
        ParsedDocument with pre-built indexes.

    Raises:
        ValueError: If the document structure is invalid or missing tabs.
    """
    tabs = doc.get("tabs")
    if not tabs:
        raise ValueError("Document has no tabs")

    tab = tabs[0]
    tab_props = tab.get("tabProperties", {})
    tab_id = tab_props.get("tabId")

    doc_tab = tab.get("documentTab", {})
    body_content = doc_tab.get("body", {}).get("content", [])

    revision_id = doc.get("revisionId", "")

    # Body end index
    body_end_index = 1
    if body_content:
        last = body_content[-1]
        body_end_index = last.get("endIndex", last.get("startIndex", 0) + 1)

    # Build heading index
    heading_index: dict[str, list[tuple[int, int, str | None]]] = {}
    for element in body_content:
        if "paragraph" not in element:
            continue
        para = element["paragraph"]
        style = para.get("paragraphStyle", {})
        named_style = style.get("namedStyleType", "")
        if not named_style.startswith("HEADING_"):
            continue

        heading_id = style.get("headingId")
        start = element.get("startIndex", 0)
        end = element["endIndex"]

        # Extract heading text from textRun elements
        text_parts = []
        for elem in para.get("elements", []):
            text_run = elem.get("textRun")
            if text_run:
                text_parts.append(text_run.get("content", ""))
        heading_text = "".join(text_parts).rstrip("\n")

        if heading_text:
            heading_index.setdefault(heading_text, []).append(
                (start, end, heading_id)
            )

    # Build named range index
    named_range_index: dict[str, list[tuple[int, int, str]]] = {}
    for name, nr_data in doc_tab.get("namedRanges", {}).items():
        for nr in nr_data.get("namedRanges", []):
            nr_id = nr.get("namedRangeId", "")
            for r in nr.get("ranges", []):
                start = r.get("startIndex", 0)
                end = r["endIndex"]
                named_range_index.setdefault(name, []).append(
                    (start, end, nr_id)
                )

    # Build bookmark index
    bookmark_index: dict[str, int] = {}
    for bm_id, bm_data in doc_tab.get("bookmarks", {}).items():
        location = bm_data.get("location", {})
        bookmark_index[bm_id] = location.get("index", 0)

    # Segments
    headers = dict(doc_tab.get("headers", {}))
    footers = dict(doc_tab.get("footers", {}))
    footnotes = dict(doc_tab.get("footnotes", {}))
    lists = dict(doc_tab.get("lists", {}))
    inline_objects = dict(doc_tab.get("inlineObjects", {}))

    return ParsedDocument(
        raw=doc,
        tab_id=tab_id,
        revision_id=revision_id,
        body=body_content,
        body_end_index=body_end_index,
        heading_index=heading_index,
        named_range_index=named_range_index,
        bookmark_index=bookmark_index,
        headers=headers,
        footers=footers,
        footnotes=footnotes,
        lists=lists,
        inline_objects=inline_objects,
    )
```

---

## arezzo/address.py

```python
"""Address resolution — 6 modes for resolving semantic references to indices.

Every address mode requires a ParsedDocument. Resolution is exact —
no fuzzy matching, no heuristics, no fallbacks.
"""

from __future__ import annotations

from arezzo.errors import ArezzoAddressError
from arezzo.parser import ParsedDocument


def resolve_address(parsed: ParsedDocument, address: dict) -> int:
    """Resolve an address dict to a document index.

    Args:
        parsed: ParsedDocument from parser.
        address: One of the 6 address mode dicts.

    Returns:
        The resolved index position.

    Raises:
        ArezzoAddressError: If the address cannot be resolved.
    """
    if "heading" in address:
        return _resolve_heading(parsed, address["heading"], address.get("position", "after"))
    if "named_range" in address:
        return _resolve_named_range(parsed, address["named_range"], address.get("position", "start"))
    if "bookmark" in address:
        return _resolve_bookmark(parsed, address["bookmark"])
    if address.get("end"):
        return _resolve_end(parsed)
    if address.get("start"):
        return _resolve_start()
    if "index" in address:
        return _resolve_absolute(parsed, address["index"])

    raise ArezzoAddressError(f"Unknown address mode: {address}")


def resolve_address_range(parsed: ParsedDocument, address: dict) -> tuple[int, int]:
    """Resolve an address to a (start, end) range.

    Used for operations that target a range (named ranges, sections between headings).

    Returns:
        (start_index, end_index) tuple.
    """
    if "named_range" in address:
        return _resolve_named_range_bounds(parsed, address["named_range"])
    if "heading" in address:
        # Return the heading paragraph's own range
        return _resolve_heading_range(parsed, address["heading"])

    raise ArezzoAddressError(f"Address mode does not support range resolution: {address}")


def _resolve_heading(parsed: ParsedDocument, heading_text: str, position: str = "after") -> int:
    """Resolve heading text to an index position."""
    entries = parsed.heading_index.get(heading_text)
    if not entries:
        available = list(parsed.heading_index.keys())
        raise ArezzoAddressError(
            f"Heading '{heading_text}' not found. "
            f"Available headings: {available}"
        )
    if len(entries) > 1:
        locations = [(s, e) for s, e, _ in entries]
        raise ArezzoAddressError(
            f"Heading '{heading_text}' is ambiguous — found {len(entries)} matches "
            f"at indices: {locations}. Use absolute index or make heading text unique."
        )
    start, end, _ = entries[0]
    if position == "before":
        return start
    return end  # "after" — insert at heading's endIndex


def _resolve_heading_range(parsed: ParsedDocument, heading_text: str) -> tuple[int, int]:
    """Resolve heading to its paragraph's (start, end) range."""
    entries = parsed.heading_index.get(heading_text)
    if not entries:
        raise ArezzoAddressError(f"Heading '{heading_text}' not found.")
    if len(entries) > 1:
        raise ArezzoAddressError(
            f"Heading '{heading_text}' is ambiguous — {len(entries)} matches."
        )
    start, end, _ = entries[0]
    return (start, end)


def _resolve_named_range(parsed: ParsedDocument, name: str, position: str = "start") -> int:
    """Resolve named range to a single index position."""
    entries = parsed.named_range_index.get(name)
    if not entries:
        available = list(parsed.named_range_index.keys())
        raise ArezzoAddressError(
            f"Named range '{name}' not found. Available: {available}"
        )
    start, end, _ = entries[0]
    if position == "end":
        return end
    return start


def _resolve_named_range_bounds(parsed: ParsedDocument, name: str) -> tuple[int, int]:
    """Resolve named range to its (start, end) range."""
    entries = parsed.named_range_index.get(name)
    if not entries:
        raise ArezzoAddressError(f"Named range '{name}' not found.")
    start, end, _ = entries[0]
    return (start, end)


def _resolve_bookmark(parsed: ParsedDocument, bookmark_id: str) -> int:
    """Resolve bookmark ID to its index."""
    if bookmark_id not in parsed.bookmark_index:
        available = list(parsed.bookmark_index.keys())
        raise ArezzoAddressError(
            f"Bookmark '{bookmark_id}' not found. Available: {available}"
        )
    return parsed.bookmark_index[bookmark_id]


def _resolve_end(parsed: ParsedDocument) -> int:
    """Resolve 'end of document' to the insertion point before trailing newline."""
    # The last element is always a trailing empty paragraph.
    # Insert before it — at its startIndex.
    if len(parsed.body) < 2:
        return 1
    return parsed.body[-1].get("startIndex", parsed.body_end_index - 1)


def _resolve_start() -> int:
    """Start of document is always index 1."""
    return 1


def _resolve_absolute(parsed: ParsedDocument, index: int) -> int:
    """Validate and return an absolute index."""
    if index < 0:
        raise ArezzoAddressError(f"Negative index: {index}")
    if index >= parsed.body_end_index:
        raise ArezzoAddressError(
            f"Index {index} is past document end ({parsed.body_end_index})"
        )
    return index
```

---

## arezzo/index.py

```python
"""UTF-16 index arithmetic for Google Docs API.

The API uses UTF-16 code units for all index positions. Surrogate pairs
(emoji, CJK supplementary, etc.) consume two index positions.
"""

from __future__ import annotations

from arezzo.errors import ArezzoIndexError


def utf16_length(text: str) -> int:
    """Calculate the UTF-16 code unit length of a Python string.

    Python strings are UTF-32 internally. The Google Docs API uses UTF-16.
    Characters in the Basic Multilingual Plane (U+0000–U+FFFF) consume 1
    code unit. Characters above U+FFFF (supplementary planes) consume 2
    code units (a surrogate pair).
    """
    count = 0
    for char in text:
        cp = ord(char)
        if cp > 0xFFFF:
            count += 2  # surrogate pair
        else:
            count += 1
    return count


def validate_index(index: int, segment_end: int, context: str = "") -> None:
    """Validate that an index is within a valid range.

    Raises ArezzoIndexError if the index is invalid.
    """
    if index < 0:
        raise ArezzoIndexError(f"Negative index {index}{_ctx(context)}")
    if index > segment_end:
        raise ArezzoIndexError(
            f"Index {index} exceeds segment end {segment_end}{_ctx(context)}"
        )


def validate_range(start: int, end: int, segment_end: int, context: str = "") -> None:
    """Validate a start/end range."""
    if start < 0:
        raise ArezzoIndexError(f"Negative start index {start}{_ctx(context)}")
    if end < start:
        raise ArezzoIndexError(
            f"End index {end} < start index {start}{_ctx(context)}"
        )
    if end > segment_end:
        raise ArezzoIndexError(
            f"End index {end} exceeds segment end {segment_end}{_ctx(context)}"
        )


def validate_not_in_surrogate(text: str, offset: int, context: str = "") -> None:
    """Validate that a UTF-16 offset doesn't fall inside a surrogate pair.

    Given the original text and a UTF-16 offset, verify the offset doesn't
    land on the second code unit of a surrogate pair.
    """
    utf16_pos = 0
    for char in text:
        cp = ord(char)
        char_len = 2 if cp > 0xFFFF else 1
        if utf16_pos < offset < utf16_pos + char_len and char_len == 2:
            raise ArezzoIndexError(
                f"Index {offset} falls inside surrogate pair for "
                f"U+{cp:04X}{_ctx(context)}"
            )
        utf16_pos += char_len
        if utf16_pos >= offset:
            break


def sort_requests_reverse_index(requests: list[dict]) -> list[dict]:
    """Sort batchUpdate requests by their target index in descending order.

    This is the standard technique for avoiding cascading index shifts:
    process from end of document toward beginning.

    Requests without a clear index (like replaceAllText) are placed first
    (they don't depend on specific indices).
    """
    def _extract_index(req: dict) -> int:
        """Extract the primary index from a batchUpdate request."""
        for key, value in req.items():
            if not isinstance(value, dict):
                continue
            # Location-based requests
            loc = value.get("location", {})
            if "index" in loc:
                return loc["index"]
            # Range-based requests
            rng = value.get("range", {})
            if "startIndex" in rng:
                return rng["startIndex"]
            # TableCellLocation
            tcl = value.get("tableCellLocation", {})
            tsl = tcl.get("tableStartLocation", {})
            if "index" in tsl:
                return tsl["index"]
            # ContainsText (replaceAllText) — no index
            if "containsText" in value:
                return -1
        return -1  # no index found — place first

    return sorted(requests, key=_extract_index, reverse=True)


def _ctx(context: str) -> str:
    return f" ({context})" if context else ""
```

---

## arezzo/errors.py

```python
"""Arezzo error hierarchy.

The compiler is a correctness guarantee. If it emits a request, that request
MUST be valid. If there is any doubt, raise one of these errors. Partial
correctness is total failure.
"""


class ArezzoCompileError(Exception):
    """Base class for all Arezzo compilation errors."""


class ArezzoAddressError(ArezzoCompileError):
    """Raised when an address cannot be resolved or is ambiguous.

    Includes: heading not found, multiple heading matches, named range
    not found, bookmark not found, index out of bounds.
    """


class ArezzoOperationError(ArezzoCompileError):
    """Raised when an operation type is invalid or its parameters are wrong.

    Includes: unknown operation type, missing required params, invalid
    param values, operation not applicable to target element.
    """


class ArezzoIndexError(ArezzoCompileError):
    """Raised when UTF-16 index arithmetic produces an invalid result.

    Includes: index in surrogate pair boundary, index past document end,
    index inside structural element marker, negative index.
    """
```

---

## arezzo/auth.py

```python
"""OAuth2 authentication for the Arezzo MCP server.

Credential lookup order:
  1. AREZZO_CREDENTIALS_FILE env var (absolute path)
  2. ~/.config/arezzo/credentials.json  (installed / arezzo init)
  3. <repo-root>/credentials.json       (development fallback)

Token is always cached next to the credentials file it was derived from.
"""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

_CONFIG_DIR = Path.home() / ".config" / "arezzo"
_REPO_ROOT = Path(__file__).parent.parent  # dev/arezzo/


def _resolve_credentials_file() -> Path:
    """Return the credentials.json path to use, in priority order."""
    env_path = os.environ.get("AREZZO_CREDENTIALS_FILE")
    if env_path:
        return Path(env_path)

    installed = _CONFIG_DIR / "credentials.json"
    if installed.exists():
        return installed

    dev = _REPO_ROOT / "credentials.json"
    if dev.exists():
        return dev

    raise FileNotFoundError(
        "No credentials.json found. Run `arezzo init` to set up authentication, "
        "or set AREZZO_CREDENTIALS_FILE to the path of your OAuth client secret."
    )


def _token_file_for(credentials_file: Path) -> Path:
    """Return the token.json path co-located with the given credentials file."""
    return credentials_file.parent / "token.json"


def get_credentials() -> Credentials:
    """Return valid OAuth2 credentials, running the consent flow if needed."""
    credentials_file = _resolve_credentials_file()
    token_file = _token_file_for(credentials_file)

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
        creds = flow.run_local_server(port=0)

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json())
    return creds


def get_docs_service():
    """Return an authenticated Google Docs API service."""
    from googleapiclient.discovery import build

    return build("docs", "v1", credentials=get_credentials())
```

---

## arezzo/cli.py

```python
"""Arezzo CLI entry point.

Usage:
    arezzo               Run the MCP server (stdio transport, default)
    arezzo serve         Run the MCP server (explicit)
    arezzo init          Set up authentication and generate platform configs
    arezzo version       Print version
"""

from __future__ import annotations

import sys


def _cmd_serve():
    from arezzo.server import main
    main()


def _cmd_init():
    from arezzo.setup import run_init
    run_init()


def _cmd_version():
    from importlib.metadata import version, PackageNotFoundError
    try:
        v = version("arezzo")
    except PackageNotFoundError:
        v = "0.1.0 (dev)"
    print(f"arezzo {v}")


def main():
    args = sys.argv[1:]

    if not args or args[0] == "serve":
        _cmd_serve()
    elif args[0] == "init":
        _cmd_init()
    elif args[0] == "version" or args[0] in ("-V", "--version"):
        _cmd_version()
    else:
        print(f"arezzo: unknown command '{args[0]}'", file=sys.stderr)
        print("Usage: arezzo [serve|init|version]", file=sys.stderr)
        sys.exit(1)
```

---

## arezzo/setup.py

```python
"""arezzo init — setup wizard and platform config generation."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "arezzo"
CREDENTIALS_DEST = CONFIG_DIR / "credentials.json"
TOKEN_DEST = CONFIG_DIR / "token.json"


# ── Platform config templates ────────────────────────────────────────────

def _claude_code_config() -> dict:
    return {"mcpServers": {"arezzo": {"command": "arezzo"}}}


def _cursor_config() -> dict:
    return {"mcpServers": {"arezzo": {"command": "arezzo"}}}


def _vscode_config() -> dict:
    return {"servers": {"arezzo": {"type": "stdio", "command": "arezzo"}}}


# ── Config generation ────────────────────────────────────────────────────

def generate_platform_configs(target_dir: Path) -> list[str]:
    """Write platform config files to target_dir. Returns list of written paths."""
    written = []

    # Claude Code (.mcp.json in project root)
    p = target_dir / ".mcp.json"
    p.write_text(json.dumps(_claude_code_config(), indent=2) + "\n")
    written.append(str(p))

    # Cursor (.cursor/mcp.json)
    cursor_dir = target_dir / ".cursor"
    cursor_dir.mkdir(exist_ok=True)
    p = cursor_dir / "mcp.json"
    p.write_text(json.dumps(_cursor_config(), indent=2) + "\n")
    written.append(str(p))

    # VS Code (.vscode/mcp.json)
    vscode_dir = target_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    p = vscode_dir / "mcp.json"
    p.write_text(json.dumps(_vscode_config(), indent=2) + "\n")
    written.append(str(p))

    return written


def _claude_desktop_path() -> Path:
    """Return the Claude Desktop config path for this platform."""
    import platform
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    # Linux
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


# ── Init wizard ─────────────────────────────────────────────────────────

def run_init():
    """Interactive setup wizard for Arezzo."""
    print("Arezzo Setup\n")

    # ── Step 1: Credentials ──────────────────────────────────────────────
    if CREDENTIALS_DEST.exists():
        print(f"  credentials.json found at {CREDENTIALS_DEST}")
    else:
        print("  credentials.json not found at ~/.config/arezzo/credentials.json")
        print()
        print("  To get credentials.json:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create an OAuth 2.0 client ID (Desktop application)")
        print("  3. Download the JSON file")
        print()
        src_input = input("  Path to your credentials.json: ").strip()
        src = Path(src_input).expanduser()

        if not src.exists():
            print(f"  Error: file not found: {src}", file=sys.stderr)
            sys.exit(1)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, CREDENTIALS_DEST)
        print(f"  Copied to {CREDENTIALS_DEST}")

    # ── Step 2: OAuth token ──────────────────────────────────────────────
    print()
    if TOKEN_DEST.exists():
        print("  OAuth token already present — skipping authorization flow.")
    else:
        print("  Running OAuth authorization flow (browser will open)...")
        try:
            from arezzo.auth import get_credentials
            get_credentials()
            print(f"  Token saved to {TOKEN_DEST}")
        except Exception as e:
            print(f"  Error during authorization: {e}", file=sys.stderr)
            sys.exit(1)

    # ── Step 3: Platform configs ─────────────────────────────────────────
    print()
    cwd = Path.cwd()
    answer = input(f"  Generate platform config files in {cwd}? [Y/n] ").strip().lower()
    if answer in ("", "y", "yes"):
        written = generate_platform_configs(cwd)
        print()
        for path in written:
            print(f"  Wrote {path}")

        # Claude Desktop — print instructions, don't write automatically
        desktop_path = _claude_desktop_path()
        print()
        print("  For Claude Desktop, add this to:")
        print(f"  {desktop_path}")
        print()
        print('  "mcpServers": {')
        print('    "arezzo": {')
        print('      "command": "arezzo"')
        print('    }')
        print('  }')

    # ── Done ─────────────────────────────────────────────────────────────
    print()
    print("Setup complete. Test with: arezzo (runs the MCP server on stdio)")
    print()
    print("In your MCP client, Arezzo exposes three tools:")
    print("  read_document(document_id)             — see document structure")
    print("  edit_document(document_id, operations) — compile + execute changes")
    print("  validate_operations(document_id, ops)  — dry-run compile only")
```

---

# OPUS_REVIEW_RESPONSE.md

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

