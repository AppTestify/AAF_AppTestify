import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("axe accessibility audit on workspace", async ({ page }) => {
  // Login
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("admin@localhost");
  await page.getByLabel(/password/i).fill("changeme");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/app/);

  // Wait for the workspace to load
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();

  // Run Axe
  const accessibilityScanResults = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  if (accessibilityScanResults.violations.length > 0) {
    console.log(JSON.stringify(accessibilityScanResults.violations, null, 2));
  }
  
  expect(accessibilityScanResults.violations).toEqual([]);
});
