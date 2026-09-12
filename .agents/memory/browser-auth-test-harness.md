---
name: Browser auth test harness
description: Durable constraints for browser-level auth tests in the Mini App workspace
---

Production-like browser tests should hold the initial identity response until the test has installed its Telegram WebApp fixture. This avoids racing the app's initial auth effect and makes the test cover delayed SDK initialization rather than accidentally falling into the missing-data branch.

**Why:** The app deliberately waits for Telegram SDK data while the initial identity query is pending, and test-runner-transformed functions passed to browser evaluation can reference unavailable bundler helpers.

**How to apply:** Use a controlled server gate for the first identity response, inject the fixture after the page is loaded, and prefer string browser evaluation when the test file is executed through tsx.