"""Tests for object operations against Phase 1 mutation pairs."""

from arezzo.operations.objects import (
    compile_create_footer,
    compile_create_footnote,
    compile_create_header,
    compile_insert_inline_image,
)
from arezzo.tests.conftest import load_mutation


class TestInsertInlineImage:
    def test_basic(self):
        req = compile_insert_inline_image(100, "https://example.com/img.png", 200, 100)
        assert req["insertInlineImage"]["uri"] == "https://example.com/img.png"
        assert req["insertInlineImage"]["location"]["index"] == 100
        assert req["insertInlineImage"]["objectSize"]["width"]["magnitude"] == 200

    def test_matches_o1_mutation(self):
        mutation = load_mutation("O1_insert_image")
        expected = mutation["request"][0]
        img = expected["insertInlineImage"]

        compiled = compile_insert_inline_image(
            img["location"]["index"],
            img["uri"],
            img["objectSize"]["width"]["magnitude"],
            img["objectSize"]["height"]["magnitude"],
        )
        assert compiled == expected


class TestCreateHeaderFooter:
    def test_create_header(self):
        req = compile_create_header()
        assert req == {"createHeader": {"type": "DEFAULT"}}

    def test_create_footer(self):
        req = compile_create_footer()
        assert req == {"createFooter": {"type": "DEFAULT"}}

    def test_matches_o2_mutation(self):
        mutation = load_mutation("O2_create_header")
        expected = mutation["request"]
        assert len(expected) == 2

        compiled_header = compile_create_header()
        compiled_footer = compile_create_footer()
        assert compiled_header == expected[0]
        assert compiled_footer == expected[1]


class TestCreateFootnote:
    def test_basic(self):
        req = compile_create_footnote(100)
        assert req["createFootnote"]["location"]["index"] == 100

    def test_matches_o4_mutation(self):
        mutation = load_mutation("O4_insert_footnote")
        expected = mutation["request"][0]
        idx = expected["createFootnote"]["location"]["index"]

        compiled = compile_create_footnote(idx)
        assert compiled == expected
