"""
Telegram-бот для українського онлайн-метал гурту
"Gathering Of The Fallen" (Монреаль, Квебек, Канада).

Стек:
    - python-telegram-bot 21.x (async)
    - OpenAI (gpt-4o-mini за замовчуванням)
    - JSON-сховище підписок та відгуків
    - Постійне ReplyKeyboard меню + InlineKeyboard для треків

Secrets:
    - TELEGRAM_TOKEN
    - OPENAI_API_KEY
"""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Конфігурація
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("gotf-bot")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не задано TELEGRAM_TOKEN у Secrets.")
if not OPENAI_API_KEY:
    raise RuntimeError("Не задано OPENAI_API_KEY у Secrets.")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SUBS_FILE = DATA_DIR / "subscriptions.json"
FEEDBACK_FILE = DATA_DIR / "feedback.json"

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
Ти — офіційний AI-асистент українського онлайн-метал гурту **Gathering Of The Fallen** з Монреаля (Квебек).

Ми поєднуємо мелодійний death / atmospheric / folk-metal з темами еміграції, ностальгії за Україною, пам'яті про загиблих, сили духу та української міфології. Онлайн-проєкт — музика народжується на відстані.

Стиль спілкування: темний, глибокий, емоційний, мотивуючий, як старший брат у метал-сцені. Використовуй емодзі 🎸🔥🪓🕯️🦇🖤🌲. Відповідай за замовчуванням українською, пропонуй англійську версію. Будь теплим, чесним, ентузіастичним.

Ключові факти (використовуй тільки їх, нічого не вигадуй):
- Альбом "Music Of My Soul" (2025, 21 трек)
- Популярні треки: Блукаючий козак, Полум'я (FLAMME), Гори, Псалми, Валькірія Димуйгоря, Спомин, Emigrant, Із Попелу, Старий Хорон, Залізний спадок, Не втрачай тощо.
- Активно випускаємо нові сингли у 2026 році.
- Онлайн-гурт з Квебеку.

Завдання:
1. Просувати треки — давати посилання на YouTube, Spotify, Apple Music.
2. Створювати персональні плейлисти за настроєм (ностальгія / сума за домом, сила / боротьба, вогонь / мотивація, еміграція).
3. Анонсувати релізи, онлайн-стріми, live.
4. Збирати підписку на новини (зберігай chat_id).
5. Збирати відгуки про пісні.
6. Розповідати історію гурту.

