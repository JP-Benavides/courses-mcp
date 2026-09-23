import importlib
import unittest
from unittest.mock import patch

from src.db import connection


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        connection.get_supabase.cache_clear()
        self.addCleanup(connection.get_supabase.cache_clear)

    @patch.dict("os.environ", {}, clear=True)
    @patch("dotenv.load_dotenv")
    @patch("supabase.create_client")
    def test_import_does_not_load_configuration_or_create_client(self, create, load):
        importlib.reload(connection)
        create.assert_not_called()
        load.assert_not_called()
        # Restore the module's real imports after the patches are removed.
        self.addCleanup(lambda: importlib.reload(connection))

    @patch.dict("os.environ", {}, clear=True)
    @patch("src.db.connection.load_dotenv")
    @patch("src.db.connection.create_client")
    def test_missing_configuration_fails_only_on_use(self, create, load):
        with self.assertRaisesRegex(ValueError, "SUPABASE_URL"):
            connection.get_supabase()
        create.assert_not_called()

    @patch.dict("os.environ", {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_PUBLISHABLE_KEY": "test-key",
    }, clear=True)
    @patch("src.db.connection.load_dotenv")
    @patch("src.db.connection.create_client")
    def test_client_is_created_once_and_reused(self, create, load):
        first = connection.get_supabase()
        self.assertIs(first, create.return_value)
        self.assertIs(connection.get_supabase(), first)
        create.assert_called_once()
        self.assertEqual(create.call_args.args, (
            "https://example.supabase.co", "test-key",
        ))
