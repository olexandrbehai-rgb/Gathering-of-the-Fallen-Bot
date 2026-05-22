"""
Telegram-бот для українського онлайн-метал гурту
"Gathering Of The Fallen" (Монреаль, Квебек, Канада).

Стек:
    - python-telegram-bot 21.x (async, polling)
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
import urllib.parse
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

# ===========================================================================
# 🔧 CONFIG — впиши сюди РЕАЛЬНІ посилання гурту
# ===========================================================================
#
# 1) BAND_LINKS — головні сторінки гурту на платформах.
#    Якщо реальної URL ще немає — лиши None, тоді кнопка не з'явиться
#    і бот замість неї покаже пошук на платформі.
#
# 2) TRACK_LINKS — прямі URL на конкретний трек/кліп.
#    Ключ = точна назва треку зі списку TRACKS нижче.
#    Якщо для треку прямого URL немає — лиши порожній dict {} або None.
#    Тоді бот сам зробить пошуковий лінк на платформі (з лапками,
#    щоб шукав ТОЧНУ назву + назву гурту).
# ===========================================================================

BAND_NAME = "Gathering Of The Fallen"

BAND_LINKS: dict[str, str | None] = {
    "YouTube":     "https://www.youtube.com/@gathering-of-the-fallen",
    "Spotify":     None,
    "Apple Music": None,
    "Bandcamp":    None,
    "Instagram":   None,
}

# Прямі URL з YouTube-каналу гурту. Для треку → словник {платформа: URL}.
# Якщо для платформи немає прямого URL — бот зробить пошук точно за назвою.
def _yt(vid: str) -> str:
    return f"https://www.youtube.com/watch?v={vid}"


TRACK_LINKS: dict[str, dict[str, str]] = {
    "Псалми":                          {"YouTube": _yt("sm4yVIlE0Oc")},
    "Гори":                            {"YouTube": _yt("ZwNsc0A6mD8")},
    "Не втрачай":                      {"YouTube": _yt("z4-EGoYiADM")},
    "If You Want":                     {"YouTube": _yt("ZPF_APH08OI")},
    "Wings of the Eternal Night":      {"YouTube": _yt("2AkrCvzU4Ss")},
    "Емігрант":                        {"YouTube": _yt("2kdtj1rwS5w")},
    "Вогонь В Руках":                  {"YouTube": _yt("bfbYohcYrnM")},
    "Through the Ashes":               {"YouTube": _yt("pGHn8UmSeVw")},
    "Я прийшла щоб торкнутися серця":  {"YouTube": _yt("FiyWewQWruE")},
    "Попіл і Воля":                    {"YouTube": _yt("V7Q1UoT6a68")},
    "Несу":                            {"YouTube": _yt("2zY3ABqlVYI")},
    "Живи!!!":                         {"YouTube": _yt("CnkVZDSzIXM")},
    "Валькірія Димуйгоря":             {"YouTube": _yt("KCCYiTESTng")},
    "Молодість":                       {"YouTube": _yt("YGqN3dVWBqg")},
    "Реквієм Народу":                  {"YouTube": _yt("D_PbC5L54nM")},
    "У Танці із Попелом":              {"YouTube": _yt("3Kkywl6MFfw")},
    "Крізь уламки і Дим":              {"YouTube": _yt("f_KBbl_kK4A")},
    "Полум'я (FLAMME)":                {"YouTube": _yt("ZXUrVVPXMgc")},
    "Тихі кроки":                      {"YouTube": _yt("lZIELnU0GUo")},
    "Із Попелу":                       {"YouTube": _yt("kdlPQTC4kY8")},
    "Пустка":                          {"YouTube": _yt("Te4lw6K1udc")},
    "Пустеля Душ":                     {"YouTube": _yt("U9uMhqNU6_g")},
    "Заграй мені трішки":              {"YouTube": _yt("uEKQHQZmc8E")},
    "Ти вже не той":                   {"YouTube": _yt("Tplib3iBlzQ")},
    "Залізний Спадок":                 {"YouTube": _yt("J2HkPII236E")},
    "Ой, розлився степ широкий":       {"YouTube": _yt("tUGs3URdn9E")},
    "Кобзар":                          {"YouTube": _yt("8lSH05b_iCM")},
    "Зацвіли Яблуні":                  {"YouTube": _yt("0o8EQS2Qt-w")},
    "Ой, у лузі вітер виє":            {"YouTube": _yt("L4agQMNaYMQ")},
    "Life (Життя)":                    {"YouTube": _yt("4X7wMT18BwI")},
    "Крізь тіні і час":                {"YouTube": _yt("jmnXHH2n6HU")},
    "Орися (кавер)":                   {"YouTube": _yt("sHv_WeLfV8w")},
    "Samurai":                         {"YouTube": _yt("S-RaWBjxzp0")},
    "Дід Максим":                      {"YouTube": _yt("k1Ynjs0hIcg")},
    "Ashes Whispering":                {"YouTube": _yt("CdEamcdn1YU")},
    "Легіон":                          {"YouTube": _yt("Wj2Qin2lrEQ")},
    "Road Through The Sand":           {"YouTube": _yt("DHBZ-TmBAiM")},
    "Only She (Лиш Вона)":             {"YouTube": _yt("Y6adLwYohxs")},
    "Піду я до Саду":                  {"YouTube": _yt("VFyCGl1t_zU")},
    "Shadows of the Past":             {"YouTube": _yt("QAe7KhW1WgM")},
    "Рагга душі Хард":                 {"YouTube": _yt("mRgQnw2qfuE")},
    "Shadows Beneath the Flame":       {"YouTube": _yt("1Km3XvJs3f8")},
    "Полум'я серця":                   {"YouTube": _yt("AcNZ1TwbMj0")},
    "Гілка Бузку":                     {"YouTube": _yt("jsN1BC4TvMA")},
    "Темний Політ":                    {"YouTube": _yt("x3q-OnH3Y-U")},
    "Палаючі серця":                   {"YouTube": _yt("4Rt5017mOqM")},
    "White Dove":                      {"YouTube": _yt("RSzsjxLMUXY")},
    "Тетянин Блюз":                    {"YouTube": _yt("50cnwwCiizs")},
    "In Memory Of Diesel":             {"YouTube": _yt("LhmTGCH6gwQ")},
    "Скрипаль":                        {"YouTube": _yt("x-0jSjQ9rek")},
    "Echoes of the Fallen":            {"YouTube": _yt("T2p6xWZY1ZQ")},
    "Вигнаний ангел":                  {"YouTube": _yt("Qf3wvFyuwEk")},
    "Подруга стара":                   {"YouTube": _yt("G4D7BxZq94M")},
    "У Темряві Серця":                 {"YouTube": _yt("CJe_Agp5spM")},
    "Подорож Довжиною в Життя":        {"YouTube": _yt("QRLvSMnnYCk")},
    "Я виріс на акордах":              {"YouTube": _yt("WV9WgPktKA0")},
    "To Bring You Back":               {"YouTube": _yt("10KtIjQ7Fuw")},
    "Старий Хорон":                    {"YouTube": _yt("ap0x6uMBEnE")},
    "Різдвяна Рок Опера":              {"YouTube": _yt("7ABVER4M8Tk")},
    "Shadows of Yesterday":            {"YouTube": _yt("IdffXpX0xOA")},
    "Жовті Ліхтарі":                   {"YouTube": _yt("tT-fEW5sGsg")},
    "Блукаючий козак":                 {"YouTube": _yt("ZNSGqJzCv08")},
    "Чорна Береза":                    {"YouTube": _yt("QUB5m6Me7tk")},
}

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
# Дані про треки + теги настроїв
# ---------------------------------------------------------------------------

# tags — ключі словника MOODS нижче, до яких належить трек
TRACKS: list[dict[str, Any]] = [
    {"title": "Блукаючий козак",                "tags": ["emigrant", "nostalgia"]},
    {"title": "Полум'я (FLAMME)",               "tags": ["fire", "strength"]},
    {"title": "Полум'я серця",                  "tags": ["fire"]},
    {"title": "Валькірія Димуйгоря",            "tags": ["fire", "strength"]},
    {"title": "Із Попелу",                      "tags": ["strength", "fire"]},
    {"title": "Through the Ashes",             "tags": ["strength", "fire"]},
    {"title": "Гори",                           "tags": ["strength"]},
    {"title": "Залізний Спадок",                "tags": ["strength"]},
    {"title": "Легіон",                         "tags": ["strength"]},
    {"title": "Темний Політ",                   "tags": ["strength"]},
    {"title": "Кобзар",                         "tags": ["strength", "nostalgia"]},
    {"title": "Дід Максим",                     "tags": ["strength"]},
    {"title": "Samurai",                        "tags": ["fire", "strength"]},
    {"title": "Не втрачай",                     "tags": ["fire", "strength"]},
    {"title": "Живи!!!",                        "tags": ["fire", "strength"]},
    {"title": "Вогонь В Руках",                 "tags": ["fire"]},
    {"title": "Палаючі серця",                  "tags": ["fire"]},
    {"title": "Shadows Beneath the Flame",      "tags": ["fire"]},
    {"title": "Попіл і Воля",                   "tags": ["strength"]},
    {"title": "У Танці із Попелом",             "tags": ["strength"]},
    {"title": "Крізь уламки і Дим",             "tags": ["strength"]},
    {"title": "Реквієм Народу",                 "tags": ["nostalgia"]},
    {"title": "Псалми",                         "tags": ["nostalgia"]},
    {"title": "Молодість",                      "tags": ["nostalgia"]},
    {"title": "Я виріс на акордах",             "tags": ["nostalgia"]},
    {"title": "Старий Хорон",                   "tags": ["nostalgia"]},
    {"title": "Чорна Береза",                   "tags": ["nostalgia"]},
    {"title": "Гілка Бузку",                    "tags": ["nostalgia"]},
    {"title": "Зацвіли Яблуні",                 "tags": ["nostalgia"]},
    {"title": "Жовті Ліхтарі",                  "tags": ["nostalgia"]},
    {"title": "Тихі кроки",                     "tags": ["nostalgia"]},
    {"title": "Скрипаль",                       "tags": ["nostalgia"]},
    {"title": "Заграй мені трішки",             "tags": ["nostalgia"]},
    {"title": "Тетянин Блюз",                   "tags": ["nostalgia"]},
    {"title": "Подруга стара",                  "tags": ["nostalgia"]},
    {"title": "Піду я до Саду",                 "tags": ["nostalgia"]},
    {"title": "Ой, розлився степ широкий",      "tags": ["nostalgia"]},
    {"title": "Ой, у лузі вітер виє",           "tags": ["nostalgia"]},
    {"title": "Орися (кавер)",                  "tags": ["nostalgia"]},
    {"title": "Ти вже не той",                  "tags": ["nostalgia"]},
    {"title": "Пустка",                         "tags": ["nostalgia"]},
    {"title": "Пустеля Душ",                    "tags": ["nostalgia", "emigrant"]},
    {"title": "У Темряві Серця",                "tags": ["nostalgia"]},
    {"title": "Wings of the Eternal Night",     "tags": ["nostalgia"]},
    {"title": "Ashes Whispering",               "tags": ["nostalgia"]},
    {"title": "Shadows of the Past",            "tags": ["nostalgia"]},
    {"title": "Shadows of Yesterday",           "tags": ["nostalgia"]},
    {"title": "Echoes of the Fallen",           "tags": ["nostalgia"]},
    {"title": "White Dove",                     "tags": ["nostalgia"]},
    {"title": "In Memory Of Diesel",            "tags": ["nostalgia"]},
    {"title": "Only She (Лиш Вона)",            "tags": ["nostalgia"]},
    {"title": "Хіба у тому вся вина",           "tags": ["nostalgia"]},
    {"title": "Емігрант",                       "tags": ["emigrant", "nostalgia"]},
    {"title": "Вигнаний ангел",                 "tags": ["emigrant"]},
    {"title": "Несу",                           "tags": ["emigrant"]},
    {"title": "Подорож Довжиною в Життя",       "tags": ["emigrant"]},
    {"title": "Road Through The Sand",          "tags": ["emigrant"]},
    {"title": "To Bring You Back",              "tags": ["emigrant"]},
    {"title": "Я прийшла щоб торкнутися серця", "tags": ["nostalgia"]},
    {"title": "Крізь тіні і час",               "tags": ["nostalgia"]},
    {"title": "Life (Життя)",                   "tags": ["fire"]},
    {"title": "If You Want",                    "tags": ["fire"]},
    {"title": "Рагга душі Хард",                "tags": ["fire"]},
    {"title": "Різдвяна Рок Опера",             "tags": ["fire"]},
]

MOODS = {
    "nostalgia": "🕯️ Ностальгія / сум за домом",
    "strength":  "🪓 Сила / боротьба",
    "fire":      "🔥 Вогонь / мотивація",
    "emigrant":  "🌲 Еміграція",
}

# ---------------------------------------------------------------------------
# URL-хелпери: повертають або прямий лінк (якщо заданий), або робочий пошук
# ---------------------------------------------------------------------------


def _q(s: str) -> str:
    return urllib.parse.quote_plus(s)


def search_url(platform: str, query: str) -> str:
    """Гарантовано робочий URL пошуку на платформі. Лапки для точного збігу."""
    q = f'"{BAND_NAME}" {query}'
    if platform == "YouTube":
        return f"https://www.youtube.com/results?search_query={_q(q)}"
    if platform == "Spotify":
        return f"https://open.spotify.com/search/{_q(q)}"
    if platform == "Apple Music":
        return f"https://music.apple.com/search?term={_q(q)}"
    if platform == "Bandcamp":
        return f"https://bandcamp.com/search?q={_q(q)}"
    if platform == "Instagram":
        tag = (query or BAND_NAME).replace(" ", "").replace("'", "")
        return f"https://www.instagram.com/explore/tags/{_q(tag)}/"
    return f"https://www.google.com/search?q={_q(q)}"


def band_url(platform: str) -> str:
    """Головна сторінка гурту, або пошук на платформі."""
    direct = BAND_LINKS.get(platform)
    if direct:
        return direct
    return search_url(platform, "")


def track_url(track_title: str, platform: str) -> str:
    """Прямий URL треку, або пошук точно за назвою треку + назвою гурту."""
    direct = (TRACK_LINKS.get(track_title) or {}).get(platform)
    if direct:
        return direct
    return search_url(platform, track_title)


# ---------------------------------------------------------------------------
# Меню
# ---------------------------------------------------------------------------

BTN_TRACKS    = "🎵 Треки та плейлисти"
BTN_RELEASES  = "🔥 Нові релізи"
BTN_LIVE      = "📺 Онлайн-стріми / Live"
BTN_ABOUT     = "🖤 Про гурт"
BTN_SUBSCRIBE = "🔔 Фан-клуб (підписка)"
BTN_FEEDBACK  = "💬 Запитання / Відгуки"
BTN_DONATE    = "🪙 Підтримати копійчиною"

DONATE_URL = "https://paypal.me/Sasha89Alex"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_TRACKS), KeyboardButton(BTN_RELEASES)],
        [KeyboardButton(BTN_LIVE), KeyboardButton(BTN_ABOUT)],
        [KeyboardButton(BTN_SUBSCRIBE), KeyboardButton(BTN_FEEDBACK)],
        [KeyboardButton(BTN_DONATE)],
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


class AIQuotaError(Exception):
    """OpenAI вичерпав квоту/біллінг."""


async def ai_reply(user_message: str, history: list[dict] | None = None) -> str:
    """Запит до OpenAI з фірмовим system prompt. Кидає AIQuotaError при 429."""
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
        msg = str(e)
        if "insufficient_quota" in msg or "429" in msg:
            log.warning("OpenAI quota exhausted: %s", msg[:200])
            raise AIQuotaError(msg) from e
        log.exception("OpenAI error: %s", e)
        return (
            "🦇 Зараз сили темряви блокують зв'язок з оракулом. "
            "Спробуй ще раз за хвилину."
        )


# ---------------------------------------------------------------------------
# Хелпери для історії чату
# ---------------------------------------------------------------------------


def get_history(context: ContextTypes.DEFAULT_TYPE) -> list[dict]:
    return context.user_data.setdefault("history", [])


def push_history(context: ContextTypes.DEFAULT_TYPE, role: str, content: str) -> None:
    hist = get_history(context)
    hist.append({"role": role, "content": content})
    if len(hist) > 16:
        del hist[: len(hist) - 16]


QUOTA_MESSAGE = (
    "🦇 Зараз AI-оракул мовчить — у власника бота закінчилась квота OpenAI.\n"
    "Поповни баланс на https://platform.openai.com/account/billing — "
    "і темна магія повернеться 🔥"
)


def static_mood_playlist(mood_key: str) -> str:
    """Запасний плейлист коли AI недоступний — будуємо з тегів треків."""
    mood_label = MOODS[mood_key]
    picks = [t["title"] for t in TRACKS if mood_key in t["tags"]]
    if not picks:
        picks = [t["title"] for t in TRACKS[:5]]
    lines = [f"🎧 *Плейлист під настрій:* {mood_label}", ""]
    for i, title in enumerate(picks[:6], 1):
        lines.append(f"{i}. *{title}*")
    lines += [
        "",
        "Натисни 🎵 у меню — і відкрий будь-який трек на YouTube / Spotify / Apple Music.",
        "Або 🔔 *Фан-клуб* — щоб не пропустити нові релізи 🖤",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Команди
# ---------------------------------------------------------------------------


def _md_escape(s: str) -> str:
    """Екранує символи Markdown V1 для безпечної підстановки в шаблони."""
    for ch in ("_", "*", "`", "["):
        s = s.replace(ch, "\\" + ch)
    return s


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = _md_escape(user.first_name) if user and user.first_name else "брате"
    text = (
        f"🖤 Вітаю, {name}!\n\n"
        f"Ти потрапив у простір *{BAND_NAME}* — "
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
        "Підпишись 🔔 — і бот сам надішле тобі сповіщення, коли вийде новий реліз."
    )
    buttons = [[InlineKeyboardButton("🔔 Підписатися", callback_data="subscribe")]]
    for name in ("YouTube", "Spotify", "Apple Music", "Bandcamp"):
        buttons.append([InlineKeyboardButton(f"▶️ {name}", url=band_url(name))])
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
        [InlineKeyboardButton("▶️ YouTube", url=band_url("YouTube"))],
        [InlineKeyboardButton("🔔 Підписатися на анонси", callback_data="subscribe")],
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


async def section_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"🖤 *{BAND_NAME}*\n\n"
        "Український онлайн-метал гурт з Монреаля (Квебек, Канада) 🇨🇦🇺🇦\n\n"
        "Жанр: melodic death / atmospheric / folk-metal 🪓🌲\n\n"
        "Теми: еміграція, ностальгія за Україною, пам'ять про загиблих, "
        "сила духу, українська міфологія — Валькірія, Козак, попіл, вогонь 🔥\n\n"
        "Музика народжується дистанційно — у різних кутках світу, але з одним серцем."
    )
    buttons = []
    for name in ("YouTube", "Spotify", "Apple Music", "Bandcamp", "Instagram"):
        buttons.append([InlineKeyboardButton(f"▶️ {name}", url=band_url(name))])
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
    )


def _youtube_subscribe_url() -> str:
    """URL каналу з параметром, що автоматично відкриває діалог підписки."""
    base = BAND_LINKS.get("YouTube") or "https://www.youtube.com/@gathering-of-the-fallen"
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}sub_confirmation=1"


async def section_subscribe(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    is_new = add_subscription(chat_id, user.username if user else None)
    if is_new:
        text = (
            f"🔔 Вітаємо у фан-клубі *{BAND_NAME}*! 🖤🔥\n\n"
            "Бот тепер сам надсилатиме тобі сповіщення про нові релізи та стріми.\n\n"
            "👇 І ще один крок — *підпишись на наш YouTube*, "
            "щоб не пропустити жодного кліпу. Кнопка нижче одразу відкриє "
            "віконце підтвердження підписки 🎬\n\n"
            "Щоб відписатись від бота — /unsubscribe"
        )
    else:
        text = (
            "🖤 Ти вже у фан-клубі бота. Дякуємо, що з нами! 🔥\n\n"
            "Якщо ще не підписаний на YouTube — зроби це одним тапом:"
        )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎬 Підписатись на YouTube",
                               url=_youtube_subscribe_url())]]
    )
    await update.message.reply_text(
        text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN
    )
    # повертаємо нижнє меню окремим коротким повідомленням
    await update.message.reply_text("🪓", reply_markup=MAIN_KEYBOARD)


async def section_donate(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    text = (
        "🪙 *Підтримай нас копійчиною* 🖤🔥\n\n"
        "Кожна копійка йде на репетиції, запис нових треків, "
        "струни, барабанні палички і свічки у студії 🕯️🎸\n\n"
        "Дякуємо, що ти з нами у цій темряві. Без тебе не було б "
        "ні полум'я, ні звуку. 🤘"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💸 Підтримати через PayPal", url=DONATE_URL)]]
    )
    await update.message.reply_text(
        text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text("🖤", reply_markup=MAIN_KEYBOARD)


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

    # Перегляд треку
    if data.startswith("track:"):
        idx = int(data.split(":", 1)[1])
        if not (0 <= idx < len(TRACKS)):
            return
        track = TRACKS[idx]
        title = track["title"]
        moods = ", ".join(MOODS[m].split(" ", 1)[1] for m in track["tags"])
        has_direct = bool((TRACK_LINKS.get(title) or {}))
        hint = "" if has_direct else "\n_(посилання — пошук точно за назвою на платформі)_"
        buttons = [
            [
                InlineKeyboardButton("▶️ YouTube", url=track_url(title, "YouTube")),
                InlineKeyboardButton("🎧 Spotify", url=track_url(title, "Spotify")),
            ],
            [
                InlineKeyboardButton("🍎 Apple Music", url=track_url(title, "Apple Music")),
                InlineKeyboardButton("💬 Лишити відгук", callback_data=f"fb:{idx}"),
            ],
        ]
        await query.message.reply_text(
            f"🎵 *{title}*\n_Настрій: {moods}_ 🔥{hint}",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Меню настроїв
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

    # Конкретний настрій → AI або статичний fallback
    if data.startswith("mood:"):
        mood_key = data.split(":", 1)[1]
        if mood_key not in MOODS:
            return

        # Миттєвий індикатор, щоб юзер бачив що щось відбувається
        loading = await query.message.reply_text(
            f"🕯️ Складаю плейлист під настрій *{MOODS[mood_key]}*...",
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.message.chat.send_action(ChatAction.TYPING)

        track_list = ", ".join(t["title"] for t in TRACKS)
        prompt = (
            f"Склади короткий плейлист (4-6 треків) з наших пісень "
            f"для настрою «{MOODS[mood_key]}». Використай ТІЛЬКИ ці треки "
            f"(без вигаданих): {track_list}. "
            "Для кожного — 1 рядок, чому саме він. "
            "В кінці запропонуй відкрити меню 🎵 щоб послухати, або 🔔 підписатися."
        )

        try:
            reply = await ai_reply(prompt)
        except AIQuotaError:
            reply = static_mood_playlist(mood_key) + "\n\n" + QUOTA_MESSAGE
        except Exception as e:
            log.exception("mood callback ai error: %s", e)
            reply = static_mood_playlist(mood_key)

        try:
            await loading.delete()
        except Exception:
            pass
        # AI-вивід шлемо як plain text, щоб Telegram не падав на парсингу Markdown
        await query.message.reply_text(
            reply,
            reply_markup=MAIN_KEYBOARD,
        )
        return

    # Підписка з inline-кнопки
    if data == "subscribe":
        user = update.effective_user
        is_new = add_subscription(
            update.effective_chat.id, user.username if user else None
        )
        msg = (
            "🔔 Готово! Ти у фан-клубі 🖤🔥\n\n"
            "Підпишись ще й на наш YouTube — один тап:"
            if is_new
            else "🖤 Ти вже з нами. А на YouTube підписаний? 🎬"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🎬 Підписатись на YouTube",
                                   url=_youtube_subscribe_url())]]
        )
        await query.message.reply_text(msg, reply_markup=keyboard)
        return

    # Відгук про конкретний трек
    if data.startswith("fb:"):
        idx = int(data.split(":", 1)[1])
        if not (0 <= idx < len(TRACKS)):
            return
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

    routes = {
        BTN_TRACKS: section_tracks,
        BTN_RELEASES: section_releases,
        BTN_LIVE: section_live,
        BTN_ABOUT: section_about,
        BTN_SUBSCRIBE: section_subscribe,
        BTN_FEEDBACK: section_feedback,
        BTN_DONATE: section_donate,
    }
    if text in routes:
        await routes[text](update, context)
        return

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
    try:
        reply = await ai_reply(text, history)
        push_history(context, "user", text)
        push_history(context, "assistant", reply)
    except AIQuotaError:
        reply = QUOTA_MESSAGE
    # plain text — AI-вивід може містити сирий Markdown, який ламає парсинг
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
    """Heartbeat у лог — щоб контейнер не "засинав"."""
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


async def main() -> None:
    start_keep_alive()
    app = build_app()
    log.info("🔥 Bot is starting (model=%s)...", OPENAI_MODEL)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("👋 Bot stopped.")
    except Exception as e:
        log.exception("💀 Fatal: %s", e)
        raise
