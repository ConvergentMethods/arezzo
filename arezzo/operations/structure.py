"""Structure operation compilers — tables, lists, page breaks."""

from __future__ import annotations

from arezzo.index import utf16_length


def compile_insert_table(
    index: int, rows: int, columns: int, tab_id: str | None = None
) -> dict:
    """Compile an insertTable request."""
    loc = {"index": index}
    if tab_id:
        loc["tabId"] = tab_id
    return {"insertTable": {"location": loc, "rows": rows, "columns": columns}}


def compile_insert_table_row(
    table_start_index: int,
    row_index: int,
    column_index: int = 0,
    insert_below: bool = True,
    tab_id: str | None = None,
) -> dict:
    """Compile an insertTableRow request."""
    tsl = {"index": table_start_index}
    if tab_id:
        tsl["tabId"] = tab_id
    return {
        "insertTableRow": {
            "tableCellLocation": {
                "tableStartLocation": tsl,
                "rowIndex": row_index,
                "columnIndex": column_index,
            },
            "insertBelow": insert_below,
        }
    }


def compile_insert_table_column(
    table_start_index: int,
    row_index: int = 0,
    column_index: int = 0,
    insert_right: bool = True,
    tab_id: str | None = None,
) -> dict:
    """Compile an insertTableColumn request."""
    tsl = {"index": table_start_index}
    if tab_id:
        tsl["tabId"] = tab_id
    return {
        "insertTableColumn": {
            "tableCellLocation": {
                "tableStartLocation": tsl,
                "rowIndex": row_index,
                "columnIndex": column_index,
            },
            "insertRight": insert_right,
        }
    }


def compile_delete_table_row(
    table_start_index: int,
    row_index: int,
    column_index: int = 0,
    tab_id: str | None = None,
) -> dict:
    """Compile a deleteTableRow request."""
    tsl = {"index": table_start_index}
    if tab_id:
        tsl["tabId"] = tab_id
    return {
        "deleteTableRow": {
            "tableCellLocation": {
                "tableStartLocation": tsl,
                "rowIndex": row_index,
                "columnIndex": column_index,
            }
        }
    }


def compile_delete_table_column(
    table_start_index: int,
    row_index: int = 0,
    column_index: int = 0,
    tab_id: str | None = None,
) -> dict:
    """Compile a deleteTableColumn request."""
    tsl = {"index": table_start_index}
    if tab_id:
        tsl["tabId"] = tab_id
    return {
        "deleteTableColumn": {
            "tableCellLocation": {
                "tableStartLocation": tsl,
                "rowIndex": row_index,
                "columnIndex": column_index,
            }
        }
    }


def compile_insert_bullet_list(
    index: int,
    items: list[str],
    bullet_preset: str = "BULLET_DISC_CIRCLE_SQUARE",
    tab_id: str | None = None,
) -> list[dict]:
    """Compile a bullet/numbered list insertion (insert text + create bullets).

    Returns two requests in a single-batch array.
    """
    text = "\n".join(items) + "\n"
    text_len = utf16_length(text)

    loc = {"index": index}
    rng = {"startIndex": index, "endIndex": index + text_len}
    if tab_id:
        loc["tabId"] = tab_id
        rng["tabId"] = tab_id

    return [
        {"insertText": {"location": loc, "text": text}},
        {"createParagraphBullets": {"range": rng, "bulletPreset": bullet_preset}},
    ]


def compile_insert_page_break(index: int, tab_id: str | None = None) -> dict:
    """Compile an insertPageBreak request."""
    loc = {"index": index}
    if tab_id:
        loc["tabId"] = tab_id
    return {"insertPageBreak": {"location": loc}}
