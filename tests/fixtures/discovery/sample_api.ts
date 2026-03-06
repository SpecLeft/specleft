// Sample Express API module for discovery tests

import express from "express";

const app = express();
const router = express.Router();

router.get("/health", healthHandler);
app.post("/users", createUserHandler);

function healthHandler() {
  return { ok: true };
}

function createUserHandler() {
  return { created: true };
}
