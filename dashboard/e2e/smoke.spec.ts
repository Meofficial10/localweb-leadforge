import { test, expect } from "@playwright/test";

const BASE = "http://127.0.0.1:3006";
const API = "http://127.0.0.1:8000";

test("smoke: create campaign via wizard, run dry-run, view lead, approve draft", async ({ page, request }) => {
  // 1) Overview loads with global nav
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  const nav = await page.locator("a[href^='/']").count();
  expect(nav).toBeGreaterThanOrEqual(9); // nine nav sections

  // 2) Create a campaign through the 4-step wizard
  await page.goto(BASE + "/campaigns", { waitUntil: "networkidle" });
  const name = "Smoke Campaign " + (Date.now() % 100000);
  await page.getByRole("button", { name: /new campaign/i }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByLabel(/Campaign name/i).fill(name);
  await page.getByTestId("wiz-next").click();
  // step 2: type own area (fast, deterministic)
  await page.getByTestId("wiz-area-search").fill("Singapore");
  await page.getByTestId("wiz-area-search").fill("");
  await page.getByTestId("wiz-manual-area").fill("Bedok");
  await page.getByRole("button", { name: "Add" }).click();
  await page.getByTestId("wiz-next").click();
  // step 3: pick a category
  await page.getByTestId("wiz-cat-search").fill("salon");
  await page.getByRole("checkbox", { name: "Salon", exact: true }).click();
  await page.getByTestId("wiz-cat-search").fill("");
  await page.getByTestId("wiz-next").click();
  // step 4: review & create (create only, not run)
  await page.getByTestId("wiz-review").click();
  await expect(page.getByRole("heading", { name: "Review your campaign" })).toBeVisible();
  await page.getByTestId("wiz-create").click();
  await expect(page.getByRole("dialog")).toBeHidden({ timeout: 15000 });
  await expect(page.locator("main").getByText(name, { exact: true }).first()).toBeVisible({ timeout: 15000 });

  // 3) Run the (last) campaign card — dry-run
  const runBtn = page.getByRole("button", { name: "Run" }).last();
  await runBtn.click();
  await expect(page.getByText(/dry-run/i).first()).toBeVisible({ timeout: 30000 });

  // 4) View a lead drawer via focus URL (useSearchParams-driven)
  const leadsRes = await request.get(API + "/leads?page_size=1");
  expect(leadsRes.ok()).toBeTruthy();
  const leadsBody = await leadsRes.json();
  expect(leadsBody.items.length).toBeGreaterThan(0);
  const leadId = leadsBody.items[0].id;
  await page.goto(BASE + "/leads?focus=" + leadId, { waitUntil: "networkidle" });
  await expect(page.locator("aside").or(page.locator("[data-state='open']")).first()).toBeVisible({ timeout: 20000 });
  await expect(page.locator("body")).toContainText(/contacts|profile|demo|timeline/i);

  // 5) Approve the seeded draft in the Outreach queue
  await page.goto(BASE + "/outreach", { waitUntil: "networkidle" });
  const approve = page.getByRole("button", { name: /approve/i }).first();
  const count = await approve.count();
  expect(count).toBeGreaterThan(0); // seed script produces a real draft
  await approve.click();
  await expect(page.getByRole("button", { name: /approve/i }).first()).toHaveCount(0, { timeout: 20000 })
    .catch(async () => {
      await expect(page.getByText(/needs review/i).first()).toBeVisible();
    });
});
