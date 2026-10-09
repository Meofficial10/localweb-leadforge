const { test, expect } = require("@playwright/test");

test("LLM drawer shows Playground and custom providers", async ({ page }) => {
  await page.goto("http://127.0.0.1:3006/integrations", { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  const llmCard = page.getByText("LLM", { exact: false }).first();
  // click configure for the LLM card - find the card by role
  const cfgBtn = page.locator("div.rounded-lg").filter({ hasText: "LLM" }).first().getByRole("button", { name: /configure/i });
  await cfgBtn.click().catch(async () => { await page.getByRole("button", { name: /configure/i }).last().click(); });
  await page.waitForTimeout(1200);
  const drawer = await page.locator("[role=dialog]").innerText().catch(()=> "");
  console.log("DRAWER_TEXT:", drawer.slice(0, 1500).replace(/\s+/g," "));
  console.log("HAS_PLAYGROUND:", drawer.includes("Playground"));
  console.log("HAS_CUSTOM:", drawer.includes("Custom OpenAI-compatible providers"));
  console.log("HAS_FETCH_MODELS:", drawer.includes("Fetch model list"));
});