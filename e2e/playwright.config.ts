import { defineConfig } from "@playwright/test";

const apiPort = 8000;
const frontendPort = 5173;

export default defineConfig({
  testDir: ".",
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${frontendPort}`,
  },
  webServer: [
    {
      command:
        "python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: "..",
      port: apiPort,
      reuseExistingServer: true,
      env: {
        DATABASE_URL: "sqlite:///./data/e2e-smoke.db",
        JWT_SECRET: "e2e-test-jwt-secret-key-min-32-chars-long",
        APP_ENCRYPTION_KEY: "e2e-test-encryption-key-with-entropy-xyz",
        ADMIN_EMAIL: "admin@localhost",
        ADMIN_PASSWORD: "changeme",
        SUPERADMIN_EMAIL: "superadmin@localhost",
        SUPERADMIN_PASSWORD: "changeme",
      },
    },
    {
      command: "npm run dev -- --host",
      cwd: "../frontend",
      port: frontendPort,
      reuseExistingServer: true,
    },
  ],
});
