import { Router, type IRouter } from "express";
import healthRouter from "./health";
import fallenRouter from "./fallen";

const router: IRouter = Router();

router.use(healthRouter);
router.use(fallenRouter);

export default router;
