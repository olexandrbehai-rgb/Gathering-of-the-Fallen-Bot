# Деплой бота на Render (безкоштовно, 24/7)

## Що зроблено в репо

- `requirements.txt` — Python-залежності для Render
- `render.yaml` — конфіг Render Blueprint (тип `worker`, без HTTP-порта)
- Постійний диск 1 GB змонтований у `data/` — підписки і відгуки переживуть рестарти

## Покрокова інструкція

### 1. Залий код на GitHub

Якщо ще не зробив:

1. Створи новий приватний репозиторій на github.com
2. У Replit Shell:
   ```bash
   git remote add origin https://github.com/<твій-юзер>/<репо>.git
   git push -u origin main
   ```
   (якщо `origin` уже є — `git remote set-url origin <URL>`)

### 2. Створи акаунт на Render

1. Перейди на https://render.com → **Get Started for Free**
2. Зареєструйся через GitHub (найшвидше)

### 3. Створи сервіс через Blueprint

1. У Render Dashboard → **New +** → **Blueprint**
2. Підключи свій GitHub-репозиторій
3. Render автоматично знайде `render.yaml` і запропонує створити worker
4. Натисни **Apply**

### 4. Вкажи секрети

Render запитає значення для двох змінних (бо в `render.yaml` стоїть `sync: false`):

- **TELEGRAM_TOKEN** — твій токен з @BotFather
- **OPENAI_API_KEY** — твій ключ OpenAI

Збережи. Деплой запуститься автоматично.

### 5. ⚠️ ВАЖЛИВО: вимкни бота в Replit

Telegram дозволяє тільки **один** інстанс на polling. Перед запуском Render-деплою зупини workflow `Telegram Bot` тут, у Replit:

- Скажи мені "зупини бота в Replit" — я це зроблю
- Або сам натисни Stop у workflow `Telegram Bot`

Інакше Render-бот видасть `Conflict: terminated by other getUpdates request`.

### 6. Перевір

- У Render Dashboard → твій сервіс → вкладка **Logs**
- Має з'явитися: `🔥 Bot is starting (model=gpt-4o-mini)...`
- Напиши боту в Telegram `/start` — має відповісти

## Особливості Render Free Tier

- **750 годин/міс безкоштовно** — на один worker вистачає з головою (24/7 = ~720 год)
- **Disk 1 GB** — у Free tier диски доступні, дані `data/*.json` зберігаються
- **Регіон Frankfurt** — найближче до України; можеш змінити на `oregon` / `ohio` у `render.yaml`

## Подальші оновлення

Будь-який `git push` у main гілку → Render автоматично передеплоїть бота.
