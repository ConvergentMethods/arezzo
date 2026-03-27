"""Tests for text operations against Phase 1 mutation pairs."""

import json
from pathlib import Path

import pytest

from arezzo.operations.text import (
    compile_delete_content_range,
    compile_insert_text,
    compile_replace_all_text,
    compile_replace_section,
)
from arezzo.tests.conftest import load_mutation


class TestInsertText:
    def test_basic_insert(self):
        req = compile_insert_text(1, "Hello\n")
        assert req == {"insertText": {"location": {"index": 1}, "text": "Hello\n"}}

    def test_insert_with_tab_id(self):
        req = compile_insert_text(1, "Hello\n", tab_id="t.0")
        assert req["insertText"]["location"]["tabId"] == "t.0"

    def test_insert_no_tab_id(self):
        req = compile_insert_text(1, "Hello\n")
        assert "tabId" not in req["insertText"]["location"]

    def test_matches_t1_mutation(self):
        """Validate against T1 mutation pair (insert at start)."""
        mutation = load_mutation("T1_insert_text_start")
        expected_requests = mutation["request"]
        assert len(expected_requests) == 1
        expected = expected_requests[0]

        compiled = compile_insert_text(1, "INSERTED AT START.\n")
        assert compiled["insertText"]["location"]["index"] == expected["insertText"]["location"]["index"]
        assert compiled["insertText"]["text"] == expected["insertText"]["text"]

    def test_matches_t2_mutation(self):
        """Validate against T2 mutation pair (insert at end)."""
        mutation = load_mutation("T2_insert_text_end")
        expected = mutation["request"][0]
        idx = expected["insertText"]["location"]["index"]
        text = expected["insertText"]["text"]

        compiled = compile_insert_text(idx, text)
        assert compiled == expected

    def test_matches_t3_mutation(self):
        """Validate against T3 mutation pair (insert after heading)."""
        mutation = load_mutation("T3_insert_after_heading")
        expected = mutation["request"][0]
        idx = expected["insertText"]["location"]["index"]
        text = expected["insertText"]["text"]

        compiled = compile_insert_text(idx, text)
        assert compiled == expected

    def test_matches_t4_mutation(self):
        """Validate against T4 mutation pair (insert between paragraphs)."""
        mutation = load_mutation("T4_insert_between_paragraphs")
        expected = mutation["request"][0]
        idx = expected["insertText"]["location"]["index"]
        text = expected["insertText"]["text"]

        compiled = compile_insert_text(idx, text)
        assert compiled == expected


class TestDeleteContentRange:
    def test_basic_delete(self):
        req = compile_delete_content_range(10, 50)
        assert req == {"deleteContentRange": {"range": {"startIndex": 10, "endIndex": 50}}}

    def test_delete_with_tab_id(self):
        req = compile_delete_content_range(10, 50, tab_id="t.0")
        assert req["deleteContentRange"]["range"]["tabId"] == "t.0"

    def test_matches_t6_mutation(self):
        """Validate against T6 mutation pair (delete paragraph)."""
        mutation = load_mutation("T6_delete_paragraph")
        expected = mutation["request"][0]
        rng = expected["deleteContentRange"]["range"]

        compiled = compile_delete_content_range(rng["startIndex"], rng["endIndex"])
        assert compiled == expected


class TestReplaceAllText:
    def test_basic_replace(self):
        req = compile_replace_all_text("old", "new")
        assert req["replaceAllText"]["containsText"]["text"] == "old"
        assert req["replaceAllText"]["replaceText"] == "new"
        assert req["replaceAllText"]["containsText"]["matchCase"] is True

    def test_case_insensitive(self):
        req = compile_replace_all_text("old", "new", match_case=False)
        assert req["replaceAllText"]["containsText"]["matchCase"] is False

    def test_matches_t7_mutation(self):
        """Validate against T7 mutation pair (replace all text)."""
        mutation = load_mutation("T7_replace_all_text")
        expected = mutation["request"][0]

        compiled = compile_replace_all_text("revenue", "REVENUE", match_case=False)
        assert compiled == expected


class TestReplaceSection:
    def test_produces_two_requests(self):
        reqs = compile_replace_section(10, 50, "New content.\n")
        assert len(reqs) == 2
        assert "deleteContentRange" in reqs[0]
        assert "insertText" in reqs[1]

    def test_delete_then_insert_at_same_index(self):
        reqs = compile_replace_section(10, 50, "New content.\n")
        delete_start = reqs[0]["deleteContentRange"]["range"]["startIndex"]
        insert_idx = reqs[1]["insertText"]["location"]["index"]
        assert delete_start == insert_idx == 10

    def test_matches_t5_mutation(self):
        """Validate against T5 mutation pair (replace section)."""
        mutation = load_mutation("T5_replace_section")
        expected = mutation["request"]
        assert len(expected) == 2

        delete_range = expected[0]["deleteContentRange"]["range"]
        insert_text = expected[1]["insertText"]["text"]
        insert_idx = expected[1]["insertText"]["location"]["index"]

        compiled = compile_replace_section(
            delete_range["startIndex"],
            delete_range["endIndex"],
            insert_text,
        )
        assert compiled[0] == expected[0]
        assert compiled[1]["insertText"]["location"]["index"] == insert_idx
        assert compiled[1]["insertText"]["text"] == insert_text
