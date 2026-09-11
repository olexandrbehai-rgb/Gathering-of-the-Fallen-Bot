# Gathering Of The Fallen — Telegram Bot

Telegram-бот українського онлайн-метал гурту "Gathering Of The Fallen" (Монреаль, Квебек).
Атмосферний AI-асистент: треки, плейлисти за настроєм, релізи, live-стріми, підписка та відгуки.

## Run & Operate

- Production: Render worker запускає `python main.py` (polling, один інстанс).
- Required secrets: `TELEGRAM_TOKEN`, `OPENAI_API_KEY`, `ADMIN_CHAT_ID`.
- Optional env: `OPENAI_MODEL`, `OPENAI_TRANSCRIBE_MODEL`, `BAND_SITE_URL`,
  `AI_COOLDOWN_SECONDS`, `MAX_MESSAGE_CHARS`, `MAX_FAN_MESSAGE_CHARS`.

## Stack

- Python 3.11
- `python-telegram-bot` 21.x (async, polling)
- `openai` SDK (Chat Completions + function tools + transcription)
- SQLite: `data/gathering.sqlite3`; старі JSON-файли мігруються автоматично.

## Where things live

- `main.py` — handlers, AI tools, адмін-команди, розсилки та сховище.
- `data/` — SQLite-база на persistent disk Render.

## Architecture decisions

- Один Python-процес polling; горизонтальне масштабування вимкнене, щоб не було
  Telegram `Conflict`.
- AI використовує перевірені інструменти для треків, посилань, релізів і підписки.
- Історія AI, фан-чат, підписки, релізи та відгуки зберігаються в SQLite.
- Старі JSON-дані імпортуються без втрат при першому старті.

## Product

Користувачі: `/start`, `/help`, `/about`, `/tracks`, `/search`, `/subscribe`,
`/unsubscribe`, `/feedback`, `/fanclub`, `/resetai`, `/privacy`.
Адмін: `/admin`, `/stats`, `/broadcast`, `/release`, `/hidepost`.
Текст або голосове повідомлення → AI-відповідь у фірмовому темному метал-стилі.

## User preferences

- Мова інтерфейсу: українська.
- Стиль: темний, емоційний, метал-естетика, з емодзі 🎸🔥🪓🕯️🦇🖤🌲.

## Gotchas

- Після зміни змінних у Render — перезапустити production worker.
- У Telegram має бути активним тільки один інстанс бота, інакше polling видасть `Conflict`.
- `data/` має бути змонтована як persistent disk у Render.
