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
