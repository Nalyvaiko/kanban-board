import { execFileSync } from "node:child_process";
import path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "..");

export default async function globalTeardown(): Promise<void> {
  execFileSync("docker", ["compose", "down", "-v"], { cwd: REPO_ROOT, stdio: "inherit" });
}
