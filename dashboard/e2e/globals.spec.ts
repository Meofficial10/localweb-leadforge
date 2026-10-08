import { test, expect } from "@playwright/test";

test("global UI: kill switch engage/release + dark theme", async ({ page, request }) => {
  // ensure system is NOT paused before the test (release kill switch via API)
  await request.post("http://127.0.0.1:8000/system/pause", { data: { paused: false } });
  await page.goto("http://127.0.0.1:3006/", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);

  // Kill switch present in top bar
  const ks = page.locator("header").getByRole("button", { name: /kill switch/i });
  await expect(ks).toBeVisible();
  await ks.click();
  await expect(page.getByRole("alertdialog")).toBeVisible({ timeout: 10000 });
  await page.getByRole("button", { name: "Engage kill switch" }).click();
  await expect(page.getByRole("button", { name: /resume/i }).first()).toBeVisible({ timeout: 15000 });

  // release it again so the system is left running
  await page.getByRole("button", { name: /resume/i }).first().click();
  await expect(page.getByRole("alertdialog")).toBeVisible({ timeout: 10000 });
  await page.getByRole("button", { name: /resume sending/i }).click();

  // theme toggle → Dark
  const theme = page.getByRole("button", { name: "Toggle theme" }).first();
  await expect(theme).toBeVisible();
  await theme.click();
  await expect(page.getByText("Dark", { exact: true }).first()).toBeVisible();
  await page.getByText("Dark", { exact: true }).first().click();
  await page.waitForTimeout(600);
  const dark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  console.log("dark applied:", dark);
  expect(dark).toBe(true);
});
