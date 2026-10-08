import { test, expect, type Page } from "@playwright/test";

/**
 * QA sweep — navigates every page at 1440px and 390px, records console
 * errors, failed HTTP requests, horizontal overflow, and saves a screenshot
 * per page per viewport. Reusable as before/after baseline.
 */
const BASE = "http://127.0.0.1:3006";
const PAGES: { path: string; label: string }[] = [
  { path: "/", label: "overview" },
  { path: "/campaigns", label: "campaigns" },
  { path: "/leads", label: "leads" },
  { path: "/outreach", label: "outreach" },
  { path: "/inbox", label: "inbox" },
  { path: "/calls", label: "calls" },
  { path: "/compliance", label: "compliance" },
  { path: "/integrations", label: "integrations" },
  { path: "/settings", label: "settings" },
];
const VIEWPORTS: { w: number; h: number; tag: string }[] = [
  { w: 1440, h: 900, tag: "desktop" },
  { w: 390, h: 844, tag: "mobile" },
];

async function sweep(page: Page, label: string, tag: string, dest: string) {
  await page.setViewportSize({ width: tag === "desktop" ? 1440 : 390, height: tag === "desktop" ? 900 : 844 });
  const errors: string[] = [];
  const failed: string[] = [];
  const onConsole = (m) => { if (m.type() === "error") errors.push("CONSOLE: " + m.text().slice(0, 300)); };
  page.on("console", onConsole);
  const onResp = async (r) => { if (r.status() >= 400) failed.push("HTTP " + r.status() + " " + r.url().replace(BASE, "")); };
  page.on("response", onResp);
  await page.goto(BASE + "/" + (label === "overview" ? "" : label) + (label === "overview" ? "" : ""), { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(2500);
  const dh = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }));
  await page.screenshot({ path: dest + "/" + tag + "-" + label + ".png" });
  page.off("console", onConsole);
  page.off("response", onResp);
  return { label, errors, failed, overflow: dh.sw, inner: dh.iw };
}

test("QA sweep every page at both viewports", async ({ page }) => {
  const dest = process.env.QA_DEST || "qa-artifacts";
  const all = [];
  for (const tag of VIEWPORTS) {
    for (const pg of PAGES) {
      const res = await sweep(page, pg.label, tag.tag, dest);
      all.push(res);
      console.log(`[${tag.tag}] ${pg.label}: ovf=${res.overflow}/${res.inner} errs=${res.errors.length} failed=${res.failed.length}`);
      res.errors.forEach((e) => console.log("   " + e));
      res.failed.forEach((e) => console.log("   " + e));
    }
  }
  console.log("SWEEP DONE total pages: " + all.length);
  expect(all.length).toBeGreaterThan(0);
});
