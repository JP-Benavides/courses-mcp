import sys
import unittest
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from toon_format import decode
from tools.courses import course_codes, list_programs


class CourseCodesTests(unittest.TestCase):
    def make_query(self, client, pages):
        query = MagicMock()
        client.table.return_value = query
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.range.return_value = query
        query.execute.side_effect = [SimpleNamespace(data=page) for page in pages]
        return query

    @patch("tools.courses.supabase")
    def test_every_filter_combination(self, client):
        values = {
            "program": "CSCI-UA",
            "program_name": "Computer Science",
            "school": "College of Arts and Science",
        }
        for size in range(1, 4):
            for fields in combinations(values, size):
                with self.subTest(fields=fields):
                    query = self.make_query(client, [[{"code": "CSCI-UA 101"}], []])
                    filters = {field: values[field] for field in fields}
                    self.assertEqual(decode(course_codes(**filters)), {"course_codes": ["CSCI-UA 101"]})
                    query.select.assert_called_with("code")
                    # The same filters must be applied to every page.
                    self.assertEqual(query.eq.call_count, len(filters) * 2)
                    for field, value in filters.items():
                        query.eq.assert_any_call(field, value)

    @patch("tools.courses.supabase")
    def test_pagination_deduplication_and_string_output(self, client):
        query = self.make_query(client, [
            [{"code": "B"}, {"code": "A"}],
            [{"code": "B"}, {"code": None}, {"code": " "}],
            [],
        ])
        result = course_codes(program=" CSCI-UA ")
        self.assertIsInstance(result, str)
        self.assertEqual(decode(result), {"course_codes": ["A", "B"]})
        self.assertEqual(
            [call.args for call in query.range.call_args_list],
            [(0, 999), (2, 1001), (5, 1004)],
        )
        query.eq.assert_called_with("program", "CSCI-UA")

    @patch("tools.courses.supabase")
    def test_programs_are_preserved_and_sorted_in_toon(self, client):
        first = {"program": "A", "program_name": "Alpha", "school": "School A"}
        last = {"program": "Z", "program_name": "Zeta", "school": "School Z"}
        self.make_query(client, [[last, first, last], []])
        result = list_programs()
        self.assertIsInstance(result, str)
        self.assertEqual(decode(result), {"programs": [first, last]})

    @patch("tools.courses.supabase")
    def test_no_matches(self, client):
        self.make_query(client, [[]])
        self.assertEqual(decode(course_codes(school="Unknown")), {"course_codes": []})

    @patch("tools.courses.supabase")
    def test_missing_or_blank_filters_fail_before_query(self, client):
        for filters in ({}, {"program": None}, {"school": " "},
                        {"program": "CSCI-UA", "program_name": ""}):
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                course_codes(**filters)
        client.table.assert_not_called()


if __name__ == "__main__":
    unittest.main()
