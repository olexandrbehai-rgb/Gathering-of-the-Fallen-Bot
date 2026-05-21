# Gathering Of The Fallen — Telegram Bot

Telegram-бот українського онлайн-метал гурту "Gathering Of The Fallen" (Монреаль, Квебек).
Атмосферний AI-асистент: треки, плейлисти за настроєм, релізи, live-стріми, підписка та відгуки.

## Run & Operate

- Workflow `Telegram Bot` — запускає `python3 main.py` (працює 24/7, polling)
- Required secrets: `TELEGRAM_TOKEN`, `OPENAI_API_KEY`
- Optional env: `OPENAI_MODEL` (за замовчуванням `gpt-4o-mini`)

## Stack

- Python 3.11
- `python-telegram-bot` 21.x (async, polling)
- `openai` SDK (Chat Completions)
- JSON-сховище: `data/subscriptions.json`, `data/feedback.json`

## Where things live

- `main.py` — увесь бот (handlers, OpenAI, сховище, keep-alive)
- `data/` — підписки та відгуки (створюється автоматично)

## Architecture decisions

- Один файл `main.py` — за специфікацією користувача.
- Polling замість webhooks — простіше і стабільніше у Replit-середовищі.
- Keep-alive — окремий daemon-thread з heartbeat у лог кожні 5 хв.
- Історія діалогу зберігається у `context.user_data` (останні 16 повідомлень).

## Product

Команди: `/start`, `/help`, `/about`, `/tracks`, `/subscribe`, `/unsubscribe`, `/feedback`.
Постійне нижнє меню: 🎵 Треки / 🔥 Релізи / 📺 Live / 🖤 Про гурт / 🔔 Підписка / 💬 Відгуки.
Будь-яке інше повідомлення → AI-відповідь у фірмовому темному метал-стилі.

## User preferences

- Мова інтерфейсу: українська.
- Стиль: темний, емоційний, метал-естетика, з емодзі 🎸🔥🪓🕯️🦇🖤🌲.

## Gotchas

- Після зміни секретів — обов'язково перезапустити workflow `Telegram Bot`.
- У Telegram має бути активним тільки один інстанс бота, інакше polling видасть `Conflict`.
