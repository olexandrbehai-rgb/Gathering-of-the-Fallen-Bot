# Gathering Of The Fallen — Telegram Bot + Mini App

Telegram-бот українського онлайн-метал гурту "Gathering Of The Fallen" (Монреаль, Квебек).
Атмосферний AI-асистент і Telegram Mini App: актуальні треки та кліпи, плейлисти за настроєм, релізи, фан-простір, підписка та відгуки.

## Run & Operate

- Production: Render worker запускає `python main.py` (polling, один інстанс).
- Mini App/API: окремі Replit artifacts `fallen-mini-app` та `api-server`.
- Required secrets: `TELEGRAM_TOKEN`, `OPENAI_API_KEY`, `ADMIN_CHAT_ID`.
- Optional env: `OPENAI_MODEL`, `OPENAI_TRANSCRIBE_MODEL`, `BAND_SITE_URL`,
  `AI_COOLDOWN_SECONDS`, `MAX_MESSAGE_CHARS`, `MAX_FAN_MESSAGE_CHARS`.

## Stack

- Python 3.11
- `python-telegram-bot` 21.x (async, polling)
- `openai` SDK (Chat Completions + function tools + transcription)
- SQLite: `data/gathering.sqlite3`; старі JSON-файли мігруються автоматично.
- Mini App: React/Vite + generated OpenAPI client; API: Express + PostgreSQL.

## Where things live

- `main.py` — handlers, AI tools, адмін-команди, розсилки та сховище.
- `data/` — SQLite-база на persistent disk Render.
- `artifacts/fallen-mini-app/` — Telegram Mini App.
- `artifacts/api-server/` — API, Telegram WebApp auth і usage ledger.
- `lib/api-spec/openapi.yaml` — канонічний контракт Mini App API.

## Architecture decisions

- Один Python-процес polling; горизонтальне масштабування вимкнене, щоб не було
  Telegram `Conflict`.
- AI використовує перевірені інструменти для треків, посилань, релізів і підписки.
- Історія AI, фан-чат, підписки, релізи та відгуки зберігаються в SQLite.
- Старі JSON-дані імпортуються без втрат при першому старті.
- Telegram Mini App перевіряє підписаний `initData`; preview identity дозволена лише в development.
- Офіційний YouTube: `https://www.youtube.com/@gathering_of_the_fallen`.

## Product

Користувачі: `/start`, `/help`, `/about`, `/tracks`, `/clips`, `/search`, `/subscribe`,
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
