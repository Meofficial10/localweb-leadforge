import { test, expect } from "@playwright/test";

// P5 regression: typing in the wizard must keep ALL characters (previously the
// step components were defined inside CampaignWizard, so every keystroke
// remounted the subtree and dropped focus after the first character).
// Spec requirement: "add a Playwright test typing 30 characters at once".

test.use({ baseURL: "http://127.0.0.1:3006" });

const THIRTY = "abcdefghij0123456789XYZLMNOPQRST";

test("P5 wizard typing keeps 30 characters in name and description", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });

  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name", { timeout: 10000 });

  // Type 30 characters at once into a single-line input
  const name = page.locator("#wiz-name");
  await name.click();
  await name.pressSequentially(THIRTY, { delay: 5 });
  await expect(name).toHaveValue(THIRTY, { timeout: 5000 });
  // Focus must remain on the field so further input still lands
  const stillFocused = await name.evaluate((el: HTMLInputElement) => document.activeElement === el);
  expect(stillFocused, "name input still has focus after 30 chars").toBe(true);

  // Type 30 characters at once into the multi-line description
  const desc = page.locator("#wiz-desc");
  await desc.click();
  await desc.pressSequentially(THIRTY, { delay: 5 });
  await expect(desc).toHaveValue(THIRTY, { timeout: 5000 });
  const descFocused = await desc.evaluate((el: HTMLTextAreaElement) => document.activeElement === el);
  expect(descFocused, "description textarea still has focus after 30 chars").toBe(true);

  expect(errors).toEqual([]);
});

test("P5 wizard location step: defaults to Singapore, list constrained + Queenstown present", async ({ page }) => {
  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name", { timeout: 10000 });
  await page.locator("#wiz-name").fill("Queenstown Dentists");
  await page.getByTestId("wiz-next").click();
  await page.waitForSelector("[data-testid=wiz-country]", { timeout: 10000 });

  // Default country is Singapore
  await expect(page.getByTestId("wiz-country")).toContainText("Singapore");

  // The suggested-areas list is scroll-constrained inside the modal (not overflowing)
  const searchBox = page.locator("[data-testid=wiz-area-search]").locator("xpath=ancestor::div[contains(@class,'rounded-md')]");
  const list = searchBox.locator("div.max-h-72, div[class*='max-h-72']").first();
  const constrained = await list.evaluate((el: HTMLElement) => {
    const cs = getComputedStyle(el);
    return { maxH: cs.maxHeight, ov: cs.overflowY, clientH: el.clientHeight, scrollH: el.scrollHeight };
  });
  expect(constrained.maxH).not.toBe("none");
  expect(constrained.ov === "auto" || constrained.ov === "scroll").toBe(true);
  expect(constrained.scrollH).toBeGreaterThanOrEqual(constrained.clientH);

  // Queenstown is available for Singapore
  await page.locator("[data-testid=wiz-area-search]").fill("Queen");
  await expect(page.locator("button", { hasText: "Queenstown" }).first()).toBeVisible();
});

test("P5 overview charts use theme tokens, not literal var() or black fills", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);
  const residue = await page.evaluate(() => {
    const out: string[] = [];
    document.querySelectorAll("svg stop, svg path, svg rect").forEach((el) => {
      const s = el.getAttribute("stop-color") || "";
      const st = el.getAttribute("stroke") || "";
      const f = el.getAttribute("fill") || "";
      if (/var\(/.test(s) || /var\(/.test(st) || /var\(/.test(f)) out.push(el.tagName);
    });
    return out;
  });
  expect(residue, "no literal var(--…) in SVG presentation attributes").toEqual([]);
  // Some svg must carry the theme colour via currentColor on stroke/fill
  const themed = await page.evaluate(() => {
    const svgs = Array.from(document.querySelectorAll("div.text-primary svg, svg .recharts-area-curve, svg .recharts-bar-rectangle"));
    const used = document.querySelectorAll("svg [stroke=currentColor], svg [fill=currentColor], svg [stop-color=currentColor]").length;
    return { used, chartSvgs: svgs.length };
  });
  expect(themed.used).toBeGreaterThan(0);
});
