---
name: Render pnpm version
description: Render's Corepack cache can point at an unavailable pnpm release when the workspace does not pin its package manager.
---

Pin the workspace package manager version in `package.json` and explicitly prepare that version in the Render Node build command.

**Why:** Render may otherwise select a newer pnpm release whose cached `pnpm.cjs` path is missing, failing the build before dependencies are installed.

**How to apply:** Keep the package-manager version aligned with the lockfile and use the same pinned version for root install and workspace build commands.