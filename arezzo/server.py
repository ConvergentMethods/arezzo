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
    changes using heading names or named ranges as addresses.

    Valid operation types: insert_text, delete_content, replace_all_text,
    replace_section, update_text_style, update_paragraph_style,
    create_paragraph_bullets, convert_to_list, insert_table,
    insert_table_row, insert_table_column, delete_table_row,
    delete_table_column, insert_bullet_list, insert_numbered_list,
    insert_page_break, insert_inline_image, create_header, create_footer,
    create_footnote, create_named_range, delete_named_range,
    replace_named_range_content.

    Args:
        document_id: The Google Docs document ID.
        operations: List of operation dicts. Each has:
            - type: one of the operation types listed above
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
