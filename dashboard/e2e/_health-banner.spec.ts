import { test, expect } from "@playwright/test";
const BASE = "http://127.0.0.1:3006";

test("backend-unreachable banner shows and Retry works", async ({ page }) => {
  await page.route("**/health", (route) => route.abort());
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  const banner = page.getByRole("alert").filter({ hasText: /Backend not reachable at/i });
  await expect(banner).toBeVisible({ timeout: 15000 });
  await expect(banner).toContainText(/Backend not reachable at/i);
  await expect(banner.getByRole("button", { name: /retry/i })).toBeVisible();
});
