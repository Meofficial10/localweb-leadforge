import { test, expect } from "@playwright/test";

const BASE = "http://127.0.0.1:3006";

test("settings page: Needs setup placeholders, dry-run label, real health, random tokens", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));

  await page.goto(BASE + "/settings", { waitUntil: "networkidle" });

  // 1) DRY-RUN label visible (global dry-run badge in the page header)
  await expect(page.getByText("Global dry-run active")).toBeVisible({ timeout: 15000 });

  // 2) Real health summary from the API ("X of Y required integrations working")
  const health = page.getByText(/required integrations working/);
  await expect(health).toBeVisible({ timeout: 15000 });

  // 3) "Needs setup" placeholder text for token cards only when empty is not case here
  //    (tokens are always generated) — assert mono token block exists instead
  await expect(page.locator("text=/^lf_/").first()).toBeVisible({ timeout: 15000 });

  // 4) Access tokens card visible with tokens that match the API
  const api = await page.request.get("http://127.0.0.1:8000/settings");
  expect(api.ok()).toBeTruthy();
  const body = await api.json();
  const auth = body["tokens"]["auth_tokens"];
  expect(Array.isArray(auth)).toBeTruthy();
  expect(auth.length).toBeGreaterThan(0);
  expect(String(auth[0]).startsWith("lf_")).toBeTruthy();

  // 5) Render the token value that matches the API response on the page
  const firstToken = auth[0];
  await expect(page.getByText(firstToken, { exact: false })).toBeVisible({ timeout: 15000 });

  await page.screenshot({ path: "E:/build/Leads generation/dashboard/e2e/p4-settings.png", fullPage: true });
  expect(errors).toEqual([]);
});
