import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import tempfile
from threading import Barrier
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

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

    def test_daily_voice_limit_is_persistent_and_runtime_configurable(self) -> None:
        original_limit = main.VOICE_REPLY_DAILY_LIMIT
        try:
            main.set_voice_reply_daily_limit(35)
            self.assertEqual(main.get_voice_reply_daily_limit(), 35)
            main.VOICE_REPLY_DAILY_LIMIT = 99
            main.init_database()
            self.assertEqual(main.get_voice_reply_daily_limit(), 35)
            self.assertEqual(main.VOICE_REPLY_DAILY_LIMIT, 35)
        finally:
            main.VOICE_REPLY_DAILY_LIMIT = original_limit

    def test_daily_voice_limit_command_requires_owner_and_rejects_invalid_values(
        self,
    ) -> None:
        original_admin = main.ADMIN_CHAT_ID
        original_limit = main.VOICE_REPLY_DAILY_LIMIT
        main.ADMIN_CHAT_ID = 999
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=999),
            message=message,
        )
        try:
            non_owner_update = SimpleNamespace(
                effective_user=SimpleNamespace(id=1000),
                message=message,
                effective_message=message,
            )
            asyncio.run(
                main.cmd_voice_limit(
                    non_owner_update, SimpleNamespace(args=["45"])
                )
            )
            self.assertIn(
                "тільки власнику",
                message.reply_text.await_args.args[0],
            )
            self.assertEqual(main.get_voice_reply_daily_limit(), original_limit)

            for raw_limit in ("0", "-1", "abc", "1.5"):
                message.reply_text.reset_mock()
                asyncio.run(
                    main.cmd_voice_limit(
                        update, SimpleNamespace(args=[raw_limit])
                    )
                )
                self.assertIn(
                    "Некоректний денний ліміт",
                    message.reply_text.await_args.args[0],
                )

            message.reply_text.reset_mock()
            asyncio.run(main.cmd_voice_limit(update, SimpleNamespace(args=[])))
            self.assertIn("Поточний денний ліміт", message.reply_text.await_args.args[0])

            message.reply_text.reset_mock()
            asyncio.run(
                main.cmd_voice_limit(update, SimpleNamespace(args=["45"]))
            )
            self.assertEqual(main.get_voice_reply_daily_limit(), 45)
            self.assertIn(
                "застосовується без перезапуску",
                message.reply_text.await_args.args[0],
            )
            self.assertEqual(
                main.load_admin_audit(limit=1)[0]["action"],
                "set_voice_reply_daily_limit",
            )
        finally:
            main.ADMIN_CHAT_ID = original_admin
            main.VOICE_REPLY_DAILY_LIMIT = original_limit

    def test_voice_message_is_transcribed_and_gets_text_response_for_any_user(self) -> None:
        original_client = main.openai_client
        transcription = AsyncMock(
            return_value=SimpleNamespace(text="Розкажи про гурт")
        )
        main.openai_client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=transcription))
        )
        tg_file = SimpleNamespace()

        async def download_to_drive(path: str) -> None:
            Path(path).write_bytes(b"OggS-test-voice")

        tg_file.download_to_drive = download_to_drive
        message = SimpleNamespace(
            voice=SimpleNamespace(
                file_id="voice-file",
                file_size=1024,
                duration=4,
                mime_type="audio/ogg",
            ),
            audio=None,
            text=None,
            caption=None,
            chat=SimpleNamespace(id=101, send_action=AsyncMock()),
            reply_text=AsyncMock(),
        )
        update = SimpleNamespace(
            effective_user=SimpleNamespace(
                id=101,
                username="fan",
                first_name="Fan",
                full_name="Fan",
                language_code="uk",
            ),
            effective_chat=SimpleNamespace(id=101),
            effective_message=message,
            message=message,
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(
                get_file=AsyncMock(return_value=tg_file),
                send_message=AsyncMock(),
            )
        )
        original_ai_reply = main.ai_reply
        original_send_voice_reply = main._send_voice_reply
        ai_reply_mock = AsyncMock(
            return_value="Наш гурт поєднує метал і українську лірику."
        )
        main.ai_reply = ai_reply_mock
        main._send_voice_reply = AsyncMock(return_value="disabled")
        try:
            asyncio.run(main.on_voice(update, context))
        finally:
            main.openai_client = original_client
            main.ai_reply = original_ai_reply
            main._send_voice_reply = original_send_voice_reply

        transcription.assert_awaited_once()
        self.assertEqual(
            transcription.await_args.kwargs["model"],
            os.environ.get("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"),
        )
        ai_reply_mock.assert_awaited_once_with(
            "Розкажи про гурт",
            [],
            chat_id=101,
            username="fan",
        )
        sent_text = "\n".join(
            call.args[0] for call in message.reply_text.await_args_list
        )
        self.assertIn("Почув: Розкажи про гурт", sent_text)
        self.assertIn("Наш гурт поєднує", sent_text)

    def test_mini_app_uses_inline_button_that_receives_telegram_identity(self) -> None:
        reply_labels = {
            button.text
            for row in main.MAIN_KEYBOARD.keyboard
            for button in row
        }
        self.assertNotIn(main.BTN_APP, reply_labels)

        first_button = main.APP_LAUNCH_KEYBOARD.inline_keyboard[0][0]
        self.assertEqual(first_button.text, main.BTN_APP)
        self.assertIsNotNone(first_button.web_app)
        self.assertEqual(first_button.web_app.url, main.BAND_SITE_URL)

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

    def test_voice_usage_warning_is_claimed_once_under_concurrent_spike(self) -> None:
        original_limit = main.VOICE_REPLY_DAILY_LIMIT
        original_percent = main.VOICE_USAGE_WARNING_PERCENT
        attempt_count = 8
        start_gate = Barrier(attempt_count)
        try:
            main.VOICE_REPLY_DAILY_LIMIT = 10
            main.VOICE_USAGE_WARNING_PERCENT = 80
            today = datetime.now().astimezone().date().isoformat()
            with main._db() as conn:
                conn.executemany(
                    """INSERT INTO voice_usage(chat_id, usage_date, reply_count)
                       VALUES (?, ?, ?)""",
                    [(chat_id, today, 1) for chat_id in range(101, 109)],
                )
                conn.commit()

            def claim_after_start_gate(_attempt: int) -> dict[str, int] | None:
                start_gate.wait(timeout=5)
                return main._claim_voice_usage_warning()

            with ThreadPoolExecutor(max_workers=attempt_count) as executor:
                claims = list(executor.map(claim_after_start_gate, range(attempt_count)))

            successful_claims = [claim for claim in claims if claim is not None]
            self.assertEqual(
                successful_claims,
                [{"today": 8, "limit": 10, "percent": 80}],
            )
            self.assertEqual(claims.count(None), attempt_count - 1)
        finally:
            main.VOICE_REPLY_DAILY_LIMIT = original_limit
            main.VOICE_USAGE_WARNING_PERCENT = original_percent

    def test_voice_warning_threshold_is_persistent_and_runtime_configurable(self) -> None:
        original_percent = main.VOICE_USAGE_WARNING_PERCENT
        try:
            main.set_voice_usage_warning_percent(35)
            self.assertEqual(main.get_voice_usage_warning_percent(), 35)
            main.VOICE_USAGE_WARNING_PERCENT = 99
            main.init_database()
            self.assertEqual(main.get_voice_usage_warning_percent(), 35)
            self.assertEqual(main.VOICE_USAGE_WARNING_PERCENT, 35)
        finally:
            main.VOICE_USAGE_WARNING_PERCENT = original_percent

    def test_voice_warning_command_requires_owner_and_rejects_invalid_values(self) -> None:
        original_admin = main.ADMIN_CHAT_ID
        original_percent = main.VOICE_USAGE_WARNING_PERCENT
        original_environment_percent = main.VOICE_USAGE_WARNING_PERCENT_ENVIRONMENT
        main.ADMIN_CHAT_ID = 999
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=999),
            message=message,
        )
        try:
            for raw_percent in ("0", "101", "abc", "80%"):
                message.reply_text.reset_mock()
                asyncio.run(
                    main.cmd_voice_warning(
                        update, SimpleNamespace(args=[raw_percent])
                    )
                )
                self.assertIn("Некоректний поріг", message.reply_text.await_args.args[0])

            message.reply_text.reset_mock()
            asyncio.run(main.cmd_voice_warning(update, SimpleNamespace(args=[])))
            self.assertIn("Поточний поріг", message.reply_text.await_args.args[0])

            message.reply_text.reset_mock()
            asyncio.run(
                main.cmd_voice_warning(update, SimpleNamespace(args=["45"]))
            )
            self.assertEqual(main.get_voice_usage_warning_percent(), 45)
            self.assertIn("застосовується без перезапуску", message.reply_text.await_args.args[0])
            self.assertEqual(
                main.load_admin_audit(limit=1)[0]["action"],
                "set_voice_warning_percent",
            )
        finally:
            main.ADMIN_CHAT_ID = original_admin
            main.VOICE_USAGE_WARNING_PERCENT = original_percent
            main.VOICE_USAGE_WARNING_PERCENT_ENVIRONMENT = original_environment_percent

    def test_voice_warning_reset_is_owner_only_and_restores_environment_value(self) -> None:
        original_admin = main.ADMIN_CHAT_ID
        original_percent = main.VOICE_USAGE_WARNING_PERCENT
        original_environment_percent = main.VOICE_USAGE_WARNING_PERCENT_ENVIRONMENT
        main.ADMIN_CHAT_ID = 999
        main.VOICE_USAGE_WARNING_PERCENT_ENVIRONMENT = 65
        message = SimpleNamespace(reply_text=AsyncMock())
        owner_update = SimpleNamespace(
            effective_user=SimpleNamespace(id=999),
            message=message,
        )
        non_owner_update = SimpleNamespace(
            effective_user=SimpleNamespace(id=1000),
            message=message,
            effective_message=message,
        )
        try:
            main.set_voice_usage_warning_percent(35)
            asyncio.run(
                main.cmd_voice_warning(
                    non_owner_update, SimpleNamespace(args=["reset"])
                )
            )
            self.assertIn("тільки власнику", message.reply_text.await_args.args[0])
            self.assertEqual(main.get_voice_usage_warning_percent(), 35)

            message.reply_text.reset_mock()
            asyncio.run(
                main.cmd_voice_warning(owner_update, SimpleNamespace(args=["reset"]))
            )

            self.assertEqual(main.get_voice_usage_warning_percent(), 65)
            self.assertEqual(main.VOICE_USAGE_WARNING_PERCENT, 65)
            with main._db() as conn:
                self.assertIsNone(
                    conn.execute(
                        "SELECT value FROM metadata WHERE key=?",
                        (main.VOICE_USAGE_WARNING_PERCENT_METADATA_KEY,),
                    ).fetchone()
                )
            self.assertIn("повернуто до налаштування середовища", message.reply_text.await_args.args[0])
            audit = main.load_admin_audit(limit=1)[0]
            self.assertEqual(audit["action"], "reset_voice_warning_percent")
            self.assertEqual(audit["actor_id"], 999)
            self.assertIn("source=environment", audit["detail"])
        finally:
            main.ADMIN_CHAT_ID = original_admin
            main.VOICE_USAGE_WARNING_PERCENT = original_percent
            main.VOICE_USAGE_WARNING_PERCENT_ENVIRONMENT = original_environment_percent

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

    def test_admin_command_queues_retry_without_losing_local_change(self) -> None:
        original_admin = main.ADMIN_CHAT_ID
        main.ADMIN_CHAT_ID = 999
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=999),
            message=message,
        )
        context = SimpleNamespace(args=["101"])
        try:
            main.init_database()
            with patch.object(
                main,
                "_sync_mini_app_admin_role",
                side_effect=RuntimeError("web unavailable"),
            ):
                asyncio.run(main.cmd_add_admin(update, context))
            self.assertTrue(main.is_admin_id(101))
            pending = main.load_pending_admin_role_changes()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["target_id"], 101)
            self.assertTrue(pending[0]["is_admin"])
            self.assertIn(
                "синхронізується автоматично",
                message.reply_text.await_args.args[0],
            )
            audit = main.load_admin_audit()
            self.assertEqual(audit[0]["action"], "grant_admin")
            self.assertEqual(audit[0]["actor_id"], 999)
        finally:
            main.ADMIN_CHAT_ID = original_admin

    def test_failed_revocation_stays_pending_without_claiming_success(self) -> None:
        original_admin = main.ADMIN_CHAT_ID
        main.ADMIN_CHAT_ID = 999
        main.grant_admin(101, 999)
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=999),
            message=message,
        )
        context = SimpleNamespace(args=["101"])
        try:
            with patch.object(
                main,
                "_sync_mini_app_admin_role",
                side_effect=RuntimeError("web unavailable"),
            ):
                asyncio.run(main.cmd_remove_admin(update, context))
            self.assertTrue(main.is_admin_id(101))
            self.assertIn("очікує синхронізації", message.reply_text.await_args.args[0])
            pending = main.load_pending_admin_role_changes()
            self.assertEqual(len(pending), 1)
            self.assertFalse(pending[0]["is_admin"])
            self.assertNotIn(
                "revoke_admin",
                [row["action"] for row in main.load_admin_audit()],
            )
        finally:
            main.ADMIN_CHAT_ID = original_admin

    def test_existing_admin_is_backfilled_once_for_mini_app(self) -> None:
        main.grant_admin(101, 999)
        self.assertEqual(main.load_pending_admin_role_changes(), [])

        self.assertEqual(main.enqueue_legacy_admin_role_backfill(), 1)
        pending = main.load_pending_admin_role_changes()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["target_id"], 101)
        self.assertTrue(pending[0]["is_admin"])
        self.assertEqual(main.enqueue_legacy_admin_role_backfill(), 0)
        self.assertEqual(len(main.load_pending_admin_role_changes()), 1)

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
