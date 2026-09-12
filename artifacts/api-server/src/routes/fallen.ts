import { Router, type IRouter, type Request, type Response } from "express";
import { and, count, desc, eq, gte } from "drizzle-orm";
import {
  db,
  fallenAiUsageTable,
  fallenFanPostsTable,
  fallenUsersTable,
} from "@workspace/db";
import {
  AskAssistantBody,
  AskAssistantResponse,
  AuthenticateTelegramBody,
  AuthenticateTelegramResponse,
  CreateFanPostBody,
  GetExperienceResponse,
  GetMeResponse,
  GetUsageSummaryResponse,
  HideFanPostResponse,
  ListFanPostsResponse,
  ListReleasesResponse,
  ListTracksQueryParams,
  ListTracksResponse,
  ListVideosResponse,
  UpdateSubscriptionBody,
  UpdateSubscriptionResponse,
} from "@workspace/api-zod";
import { getSession, setSession, verifyTelegramInitData } from "../lib/telegram-auth";
import { releases, tracks, videos } from "../lib/fallen-catalog";

const router: IRouter = Router();
const FAN_POST_LIMIT = 3;
const FAN_POST_WINDOW_MS = 10 * 60 * 1000;

function identityOr401(req: Request, res: Response) {
  const identity = getSession(req);
  if (!identity) {
    res.status(401).json({ error: "Open this experience from the Telegram bot." });
    return null;
  }
  return identity;
}

