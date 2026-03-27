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
