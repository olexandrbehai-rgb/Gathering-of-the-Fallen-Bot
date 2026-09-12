import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

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

    def test_official_youtube_catalog_is_current(self) -> None:
        self.assertEqual(
            main.BAND_LINKS["YouTube"],
            "https://www.youtube.com/@gathering_of_the_fallen",
        )
        self.assertEqual(len(main.YOUTUBE_VIDEOS), 30)
        self.assertEqual(main.YOUTUBE_VIDEOS[0]["video_id"], "eBgXAXDKgDk")
        self.assertTrue(
            main.track_url(
                "Додому (за участі Olia Stefaniw)", "YouTube"
            ).endswith("eBgXAXDKgDk")
        )
        self.assertEqual(
            main.BAND_LINKS["YouTube Music"],
            "https://music.youtube.com/@gathering_of_the_fallen",
        )
        self.assertTrue(
            main.track_url(
                "Додому (за участі Olia Stefaniw)", "YouTube Music"
            ).endswith("eBgXAXDKgDk")
        )

    def test_shared_catalog_drives_bot_tracks_releases_and_links(self) -> None:
        catalog = main._load_catalog()
        expected_titles = [
            item["title"] for item in catalog["videos"] + catalog["tracks"]
        ]
        self.assertEqual([track["title"] for track in main.TRACKS], expected_titles)
        self.assertEqual(main.RELEASES, catalog["releases"])
        self.assertEqual(
            main.RELEASES[0]["title"],
            "Music Of My Soul",
        )
        self.assertEqual(
            main.track_url("Гори", "YouTube"),
            next(
                track["links"]["YouTube"]
                for track in catalog["tracks"]
                if track["title"] == "Гори"
            ),
        )

    def test_shared_catalog_rejects_duplicate_titles(self) -> None:
        catalog = main._load_catalog()
        catalog["tracks"].append(dict(catalog["tracks"][0]))
        path = Path(self.temp_dir.name) / "invalid-catalog.json"
        import json

        path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Дубльована"):
            main._load_catalog(path)

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

    def test_voice_setting_is_persistent_and_deleted_with_user(self) -> None:
        self.assertFalse(main.voice_replies_enabled(101))
        main.set_voice_replies(101, True)
        self.assertTrue(main.voice_replies_enabled(101))
        main.delete_user_data(101)
        self.assertFalse(main.voice_replies_enabled(101))

    def test_voice_text_is_cleaned_and_shortened(self) -> None:
        text = (
            "**Перше речення** про трек. "
            "Друге речення з https://example.com/дуже-довгим-посиланням. "
            "Третє речення не повинно потрапити повністю."
        )
        shortened = main._shorten_for_voice(text, max_chars=85)
        self.assertLessEqual(len(shortened), 85)
        self.assertNotIn("**", shortened)
        self.assertNotIn("https://", shortened)
        self.assertTrue(shortened.endswith((".", "!", "?", "…")))

    def test_daily_voice_limit_is_enforced(self) -> None:
        original = main.VOICE_REPLY_DAILY_LIMIT
        try:
            main.VOICE_REPLY_DAILY_LIMIT = 2
            self.assertTrue(main._reserve_voice_reply(101))
            self.assertTrue(main._reserve_voice_reply(101))
            self.assertFalse(main._reserve_voice_reply(101))
        finally:
            main.VOICE_REPLY_DAILY_LIMIT = original

    def test_voice_usage_warning_is_claimed_only_once_per_day(self) -> None:
        original_limit = main.VOICE_REPLY_DAILY_LIMIT
        original_percent = main.VOICE_USAGE_WARNING_PERCENT
        try:
            main.VOICE_REPLY_DAILY_LIMIT = 10
            main.VOICE_USAGE_WARNING_PERCENT = 80
            with main._db() as conn:
                conn.executemany(
                    """INSERT INTO voice_usage(chat_id, usage_date, reply_count)
                       VALUES (?, ?, ?)""",
                    [
                        (101, datetime.now().astimezone().date().isoformat(), 4),
                        (202, datetime.now().astimezone().date().isoformat(), 4),
                    ],
                )
                conn.commit()

            self.assertEqual(
                main._claim_voice_usage_warning(),
                {"today": 8, "limit": 10, "percent": 80},
            )
            self.assertIsNone(main._claim_voice_usage_warning())
        finally:
            main.VOICE_REPLY_DAILY_LIMIT = original_limit
            main.VOICE_USAGE_WARNING_PERCENT = original_percent

    def test_voice_usage_warning_contains_only_aggregate_numbers(self) -> None:
        original_admin = main.ADMIN_CHAT_ID
        original_limit = main.VOICE_REPLY_DAILY_LIMIT
        original_percent = main.VOICE_USAGE_WARNING_PERCENT
        try:
            main.ADMIN_CHAT_ID = 999
            main.VOICE_REPLY_DAILY_LIMIT = 2
            main.VOICE_USAGE_WARNING_PERCENT = 50
            self.assertTrue(main._reserve_voice_reply(101))
            bot = SimpleNamespace(send_message=AsyncMock())
            message = SimpleNamespace(get_bot=lambda: bot)

            asyncio.run(main._notify_voice_usage_warning(message))

            sent = bot.send_message.await_args.kwargs
            self.assertEqual(sent["chat_id"], 999)
            self.assertIn("Сьогодні використано: 1", sent["text"])
            self.assertNotIn("101", sent["text"])
        finally:
            main.ADMIN_CHAT_ID = original_admin
            main.VOICE_REPLY_DAILY_LIMIT = original_limit
            main.VOICE_USAGE_WARNING_PERCENT = original_percent

    def test_voice_stats_aggregate_usage_without_message_texts(self) -> None:
        today = datetime.now().astimezone().date()
        main.set_voice_replies(101, True)
        main.set_voice_replies(202, True)
        main.set_voice_replies(303, False)
        with main._db() as conn:
            conn.executemany(
                """INSERT INTO voice_usage(chat_id, usage_date, reply_count)
                   VALUES (?, ?, ?)""",
                [
                    (101, today.isoformat(), 2),
                    (202, (today - timedelta(days=6)).isoformat(), 3),
                    (303, (today - timedelta(days=7)).isoformat(), 20),
                ],
            )
            conn.commit()

        self.assertEqual(
            main.get_voice_stats(),
            {"today": 2, "last_7_days": 5, "enabled_users": 2},
        )

    def test_admin_stats_message_includes_voice_usage(self) -> None:
        original_admin = main.ADMIN_CHAT_ID
        main.ADMIN_CHAT_ID = 999
        main.set_voice_replies(101, True)
        self.assertTrue(main._reserve_voice_reply(101))
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=999),
            message=message,
        )
        try:
            asyncio.run(main.cmd_stats(update, SimpleNamespace()))
        finally:
            main.ADMIN_CHAT_ID = original_admin

        text = message.reply_text.await_args.args[0]
        self.assertIn("Сьогодні: 1", text)
        self.assertIn("За останні 7 днів: 1", text)
        self.assertIn("Голос увімкнули: 1", text)

    def test_owner_can_manage_admins_and_owner_cannot_be_removed(self) -> None:
        original_admin = main.ADMIN_CHAT_ID
        main.ADMIN_CHAT_ID = 999
        try:
            main.init_database()
            self.assertTrue(main.is_owner_id(999))
            self.assertTrue(main.grant_admin(101, 999))
            self.assertTrue(main.is_admin_id(101))
            self.assertFalse(main.grant_admin(101, 999))
            self.assertFalse(main.revoke_admin(999, 999))
            self.assertTrue(main.revoke_admin(101, 999))
            self.assertFalse(main.is_admin_id(101))
            actions = [row["action"] for row in main.load_admin_audit()]
            self.assertIn("grant_admin", actions)
            self.assertIn("revoke_admin", actions)
        finally:
            main.ADMIN_CHAT_ID = original_admin

    def test_activity_and_user_overview_capture_interest_without_text_body(self) -> None:
        update = SimpleNamespace(
            effective_user=SimpleNamespace(
                id=101,
                username="fan",
                first_name="Fan",
                language_code="uk",
            ),
            effective_chat=SimpleNamespace(id=101),
        )
        main.touch_user(update)
        main.record_activity(101, "search", "Гори")
        main.add_subscription(101, "fan")
        overview = main.get_user_overview(101)
        self.assertIsNotNone(overview)
        self.assertEqual(overview["subscribed"], 1)
        self.assertTrue(any(item["event_type"] == "search" for item in overview["recent"]))
        self.assertNotIn("content", overview)

    def test_tts_opus_is_sent_as_telegram_voice(self) -> None:
        main.set_voice_replies(101, True)
        response = Mock()

        def write_audio(path: str) -> None:
            Path(path).write_bytes(b"OggS-test-opus")

        response.write_to_file.side_effect = write_audio
        create = AsyncMock(return_value=response)
        original_client = main.openai_client
        main.openai_client = SimpleNamespace(
            audio=SimpleNamespace(speech=SimpleNamespace(create=create))
        )
        message = SimpleNamespace(
            chat=SimpleNamespace(send_action=AsyncMock()),
            reply_voice=AsyncMock(),
        )
        try:
            status = asyncio.run(
                main._send_voice_reply(message, 101, "Коротка AI-відповідь.")
            )
        finally:
            main.openai_client = original_client

        self.assertEqual(status, "sent")
        create.assert_awaited_once()
        self.assertEqual(create.await_args.kwargs["response_format"], "opus")
        message.reply_voice.assert_awaited_once()

    def test_tts_failure_keeps_fallback_and_refunds_limit(self) -> None:
        main.set_voice_replies(101, True)
        original_client = main.openai_client
        original_limit = main.VOICE_REPLY_DAILY_LIMIT
        main.VOICE_REPLY_DAILY_LIMIT = 1
        main.openai_client = SimpleNamespace(
            audio=SimpleNamespace(
                speech=SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("TTS down")))
            )
        )
        message = SimpleNamespace(
            chat=SimpleNamespace(send_action=AsyncMock()),
            reply_voice=AsyncMock(),
        )
        try:
            status = asyncio.run(
                main._send_voice_reply(message, 101, "Текстовий fallback уже надіслано.")
            )
        finally:
            main.openai_client = original_client
            main.VOICE_REPLY_DAILY_LIMIT = original_limit

        self.assertEqual(status, "error")
        message.reply_voice.assert_not_awaited()
        original_limit = main.VOICE_REPLY_DAILY_LIMIT
        try:
            main.VOICE_REPLY_DAILY_LIMIT = 1
            self.assertTrue(main._reserve_voice_reply(101))
        finally:
            main.VOICE_REPLY_DAILY_LIMIT = original_limit


if __name__ == "__main__":
    unittest.main()
