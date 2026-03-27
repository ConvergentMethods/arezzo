"""Text operation compilers — insert, delete, replace_all, replace_section."""

from __future__ import annotations

from arezzo.index import utf16_length  # noqa: F401 — used by callers for shift calc


def compile_insert_text(index: int, text: str, tab_id: str | None = None) -> dict:
    """Compile an insertText request."""
    loc = {"index": index}
    if tab_id:
        loc["tabId"] = tab_id
    return {"insertText": {"location": loc, "text": text}}


def compile_insert_text_end(tab_id: str | None = None) -> dict:
    """Compile an insertText at end of segment using endOfSegmentLocation."""
    loc = {}
    if tab_id:
        loc["tabId"] = tab_id
    return {"insertText": {"endOfSegmentLocation": loc, "text": ""}}


def compile_delete_content_range(
    start: int, end: int, tab_id: str | None = None
) -> dict:
    """Compile a deleteContentRange request."""
    rng = {"startIndex": start, "endIndex": end}
    if tab_id:
        rng["tabId"] = tab_id
    return {"deleteContentRange": {"range": rng}}


def compile_replace_all_text(
    find_text: str, replace_text: str, match_case: bool = True
) -> dict:
    """Compile a replaceAllText request."""
    return {
        "replaceAllText": {
            "containsText": {"text": find_text, "matchCase": match_case},
            "replaceText": replace_text,
        }
    }


def compile_replace_section(
    start: int, end: int, new_text: str, tab_id: str | None = None
) -> list[dict]:
    """Compile a section replacement (delete + insert).

    Returns two requests: delete range then insert at the same position.
    These go in a single batchUpdate — the delete runs first, then the
    insert uses the same start index (which is now valid post-deletion).
    """
    return [
        compile_delete_content_range(start, end, tab_id),
        compile_insert_text(start, new_text, tab_id),
    ]
