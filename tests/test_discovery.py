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
         "prerequisites": [{"type": "alternative", "courses": ["CS-X 100"]}],
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


def test_similarity_excludes_self_and_missing_descriptions(catalog):
    result = decode(d.find_similar_courses("CS-X 100"))
    assert result["courses"][0]["code"] == "CS-X 200"
    assert 0 < result["courses"][0]["similarity"] <= 1
    assert decode(d.find_similar_courses("ART 100"))["courses"] == []


@pytest.mark.parametrize("completed,met", [(["A 1", "C 3"], False),
    (["A 1", "B 2"], False), (["a 1", "B\u00a02", "D 4"], True)])
def test_check_prerequisites_requires_all_groups(catalog, completed, met):
    catalog.return_value = [{"code": "TARGET 1", "prerequisites": [
        {"type": "required", "courses": ["A 1", "B 2"]},
        {"type": "alternative", "courses": ["C 3", "D 4"]}],
        "metadata": {"description": "Prerequisite: WRONG 9", "prerequisites": "WRONG 9"}}]
    result = decode(d.check_prerequisites("TARGET 1", completed))
    catalog.assert_called_once_with(include_prerequisites=True)
    assert result["course_requirements_met"] is met
    assert result["referenced_codes"] == ["A 1", "B 2", "C 3", "D 4"]
    if met:
        assert result["groups"][1]["remaining_options"] == []
        assert len(result["not_completed_references"]) == 1


@pytest.mark.parametrize("prerequisites,met", [(None, None), ([], True),
    ([{"type": "other", "courses": ["A 1"]}], None)])
def test_check_prerequisites_missing_empty_and_unknown(catalog, prerequisites, met):
    catalog.return_value = [{"code": "A 1", "prerequisites": prerequisites}]
    result = decode(d.check_prerequisites("A 1", []))
    assert result["course_requirements_met"] is met
    assert result["status"] == "unverified"


def test_unlocks_use_prerequisite_column_not_description(catalog):
    groups = [{"type": "required", "courses": ["OTHER 1"]},
              {"type": "alternative", "courses": [" psych-ua\u00a01 ", "APSY-UE 2"]}]
    catalog.return_value = [
        {"code": "PSYCH-UA 1"},
        {"code": "PSYCH-UA 29", "prerequisites": groups},
        {"code": "PSYCH-UA 32", "prerequisites": {"courses": ["PSYCH-UA 1"]}},
        {"code": "PSYCH-UA 99", "prerequisites": [{"courses": ["PSYCH-UA 10"]}]},
        {"code": "PSYCH-UA 98", "metadata": {"description": "Prerequisite: PSYCH-UA 1"}},
    ]
    result = decode(d.courses_unlocked_by("psych-ua 1", limit=1))
    catalog.assert_called_once_with(include_prerequisites=True)
    assert result["total_candidates"] == 2
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["code"] == "PSYCH-UA 29"
    assert result["candidates"][0]["prerequisite_fields"]["prerequisites"] == groups
    assert result["candidates"][0]["status"] == "unverified"


@pytest.mark.parametrize("prerequisites", [None, [], [{"courses": "PSYCH-UA 1"}]])
def test_unlocks_skip_missing_or_malformed_prerequisites(catalog, prerequisites):
    catalog.return_value = [{"code": "PSYCH-UA 1"},
                            {"code": "PSYCH-UA 29", "prerequisites": prerequisites}]
    assert decode(d.courses_unlocked_by("PSYCH-UA 1"))["total_candidates"] == 0


@pytest.mark.parametrize("call", [
    lambda: d.courses_unlocked_by(" "), lambda: d.courses_unlocked_by("X", limit=0),
    lambda: d.check_prerequisites("X", [""]),
])
def test_invalid_inputs_do_not_query(catalog, call):
    with pytest.raises(ValueError):
        call()
    catalog.assert_not_called()


def test_unknown_course_is_explicit(catalog):
    with pytest.raises(ValueError, match="found 0"):
        d.check_prerequisites("UNKNOWN", [])


@pytest.mark.parametrize("include_prerequisites", [False, True])
def test_catalog_continues_through_server_capped_pages(include_prerequisites):
    query = MagicMock()
    for method in ("select", "eq", "order", "range"):
        getattr(query, method).return_value = query
    query.execute.side_effect = [SimpleNamespace(data=[{"code": "A"}]),
                                 SimpleNamespace(data=[{"code": "B"}]), SimpleNamespace(data=[])]
    with patch.object(d, "get_supabase") as client:
        client.return_value.table.return_value = query
        assert d._catalog(program="CS", include_prerequisites=include_prerequisites) == [{"code": "A"}, {"code": "B"}]
    columns = "code,program,program_name,school,metadata"
    query.select.assert_called_with(columns + (",prerequisites" if include_prerequisites else ""))
    assert [call.args for call in query.range.call_args_list] == [(0, 999), (1, 1000), (2, 1001)]
