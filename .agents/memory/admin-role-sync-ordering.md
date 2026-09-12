---
name: Admin role synchronization ordering
description: Safety rule for synchronizing delegated admin grants and revocations across the bot and Mini App stores.
---

Role operations shared by the bot and Mini App must be durable, idempotent, and ordered per target. Revocation is not complete until the Mini App authorization store confirms it; only then should the bot finalize its local revocation and audit.

**Why:** Finalizing the bot first can leave an already-open Mini App session authorized during a network failure. Finalizing the Mini App first fails closed, while a durable outbox and version guard safely complete the bot side after retries.

**How to apply:** For any future cross-store role change, persist a unique operation and monotonic target version, reject stale replays, and never report revocation success before the authorization store used on each web request has committed it.