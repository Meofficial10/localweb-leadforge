import { test } from "@playwright/test";
test.use({ baseURL: "http://127.0.0.1:3006" });
test("deep: identify exactly what remounts", async ({ page }) => {
  const notes: string[] = [];
  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name");
  await page.evaluate(() => {
    const out: string[] = [];
    (window as any).__mut2 = out;
    const obs = new MutationObserver((muts) => {
      for (const m of muts) {
        for (const n of Array.from(m.removedNodes)) out.push("REM " + (n as HTMLElement).tagName + ":" + String((n as HTMLElement).className).slice(0, 60));
        for (const n of Array.from(m.addedNodes)) out.push("ADD " + (n as HTMLElement).tagName + ":" + String((n as HTMLElement).className).slice(0, 60));
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
    const name = document.getElementById("wiz-name");
    (window as any).__name1 = name;
    (window as any).__ta1 = document.querySelector("textarea");
    (window as any).__scroll = document.querySelector('[class*="overflow-y-auto"][class*="px-6"]');
  });
  const ta = page.locator("textarea");
  await ta.click();
  await ta.pressSequentially("A", { delay: 50 });
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => {
    const t = document.querySelector("textarea") as HTMLTextAreaElement | null;
    return {
      taVal: t ? t.value : null,
      taSame: t === (window as any).__ta1,
      nameSame: document.getElementById("wiz-name") === (window as any).__name1,
      active: document.activeElement ? document.activeElement.tagName + "#" + document.activeElement.id : "NONE",
      muts: (window as any).__mut2,
    };
  });
  notes.push("after A: " + JSON.stringify(after));
  console.log("DP:\n" + notes.join("\n"));
});
