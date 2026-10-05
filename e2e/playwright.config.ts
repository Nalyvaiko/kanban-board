import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  // Raised from Playwright's 60s default as general headroom for a
  // test that drives two full sessions through register/login/invite/
  // accept/edit against a stack that just finished a cold
  // `docker compose up --build`. (The one time this test actually hit
  // 60s turned out to be a real app bug - see httpApi.ts's `request` -
  // not slowness; confirmed runs now take ~10-25s. Kept at 120s anyway
  // as cheap, honest headroom for a CI runner having a slow day, not
  // because anything here is known to need it.)
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  // Retry once on CI only - local runs stay strict/fast-failing, since
  // a local retry would just hide a real local regression. On CI, one
  // retry absorbs a one-off runner-speed hiccup; a test still failing
  // on *both* attempts is real signal, not noise.
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  globalSetup: "./global-setup.ts",
  globalTeardown: "./global-teardown.ts",
});
