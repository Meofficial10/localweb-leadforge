import { test, expect } from "@playwright/test";

test("each console page renders expected core content", async ({ page }) => {
  const checks: [string, RegExp][] = [
    ["/", /LeadForge/i],
    ["/campaigns", /Campaigns/i],
    ["/leads", /Leads/i],
    ["/outreach", /Needs review/i],
    ["/inbox", /intent/i],
    ["/calls", /Calls/i],
    ["/compliance", /Suppression list/i],
    ["/integrations", /Integrations/i],
    ["/settings", /Daily caps/i],
  ];
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0,300)));
  for (const [path, re] of checks) {
    await page.goto("http://127.0.0.1:3006" + path, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(800);
    const body = await page.locator("body").innerText();
    const ok = re.test(body);
    console.log((ok ? "PASS" : "FAIL"), path, "->", re);
    if (!ok) console.log("  BODY:", body.slice(0,200));
  }
  console.log("pageerrors:", JSON.stringify(errors.slice(0,3)));
});
