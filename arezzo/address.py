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