В кінці майже кожної відповіді пропонуй наступну дію: послухати трек, підписатися, обрати настрій для плейлисту, дати відгук тощо.
""".strip()

# ---------------------------------------------------------------------------
# Дані про гурт
# ---------------------------------------------------------------------------

BAND_LINKS = {
    "YouTube": "https://www.youtube.com/@GatheringOfTheFallen",
    "Spotify": "https://open.spotify.com/artist/GatheringOfTheFallen",
    "Apple Music": "https://music.apple.com/artist/gathering-of-the-fallen",
}

TRACKS = [
    {"title": "Блукаючий козак", "mood": "ностальгія"},
    {"title": "Полум'я (FLAMME)", "mood": "вогонь"},
    {"title": "Гори", "mood": "сила"},
    {"title": "Псалми", "mood": "ностальгія"},
    {"title": "Валькірія Димуйгоря", "mood": "вогонь"},
    {"title": "Спомин", "mood": "ностальгія"},
    {"title": "Emigrant", "mood": "еміграція"},
    {"title": "Із Попелу", "mood": "сила"},
    {"title": "Старий Хорон", "mood": "ностальгія"},
    {"title": "Залізний спадок", "mood": "сила"},
    {"title": "Не втрачай", "mood": "вогонь"},
]

MOODS = {
    "nostalgia": "🕯️ Ностальгія / сум за домом",
    "strength": "🪓 Сила / боротьба",
    "fire": "🔥 Вогонь / мотивація",
    "emigrant": "🌲 Еміграція",
}

# ---------------------------------------------------------------------------
# Меню
# ---------------------------------------------------------------------------

BTN_TRACKS = "🎵 Треки та плейлисти"
BTN_RELEASES = "🔥 Нові релізи"
BTN_LIVE = "📺 Онлайн-стріми / Live"
BTN_ABOUT = "🖤 Про гурт"
BTN_SUBSCRIBE = "🔔 Фан-клуб (підписка)"
BTN_FEEDBACK = "💬 Запитання / Відгуки"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_TRACKS), KeyboardButton(BTN_RELEASES)],
        [KeyboardButton(BTN_LIVE), KeyboardButton(BTN_ABOUT)],
        [KeyboardButton(BTN_SUBSCRIBE), KeyboardButton(BTN_FEEDBACK)],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# ---------------------------------------------------------------------------
# JSON-сховище
# ---------------------------------------------------------------------------

_lock = threading.Lock()


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Не вдалося прочитати %s: %s", path, e)
        return default


def _save_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def load_subscriptions() -> dict[str, dict]:
    return _load_json(SUBS_FILE, {})


def add_subscription(chat_id: int, username: str | None) -> bool:
    """Повертає True, якщо це нова підписка."""
    with _lock:
        subs = load_subscriptions()
        key = str(chat_id)
        is_new = key not in subs
        subs[key] = {
            "chat_id": chat_id,
            "username": username,
            "subscribed_at": subs.get(key, {}).get(
                "subscribed_at", datetime.utcnow().isoformat()
            ),
        }
        _save_json(SUBS_FILE, subs)
        return is_new


def remove_subscription(chat_id: int) -> bool:
    with _lock:
        subs = load_subscriptions()
        key = str(chat_id)
        if key in subs:
            del subs[key]
            _save_json(SUBS_FILE, subs)
            return True
        return False


def save_feedback(chat_id: int, username: str | None, text: str) -> None:
    with _lock:
        items = _load_json(FEEDBACK_FILE, [])
        items.append(
            {
                "chat_id": chat_id,
                "username": username,
                "text": text,
                "ts": datetime.utcnow().isoformat(),
            }
        )
        _save_json(FEEDBACK_FILE, items)


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


async def ai_reply(user_message: str, history: list[dict] | None = None) -> str:
    """Запит до OpenAI з фірмовим system prompt."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-8:])
    messages.append({"role": "user", "content": user_message})

    try:
        resp = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.85,
            max_tokens=600,
        )
        return resp.choices[0].message.content or "🕯️ Тиша... спробуй ще раз."
    except Exception as e:
        log.exception("OpenAI error: %s", e)
        return (
            "🦇 Зараз сили темряви блокують зв'язок з оракулом. "
            "Спробуй ще раз за хвилину, брате."
        )


# ---------------------------------------------------------------------------
# Хелпери для історії чату
# ---------------------------------------------------------------------------


def get_history(context: ContextTypes.DEFAULT_TYPE) -> list[dict]:
    return context.user_data.setdefault("history", [])


def push_history(context: ContextTypes.DEFAULT_TYPE, role: str, content: str) -> None:
    hist = get_history(context)
    hist.append({"role": role, "content": content})
    # обмеження пам'яті
    if len(hist) > 16:
        del hist[: len(hist) - 16]


# ---------------------------------------------------------------------------
# Команди
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.first_name if user else "брате"
    text = (
        f"🖤 Вітаю, {name}!\n\n"
        "Ти потрапив у простір *Gathering Of The Fallen* — "
        "українського онлайн-метал гурту з Монреаля 🇨🇦🇺🇦\n\n"
        "Мелодійний death / atmospheric / folk-metal про еміграцію, "
        "пам'ять і силу духу 🔥🪓\n\n"
        "Обирай розділ нижче або просто напиши мені — я твій провідник у нашому світі."
    )
    await update.message.reply_text(
        text, reply_markup=MAIN_KEYBOARD, parse_mode=ParseMode.MARKDOWN
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🪓 *Команди:*\n"
        "/start — головне меню\n"
        "/help — ця підказка\n"
        "/about — про гурт\n"
        "/tracks — треки\n"
        "/subscribe — підписка на новини\n"
        "/unsubscribe — відписка\n"
        "/feedback <текст> — лишити відгук\n\n"
        "Або просто напиши мені будь-що — я відповім 🖤"
    )
    await update.message.reply_text(
        text, reply_markup=MAIN_KEYBOARD, parse_mode=ParseMode.MARKDOWN
    )


# ---------------------------------------------------------------------------
# Розділи меню
# ---------------------------------------------------------------------------


