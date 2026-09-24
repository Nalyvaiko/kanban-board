import { execFileSync } from "node:child_process";
import path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "..");
const BASE_URL = "http://localhost:8000";
const STARTUP_TIMEOUT_MS = 90_000;

export default async function globalSetup(): Promise<void> {
  execFileSync("docker", ["compose", "up", "-d", "--build"], { cwd: REPO_ROOT, stdio: "inherit" });
  await waitUntilHealthy();
}

async function waitUntilHealthy(timeoutMs = STARTUP_TIMEOUT_MS): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError: unknown;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${BASE_URL}/docs`);
      if (response.ok) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`App never became reachable at ${BASE_URL} within ${timeoutMs}ms: ${String(lastError)}`);
}
