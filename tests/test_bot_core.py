import asyncio
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("TELEGRAM_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("OPENAI_API_KEY", "diagnostic-placeholder")

import main


class BotCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.original_paths = (
            main.DB_FILE,
            main.SUBS_FILE,
            main.FEEDBACK_FILE,
            main.FAN_CHAT_FILE,
        )
        main.DB_FILE = base / "test.sqlite3"
        main.SUBS_FILE = base / "subscriptions.json"
        main.FEEDBACK_FILE = base / "feedback.json"
        main.FAN_CHAT_FILE = base / "fan_chat.json"
        main.init_database()

    def tearDown(self) -> None:
        (
            main.DB_FILE,
            main.SUBS_FILE,
            main.FEEDBACK_FILE,
            main.FAN_CHAT_FILE,
        ) = self.original_paths
        self.temp_dir.cleanup()

    def test_database_flow_and_deletion(self) -> None:
        self.assertTrue(main.add_subscription(101, "fan"))
        self.assertFalse(main.add_subscription(101, "fan"))

        post = main.add_fan_message(101, "fan", "Fan", "Вогонь!")
        self.assertTrue(main.hide_fan_message(post["id"]))
        main.save_feedback(101, "fan", "Круто", "Гори")
        main.save_history(101, "user", "Привіт")
        main.save_history(101, "assistant", "Вітаю")
        self.assertEqual(len(main.load_history(101)), 2)

        main.delete_user_data(101)
        self.assertEqual(
            main.get_stats(),
            {
                "users": 0,
                "subscriptions": 0,
                "fan_messages": 0,
                "feedback": 0,
                "ai_messages": 0,
            },
        )

    def test_json_migration_runs_once(self) -> None:
        main.SUBS_FILE.write_text(
            '{"55":{"chat_id":55,"username":"legacy","subscribed_at":"2026-01-01"}}',
            encoding="utf-8",
        )
        main.DB_FILE.unlink(missing_ok=True)
        main.init_database()
        first = main.get_stats()
        main.delete_user_data(55)
        main.init_database()
        self.assertEqual(main.get_stats()["users"], first["users"] - 1)

    def test_track_search_normalizes_apostrophes(self) -> None:
        straight = main._find_tracks("Полум'я")
        curved = main._find_tracks("Полумʼя")
        self.assertTrue(straight)
        self.assertEqual(straight, curved)

    def test_fan_chat_rejects_spam_shapes(self) -> None:
        self.assertIsNotNone(main._fan_message_problem("https://spam.example"))
        self.assertIsNotNone(main._fan_message_problem("а" * 20))
        self.assertIsNone(main._fan_message_problem("Цей трек — справжній вогонь!"))

    def test_ai_tools_use_verified_catalog(self) -> None:
        result = asyncio.run(
            main._execute_ai_tool(
                "get_track_links", {"title": "Гори"}, chat_id=101, username="fan"
            )
        )
        self.assertIn("ZwNsc0A6mD8", result)

    def test_modern_model_parameters(self) -> None:
        original = main.OPENAI_MODEL
        try:
            main.OPENAI_MODEL = "gpt-5"
            options = main._completion_options()
            self.assertIn("max_completion_tokens", options)
            self.assertNotIn("temperature", options)
        finally:
            main.OPENAI_MODEL = original


if __name__ == "__main__":
    unittest.main()