import { test, expect, type Page } from "@playwright/test";

const APP = process.env.APP_URL ?? "http://127.0.0.1:3006";

async function gotoCampaigns(page: Page) {
  await page.goto(APP + "/campaigns", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /campaigns/i }).first()).toBeVisible({ timeout: 15000 });
}

// M4: create a campaign through all 4 wizard steps with cascading dropdowns,
// then run it dry. Assumes backend on :8000 with geo dataset + validate endpoint.
test("create campaign through 4-step wizard and run dry", async ({ page }) => {
  await gotoCampaigns(page);
  await page.getByRole("button", { name: "New campaign" }).first().click();

  // --- Step 1: Basics ---
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("step 1 of 4")).toBeVisible();
  await page.getByLabel("Campaign name *").fill("Orchard Dental Clinics");
  // lead sources default google+osm; add apify
  await page.getByRole("checkbox", { name: "Apify scraper" }).click();
  await page.getByTestId("wiz-next").click();

  // --- Step 2: Location ---
  await expect(page.getByText("step 2 of 4")).toBeVisible();
  await expect(page.getByText("Suggested areas")).toBeVisible({ timeout: 15000 });
  // search narrowing
  await page.getByTestId("wiz-area-search").fill("Orchard");
  await expect(page.getByRole("button", { name: /^Orchard$/ }).first()).toBeVisible();
  await page.getByRole("button", { name: /^Orchard$/ }).first().click();
  // deselect search first to reveal others is unnecessary; add second town via manual
  await page.getByTestId("wiz-area-search").fill("");
  await page.getByTestId("wiz-manual-area").fill("Tampines");
  await page.getByRole("button", { name: "Add" }).click();
  await expect(page.getByText("Tampines", { exact: true }).first()).toBeVisible();
  await page.getByTestId("wiz-next").click();

  // --- Step 3: Business types ---
  await expect(page.getByText("step 3 of 4")).toBeVisible();
  await page.getByTestId("wiz-cat-search").fill("clinic");
  await page.getByRole("checkbox", { name: "Clinic" }).click();
  await page.getByTestId("wiz-cat-search").fill("");
  await page.getByTestId("wiz-next").click();

  // --- Step 4: Outreach & limits ---
  await expect(page.getByText("step 4 of 4")).toBeVisible();
  await page.getByLabel("Daily email cap").fill("12");
  await page.getByLabel("Max leads / run").fill("50");
  await page.getByTestId("wiz-review").click();

  // --- Review ---
  await expect(page.getByRole("heading", { name: "Review your campaign" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Create & start/ })).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole("button", { name: /Create & start/ })).toBeVisible({ timeout: 15000 });
  await page.getByTestId("wiz-create-run").scrollIntoViewIfNeeded();
  await page.getByTestId("wiz-create-run").click();
  await expect(page.getByText("Campaign created")).toBeVisible({ timeout: 15000 });
  await expect(page).toHaveURL(/\/campaigns/);

  // New campaign appears on the list
  await expect(page.locator("main").getByText("Orchard Dental Clinics", { exact: true }).first()).toBeVisible({ timeout: 15000 });
});
