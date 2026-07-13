import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

const cwd = process.env.CODEX_DECK_POC_CWD;
if (!cwd) {
  throw new Error("Set CODEX_DECK_POC_CWD to an absolute disposable workspace path.");
}
const scenario = process.env.CODEX_DECK_POC_SCENARIO ?? "basic";
if (!new Set(["basic", "approval", "control"]).has(scenario)) {
  throw new Error("CODEX_DECK_POC_SCENARIO must be basic, approval, or control.");
}

const server = spawn("codex", ["app-server", "--stdio"], {
  stdio: ["pipe", "pipe", "pipe"],
  windowsHide: true,
});
const startedAt = new Date().toISOString();
const pending = new Map();
const notifications = [];
const serverRequests = [];
const stderr = [];
let nextId = 1;

const redactId = (value) => createHash("sha256").update(value).digest("hex").slice(0, 12);
const write = (message) => server.stdin.write(`${JSON.stringify(message)}\n`);
const request = (method, params) => new Promise((resolve, reject) => {
  const id = nextId++;
  pending.set(id, { method, reject, resolve });
  write({ id, method, params });
});
const waitFor = (method, timeoutMs = 120_000) => new Promise((resolve, reject) => {
  const deadline = setTimeout(() => reject(new Error(`Timed out waiting for ${method}`)), timeoutMs);
  const poll = () => {
    const match = notifications.find((entry) => entry.method === method);
    if (match) {
      clearTimeout(deadline);
      resolve(match);
      return;
    }
    setTimeout(poll, 50);
  };
  poll();
});

createInterface({ input: server.stdout }).on("line", (line) => {
  const message = JSON.parse(line);
  if (Object.hasOwn(message, "id") && pending.has(message.id)) {
    const entry = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) entry.reject(new Error(`${entry.method}: ${JSON.stringify(message.error)}`));
    else entry.resolve(message.result);
    return;
  }
  if (Object.hasOwn(message, "id") && message.method?.endsWith("/requestApproval")) {
    serverRequests.push(message.method);
    write({ id: message.id, result: { decision: "decline" } });
    return;
  }
  if (message.method) notifications.push({ method: message.method, params: message.params ?? null });
});
createInterface({ input: server.stderr }).on("line", (line) => stderr.push(line));

try {
  const initialize = await request("initialize", {
    clientInfo: { name: "codex-deck-poc", version: "0.1.0" },
    capabilities: { experimentalApi: false },
  });
  write({ method: "initialized", params: {} });
  const before = await request("thread/list", { cwd, limit: 10, useStateDbOnly: true });
  const started = await request("thread/start", {
    approvalPolicy: "untrusted",
    cwd,
    sandbox: scenario === "approval" ? "workspace-write" : "read-only",
  });
  const threadId = started.thread.id;
  const turn = await request("turn/start", {
    threadId,
    input: [{
      type: "text",
      text: scenario === "approval"
        ? "Create a file named approval_probe.txt containing exactly APPROVED."
        : "Explain the numbers from 1 through 1000 one at a time. Do not run commands or modify files.",
    }],
  });
  let steerOutcome = null;
  let interruptOutcome = null;
  if (scenario === "control") {
    try {
      await request("turn/steer", {
        threadId,
        expectedTurnId: turn.turn.id,
        input: [{ type: "text", text: "Stop the enumeration and summarize in one sentence." }],
      });
      steerOutcome = "accepted";
    } catch (error) {
      steerOutcome = error.message.includes("no active turn") ? "rejected-no-active-turn" : "rejected";
    }
    try {
      await request("turn/interrupt", { threadId, turnId: turn.turn.id });
      interruptOutcome = "accepted";
    } catch (error) {
      interruptOutcome = error.message.includes("no active turn") ? "rejected-no-active-turn" : "rejected";
    }
  }
  await waitFor("turn/completed");
  const read = await request("thread/read", { threadId });
  const resumed = await request("thread/resume", { threadId });
  const itemMethods = [...new Set(notifications.map((entry) => entry.method))].sort();
  console.log(JSON.stringify({
    startedAt,
    initialize: { platformFamily: initialize.platformFamily, platformOs: initialize.platformOs, userAgent: initialize.userAgent },
    threadListBeforeCount: before.data?.length ?? before.threads?.length ?? null,
    threadIdHash: redactId(threadId),
    turnIdHash: redactId(turn.turn.id),
    threadRead: Boolean(read.thread),
    threadResume: Boolean(resumed.thread),
    scenario,
    serverRequestMethods: serverRequests,
    steerOutcome,
    interruptOutcome,
    notificationMethods: itemMethods,
    stderrLineCount: stderr.length,
  }, null, 2));
} finally {
  server.kill();
}
