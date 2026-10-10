import { test } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:3006" });

test("char-by-char description typing diagnostic", async ({ page }) => {
  const logs: string[] = [];
  page.on("pageerror", (e) => logs.push("PAGEERROR: " + e.message));
  page.on("console", (m) => { if (m.type() === "error") logs.push("CONSOLE: " + m.text()); });

  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name");
  const ta = page.locator("textarea");
  await ta.click();
  await ta.pressSequentially("A", { delay: 100 });
  await page.waitForTimeout(150);
  logs.push("after 1 char: " + JSON.stringify(await ta.inputValue()));
  await ta.pressSequentially("B", { delay: 100 });
  await page.waitForTimeout(150);
  logs.push("after 2 chars: " + JSON.stringify(await ta.inputValue()));
  await ta.pressSequentially("C", { delay: 100 });
  await page.waitForTimeout(150);
  logs.push("after 3 chars: " + JSON.stringify(await ta.inputValue()));
  await page.keyboard.type("typed-events", { delay: 40 });
  await page.waitForTimeout(300);
  logs.push("after keyboard.type: " + JSON.stringify(await ta.inputValue()));
  await ta.fill("full-fill-value");
  await page.waitForTimeout(200);
  logs.push("after fill: " + JSON.stringify(await ta.inputValue()));
  await page.screenshot({ path: "e2e/p5-typing.png" });
  console.log("TYPNOTES:\n" + logs.join("\n"));
});
