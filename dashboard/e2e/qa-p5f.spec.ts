import { test } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3006" });

test("whole-doc remount probe", async ({ page }) => {
  const notes: string[] = [];
  page.on("framenavigated", (f) => notes.push("NAVIGATED: " + f.url()));
  page.on("popstate", () => notes.push("popstate"));
  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name");
  // observe document.body: log any subtree removal/addition with tag names
  await page.evaluate(() => {
    const out: string[] = [];
    (window as any).__mut = out;
    const obs = new MutationObserver((muts) => {
      for (const m of muts) {
        if (m.type === "childList") {
          for (const n of Array.from(m.removedNodes)) out.push("REMOVED " + (n as HTMLElement).tagName + ":" + String((n as HTMLElement).className).slice(0, 50));
          if (m.addedNodes.length) out.push("ADDED " + m.addedNodes.length + " nodes under " + (m.target as HTMLElement).tagName + ":" + String((m.target as HTMLElement).className).slice(0, 40));
        }
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
    (window as any).__obs = obs;
  });
  // stash dialog node identity
  await page.evaluate(() => { (window as any).__diag = document.querySelector('[role="dialog"]'); });
  const ta = page.locator("textarea");
  await ta.click();
  await page.keyboard.type("A");
  await page.waitForTimeout(250);
  const syncA = await page.evaluate(() => {
    const a = document.activeElement as HTMLElement | null;
    const d = document.querySelector('[role="dialog"]');
    return { active: a ? a.tagName + "#" + a.id : "NONE", dialogSame: d === (window as any).__diag, dialogPresent: !!d, taVal: (document.querySelector("textarea") as HTMLTextAreaElement | null)?.value };
  });
  notes.push("sync after A: " + JSON.stringify(syncA));
  await page.keyboard.type("B");
  await page.waitForTimeout(250);
  const syncB = await page.evaluate(() => {
    const a = document.activeElement as HTMLElement | null;
    const d = document.querySelector('[role="dialog"]');
    return { active: a ? a.tagName + "#" + a.id : "NONE", dialogSame: d === (window as any).__diag, dialogPresent: !!d, taVal: (document.querySelector("textarea") as HTMLTextAreaElement | null)?.value };
  });
  notes.push("sync after B: " + JSON.stringify(syncB));
  const muts = await page.evaluate(() => (window as any).__mut);
  notes.push("body mutations: " + JSON.stringify(muts.slice(0, 25)));
  console.log("WD:\n" + notes.join("\n"));
});
