"""End-to-end compiler integration tests.

Tests compile_operations against Phase 1 fixtures and mutation pairs.
Validates the full pipeline: parse → resolve → compile → emit.
"""

import json
from pathlib import Path

import pytest

from arezzo.compiler import compile_operations
from arezzo.errors import ArezzoAddressError, ArezzoOperationError

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
MUTATIONS_DIR = FIXTURES_DIR / "mutations"


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())


def _load_mutation_before(name: str) -> dict:
    return json.loads((MUTATIONS_DIR / name / "before.json").read_text())


class TestCompilerBasics:
    def test_returns_requests_and_write_control(self):
        doc = _load("01_plain_text")
        result = compile_operations(doc, [
            {"type": "insert_text", "address": {"start": True}, "params": {"text": "Hello\n"}}
        ])
        assert "requests" in result
        assert "writeControl" in result
        assert len(result["requests"]) == 1

    def test_target_revision_default(self):
        doc = _load("01_plain_text")
        result = compile_operations(doc, [
            {"type": "insert_text", "address": {"start": True}, "params": {"text": "Hello\n"}}
        ])
        assert "targetRevisionId" in result["writeControl"]

    def test_required_revision(self):
        doc = _load("01_plain_text")
        result = compile_operations(doc, [
            {"type": "insert_text", "address": {"start": True}, "params": {"text": "Hello\n"}}
        ], write_control="required")
        assert "requiredRevisionId" in result["writeControl"]

    def test_empty_operations(self):
        doc = _load("01_plain_text")
        result = compile_operations(doc, [])
        assert result["requests"] == []

    def test_unknown_type_errors(self):
        doc = _load("01_plain_text")
        with pytest.raises(ArezzoOperationError, match="Unknown operation type"):
            compile_operations(doc, [{"type": "nonexistent_op"}])

    def test_missing_type_errors(self):
        doc = _load("01_plain_text")
        with pytest.raises(ArezzoOperationError, match="missing 'type'"):
            compile_operations(doc, [{"address": {"start": True}}])


class TestTwoPhaseOrdering:
    """Content operations come before format operations in output."""

    def test_format_after_content(self):
        doc = _load("02_heading_hierarchy")
        result = compile_operations(doc, [
            {"type": "update_text_style", "address": {"index": 1},
             "params": {"text_style": {"bold": True}, "fields": "bold", "length": 14}},
            {"type": "insert_text", "address": {"start": True},
             "params": {"text": "Prefix\n"}},
        ])
        reqs = result["requests"]
        assert len(reqs) == 2
        # Content (insert) should come first, format (style) second
        assert "insertText" in reqs[0]
        assert "updateTextStyle" in reqs[1]

    def test_multiple_content_ops_reverse_sorted(self):
        doc = _load("01_plain_text")
        result = compile_operations(doc, [
            {"type": "insert_text", "address": {"index": 1}, "params": {"text": "A\n"}},
            {"type": "insert_text", "address": {"index": 300}, "params": {"text": "B\n"}},
            {"type": "insert_text", "address": {"index": 100}, "params": {"text": "C\n"}},
        ])
        reqs = result["requests"]
        indices = [r["insertText"]["location"]["index"] for r in reqs]
        assert indices == [300, 100, 1]  # reverse order


class TestTabIdEmission:
    """All Location and Range objects include tabId."""

    def test_insert_text_has_tab_id(self):
        doc = _load("01_plain_text")
        result = compile_operations(doc, [
            {"type": "insert_text", "address": {"start": True}, "params": {"text": "X\n"}}
        ])
        loc = result["requests"][0]["insertText"]["location"]
        assert loc.get("tabId") == "t.0"

    def test_format_has_tab_id(self):
        doc = _load("02_heading_hierarchy")
        result = compile_operations(doc, [
            {"type": "update_text_style", "address": {"index": 1},
             "params": {"text_style": {"bold": True}, "fields": "bold", "length": 14}}
        ])
        rng = result["requests"][0]["updateTextStyle"]["range"]
        assert rng.get("tabId") == "t.0"


