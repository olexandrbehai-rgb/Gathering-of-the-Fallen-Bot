import express, { type Express } from "express";
import cookieParser from "cookie-parser";
import pinoHttp from "pino-http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.disable("x-powered-by");
app.use(cookieParser());
app.use(express.json({ limit: "32kb" }));
app.use(express.urlencoded({ extended: true }));

app.use("/api", router);

if (process.env.NODE_ENV === "production") {
  const currentDir = path.dirname(fileURLToPath(import.meta.url));
  const frontendDir = path.resolve(currentDir, "../../fallen-mini-app/dist/public");
  app.use(express.static(frontendDir));
  app.use((_req, res) => {
    res.sendFile(path.join(frontendDir, "index.html"));
  });
}

export default app;
