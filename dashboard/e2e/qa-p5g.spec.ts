import { test } from "@playwright/test";
test.use({ baseURL: "http://127.0.0.1:3006" });
test("two-input keystroke probe", async ({ page }) => {
  const notes: string[] = [];
  await page.goto("/campaigns", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "New campaign" }).first().click();
  await page.waitForSelector("#wiz-name");
  const nameEl = page.locator("#wiz-name");
  await nameEl.click();
  await nameEl.pressSequentially("Hello", { delay: 60 });
  await page.waitForTimeout(300);
  const nameState = await page.evaluate(() => {
    const el = document.getElementById("wiz-name") as HTMLInputElement | null;
    return { val: el ? el.value : null, active: document.activeElement ? document.activeElement.tagName + "#" + document.activeElement.id : "NONE" };
  });
  notes.push("NAME after typing Hello: " + JSON.stringify(nameState));
  const ta = page.locator("textarea");
  await ta.click();
  await ta.pressSequentially("World", { delay: 60 });
  await page.waitForTimeout(300);
  const taState = await page.evaluate(() => {
    const t = document.querySelector("textarea") as HTMLTextAreaElement | null;
    return { val: t ? t.value : null, active: document.activeElement ? document.activeElement.tagName + "#" + document.activeElement.id : "NONE" };
  });
  notes.push("TEXTAREA after typing World: " + JSON.stringify(taState));
  await nameEl.click();
  await nameEl.pressSequentially("XYZ", { delay: 60 });
  await page.waitForTimeout(200);
  const nameState2 = await page.evaluate(() => {
    const el = document.getElementById("wiz-name") as HTMLInputElement | null;
    return { val: el ? el.value : null, active: document.activeElement ? document.activeElement.tagName + "#" + document.activeElement.id : "NONE" };
  });
  notes.push("NAME2 after XYZ: " + JSON.stringify(nameState2));
  console.log("2IN:\n" + notes.join("\n"));
});
