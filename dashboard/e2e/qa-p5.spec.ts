import { test, expect } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3006" });

const CONSOLE_ERRORS: string[] = [];

test("P5 UI diagnostics: wizard typing, SG cascade, location scroll, chart, source warning", async ({ page }) => {
  const notes: string[] = [];
  page.on("console", (m) => { if (m.type() === "error") CONSOLE_ERRORS.push(m.text()); });
  page.on("pageerror", (e) => CONSOLE_ERRORS.push("PAGEERROR: " + e.message));

  // 1) Overview: theme-token chart renders and uses theme colors
  await page.goto("/", { waitUntil: "networkidle" });
  await page.waitForTimeout(3000);
  const chartSvg = await page.locator("svg").count();
  notes.push("overview svg count: " + chartSvg);
  // Inline styles on svg primitives: look for var(--primary) residue or empty fills
  const styledFills = await page.evaluate(() => {
    const out: string[] = [];
    document.querySelectorAll("svg path, svg rect, svg stop").forEach((el) => {
      const fill = el.getAttribute("fill") || "";
      const stroke = el.getAttribute("stroke") || "";
      const stop = el.getAttribute("stop-color") || "";
      if (fill.toLowerCase().includes("var(") || stroke.toLowerCase().includes("var(") || stop.toLowerCase().includes("var(")) {
        out.push((el.tagName) + " fill=" + fill + " stroke=" + stroke + " stop=" + stop);
      }
    });
    return out.slice(0, 12);
  });
  notes.push("svgs using var() as literal attr: " + JSON.stringify(styledFills));
  const anyColoredBar = await page.evaluate(() => {
    const rects = Array.from(document.querySelectorAll("svg rect"));
    return rects.filter((r) => r.getAttribute("fill") && r.getAttribute("fill") !== "none" && r.getAttribute("fill") !== "#000" && r.getAttribute("fill") !== "black")
      .map((r) => r.getAttribute("fill")).slice(0, 8);
  });
  notes.push("non-black rect fills: " + JSON.stringify(anyColoredBar));
  await page.screenshot({ path: "e2e/p5-overview.png", fullPage: true });

  // 2) Wizard: open, type name, type description with real keystrokes
  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name-nope", { timeout: 5000 }).catch(() => notes.push("no #wiz-name selector (probe other)"));
  const nameInputs = page.locator("input[type=text], input:not([type=checkbox]):not([type=radio])");
  const nameCount = await nameInputs.count();
  notes.push("text input count on basics step: " + nameCount);
  // Try the most likely first text input (campaign name)
  const firstText = nameInputs.first();
  await firstText.click();
  await firstText.fill("P5 Typing Test " + Date.now());
  await page.waitForTimeout(250);
  notes.push("first text input value after fill: " + JSON.stringify(await firstText.inputValue()));

  // Description textarea typing with real keystrokes
  const textareas = page.locator("textarea");
  const taCount = await textareas.count();
  notes.push("textarea count: " + taCount);
  if (taCount > 0) {
    const ta = textareas.first();
    await ta.click();
    await ta.pressSequentially("Typed description line with real keystrokes", { delay: 20 });
    await page.waitForTimeout(200);
    notes.push("description value: " + JSON.stringify((await ta.inputValue()).slice(0, 60)));
  }
  await page.screenshot({ path: "e2e/p5-wizard-basics.png" });

  // 3) Advance to Location step (drag along)
  const continueBtn = page.getByRole("button", { name: /continue|next|continue to location/i }).first();
  if (await continueBtn.count()) { await continueBtn.click(); } else { notes.push("no continue button found"); }
  await page.waitForTimeout(1800);

  // SG cascade: country value, states, cities
  const sgCountry = await page.locator("text=Singapore").count();
  notes.push("Singapore visible on location step: " + sgCountry);
  const statesBox = await page.locator("text=no state / -- none --").count();
  notes.push("state none option visible: " + statesBox);

  // scrollable city list
  const scrolls = page.locator("div.overflow-y-auto, [class*=overflow-y-auto]");
  const scrollCount = await scrolls.count();
  notes.push("scrollable containers on location step: " + scrollCount);
  const dims = await scrolls.last().evaluate((el) => {
    const s = el as HTMLElement;
    const cs = getComputedStyle(s);
    return { sh: s.scrollHeight, ch: s.clientHeight, ov: cs.overflowY, items: s.querySelectorAll("button, [role=option], div").length };
  }).catch(() => null);
  notes.push("area list dims: " + JSON.stringify(dims));
  const qt = await page.locator("text=Queenstown").count();
  notes.push("Queenstown visible: " + qt);
  await page.screenshot({ path: "e2e/p5-wizard-location.png" });

  // 4) Source-connection warning: look for any warning text about sources
  const srcWarn = await page.locator("text=/not connected|not configured|needs setup|requires a connection|source.*warn|warn.*source/i").count();
  notes.push("source-connection warning text found: " + srcWarn);

  console.log("P5 NOTES:\n" + notes.join("\n"));
  console.log("CONSOLE/PAGE ERRORS:\n" + (CONSOLE_ERRORS.length ? CONSOLE_ERRORS.join("\n") : "(none)"));
  expect(true).toBe(true);
});