class TestEndToEndMutationValidation:
    """Validate compiler output against actual Phase 1 mutation pairs."""

    def test_t1_insert_at_start(self):
        before = _load_mutation_before("T1_insert_text_start")
        result = compile_operations(before, [
            {"type": "insert_text", "address": {"start": True},
             "params": {"text": "INSERTED AT START.\n"}}
        ])
        reqs = result["requests"]
        assert len(reqs) == 1
        assert reqs[0]["insertText"]["location"]["index"] == 1
        assert reqs[0]["insertText"]["text"] == "INSERTED AT START.\n"

    def test_t3_insert_after_heading(self):
        before = _load_mutation_before("T3_insert_after_heading")
        result = compile_operations(before, [
            {"type": "insert_text",
             "address": {"heading": "Revenue Analysis"},
             "params": {"text": "Inserted after Revenue Analysis heading.\n"}}
        ])
        reqs = result["requests"]
        assert len(reqs) == 1
        assert "insertText" in reqs[0]
        # Should resolve to after the heading paragraph
        assert reqs[0]["insertText"]["location"]["index"] > 0

    def test_t7_replace_all(self):
        before = _load_mutation_before("T7_replace_all_text")
        result = compile_operations(before, [
            {"type": "replace_all_text",
             "params": {"find_text": "revenue", "replace_text": "REVENUE", "match_case": False}}
        ])
        reqs = result["requests"]
        assert len(reqs) == 1
        assert reqs[0]["replaceAllText"]["containsText"]["text"] == "revenue"

    def test_f1_apply_bold(self):
        before = _load_mutation_before("F1_apply_bold")
        # Find "15%" in the document and bold it
        mutation = json.loads((MUTATIONS_DIR / "F1_apply_bold" / "request.json").read_text())
        rng = mutation[0]["updateTextStyle"]["range"]

        result = compile_operations(before, [
            {"type": "update_text_style",
             "address": {"index": rng["startIndex"]},
             "params": {
                 "text_style": {"bold": True},
                 "fields": "bold",
                 "length": rng["endIndex"] - rng["startIndex"],
             }}
        ])
        reqs = result["requests"]
        assert len(reqs) == 1
        assert reqs[0]["updateTextStyle"]["textStyle"]["bold"] is True

    def test_s1_insert_table(self):
        before = _load_mutation_before("S1_insert_table")
        mutation = json.loads((MUTATIONS_DIR / "S1_insert_table" / "request.json").read_text())
        idx = mutation[0]["insertTable"]["location"]["index"]

        result = compile_operations(before, [
            {"type": "insert_table",
             "address": {"index": idx},
             "params": {"rows": 2, "columns": 3}}
        ])
        reqs = result["requests"]
        assert len(reqs) == 1
        assert reqs[0]["insertTable"]["rows"] == 2

    def test_n1_create_named_range(self):
        before = _load_mutation_before("N1_create_named_range")
        result = compile_operations(before, [
            {"type": "create_named_range",
             "address": {"heading": "Executive Summary"},
             "params": {"name": "exec_summary"}}
        ])
        reqs = result["requests"]
        assert len(reqs) == 1
        assert reqs[0]["createNamedRange"]["name"] == "exec_summary"

    def test_mixed_content_and_format(self):
        """Multiple operations of different phases."""
        before = _load_mutation_before("T1_insert_text_start")
        result = compile_operations(before, [
            {"type": "insert_text", "address": {"start": True},
             "params": {"text": "Title\n"}},
            {"type": "update_paragraph_style", "address": {"index": 1},
             "params": {"paragraph_style": {"namedStyleType": "HEADING_1"},
                        "fields": "namedStyleType", "length": 6}},
        ])
        reqs = result["requests"]
        assert len(reqs) == 2
        # Content first
        assert "insertText" in reqs[0]
        # Format second
        assert "updateParagraphStyle" in reqs[1]


class TestCorruptionDetection:
    """The compiler's core value: turn silent corruption into loud errors."""

    def test_heading_not_found_errors(self):
        doc = _load("01_plain_text")
        with pytest.raises(ArezzoAddressError, match="not found"):
            compile_operations(doc, [
                {"type": "insert_text",
                 "address": {"heading": "Nonexistent"},
                 "params": {"text": "Bad\n"}}
            ])

    def test_index_past_end_errors(self):
        doc = _load("01_plain_text")
        with pytest.raises(ArezzoAddressError, match="past document end"):
            compile_operations(doc, [
                {"type": "insert_text",
                 "address": {"index": 99999},
                 "params": {"text": "Bad\n"}}
            ])

    def test_negative_index_errors(self):
        doc = _load("01_plain_text")
        with pytest.raises(ArezzoAddressError, match="Negative"):
            compile_operations(doc, [
                {"type": "insert_text",
                 "address": {"index": -5},
                 "params": {"text": "Bad\n"}}
            ])
