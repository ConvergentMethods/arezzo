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
