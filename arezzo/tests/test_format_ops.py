"""Tests for format operations against Phase 1 mutation pairs."""

from arezzo.operations.format import (
    compile_create_paragraph_bullets,
    compile_update_paragraph_style,
    compile_update_text_style,
)
from arezzo.tests.conftest import load_mutation


class TestUpdateTextStyle:
    def test_bold(self):
        req = compile_update_text_style(20, 29, {"bold": True}, "bold")
        assert req["updateTextStyle"]["textStyle"]["bold"] is True
        assert req["updateTextStyle"]["fields"] == "bold"

    def test_with_tab_id(self):
        req = compile_update_text_style(20, 29, {"bold": True}, "bold", tab_id="t.0")
        assert req["updateTextStyle"]["range"]["tabId"] == "t.0"

    def test_matches_f1_mutation(self):
        """Validate against F1 mutation pair (apply bold)."""
        mutation = load_mutation("F1_apply_bold")
        expected = mutation["request"][0]
        rng = expected["updateTextStyle"]["range"]
        style = expected["updateTextStyle"]["textStyle"]
        fields = expected["updateTextStyle"]["fields"]

        compiled = compile_update_text_style(rng["startIndex"], rng["endIndex"], style, fields)
        assert compiled == expected

    def test_matches_f4_mutation(self):
        """Validate against F4 mutation pair (change font)."""
        mutation = load_mutation("F4_change_font")
        expected = mutation["request"][0]
        rng = expected["updateTextStyle"]["range"]
        style = expected["updateTextStyle"]["textStyle"]
        fields = expected["updateTextStyle"]["fields"]

        compiled = compile_update_text_style(rng["startIndex"], rng["endIndex"], style, fields)
        assert compiled == expected

    def test_matches_f5_mutation(self):
        """Validate against F5 mutation pair (add hyperlink)."""
        mutation = load_mutation("F5_add_hyperlink")
        expected = mutation["request"][0]
        rng = expected["updateTextStyle"]["range"]
        style = expected["updateTextStyle"]["textStyle"]
        fields = expected["updateTextStyle"]["fields"]

        compiled = compile_update_text_style(rng["startIndex"], rng["endIndex"], style, fields)
        assert compiled == expected


class TestUpdateParagraphStyle:
    def test_heading_change(self):
        req = compile_update_paragraph_style(
            68, 80, {"namedStyleType": "HEADING_3"}, "namedStyleType"
        )
        assert req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_3"

    def test_matches_f2_mutation(self):
        """Validate against F2 mutation pair (change heading level)."""
        mutation = load_mutation("F2_change_heading_level")
        expected = mutation["request"][0]
        rng = expected["updateParagraphStyle"]["range"]
        style = expected["updateParagraphStyle"]["paragraphStyle"]
        fields = expected["updateParagraphStyle"]["fields"]

        compiled = compile_update_paragraph_style(
            rng["startIndex"], rng["endIndex"], style, fields
        )
        assert compiled == expected


class TestCreateParagraphBullets:
    def test_bullet_preset(self):
        req = compile_create_paragraph_bullets(10, 50)
        assert req["createParagraphBullets"]["bulletPreset"] == "BULLET_DISC_CIRCLE_SQUARE"

    def test_numbered_preset(self):
        req = compile_create_paragraph_bullets(10, 50, "NUMBERED_DECIMAL_ALPHA_ROMAN")
        assert req["createParagraphBullets"]["bulletPreset"] == "NUMBERED_DECIMAL_ALPHA_ROMAN"

    def test_with_tab_id(self):
        req = compile_create_paragraph_bullets(10, 50, tab_id="t.0")
        assert req["createParagraphBullets"]["range"]["tabId"] == "t.0"
