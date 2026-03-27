"""Tests for MCP server tool functions.

Tests the behavioral response layer and compilation pipeline without
hitting the Google Docs API — uses Phase 1 fixtures as mock responses.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arezzo.server import (
    _build_read_response,
    _build_structural_map,
    _build_edit_response,
    _build_validate_response,
)
from arezzo.compiler import compile_operations
from arezzo.parser import parse_document

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())


class TestStructuralMap:
    def test_plain_text_no_headings(self):
        doc = _load("01_plain_text")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        assert smap["headings"] == []
        assert smap["title"] == "arezzo_fixture_01_plain_text"
        assert smap["body_end_index"] == 520

    def test_heading_hierarchy(self):
        doc = _load("02_heading_hierarchy")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        assert len(smap["headings"]) == 5
        # Verify sorted by start_index
        indices = [h["start_index"] for h in smap["headings"]]
        assert indices == sorted(indices)
        # Verify levels
        levels = {h["text"]: h["level"] for h in smap["headings"]}
        assert levels["Document Title"] == 1
        assert levels["Section One"] == 2
        assert levels["Subsection A"] == 3

    def test_named_ranges(self):
        doc = _load("08_named_ranges")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        assert len(smap["named_ranges"]) == 2
        names = {nr["name"] for nr in smap["named_ranges"]}
        assert "introduction_section" in names
        assert "conclusion_section" in names

    def test_tables(self):
        doc = _load("05_tables")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        assert len(smap["tables"]) == 2
        assert smap["tables"][0]["rows"] == 3
        assert smap["tables"][0]["columns"] == 3

    def test_headers_footers(self):
        doc = _load("07_headers_footers_footnotes")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        assert smap["has_header"] is True
        assert smap["has_footer"] is True
        assert smap["footnote_count"] == 1

    def test_lists(self):
        doc = _load("04_lists")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        assert smap["list_count"] == 3

    def test_images(self):
        doc = _load("06_images")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        assert smap["inline_object_count"] == 1

    def test_kitchen_sink(self):
        doc = _load("11_kitchen_sink")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        assert len(smap["headings"]) > 0
        assert smap["footnote_count"] >= 1


class TestReadResponse:
    def test_next_step_with_headings(self):
        doc = _load("02_heading_hierarchy")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        response = _build_read_response(parsed, smap)
        assert "next_step" in response
        assert "edit_document" in response["next_step"]
        assert "5 headings" in response["next_step"]

    def test_next_step_with_named_ranges(self):
        doc = _load("08_named_ranges")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        response = _build_read_response(parsed, smap)
        assert "named ranges" in response["next_step"]

    def test_document_reality_present(self):
        doc = _load("02_heading_hierarchy")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        response = _build_read_response(parsed, smap)
        assert "document_reality" in response
        assert response["document_reality"]["headings"] == smap["headings"]

    def test_no_headings_response(self):
        doc = _load("01_plain_text")
        parsed = parse_document(doc)
        smap = _build_structural_map(parsed)
        response = _build_read_response(parsed, smap)
        # Still has next_step, just without heading count
        assert "next_step" in response
        assert "edit_document" in response["next_step"]


class TestEditResponse:
    def test_basic_success(self):
        ops = [{"type": "insert_text", "address": {"start": True}, "params": {"text": "Hi\n"}}]
        compiled = {"requests": [{"insertText": {"location": {"index": 1}, "text": "Hi\n"}}]}
        response = _build_edit_response("doc123", ops, compiled, None)
        assert "next_step" in response
        assert "Document updated" in response["next_step"]
        assert response["operations_compiled"] == 1
        assert response["requests_emitted"] == 1

    def test_compound_op_warning(self):
        ops = [{"type": "insert_table", "address": {"index": 10}, "params": {"rows": 3, "columns": 3}}]
        compiled = {"requests": [{"insertTable": {}}]}
        response = _build_edit_response("doc123", ops, compiled, None)
        assert "present_to_user" in response
        assert "Structural elements" in response["present_to_user"]
        assert "read_document" in response["next_step"]

    def test_no_warning_for_text_ops(self):
        ops = [{"type": "insert_text", "address": {"start": True}, "params": {"text": "Hi\n"}}]
        compiled = {"requests": [{"insertText": {}}]}
        response = _build_edit_response("doc123", ops, compiled, None)
        assert "present_to_user" not in response


class TestValidateResponse:
    def test_basic(self):
        compiled = {
            "requests": [
                {"insertText": {"location": {"index": 1}, "text": "Hi\n"}},
                {"updateTextStyle": {"range": {"startIndex": 1, "endIndex": 3}, "textStyle": {"bold": True}, "fields": "bold"}},
            ],
            "writeControl": {"targetRevisionId": "abc"},
        }
        ops = [{"type": "insert_text"}, {"type": "update_text_style"}]
        response = _build_validate_response(compiled, ops)
        assert response["validation"] == "passed"
        assert response["content_mutations"] == 1
        assert response["format_mutations"] == 1
        assert response["requests_emitted"] == 2
        assert "edit_document" in response["next_step"]

    def test_compiled_requests_included(self):
        compiled = {"requests": [], "writeControl": {}}
        response = _build_validate_response(compiled, [])
        assert "compiled_requests" in response


class TestEndToEndCompileAndResponse:
    """Integration: compile real fixture + build response."""

    def test_compile_and_edit_response(self):
        doc = _load("02_heading_hierarchy")
        ops = [
            {"type": "insert_text", "address": {"heading": "Section One"},
             "params": {"text": "New paragraph.\n"}},
        ]
        compiled = compile_operations(doc, ops)
        response = _build_edit_response("fake_id", ops, compiled, doc)
        assert response["operations_compiled"] == 1
        assert response["requests_emitted"] == 1
        assert "Document updated" in response["next_step"]

    def test_compile_and_validate_response(self):
        doc = _load("02_heading_hierarchy")
        ops = [
            {"type": "insert_text", "address": {"heading": "Section One"},
             "params": {"text": "New paragraph.\n"}},
            {"type": "update_text_style", "address": {"index": 1},
             "params": {"text_style": {"bold": True}, "fields": "bold", "length": 14}},
        ]
        compiled = compile_operations(doc, ops)
        response = _build_validate_response(compiled, ops)
        assert response["validation"] == "passed"
        assert response["content_mutations"] == 1
        assert response["format_mutations"] == 1
