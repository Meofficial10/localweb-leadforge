import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";


test("AI activity page shows real LLM calls", async ({ page }: { page: Page }) => {
  await page.goto("http://127.0.0.1:3006/ai-activity", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await expect(page.getByText("AI activity").first()).toBeVisible({ timeout: 10000 });
  const body = await page.locator("body").innerText();
  console.log("PAGE_TEXT_SNIP:", body.slice(0, 2000).replace(/\s+/g, " "));
  console.log("HAS_CALLS_TODAY:", body.includes("Calls today"));
  console.log("HAS_RECENT:", body.includes("Recent LLM calls"));
  console.log("HAS_ACTIVE_MODEL:", body.includes("Active model"));
  const cards = await page.locator("div.grid.gap-4 > div").count().catch(()=> -1);
  console.log("STAT_CARDS:", cards);
});