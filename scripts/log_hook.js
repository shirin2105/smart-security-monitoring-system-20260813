#!/usr/bin/env node
/* Codex hook logger that works on Windows without a Python installation. */
const { execFileSync } = require("node:child_process");
const { appendFileSync, mkdirSync, readFileSync } = require("node:fs");
const { isAbsolute, join, resolve } = require("node:path");

const projectRoot = resolve(__dirname, "..");

function git(args) {
  try {
    return execFileSync("git", args, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

function repoName(origin) {
  return origin ? origin.replace(/\/$/, "").split("/").pop().replace(/\.git$/, "") : "";
}

function main() {
  let data;
  try {
    data = JSON.parse(readFileSync(0, "utf8").trim());
  } catch {
    process.exit(0);
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) process.exit(0);

  process.chdir(projectRoot);
  const event = data.hook_event_name || data.event || "";
  const configuredLogDir = process.env.AI_LOG_DIR || ".ai-log";
  const logDir = isAbsolute(configuredLogDir)
    ? configuredLogDir
    : join(projectRoot, configuredLogDir);
  mkdirSync(logDir, { recursive: true });
  const entry = {
    ts: new Date().toLocaleString("sv-SE", { timeZone: "Asia/Bangkok" }).replace(" ", "T") + "+07:00",
    tool: "codex",
    event,
    session_id: data.session_id || data.conversation_id || "",
    model: data.model || "",
    repo: repoName(git(["remote", "get-url", "origin"])) || projectRoot.split(/[\\/]/).pop(),
    branch: git(["rev-parse", "--abbrev-ref", "HEAD"]),
    commit: git(["rev-parse", "--short", "HEAD"]),
    student: git(["config", "user.email"]),
    prompt: String(data.prompt || "").slice(0, 1000),
    turn_id: data.turn_id || "",
    transcript_path: data.transcript_path || "",
  };

  if (entry.prompt || ["Stop", "stop", "SessionEnd", "sessionEnd"].includes(event)) {
    appendFileSync(join(logDir, "session.jsonl"), JSON.stringify(entry) + "\n", "utf8");
  }
  if (["Stop", "stop", "SessionEnd", "sessionEnd"].includes(event)) {
    process.stdout.write('{"continue":true}\n');
  }
}

main();
