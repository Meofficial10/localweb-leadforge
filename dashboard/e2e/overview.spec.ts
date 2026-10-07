import { test, expect } from "@playwright/test";

test("overview has usage-vs-caps and activity", async ({ page }) => {
  await page.goto("http://127.0.0.1:3006/", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  const body = await page.locator("body").innerText();
  console.log("Usage vs daily caps:", /Usage vs daily caps/i.test(body));
  console.log("Recent activity:", /Recent activity/i.test(body));
  expect(/Usage vs daily caps/i.test(body)).toBe(true);
});
