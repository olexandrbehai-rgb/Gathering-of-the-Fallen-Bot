import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import type { Server } from "node:http";
import { after, before, test } from "node:test";
import type { AddressInfo } from "node:net";
import { eq } from "drizzle-orm";

const TEST_TELEGRAM_ID = 8_765_432_101;
const BOT_TOKEN = "integration-test-bot-token";
const SESSION_SECRET = "integration-test-session-secret-with-sufficient-entropy";
const originalFetch = globalThis.fetch;

let server: Server;
let origin: string;
let sessionCookie = "";
let dbModule: typeof import("@workspace/db");

function createInitData(authDate: number): string {
  const params = new URLSearchParams({
    auth_date: String(authDate),
    query_id: "integration-test-query",
    user: JSON.stringify({
      id: TEST_TELEGRAM_ID,
      first_name: "Integration",
      last_name: "Fan",
      username: "integration_fan",
    }),
  });
  const dataCheckString = [...params.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");
  const secret = createHmac("sha256", "WebAppData").update(BOT_TOKEN).digest();
  params.set(
    "hash",
    createHmac("sha256", secret).update(dataCheckString).digest("hex"),
  );
  return params.toString();
}

function createSessionCookie(expiresAt: number): string {
  const payload = Buffer.from(
    JSON.stringify({
      id: TEST_TELEGRAM_ID,
      displayName: "Integration Fan",
      username: "integration_fan",
      avatarUrl: null,
      isAdmin: false,
      expiresAt,
    }),
  ).toString("base64url");
  const signature = createHmac("sha256", SESSION_SECRET)
    .update(payload)
    .digest("base64url");
  return `fallen_session=${payload}.${signature}`;
}

async function request(
  path: string,
  init: RequestInit = {},
  cookie: string | boolean = false,
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("content-type", "application/json");
  if (cookie) headers.set("cookie", typeof cookie === "string" ? cookie : sessionCookie);
  return originalFetch(`${origin}${path}`, { ...init, headers });
}

before(async () => {
  process.env.NODE_ENV = "production";
  process.env.TELEGRAM_TOKEN = BOT_TOKEN;
  process.env.SESSION_SECRET = SESSION_SECRET;
  process.env.OPENAI_API_KEY = "integration-test-openai-key";

  const [{ default: app }, database] = await Promise.all([
    import("../app"),
    import("@workspace/db"),
  ]);
  dbModule = database;
  server = app.listen(0);
  await new Promise<void>((resolve, reject) => {
    server.once("listening", resolve);
    server.once("error", reject);
  });
  const address = server.address() as AddressInfo;
  origin = `http://127.0.0.1:${address.port}`;
});

after(async () => {
  if (dbModule) {
    await dbModule.db
      .delete(dbModule.fallenFanPostsTable)
      .where(eq(dbModule.fallenFanPostsTable.telegramId, TEST_TELEGRAM_ID));
    await dbModule.db
      .delete(dbModule.fallenAiUsageTable)
      .where(eq(dbModule.fallenAiUsageTable.telegramId, TEST_TELEGRAM_ID));
    await dbModule.db
      .delete(dbModule.fallenUsersTable)
      .where(eq(dbModule.fallenUsersTable.telegramId, TEST_TELEGRAM_ID));
    await dbModule.pool.end();
  }
  if (server) {
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
  globalThis.fetch = originalFetch;
});

test("rejects unauthenticated and expired Telegram requests", async () => {
  const withoutSession = await request("/api/me");
  assert.equal(withoutSession.status, 401);

  const expired = await request("/api/auth/telegram", {
    method: "POST",
    body: JSON.stringify({
      initData: createInitData(Math.floor(Date.now() / 1000) - 3_601),
    }),
  });
  assert.equal(expired.status, 401);
  assert.equal(expired.headers.get("set-cookie"), null);
});

test("rejects a tampered session on every protected fan route", async () => {
  const validCookie = createSessionCookie(Date.now() + 60_000);
  const tamperedCookie = `${validCookie.slice(0, -1)}${validCookie.endsWith("a") ? "b" : "a"}`;

  const responses = await Promise.all([
    request("/api/me", {}, tamperedCookie),
    request(
      "/api/subscription",
      { method: "POST", body: JSON.stringify({ subscribed: true }) },
      tamperedCookie,
    ),
    request(
      "/api/fan-feed",
      { method: "POST", body: JSON.stringify({ message: "Tampered session post" }) },
      tamperedCookie,
    ),
  ]);

  assert.deepEqual(responses.map(({ status }) => status), [401, 401, 401]);
});

test("rejects an expired correctly signed session", async () => {
  const expiredCookie = createSessionCookie(Date.now() - 1);
  const profile = await request("/api/me", {}, expiredCookie);

  assert.equal(profile.status, 401);
});

test("keeps profile, subscription, fan wall, and AI available through one same-origin session", async () => {
  const authenticated = await request("/api/auth/telegram", {
    method: "POST",
    body: JSON.stringify({
      initData: createInitData(Math.floor(Date.now() / 1000)),
    }),
  });
  assert.equal(authenticated.status, 200);
  const setCookie = authenticated.headers.get("set-cookie");
  if (!setCookie) assert.fail("Authentication did not set a session cookie");
  assert.ok(setCookie.startsWith("fallen_session="));
  assert.match(setCookie, /HttpOnly/i);
  assert.match(setCookie, /SameSite=Strict/i);
  assert.match(setCookie, /Secure/i);
  assert.match(setCookie, /Path=\//i);
  sessionCookie = setCookie.split(";", 1)[0];

  const profile = await request("/api/me", {}, true);
  assert.equal(profile.status, 200);
  assert.deepEqual(
    await profile.json(),
    {
      id: String(TEST_TELEGRAM_ID),
      displayName: "Integration Fan",
      username: "integration_fan",
      avatarUrl: null,
      isAdmin: false,
      subscribed: false,
    },
  );

  const subscription = await request(
    "/api/subscription",
    { method: "POST", body: JSON.stringify({ subscribed: true }) },
    true,
  );
  assert.equal(subscription.status, 200);
  assert.deepEqual(await subscription.json(), { subscribed: true });

  const postMessage = `Integration fan post ${Date.now()}`;
  const post = await request(
    "/api/fan-feed",
    { method: "POST", body: JSON.stringify({ message: postMessage }) },
    true,
  );
  assert.equal(post.status, 201);
  const createdPost = await post.json() as { id: number; message: string };
  assert.equal(createdPost.message, postMessage);

  for (let index = 2; index <= 3; index += 1) {
    const allowedPost = await request(
      "/api/fan-feed",
      { method: "POST", body: JSON.stringify({ message: `${postMessage} ${index}` }) },
      true,
    );
    assert.equal(allowedPost.status, 201);
  }
  const rateLimitedPost = await request(
    "/api/fan-feed",
    { method: "POST", body: JSON.stringify({ message: `${postMessage} 4` }) },
    true,
  );
  assert.equal(rateLimitedPost.status, 429);
  assert.match(
    (await rateLimitedPost.json() as { error: string }).error,
    /Забагато дописів/,
  );
  assert.ok(Number(rateLimitedPost.headers.get("retry-after")) > 0);

  const forbiddenHide = await request(
    `/api/fan-feed/${createdPost.id}/hide`,
    { method: "POST" },
    true,
  );
  assert.equal(forbiddenHide.status, 403);

  globalThis.fetch = async (input, init) => {
    if (String(input) === "https://api.openai.com/v1/chat/completions") {
      assert.equal(init?.method, "POST");
      return Response.json({
        choices: [{ message: { content: "Тестова відповідь оракула" } }],
        usage: { prompt_tokens: 12, completion_tokens: 6 },
      });
    }
    return originalFetch(input, init);
  };
  const assistant = await request(
    "/api/assistant",
    { method: "POST", body: JSON.stringify({ message: "Порадь трек" }) },
    true,
  );
  assert.equal(assistant.status, 200);
  assert.equal(
    (await assistant.json() as { reply: string }).reply,
    "Тестова відповідь оракула",
  );

  const refreshedProfile = await request("/api/me", {}, true);
  assert.equal(refreshedProfile.status, 200);
  assert.equal(
    (await refreshedProfile.json() as { subscribed: boolean }).subscribed,
    true,
  );
});