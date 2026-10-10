import { test } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3006" });

test("focus probe: activeElement/value/selectionStart per keystroke", async ({ page }) => {
  const notes: string[] = [];
  page.on("pageerror", (e) => notes.push("PAGEERROR: " + e.message));
  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name");
  const ta = page.locator("textarea");
  await ta.click();
  const probe = () => page.evaluate(() => {
    const a = document.activeElement as HTMLElement | null;
    const t = document.querySelector("textarea") as HTMLTextAreaElement | null;
    return { activeTag: a ? a.tagName : null, activeId: a ? (a.id || a.getAttribute("data-testid") || a.className.slice(0,20)) : null, isTA: a === t, val: t ? t.value : null, selStart: t ? t.selectionStart : -1, taCount: document.querySelectorAll("textarea").length };
  });
  notes.push("before: " + JSON.stringify(await probe()));
  await page.keyboard.type("A", { delay: 300 });
  await page.waitForTimeout(250);
  notes.push("after A: " + JSON.stringify(await probe()));
  await page.keyboard.type("B", { delay: 300 });
  await page.waitForTimeout(250);
  notes.push("after B: " + JSON.stringify(await probe()));
  await page.keyboard.type("C", { delay: 300 });
  await page.waitForTimeout(250);
  notes.push("after C: " + JSON.stringify(await probe()));
  await page.screenshot({ path: "e2e/p5-focus.png" });
  console.log("PROBE:\n" + notes.join("\n"));
});
