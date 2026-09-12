---
name: Telegram Mini App deployment
description: Deployment boundary between the Telegram worker keyboard and the Render Mini App.
---

The Telegram worker embeds the Mini App URL into serialized reply-keyboard buttons, while the Mini App itself is served by a separate Render web service. Updating only the web service does not update buttons already sent by the worker.

Telegram Mini Apps that require authenticated `initData` must launch from an inline `web_app` button or another full WebView launch surface. A reply-keyboard `KeyboardButton.web_app` opens a SimpleWebView that may omit user information.

**Why:** A user can open a healthy Mini App from a persistent reply keyboard and still receive no Telegram `initData`; retrying or delaying frontend initialization cannot create identity data that the launch surface never provided.

**How to apply:** Keep authenticated Mini App launch buttons inline. After changing `BAND_SITE_URL` or the launch flow, deploy both Render services as needed, then send `/start` to replace stale reply keyboards. Test using the inline button under the bot message.