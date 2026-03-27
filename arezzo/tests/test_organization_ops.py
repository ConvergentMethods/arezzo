"""Tests for organization operations against Phase 1 mutation pairs."""

import pytest

from arezzo.operations.organization import (
    compile_create_named_range,
    compile_delete_named_range,
    compile_replace_named_range_content,
)
from arezzo.tests.conftest import load_mutation


class TestCreateNamedRange:
    def test_basic(self):
        req = compile_create_named_range("my_range", 10, 50)
        assert req["createNamedRange"]["name"] == "my_range"
        assert req["createNamedRange"]["range"]["startIndex"] == 10
        assert req["createNamedRange"]["range"]["endIndex"] == 50

    def test_matches_n1_mutation(self):
        mutation = load_mutation("N1_create_named_range")
        expected = mutation["request"][0]
        nr = expected["createNamedRange"]

        compiled = compile_create_named_range(
            nr["name"], nr["range"]["startIndex"], nr["range"]["endIndex"]
        )
        assert compiled == expected


class TestDeleteNamedRange:
    def test_by_id(self):
        req = compile_delete_named_range(named_range_id="kix.abc123")
        assert req["deleteNamedRange"]["namedRangeId"] == "kix.abc123"

    def test_by_name(self):
        req = compile_delete_named_range(name="my_range")
        assert req["deleteNamedRange"]["name"] == "my_range"

    def test_matches_n3_mutation(self):
        mutation = load_mutation("N3_delete_named_range")
        expected = mutation["request"][0]
        nr_id = expected["deleteNamedRange"]["namedRangeId"]

        compiled = compile_delete_named_range(named_range_id=nr_id)
        assert compiled == expected

    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="Must provide"):
            compile_delete_named_range()


class TestReplaceNamedRangeContent:
    def test_produces_two_requests(self):
        reqs = compile_replace_named_range_content(10, 50, "New content.\n")
        assert len(reqs) == 2
        assert "deleteContentRange" in reqs[0]
        assert "insertText" in reqs[1]

    def test_matches_n2_mutation(self):
        mutation = load_mutation("N2_replace_named_range_content")
        expected = mutation["request"]
        assert len(expected) == 2

        delete_range = expected[0]["deleteContentRange"]["range"]
        insert_text = expected[1]["insertText"]["text"]

        compiled = compile_replace_named_range_content(
            delete_range["startIndex"],
            delete_range["endIndex"],
            insert_text,
        )
        assert compiled[0] == expected[0]
        assert compiled[1]["insertText"]["text"] == insert_text
        assert compiled[1]["insertText"]["location"]["index"] == delete_range["startIndex"]
