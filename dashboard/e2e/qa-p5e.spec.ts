import { test } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3006" });

test("MutationObserver: what remounts on keystroke", async ({ page }) => {
  const notes: string[] = [];
  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name");
  const ta = page.locator("textarea");
  await ta.click();
  // attach observer to capture childList mutations around the textarea
  await page.evaluate(() => {
    const out: string[] = [];
    (window as any).__mut = out;
    const taEl = document.querySelector("textarea") as HTMLElement;
    let cur = taEl;
    while (cur && cur.id !== "root-of-wizard") {
      if (cur.parentElement && cur.parentElement.className && typeof cur.parentElement.className === "string" && cur.parentElement.className.includes("overflow-y-auto")) {
        break;
      }
      cur = cur.parentElement!;
    }
    const obs = new MutationObserver((muts) => {
      for (const m of muts) {
        if (m.type === "childList") {
          out.push("childList " + (m.target as HTMLElement).tagName + "." + String((m.target as HTMLElement).className).slice(0, 40) + " removed=" + m.removedNodes.length + " added=" + m.addedNodes.length);
        }
      }
    });
    const container = cur || document.body;
    obs.observe(container, { childList: true, subtree: true, attributes: false });
    (window as any).__obs = obs;
    (window as any).__containerSel = (container as HTMLElement).className || container.tagName;
  });
  notes.push("container observed: " + await page.evaluate(() => (window as any).__containerSel));
  await page.keyboard.type("A");
  await page.waitForTimeout(300);
  await page.keyboard.type("B");
  await page.waitForTimeout(300);
  const muts = await page.evaluate(() => (window as any).__mut);
  notes.push("mutations: " + JSON.stringify(muts.slice(0, 20)));
  const state = await page.evaluate(() => {
    const t = document.querySelector("textarea") as HTMLTextAreaElement | null;
    return { val: t ? t.value : null, active: document.activeElement ? document.activeElement.tagName : null };
  });
  notes.push("final state: " + JSON.stringify(state));
  console.log("MUT:\n" + notes.join("\n"));
});
