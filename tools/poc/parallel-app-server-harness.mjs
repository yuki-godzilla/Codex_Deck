import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { isAbsolute, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const separator = process.platform === "win32" ? ";" : ":";
const outputFile = process.env.CODEX_DECK_POC_PARALLEL_OUTPUT_FILE ?? null;
const workspaces = (process.env.CODEX_DECK_POC_PARALLEL_CWDS ?? "")
  .split(separator)
  .map((value) => value.trim())
  .filter(Boolean);

if (workspaces.length < 2 || workspaces.some((workspace) => !isAbsolute(workspace))) {
  throw new Error("Set CODEX_DECK_POC_PARALLEL_CWDS to two or more absolute disposable workspace paths.");
}

const harnessPath = fileURLToPath(new URL("./app-server-harness.mjs", import.meta.url));
const runHarness = (cwd) => new Promise((resolveRun, rejectRun) => {
  const child = spawn(process.execPath, [harnessPath], {
    env: {
      ...process.env,
      CODEX_DECK_POC_CWD: cwd,
      CODEX_DECK_POC_SCENARIO: "basic",
      CODEX_DECK_POC_OUTPUT_FILE: "",
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
  let stdout = "";
  let stderr = "";
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  child.once("error", rejectRun);
  child.once("exit", (code, signal) => {
    if (code !== 0) {
      rejectRun(new Error(`Harness exited with code=${code}, signal=${signal}, stderrLines=${stderr.split(/\r?\n/).filter(Boolean).length}.`));
      return;
    }
    try {
      resolveRun(JSON.parse(stdout));
    } catch {
      rejectRun(new Error("Harness did not return a JSON summary."));
    }
  });
});

const results = await Promise.all(workspaces.map(runHarness));
const summary = {
  runCount: results.length,
  workspaceMode: new Set(workspaces.map((workspace) => resolve(workspace))).size === 1 ? "same" : "separate",
  allReadAndResumeSucceeded: results.every((result) => result.threadRead && result.threadResume),
  distinctThreadIdHashes: new Set(results.map((result) => result.threadIdHash)).size === results.length,
  distinctTurnIdHashes: new Set(results.map((result) => result.turnIdHash)).size === results.length,
  serverRequestMethodCounts: results.map((result) => result.serverRequestMethods.length),
  notificationMethodSetsMatch: results.every((result) => JSON.stringify(result.notificationMethods) === JSON.stringify(results[0].notificationMethods)),
};
const text = JSON.stringify(summary, null, 2);
if (outputFile) writeFileSync(outputFile, text, "utf8");
console.log(text);
