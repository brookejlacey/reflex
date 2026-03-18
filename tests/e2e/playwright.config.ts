import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./specs",
  timeout: 120_000,
  retries: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: process.env.GITLAB_BASE_URL || "https://gitlab.com",
    extraHTTPHeaders: {
      "PRIVATE-TOKEN": process.env.GITLAB_ACCESS_TOKEN || "",
    },
  },
  projects: [
    {
      name: "api",
      testMatch: /.*\.api\.spec\.ts/,
    },
    {
      name: "flow-validation",
      testMatch: /.*\.flow\.spec\.ts/,
    },
    {
      name: "integration",
      testMatch: /.*\.integration\.spec\.ts/,
    },
  ],
});
