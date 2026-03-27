"""Tests for structure operations against Phase 1 mutation pairs."""

from arezzo.operations.structure import (
    compile_delete_table_column,
    compile_delete_table_row,
    compile_insert_bullet_list,
    compile_insert_page_break,
    compile_insert_table,
    compile_insert_table_column,
    compile_insert_table_row,
)
from arezzo.tests.conftest import load_mutation


class TestInsertTable:
    def test_basic(self):
        req = compile_insert_table(100, 3, 3)
        assert req["insertTable"]["rows"] == 3
        assert req["insertTable"]["columns"] == 3
        assert req["insertTable"]["location"]["index"] == 100

    def test_with_tab_id(self):
        req = compile_insert_table(100, 2, 2, tab_id="t.0")
        assert req["insertTable"]["location"]["tabId"] == "t.0"

    def test_matches_s1_mutation(self):
        mutation = load_mutation("S1_insert_table")
        expected = mutation["request"][0]
        idx = expected["insertTable"]["location"]["index"]
        rows = expected["insertTable"]["rows"]
        cols = expected["insertTable"]["columns"]

        compiled = compile_insert_table(idx, rows, cols)
        assert compiled == expected


class TestInsertTableRow:
    def test_basic(self):
        req = compile_insert_table_row(19, 1)
        assert req["insertTableRow"]["tableCellLocation"]["tableStartLocation"]["index"] == 19
        assert req["insertTableRow"]["tableCellLocation"]["rowIndex"] == 1
        assert req["insertTableRow"]["insertBelow"] is True

    def test_matches_s2_mutation(self):
        mutation = load_mutation("S2_add_table_row")
        expected = mutation["request"][0]
        tcl = expected["insertTableRow"]["tableCellLocation"]
        tsl = tcl["tableStartLocation"]

        compiled = compile_insert_table_row(
            tsl["index"],
            tcl["rowIndex"],
            tcl["columnIndex"],
            expected["insertTableRow"]["insertBelow"],
        )
        assert compiled == expected


class TestInsertTableColumn:
    def test_basic(self):
        req = compile_insert_table_column(19, 0, 2)
        assert req["insertTableColumn"]["tableCellLocation"]["columnIndex"] == 2
        assert req["insertTableColumn"]["insertRight"] is True


class TestDeleteTableRow:
    def test_basic(self):
        req = compile_delete_table_row(19, 1)
        assert req["deleteTableRow"]["tableCellLocation"]["rowIndex"] == 1


class TestDeleteTableColumn:
    def test_basic(self):
        req = compile_delete_table_column(19, 0, 2)
        assert req["deleteTableColumn"]["tableCellLocation"]["columnIndex"] == 2


class TestInsertBulletList:
    def test_produces_two_requests(self):
        reqs = compile_insert_bullet_list(100, ["Item one", "Item two", "Item three"])
        assert len(reqs) == 2
        assert "insertText" in reqs[0]
        assert "createParagraphBullets" in reqs[1]

    def test_text_content(self):
        reqs = compile_insert_bullet_list(100, ["A", "B", "C"])
        assert reqs[0]["insertText"]["text"] == "A\nB\nC\n"

    def test_range_covers_inserted_text(self):
        items = ["Item one", "Item two"]
        reqs = compile_insert_bullet_list(100, items)
        text = "Item one\nItem two\n"
        rng = reqs[1]["createParagraphBullets"]["range"]
        assert rng["startIndex"] == 100
        assert rng["endIndex"] == 100 + len(text)

    def test_numbered_preset(self):
        reqs = compile_insert_bullet_list(
            100, ["A", "B"], bullet_preset="NUMBERED_DECIMAL_ALPHA_ROMAN"
        )
        assert reqs[1]["createParagraphBullets"]["bulletPreset"] == "NUMBERED_DECIMAL_ALPHA_ROMAN"

    def test_matches_s5_mutation(self):
        mutation = load_mutation("S5_insert_bullet_list")
        expected = mutation["request"]
        assert len(expected) == 2

        # Extract what was inserted
        insert_text = expected[0]["insertText"]["text"]
        insert_idx = expected[0]["insertText"]["location"]["index"]
        items = insert_text.rstrip("\n").split("\n")

        compiled = compile_insert_bullet_list(insert_idx, items)
        assert compiled[0]["insertText"]["text"] == expected[0]["insertText"]["text"]
        assert compiled[0]["insertText"]["location"]["index"] == expected[0]["insertText"]["location"]["index"]

    def test_matches_s6_mutation(self):
        mutation = load_mutation("S6_insert_numbered_list")
        expected = mutation["request"]
        insert_text = expected[0]["insertText"]["text"]
        insert_idx = expected[0]["insertText"]["location"]["index"]
        items = insert_text.rstrip("\n").split("\n")
        preset = expected[1]["createParagraphBullets"]["bulletPreset"]

        compiled = compile_insert_bullet_list(insert_idx, items, bullet_preset=preset)
        assert compiled[0]["insertText"]["text"] == expected[0]["insertText"]["text"]


class TestInsertPageBreak:
    def test_basic(self):
        req = compile_insert_page_break(100)
        assert req["insertPageBreak"]["location"]["index"] == 100

    def test_matches_s8_mutation(self):
        mutation = load_mutation("S8_insert_page_break")
        expected = mutation["request"][0]
        idx = expected["insertPageBreak"]["location"]["index"]

        compiled = compile_insert_page_break(idx)
        assert compiled == expected
