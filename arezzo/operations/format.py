"""Format operation compilers — text style, paragraph style, bullets.

All format operations are index-neutral: they don't shift any indices.
They are emitted in Phase 2 of the two-phase compilation, after all
content mutations.
"""

from __future__ import annotations


def compile_update_text_style(
    start: int,
    end: int,
    text_style: dict,
    fields: str,
    tab_id: str | None = None,
) -> dict:
    """Compile an updateTextStyle request.

    The `fields` parameter is a field mask — only specified fields are
    modified. Omitting it clears all unmentioned style properties.
    """
    rng = {"startIndex": start, "endIndex": end}
    if tab_id:
        rng["tabId"] = tab_id
    return {
        "updateTextStyle": {
            "range": rng,
            "textStyle": text_style,
            "fields": fields,
        }
    }


def compile_update_paragraph_style(
    start: int,
    end: int,
    paragraph_style: dict,
    fields: str,
    tab_id: str | None = None,
) -> dict:
    """Compile an updateParagraphStyle request."""
    rng = {"startIndex": start, "endIndex": end}
    if tab_id:
        rng["tabId"] = tab_id
    return {
        "updateParagraphStyle": {
            "range": rng,
            "paragraphStyle": paragraph_style,
            "fields": fields,
        }
    }


def compile_create_paragraph_bullets(
    start: int,
    end: int,
    bullet_preset: str = "BULLET_DISC_CIRCLE_SQUARE",
    tab_id: str | None = None,
) -> dict:
    """Compile a createParagraphBullets request."""
    rng = {"startIndex": start, "endIndex": end}
    if tab_id:
        rng["tabId"] = tab_id
    return {
        "createParagraphBullets": {
            "range": rng,
            "bulletPreset": bullet_preset,
        }
    }
