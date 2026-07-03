import { test, expect } from "@playwright/test";

test("marketing home loads", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("login page renders", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByLabel(/email/i)).toBeVisible();
  await expect(page.getByLabel(/password/i)).toBeVisible();
});

test("authenticated user reaches workspace", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("admin@localhost");
  await page.getByLabel(/password/i).fill("changeme");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/app/);
  await expect(page.getByText(/governance|workspace|dashboard/i).first()).toBeVisible();
});

test("governance run can be submitted and polled", async ({ page, request }) => {
  const loginRes = await request.post("http://127.0.0.1:8000/api/v1/auth/login", {
    data: { email: "admin@localhost", password: "changeme" },
  });
  expect(loginRes.ok()).toBeTruthy();
  const cookies = await loginRes.headersArray();
  const cookieHeader = cookies
    .filter((h) => h.name.toLowerCase() === "set-cookie")
    .map((h) => h.value.split(";")[0])
    .join("; ");

  const runRes = await request.post("http://127.0.0.1:8000/api/v1/governance/runs", {
    headers: { Cookie: cookieHeader, "Content-Type": "application/json" },
    data: { prompt: "E2E smoke: assess release readiness" },
  });
  expect(runRes.ok()).toBeTruthy();
  const runBody = await runRes.json();
  expect(runBody.id).toBeTruthy();

  let status = runBody.status;
  for (let i = 0; i < 60 && (status === "queued" || status === "running"); i += 1) {
    await page.waitForTimeout(1000);
    const poll = await request.get(`http://127.0.0.1:8000/api/v1/governance/runs/${runBody.id}`, {
      headers: { Cookie: cookieHeader },
    });
    expect(poll.ok()).toBeTruthy();
    const polled = await poll.json();
    status = polled.status;
  }
  expect(["succeeded", "failed"]).toContain(status);
});

test("authenticated happy path reaches brief deep link", async ({ page, request }) => {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("admin@localhost");
  await page.getByLabel(/password/i).fill("changeme");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/app/);

  await page.goto("/app/overview");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  const loginRes = await request.post("http://127.0.0.1:8000/api/v1/auth/login", {
    data: { email: "admin@localhost", password: "changeme" },
  });
  expect(loginRes.ok()).toBeTruthy();
  const cookies = await loginRes.headersArray();
  const cookieHeader = cookies
    .filter((h) => h.name.toLowerCase() === "set-cookie")
    .map((h) => h.value.split(";")[0])
    .join("; ");

  const runRes = await request.post("http://127.0.0.1:8000/api/v1/governance/runs", {
    headers: { Cookie: cookieHeader, "Content-Type": "application/json" },
    data: { prompt: "E2E happy path: release readiness brief" },
  });
  expect(runRes.ok()).toBeTruthy();
  const runId = (await runRes.json()).id as number;

  let status = "queued";
  for (let i = 0; i < 60 && (status === "queued" || status === "running"); i += 1) {
    await page.waitForTimeout(1000);
    const poll = await request.get(`http://127.0.0.1:8000/api/v1/governance/runs/${runId}`, {
      headers: { Cookie: cookieHeader },
    });
    status = (await poll.json()).status;
  }
  expect(status).toBe("succeeded");

  await page.goto(`/app/brief?run_id=${runId}`);
  await expect(page.getByText(/brief|governance/i).first()).toBeVisible({ timeout: 15000 });
});

test("RBAC blocks unauthenticated governance API", async ({ request }) => {
  const res = await request.post("http://127.0.0.1:8000/api/v1/governance/runs", {
    data: { prompt: "Should be blocked" },
  });
  expect(res.status()).toBe(401);
});

test("authenticated user reaches settings", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("admin@localhost");
  await page.getByLabel(/password/i).fill("changeme");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/app/);

  await page.goto("/app/settings");
  await expect(page.getByRole("heading", { name: /settings/i, level: 1 })).toBeVisible();
});

test("authenticated user views cases for approval", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("admin@localhost");
  await page.getByLabel(/password/i).fill("changeme");
  await page.getByRole("button", { name: /sign in/i }).click();

  await page.goto("/app/cases");
  await expect(page.getByRole("heading", { name: /cases/i, level: 1 })).toBeVisible();
});
