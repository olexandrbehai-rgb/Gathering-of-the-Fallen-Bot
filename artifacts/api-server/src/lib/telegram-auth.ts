import { createHmac, timingSafeEqual } from "node:crypto";
import type { Request, Response } from "express";

export type SessionIdentity = {
  id: number;
  displayName: string;
  username: string;
  avatarUrl: string | null;
  isAdmin: boolean;
  expiresAt?: number;
};

const encode = (value: string) => Buffer.from(value).toString("base64url");
const sign = (value: string) =>
  createHmac("sha256", process.env.SESSION_SECRET ?? "").update(value).digest("base64url");

export function verifyTelegramInitData(initData: string): SessionIdentity {
  const botToken = process.env.TELEGRAM_TOKEN;
  if (!botToken) throw new Error("Telegram authentication is not configured");

  const params = new URLSearchParams(initData);
  const receivedHash = params.get("hash");
  const authDate = Number(params.get("auth_date"));
  if (!receivedHash || !authDate) throw new Error("Invalid Telegram authentication");
  if (Math.abs(Date.now() / 1000 - authDate) > 3600) {
    throw new Error("Telegram authentication expired");
  }

  const check = [...params.entries()]
    .filter(([key]) => key !== "hash")
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");
  const secret = createHmac("sha256", "WebAppData").update(botToken).digest();
  const expected = createHmac("sha256", secret).update(check).digest("hex");
  const left = Buffer.from(expected, "hex");
  const right = Buffer.from(receivedHash, "hex");
  if (left.length !== right.length || !timingSafeEqual(left, right)) {
    throw new Error("Invalid Telegram signature");
  }

  const user = JSON.parse(params.get("user") ?? "{}") as {
    id?: number;
    first_name?: string;
    last_name?: string;
    username?: string;
    photo_url?: string;
  };
  if (!user.id || !user.first_name) throw new Error("Telegram user missing");
  return {
    id: user.id,
    displayName: [user.first_name, user.last_name].filter(Boolean).join(" "),
    username: user.username ?? "",
    avatarUrl: user.photo_url ?? null,
    isAdmin: String(user.id) === process.env.ADMIN_CHAT_ID,
  };
}

export function setSession(res: Response, identity: SessionIdentity): void {
  if (!process.env.SESSION_SECRET) throw new Error("Session signing is not configured");
  const payload = encode(
    JSON.stringify({ ...identity, expiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000 }),
  );
  res.cookie("fallen_session", `${payload}.${sign(payload)}`, {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    maxAge: 7 * 24 * 60 * 60 * 1000,
    path: "/",
  });
}

export function getSession(req: Request): SessionIdentity | null {
  const raw = req.cookies?.fallen_session as string | undefined;
  if (raw && process.env.SESSION_SECRET) {
    const [payload, signature] = raw.split(".");
    if (payload && signature) {
      const expected = sign(payload);
      const left = Buffer.from(expected);
      const right = Buffer.from(signature);
      if (left.length === right.length && timingSafeEqual(left, right)) {
        try {
          const identity = JSON.parse(
            Buffer.from(payload, "base64url").toString(),
          ) as SessionIdentity;
          if (!identity.expiresAt || identity.expiresAt < Date.now()) return null;
          return {
            ...identity,
            isAdmin: String(identity.id) === process.env.ADMIN_CHAT_ID,
          };
        } catch {
          return null;
        }
      }
    }
  }
  if (process.env.NODE_ENV !== "production") {
    return {
      id: 999000,
      displayName: "Preview Fan",
      username: "preview",
      avatarUrl: null,
      isAdmin: true,
    };
  }
  return null;
}