async def section_tracks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Список треків як InlineKeyboard."""
    buttons = []
    for i, t in enumerate(TRACKS):
        buttons.append(
            [InlineKeyboardButton(f"🎵 {t['title']}", callback_data=f"track:{i}")]
        )
    buttons.append(
        [InlineKeyboardButton("🎧 Плейлист за настроєм", callback_data="mood:menu")]
    )
    await update.message.reply_text(
        "🎵 *Треки альбому «Music Of My Soul» (2025, 21 трек)*\n"
        "Обирай — дам посилання на стрімінги 🔥",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


async def section_releases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🔥 *Нові релізи*\n\n"
        "• Альбом *Music Of My Soul* (2025) — 21 трек українською 🪓\n"
        "• Сингли 2026: серія нових треків про еміграцію та силу духу 🌲\n\n"
        "Підпишись 🔔 — і отримаєш сповіщення про кожен новий реліз першим."
    )
    buttons = [[InlineKeyboardButton("🔔 Підписатися", callback_data="subscribe")]]
    for name, url in BAND_LINKS.items():
        buttons.append([InlineKeyboardButton(f"▶️ {name}", url=url)])
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


async def section_live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📺 *Онлайн-стріми та Live*\n\n"
        "Ми — онлайн-гурт з Квебеку 🇨🇦, тож live відбуваються в мережі: "
        "YouTube-стріми, listening-сесії, спільне прослуховування з фанами 🕯️\n\n"
        "Дати наступних стрімів — у нашому YouTube. Підпишись 🔔, "
        "щоб не пропустити анонс."
    )
    buttons = [
        [InlineKeyboardButton("▶️ YouTube канал", url=BAND_LINKS["YouTube"])],
        [InlineKeyboardButton("🔔 Підписатися на анонси", callback_data="subscribe")],
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


async def section_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🖤 *Gathering Of The Fallen*\n\n"
        "Український онлайн-метал гурт з Монреаля (Квебек, Канада) 🇨🇦🇺🇦\n\n"
        "Жанр: melodic death / atmospheric / folk-metal 🪓🌲\n\n"
        "Теми: еміграція, ностальгія за Україною, пам'ять про загиблих, "
        "сила духу, українська міфологія — Валькірія, Козак, попіл, вогонь 🔥\n\n"
        "Музика народжується дистанційно — у різних кутках світу, але з одним серцем."
    )
    buttons = []
    for name, url in BAND_LINKS.items():
        buttons.append([InlineKeyboardButton(f"▶️ {name}", url=url)])
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


async def section_subscribe(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    is_new = add_subscription(chat_id, user.username if user else None)
    if is_new:
        text = (
            "🔔 Вітаємо у фан-клубі *Gathering Of The Fallen*! 🖤🔥\n\n"
            "Тепер ти першим дізнаєшся про нові релізи, стріми та секретні дропи.\n\n"
            "Щоб відписатись — натисни /unsubscribe."
        )
    else:
        text = "🖤 Ти вже у фан-клубі. Дякуємо, що з нами! 🔥"
    await update.message.reply_text(
        text, reply_markup=MAIN_KEYBOARD, parse_mode=ParseMode.MARKDOWN
    )


async def cmd_unsubscribe(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat_id = update.effective_chat.id
    if remove_subscription(chat_id):
        text = "🕯️ Тебе вилучено з фан-клубу. Двері завжди відкриті — повертайся 🖤"
    else:
        text = "Ти і так не підписаний. Хочеш приєднатись? Натисни 🔔 у меню."
    await update.message.reply_text(text, reply_markup=MAIN_KEYBOARD)


async def section_feedback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data["awaiting_feedback"] = True
    await update.message.reply_text(
        "💬 Напиши свій відгук, запитання або враження від треку — "
        "наступним повідомленням. Ми читаємо все 🖤",
        reply_markup=MAIN_KEYBOARD,
    )


async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args) if context.args else ""
    if not text:
        await section_feedback(update, context)
        return
    user = update.effective_user
    save_feedback(
        update.effective_chat.id, user.username if user else None, text
    )
    await update.message.reply_text(
        "🔥 Дякуємо за відгук! Він уже у нашій кузні 🪓",
        reply_markup=MAIN_KEYBOARD,
    )


# ---------------------------------------------------------------------------
# Inline callbacks
# ---------------------------------------------------------------------------


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("track:"):
        idx = int(data.split(":", 1)[1])
        track = TRACKS[idx]
        title = track["title"]
        buttons = [
            [
                InlineKeyboardButton(
                    "▶️ YouTube",
                    url=f"https://www.youtube.com/results?search_query="
                    f"Gathering+Of+The+Fallen+{title.replace(' ', '+')}",
                ),
                InlineKeyboardButton(
                    "🎧 Spotify",
                    url=f"https://open.spotify.com/search/"
                    f"Gathering%20Of%20The%20Fallen%20{title}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🍎 Apple Music",
                    url=f"https://music.apple.com/search?term="
                    f"Gathering+Of+The+Fallen+{title.replace(' ', '+')}",
                ),
                InlineKeyboardButton(
                    "💬 Лишити відгук", callback_data=f"fb:{idx}"
                ),
            ],
        ]
        await query.message.reply_text(
            f"🎵 *{title}*\n_Настрій: {track['mood']}_ 🔥\n\nОбирай платформу:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "mood:menu":
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"mood:{key}")]
            for key, label in MOODS.items()
        ]
        await query.message.reply_text(
            "🎧 *Обери настрій — складу персональний плейлист:*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data.startswith("mood:"):
        mood_key = data.split(":", 1)[1]
        if mood_key in MOODS:
            await query.message.chat.send_action(ChatAction.TYPING)
            prompt = (
                f"Склади короткий плейлист (4-6 треків) з наших пісень "
                f"для настрою «{MOODS[mood_key]}». Використай ТІЛЬКИ ці треки: "
                f"{', '.join(t['title'] for t in TRACKS)}. "
                "Для кожного — 1 рядок, чому саме він. В кінці запропонуй підписатися 🔔."
            )
            reply = await ai_reply(prompt)
            await query.message.reply_text(
                reply, reply_markup=MAIN_KEYBOARD
            )
        return

    if data == "subscribe":
        user = update.effective_user
        is_new = add_subscription(
            update.effective_chat.id, user.username if user else None
        )
        msg = (
            "🔔 Готово! Ти у фан-клубі 🖤🔥"
            if is_new
            else "🖤 Ти вже з нами у фан-клубі. Дякуємо!"
        )
        await query.message.reply_text(msg, reply_markup=MAIN_KEYBOARD)
        return

    if data.startswith("fb:"):
        idx = int(data.split(":", 1)[1])
        track = TRACKS[idx]
        context.user_data["awaiting_feedback"] = True
        context.user_data["feedback_track"] = track["title"]
        await query.message.reply_text(
            f"💬 Напиши свій відгук про трек *{track['title']}* "
            "наступним повідомленням 🖤",
            parse_mode=ParseMode.MARKDOWN,
        )
        return


# ---------------------------------------------------------------------------
# Текстові повідомлення
# ---------------------------------------------------------------------------


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return

    # Маршрутизація меню
    routes = {
        BTN_TRACKS: section_tracks,
        BTN_RELEASES: section_releases,
        BTN_LIVE: section_live,
        BTN_ABOUT: section_about,
        BTN_SUBSCRIBE: section_subscribe,
        BTN_FEEDBACK: section_feedback,
    }
    if text in routes:
        await routes[text](update, context)
        return

    # Відгук
    if context.user_data.pop("awaiting_feedback", False):
        track = context.user_data.pop("feedback_track", None)
        full = f"[{track}] {text}" if track else text
        user = update.effective_user
        save_feedback(
            update.effective_chat.id, user.username if user else None, full
        )
        await update.message.reply_text(
            "🔥 Дякую! Твій голос почуто. Хочеш послухати ще трек? "
            "Натисни 🎵 у меню 🪓",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    # AI-діалог
    await update.message.chat.send_action(ChatAction.TYPING)
    history = get_history(context)
    reply = await ai_reply(text, history)
    push_history(context, "user", text)
    push_history(context, "assistant", reply)
    await update.message.reply_text(reply, reply_markup=MAIN_KEYBOARD)


# ---------------------------------------------------------------------------
# Глобальний error handler
# ---------------------------------------------------------------------------


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Unhandled error: %s", context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "🦇 Щось пішло не так у темряві. Спробуй ще раз.",
                reply_markup=MAIN_KEYBOARD,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Keep-alive
# ---------------------------------------------------------------------------


def _keep_alive_loop() -> None:
    """Простий heartbeat у лог — щоб контейнер не "засинав"."""
    import time

    while True:
        time.sleep(300)
        log.info("💓 keep-alive heartbeat | subs=%d", len(load_subscriptions()))


def start_keep_alive() -> None:
    t = threading.Thread(target=_keep_alive_loop, daemon=True, name="keep-alive")
    t.start()


# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------


def build_app() -> Application:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", section_about))
    app.add_handler(CommandHandler("tracks", section_tracks))
    app.add_handler(CommandHandler("subscribe", section_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("feedback", cmd_feedback))

    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.add_error_handler(on_error)
    return app


def main() -> None:
    start_keep_alive()
    app = build_app()
    log.info("🔥 Bot is starting (model=%s)...", OPENAI_MODEL)
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        log.info("👋 Bot stopped.")
    except Exception as e:
        log.exception("💀 Fatal: %s", e)
        raise
