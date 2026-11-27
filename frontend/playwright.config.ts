import { defineConfig } from "@playwright/test";

/** Browser tests against the running stack. They are headed on purpose: you can watch them. */
export default defineConfig({
  testDir: "./e2e",
  timeout: 420_000,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.FRONTEND_URL ?? "http://localhost:3000",
    headless: false,
    launchOptions: { slowMo: 700 },
    viewport: { width: 1360, height: 860 },
    video: "off",
    trace: "off",
  },
});
