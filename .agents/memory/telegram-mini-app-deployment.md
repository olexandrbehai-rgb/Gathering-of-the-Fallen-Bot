---
name: Telegram Mini App deployment
description: Deployment boundary between the Telegram worker keyboard and the Render Mini App.
---

The Telegram worker embeds the Mini App URL into serialized reply-keyboard buttons, while the Mini App itself is served by a separate Render web service. Updating only the web service does not update buttons already sent by the worker.

**Why:** A user can open an older URL from a persistent Telegram keyboard and see a valid web page without Telegram `initData`, even while the current Render site and API are healthy.

**How to apply:** After changing `BAND_SITE_URL` or the Mini App launch flow, deploy both Render services as needed, then send `/start` to issue a fresh keyboard. Test the app from that Telegram button rather than from a normal browser tab.