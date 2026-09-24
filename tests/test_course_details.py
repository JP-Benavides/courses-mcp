import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from toon_format import decode
from src.tools.catalog import course_details


class CourseDetailsTests(unittest.TestCase):
    def make_query(self, client, pages):
        query = MagicMock()
        client.table.return_value = query
        for method in ("select", "in_", "order", "range"):
            getattr(query, method).return_value = query
        query.execute.side_effect = [SimpleNamespace(data=page) for page in pages]
        return query

    @patch("src.tools.catalog.get_supabase")
    def test_multiple_codes_pagination_and_nested_toon(self, get_client):
        client = get_client.return_value
        first = {"code": "A", "metadata": {"description": "One, two\nthree", "credits": 4}}
        last = {"code": "B", "metadata": None}
        query = self.make_query(client, [[last], [first], []])
        result = course_details([" B ", "A", "B"])
        self.assertIsInstance(result, str)
        self.assertEqual(decode(result), {"courses": [first, last]})
        client.table.assert_called_with("courses")
        query.select.assert_called_with("code,metadata")
        self.assertEqual(query.in_.call_count, 3)
        query.in_.assert_called_with("code", ["A", "B"])
        self.assertEqual([call.args for call in query.range.call_args_list],
                         [(0, 999), (1, 1000), (2, 1001)])

    @patch("src.tools.catalog.get_supabase")
    def test_single_code(self, get_client):
        client = get_client.return_value
        row = {"code": "A", "metadata": {"description": "A course"}}
        self.make_query(client, [[row], []])
        self.assertEqual(decode(course_details(["A"])), {"courses": [row]})

    @patch("src.tools.catalog.get_supabase")
    def test_no_matches(self, get_client):
        client = get_client.return_value
        self.make_query(client, [[]])
        self.assertEqual(decode(course_details(["Unknown"])), {"courses": []})

    @patch("src.tools.catalog.get_supabase")
    def test_invalid_codes_fail_before_query(self, get_client):
        client = get_client.return_value
        for codes in ([], [""], [" "], ["A", ""], [None], [123]):
            with self.subTest(codes=codes), self.assertRaises(ValueError):
                course_details(codes)
        get_client.assert_not_called()
        client.table.assert_not_called()


if __name__ == "__main__":
    unittest.main()
