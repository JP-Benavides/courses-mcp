from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from toon_format import decode

from src.tools import discovery as d


@pytest.fixture
def catalog():
    rows = [
        {"code": "CS-X 100", "program": "CS", "program_name": "Computing", "school": "A",
         "metadata": {"description": "Python programming and algorithms", "credits": 4}},
        {"code": "CS-X 200", "program": "CS", "program_name": "Computing", "school": "A",
         "metadata": {"description": "Python algorithms. Prerequisite: CS-X\u00a0100 or placement test.",
                      "courseUrl": "https://example.com/catalog"}},
        {"code": "ART 100", "program": "ART", "program_name": "Art", "school": "B",
         "metadata": None},
        {"code": "CS-X 1000", "program": "CS", "program_name": "Computing", "school": "A",
         "metadata": {"description": "Prerequisite: CS-X 200"}},
    ]
    with patch.object(d, "_catalog", return_value=rows) as mock:
        yield mock


def test_search_filters_ranking_and_limit(catalog):
    result = decode(d.search_courses("PYTHON algorithms", program=" CS ", limit=1))
    assert result["total_matches"] == 2
    assert len(result["courses"]) == 1
    catalog.assert_called_once_with(program="CS")
    assert decode(d.search_courses("does not exist"))["courses"] == []


def test_overview_pagination(catalog):
    result = decode(d.program_overview("CS", limit=2))
    assert result["course_count"] == 4
    assert result["next_offset"] == 2
    assert decode(d.program_overview("CS", offset=4))["next_offset"] is None


def test_comparison_nulls_and_unmatched(catalog):
    result = decode(d.compare_courses([" cs-x 100 ", "CS-X 200", "UNKNOWN"]))
    assert result["unmatched_codes"] == ["UNKNOWN"]
    assert result["courses"][1]["metadata"]["credits"] is None


def test_similarity_excludes_self_and_missing_descriptions(catalog):
    result = decode(d.find_similar_courses("CS-X 100"))
    assert result["courses"][0]["code"] == "CS-X 200"
    assert 0 < result["courses"][0]["similarity"] <= 1
    assert decode(d.find_similar_courses("ART 100"))["courses"] == []


def test_prerequisites_preserve_alternatives_and_uncertainty(catalog):
    result = decode(d.check_prerequisites("CS-X 200", ["cs-x 100"]))
    assert result["completed_references"] == ["CS-X 100"]
    assert result["not_completed_references"] == []
    assert result["status"] == "unverified"
    assert "or placement test" in result["description"]
    assert decode(d.check_prerequisites("ART 100", []))["status"] == "unverified"


def test_reverse_references_do_not_match_code_prefixes(catalog):
    result = decode(d.courses_unlocked_by("CS-X 100"))
    assert [r["code"] for r in result["candidates"]] == ["CS-X 200"]
    assert decode(d.courses_unlocked_by("CS-X 1000"))["total_candidates"] == 0


@pytest.mark.parametrize("call", [
    lambda: d.search_courses(" "), lambda: d.search_courses("x", limit=0),
    lambda: d.search_courses("x", school=" "), lambda: d.program_overview("CS", offset=-1),
    lambda: d.compare_courses([]), lambda: d.compare_courses([" "]),
    lambda: d.find_similar_courses("X", limit=101),
    lambda: d.check_prerequisites("X", [""]), lambda: d.courses_unlocked_by(" "),
])
def test_invalid_inputs_do_not_query(catalog, call):
    with pytest.raises(ValueError):
        call()
    catalog.assert_not_called()


def test_unknown_course_is_explicit(catalog):
    with pytest.raises(ValueError, match="found 0"):
        d.check_prerequisites("UNKNOWN", [])


def test_catalog_continues_through_server_capped_pages():
    query = MagicMock()
    for method in ("select", "eq", "order", "range"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [SimpleNamespace(data=[{"code": "A"}]),
                                 SimpleNamespace(data=[{"code": "B"}]), SimpleNamespace(data=[])]
    with patch.object(d, "get_supabase") as client:
        client.return_value.table.return_value = query
        assert d._catalog(program="CS") == [{"code": "A"}, {"code": "B"}]
    assert [call.args for call in query.range.call_args_list] == [(0, 999), (1, 1000), (2, 1001)]
