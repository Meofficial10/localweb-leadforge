import { test, expect } from "@playwright/test";

test("campaign card opens run view with pipeline stages", async ({ page }) => {
  await page.goto("http://127.0.0.1:3006/campaigns", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  const card = page.locator("div").filter({ hasText: "Demo Campaign - dry run" }).first();
  await card.getByRole("button", { name: /View run/i }).first().click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await page.waitForTimeout(800);
  const bodyText = await page.locator("body").innerText();
  console.log("has Pipeline stages:", /Pipeline stages/i.test(bodyText));
  console.log("has discover stage:", /Discover/i.test(bodyText));
  console.log("has no-apifyruns message:", /No apify runs yet/i.test(bodyText));
  expect(/Pipeline stages/i.test(bodyText)).toBe(true);
  expect(/Discover/i.test(bodyText)).toBe(true);
  expect(/No apify runs yet/i.test(bodyText)).toBe(true);
});

test("run view reports dry-run and no active runs when idle", async ({ page }) => {
  await page.goto("http://127.0.0.1:3006/campaigns", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  const card = page.locator("div").filter({ hasText: "Demo Campaign - dry run" }).first();
  await card.getByRole("button", { name: /View run/i }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await page.waitForTimeout(800);
  const bodyText = await page.locator("body").innerText();
  console.log("has All runs idle:", /All runs idle/.test(bodyText));
  console.log("has dry-run:", /Dry-run: this view never sends anything real/.test(bodyText));
  expect(/All runs idle/.test(bodyText)).toBe(true);
  expect(/Dry-run: this view never sends anything real/.test(bodyText)).toBe(true);
});
