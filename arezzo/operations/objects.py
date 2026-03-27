"""Object operation compilers — images, headers, footers, footnotes, page breaks."""

from __future__ import annotations


def compile_insert_inline_image(
    index: int,
    uri: str,
    width_pt: float,
    height_pt: float,
    tab_id: str | None = None,
) -> dict:
    """Compile an insertInlineImage request."""
    loc = {"index": index}
    if tab_id:
        loc["tabId"] = tab_id
    return {
        "insertInlineImage": {
            "location": loc,
            "uri": uri,
            "objectSize": {
                "width": {"magnitude": width_pt, "unit": "PT"},
                "height": {"magnitude": height_pt, "unit": "PT"},
            },
        }
    }


def compile_create_header(header_type: str = "DEFAULT") -> dict:
    """Compile a createHeader request."""
    return {"createHeader": {"type": header_type}}


def compile_create_footer(footer_type: str = "DEFAULT") -> dict:
    """Compile a createFooter request."""
    return {"createFooter": {"type": footer_type}}


def compile_create_footnote(index: int, tab_id: str | None = None) -> dict:
    """Compile a createFootnote request."""
    loc = {"index": index}
    if tab_id:
        loc["tabId"] = tab_id
    return {"createFootnote": {"location": loc}}
