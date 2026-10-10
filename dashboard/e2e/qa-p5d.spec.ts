import { test } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3006" });

test("node identity probe: is the textarea remounted on keystroke?", async ({ page }) => {
  const notes: string[] = [];
  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name");
  const ta = page.locator("textarea");
  await ta.click();
  // stash node identity on window
  await page.evaluate(() => { (window as any).__ta = document.querySelector("textarea"); (window as any).__stamp = 1; });
  const snap = () => page.evaluate(() => {
    const t = document.querySelector("textarea") as HTMLTextAreaElement | null;
    const same = t === (window as any).__ta;
    const a = document.activeElement as HTMLElement | null;
    return { sameNode: same, activeIsTA: a === t, activeTag: a ? a.tagName : null, val: t ? t.value : null, taOnPage: t ? 1 : 0 };
  });
  notes.push("before: " + JSON.stringify(await snap()));
  await page.keyboard.type("A");
  await page.waitForTimeout(200);
  notes.push("after A: " + JSON.stringify(await snap()));
  await page.keyboard.type("B");
  await page.waitForTimeout(200);
  notes.push("after B: " + JSON.stringify(await snap()));
  await page.keyboard.type("C");
  await page.waitForTimeout(200);
  notes.push("after C: " + JSON.stringify(await snap()));
  // also probe the name input
  const ni = page.locator("#wiz-name");
  await ni.click();
  await ni.fill("XX");
  await page.evaluate(() => { (window as any).__ni = document.getElementById("wiz-name"); });
  const snapN = () => page.evaluate(() => {
    const t = document.getElementById("wiz-name") as HTMLInputElement | null;
    return { sameNode: t === (window as any).__ni, activeIsIt: document.activeElement === t, val: t ? t.value : null };
  });
  notes.push("name before: " + JSON.stringify(await snapN()));
  await page.keyboard.type("Y");
  await page.waitForTimeout(200);
  notes.push("name after Y: " + JSON.stringify(await snapN()));
  await page.keyboard.type("Z");
  await page.waitForTimeout(200);
  notes.push("name after Z: " + JSON.stringify(await snapN()));
  console.log("NODE:\n" + notes.join("\n"));
});