function normalize(value: string): string {
  return value
    .toLocaleLowerCase("uk-UA")
    .replace(/[’ʼ`]/g, "'")
    .trim();
}

router.get("/experience", async (_req, res): Promise<void> => {
  const [{ value: communityCount = 0 } = {}] = await db
    .select({ value: count() })
    .from(fallenUsersTable);
  res.json(
    GetExperienceResponse.parse({
      featured: tracks[6],
      recentReleases: releases,
      moods: ["fire", "strength", "nostalgia", "emigrant"],
      communityCount: Number(communityCount) || 0,
      trackCount: tracks.length,
    }),
  );
});

router.get("/tracks", (req, res): void => {
  const parsed = ListTracksQueryParams.safeParse(req.query);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const query = normalize(parsed.data.query ?? "");
  const mood = normalize(parsed.data.mood ?? "");
  const result = tracks.filter(
    (track) =>
      (!query || normalize(track.title).includes(query)) &&
      (!mood || track.moods.includes(mood as never)),
  );
  res.json(ListTracksResponse.parse(result));
});

router.get("/releases", (_req, res): void => {
  res.json(ListReleasesResponse.parse(releases));
});

router.get("/videos", (_req, res): void => {
  res.json(ListVideosResponse.parse(videos));
});

router.post("/auth/telegram", async (req, res): Promise<void> => {
  const parsed = AuthenticateTelegramBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  try {
    const identity = verifyTelegramInitData(parsed.data.initData);
    const [user] = await db
      .insert(fallenUsersTable)
      .values({
        telegramId: identity.id,
        displayName: identity.displayName,
        username: identity.username,
        avatarUrl: identity.avatarUrl,
        isAdmin: identity.isAdmin,
      })
      .onConflictDoUpdate({
        target: fallenUsersTable.telegramId,
        set: {
          displayName: identity.displayName,
          username: identity.username,
          avatarUrl: identity.avatarUrl,
          isAdmin: identity.isAdmin,
          updatedAt: new Date(),
        },
      })
      .returning();
    setSession(res, identity);
    res.json(
      AuthenticateTelegramResponse.parse({
        id: String(identity.id),
        displayName: identity.displayName,
        username: identity.username,
        avatarUrl: identity.avatarUrl,
        isAdmin: identity.isAdmin,
        subscribed: user?.subscribed ?? false,
      }),
    );
  } catch (error) {
    req.log.warn({ err: error }, "Telegram Mini App authentication rejected");
    res.status(401).json({ error: "Telegram authentication failed." });
  }
});

router.get("/me", async (req, res): Promise<void> => {
  const identity = identityOr401(req, res);
  if (!identity) return;
  const [user] = await db
    .select()
    .from(fallenUsersTable)
    .where(eq(fallenUsersTable.telegramId, identity.id))
    .limit(1);
  res.json(
    GetMeResponse.parse({
      id: String(identity.id),
      displayName: identity.displayName,
      username: identity.username,
      avatarUrl: identity.avatarUrl,
      isAdmin: identity.isAdmin,
      subscribed: user?.subscribed ?? false,
    }),
  );
});

router.post("/subscription", async (req, res): Promise<void> => {
  const identity = identityOr401(req, res);
  if (!identity) return;
  const parsed = UpdateSubscriptionBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  await db
    .insert(fallenUsersTable)
    .values({
      telegramId: identity.id,
      displayName: identity.displayName,
      username: identity.username,
      avatarUrl: identity.avatarUrl,
      isAdmin: identity.isAdmin,
      subscribed: parsed.data.subscribed,
    })
    .onConflictDoUpdate({
      target: fallenUsersTable.telegramId,
      set: { subscribed: parsed.data.subscribed, updatedAt: new Date() },
    });
  res.json(UpdateSubscriptionResponse.parse(parsed.data));
});

router.get("/fan-feed", async (_req, res): Promise<void> => {
  const posts = await db
    .select()
    .from(fallenFanPostsTable)
    .where(eq(fallenFanPostsTable.hidden, false))
    .orderBy(desc(fallenFanPostsTable.createdAt))
    .limit(50);
  res.json(
    ListFanPostsResponse.parse(
      posts.map((post) => ({
        id: post.id,
        author: post.author,
        message: post.message,
        createdAt: post.createdAt.toISOString(),
      })),
    ),
  );
});

router.post("/fan-feed", async (req, res): Promise<void> => {
  const identity = identityOr401(req, res);
  if (!identity) return;
  const parsed = CreateFanPostBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const message = parsed.data.message.trim();
  if (/https?:\/\/|t\.me\/|@\w{3,}/i.test(message)) {
    res.status(400).json({ error: "Посилання та небажані згадки у фан-стіні заборонені." });
    return;
  }
  const windowStart = new Date(Date.now() - FAN_POST_WINDOW_MS);
  const recentPosts = await db
    .select({ createdAt: fallenFanPostsTable.createdAt })
    .from(fallenFanPostsTable)
    .where(
      and(
        eq(fallenFanPostsTable.telegramId, identity.id),
        gte(fallenFanPostsTable.createdAt, windowStart),
      ),
    )
    .orderBy(desc(fallenFanPostsTable.createdAt))
    .limit(FAN_POST_LIMIT);
  if (recentPosts.length >= FAN_POST_LIMIT) {
    const retryAt = recentPosts[recentPosts.length - 1]!.createdAt.getTime() + FAN_POST_WINDOW_MS;
    const retryAfterSeconds = Math.max(1, Math.ceil((retryAt - Date.now()) / 1000));
    res.setHeader("Retry-After", String(retryAfterSeconds));
    res.status(429).json({
      error: `Забагато дописів. Спробуйте знову приблизно через ${Math.ceil(retryAfterSeconds / 60)} хв.`,
    });
    return;
  }
  const [post] = await db
    .insert(fallenFanPostsTable)
    .values({
      telegramId: identity.id,
      author: identity.displayName,
      message,
    })
    .returning();
  res.status(201).json(
    ListFanPostsResponse.element.parse({
      id: post.id,
      author: post.author,
      message: post.message,
      createdAt: post.createdAt.toISOString(),
    }),
  );
});

router.post("/fan-feed/:id/hide", async (req, res): Promise<void> => {
  const identity = identityOr401(req, res);
  if (!identity) return;
  if (!identity.isAdmin) {
    res.status(403).json({ error: "Лише адміністратор може приховувати дописи." });
    return;
  }
  const id = Number(req.params.id);
  if (!Number.isSafeInteger(id) || id <= 0) {
    res.status(404).json({ error: "Допис не знайдено." });
    return;
  }
  const [post] = await db
    .update(fallenFanPostsTable)
    .set({ hidden: true })
    .where(eq(fallenFanPostsTable.id, id))
    .returning({ id: fallenFanPostsTable.id });
  if (!post) {
    res.status(404).json({ error: "Допис не знайдено." });
    return;
  }
  res.json(HideFanPostResponse.parse({ id: post.id, hidden: true }));
});

router.post("/assistant", async (req, res): Promise<void> => {
  const identity = identityOr401(req, res);
  if (!identity) return;
  const parsed = AskAssistantBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    res.status(503).json({ error: "AI oracle is not configured." });
    return;
  }
  const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const recent = await db
    .select({ id: fallenAiUsageTable.id })
    .from(fallenAiUsageTable)
    .where(
      and(
        eq(fallenAiUsageTable.telegramId, identity.id),
        gte(fallenAiUsageTable.createdAt, dayAgo),
      ),
    )
    .limit(31);
  if (recent.length >= 30) {
    res.status(429).json({ error: "Daily oracle limit reached. Return tomorrow." });
    return;
  }

  const started = Date.now();
  const model = process.env.OPENAI_MODEL ?? "gpt-4o-mini";
  try {
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        authorization: `Bearer ${apiKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model,
        temperature: 0.7,
        max_tokens: 500,
        messages: [
          {
            role: "system",
            content:
              "Ти — офіційний AI-голос українського метал-гурту Gathering Of The Fallen. " +
              "Відповідай українською, тепло, змістовно і стисло. Не вигадуй факти чи посилання. " +
              `Каталог містить: ${tracks.map((track) => track.title).join(", ")}.`,
          },
          { role: "user", content: parsed.data.message },
        ],
      }),
      signal: AbortSignal.timeout(25_000),
    });
    if (!response.ok) throw new Error(`OpenAI ${response.status}`);
    const data = (await response.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
      usage?: { prompt_tokens?: number; completion_tokens?: number };
    };
    const reply = data.choices?.[0]?.message?.content?.trim();
    if (!reply) throw new Error("OpenAI returned no content");
    const input = data.usage?.prompt_tokens ?? 0;
    const output = data.usage?.completion_tokens ?? 0;
    await db.insert(fallenAiUsageTable).values({
      telegramId: identity.id,
      feature: "miniapp_chat",
      model,
      inputUnits: input,
      outputUnits: output,
      estimatedCostMicrousd: Math.round(input * 0.15 + output * 0.6),
      status: "success",
      latencyMs: Date.now() - started,
    });
    res.json(
      AskAssistantResponse.parse({
        reply,
        suggestions: ["Порадь трек під мій настрій", "Розкажи про Music Of My Soul"],
      }),
    );
  } catch (error) {
    req.log.error({ err: error, feature: "miniapp_chat" }, "AI request failed");
    await db.insert(fallenAiUsageTable).values({
      telegramId: identity.id,
      feature: "miniapp_chat",
      model,
      status: "error",
      latencyMs: Date.now() - started,
    });
    res.status(502).json({ error: "The oracle is temporarily silent." });
  }
});

router.get("/usage/summary", async (req, res): Promise<void> => {
  const identity = identityOr401(req, res);
  if (!identity) return;
  if (!identity.isAdmin) {
    res.status(403).json({ error: "Admin access required." });
    return;
  }
  const now = new Date();
  const monthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const dayStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const rows = await db
    .select()
    .from(fallenAiUsageTable)
    .where(gte(fallenAiUsageTable.createdAt, monthStart));
  const errors = rows.filter((row) => row.status !== "success").length;
  res.json(
    GetUsageSummaryResponse.parse({
      todayRequests: rows.filter((row) => row.createdAt >= dayStart).length,
      monthRequests: rows.length,
      monthEstimatedUsd:
        rows.reduce((sum, row) => sum + row.estimatedCostMicrousd, 0) / 1_000_000,
      voiceSeconds: rows.reduce((sum, row) => sum + row.audioSeconds, 0),
      errorRate: rows.length ? errors / rows.length : 0,
    }),
  );
});

export default router;