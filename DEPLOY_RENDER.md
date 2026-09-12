# Деплой бота і Telegram Mini App на Render

## Що зроблено в репо

- `requirements.txt` — Python-залежності для Render
- `render.yaml` — Blueprint із двома незалежними сервісами:
  - `web` обслуговує Mini App та API на одному домені;
  - `worker` запускає наявного polling-бота й не замінюється вебсервісом.
- PostgreSQL створюється Blueprint-ом, а схема застосовується командою `preDeployCommand` до запуску API.
- Постійний диск 1 GB змонтований у `data/` — підписки і відгуки переживуть рестарти

> Web service, worker, PostgreSQL і постійний диск використовують платні Render-плани. Це потрібно для `preDeployCommand`, безперервного polling та збереження даних; конфіг не заявляє несумісні безкоштовні ресурси.

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
3. Render автоматично знайде `render.yaml` і запропонує створити web service та worker
4. Натисни **Apply**

### 4. Вкажи секрети

Render запитає секрети та адреси для сервісів:

- **TELEGRAM_TOKEN** — твій токен з @BotFather
- **OPENAI_API_KEY** — твій ключ OpenAI
- **ADMIN_CHAT_ID** — Telegram ID адміністратора
- **SESSION_SECRET** — довгий випадковий рядок для підпису сесій Mini App
- **BAND_SITE_URL** — публічна HTTPS-адреса web service або власного домену, наприклад `https://fallen.example.com/`

`TELEGRAM_TOKEN` має бути однаковим для web service і worker: крім Telegram-входу,
він підписує службову синхронізацію ролей адміністраторів між ботом і Mini App.

`DATABASE_URL` Render підставить автоматично зі створеної бази. Збережи решту значень — деплой запуститься автоматично.

### 5. Налаштуй адресу Mini App

1. Відкрий створений web service у Render і скопіюй його HTTPS URL.
2. Запиши цей URL зі слешем наприкінці в `BAND_SITE_URL` worker-сервісу.
3. Для власного домену: **Settings → Custom Domains → Add Custom Domain**, додай DNS-записи, які покаже Render, і після випуску TLS-сертифіката заміни `BAND_SITE_URL` на власний HTTPS-домен.
4. Перезапусти worker. Кнопка **«Відкрити Mini App»** у меню бота відкриватиме нову адресу.

### 6. ⚠️ ВАЖЛИВО: не запускай два polling-боти

Telegram дозволяє тільки **один** інстанс на polling. Перед запуском Render-деплою зупини workflow `Telegram Bot` тут, у Replit:

- Скажи мені "зупини бота в Replit" — я це зроблю
- Або сам натисни Stop у workflow `Telegram Bot`

Інакше Render-бот видасть `Conflict: terminated by other getUpdates request`.

### 7. Перевір

- У Render Dashboard → web service → **Logs**: API має слухати виданий Render порт.
- Відкрий `https://<твій-домен>/api/healthz` — має повернути `{"status":"ok"}`.
- У Render Dashboard → worker → **Logs**
- Має з'явитися: `🔥 Bot is starting (model=gpt-4o-mini)...`
- Напиши боту `/start`, відкрий меню та натисни **«Відкрити Mini App»**.

## Ресурси

- **Worker Starter** — постійно тримає Telegram polling.
- **Web Service Starter** — підтримує `preDeployCommand`, яка створює та оновлює таблиці до запуску нової версії API.
- **PostgreSQL Basic** — зберігає користувачів, сесії взаємодії, фан-стіну та статистику.
- **Disk 1 GB** — зберігає наявні `data/*.json` polling-бота між рестартами.
- **Регіон Frankfurt** — найближчий до України з указаних у конфігурації.

## Подальші оновлення

Будь-який `git push` у main гілку → Render автоматично передеплоїть бота.
