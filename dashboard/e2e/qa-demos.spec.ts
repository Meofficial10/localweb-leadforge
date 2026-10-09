const { test, expect } = require("@playwright/test");

test("Demo sites page lists demo sites", async ({ page }) => {
  await page.goto("http://127.0.0.1:3006/demos", { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await expect(page.getByText("Demo sites").first()).toBeVisible({ timeout: 10000 });
  const body = await page.locator("body").innerText();
  console.log("HAS_OPEN_DEMO:", body.includes("Open demo"));
  console.log("HAS_BUSINESS:", body.includes("Business"));
  console.log("BODY_SNIP:", body.slice(0, 900).replace(/\s+/g, " ").slice(0, 900));
});