import {
  bigint,
  boolean,
  integer,
  pgTable,
  serial,
  text,
  timestamp,
} from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const fallenUsersTable = pgTable("fallen_users", {
  telegramId: bigint("telegram_id", { mode: "number" }).primaryKey(),
  username: text("username").notNull().default(""),
  displayName: text("display_name").notNull(),
  avatarUrl: text("avatar_url"),
  subscribed: boolean("subscribed").notNull().default(false),
  isAdmin: boolean("is_admin").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true })
    .notNull()
    .defaultNow()
    .$onUpdate(() => new Date()),
});

export const fallenFanPostsTable = pgTable("fallen_fan_posts", {
  id: serial("id").primaryKey(),
  telegramId: bigint("telegram_id", { mode: "number" }).notNull(),
  author: text("author").notNull(),
  message: text("message").notNull(),
  hidden: boolean("hidden").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const fallenAiUsageTable = pgTable("fallen_ai_usage", {
  id: serial("id").primaryKey(),
  telegramId: bigint("telegram_id", { mode: "number" }).notNull(),
  feature: text("feature").notNull(),
  model: text("model").notNull(),
  inputUnits: integer("input_units").notNull().default(0),
  outputUnits: integer("output_units").notNull().default(0),
  audioSeconds: integer("audio_seconds").notNull().default(0),
  estimatedCostMicrousd: integer("estimated_cost_microusd").notNull().default(0),
  status: text("status").notNull(),
  latencyMs: integer("latency_ms").notNull().default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertFallenUserSchema = createInsertSchema(fallenUsersTable);
export const insertFallenFanPostSchema = createInsertSchema(fallenFanPostsTable).omit({
  id: true,
  hidden: true,
  createdAt: true,
});
export const insertFallenAiUsageSchema = createInsertSchema(fallenAiUsageTable).omit({
  id: true,
  createdAt: true,
});

export type FallenUser = typeof fallenUsersTable.$inferSelect;
export type InsertFallenUser = z.infer<typeof insertFallenUserSchema>;
export type InsertFallenFanPost = z.infer<typeof insertFallenFanPostSchema>;
export type InsertFallenAiUsage = z.infer<typeof insertFallenAiUsageSchema>;