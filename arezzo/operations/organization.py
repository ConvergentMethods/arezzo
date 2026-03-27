"""Organization operation compilers — named ranges."""

from __future__ import annotations

from arezzo.operations.text import compile_delete_content_range, compile_insert_text


def compile_create_named_range(
    name: str, start: int, end: int, tab_id: str | None = None
) -> dict:
    """Compile a createNamedRange request."""
    rng = {"startIndex": start, "endIndex": end}
    if tab_id:
        rng["tabId"] = tab_id
    return {"createNamedRange": {"name": name, "range": rng}}


def compile_delete_named_range(
    named_range_id: str | None = None, name: str | None = None
) -> dict:
    """Compile a deleteNamedRange request. Accepts ID or name."""
    if named_range_id:
        return {"deleteNamedRange": {"namedRangeId": named_range_id}}
    if name:
        return {"deleteNamedRange": {"name": name}}
    raise ValueError("Must provide either named_range_id or name")


def compile_replace_named_range_content(
    start: int, end: int, new_text: str, tab_id: str | None = None
) -> list[dict]:
    """Compile a named range content replacement (delete + insert).

    Returns two requests in a single-batch array.
    """
    return [
        compile_delete_content_range(start, end, tab_id),
        compile_insert_text(start, new_text, tab_id),
    ]
