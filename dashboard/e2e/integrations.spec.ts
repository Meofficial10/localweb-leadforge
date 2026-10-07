"use strict";
import { test, expect } from "@playwright/test";
const BASE = "http://127.0.0.1:3006";


test("integrations page shows health summary and all cards", async ({ page }) => {
  await page.goto(BASE + "/integrations", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Integrations", exact: true })).toBeVisible();
  await expect(page.getByText(/of [0-9]+ required integrations working/i).first()).toBeVisible({ timeout: 15000 });
  for (const id of ["llm","places","osm","apify","hosting","email","identity","voice","dnc"]) {
    await expect(page.getByTestId("integration-" + id)).toBeVisible();
  }
},);


test("configure sender identity and see it go green", async ({ page }) => {
  await page.goto(BASE + "/integrations", { waitUntil: "networkidle" });
  const card = page.getByTestId("integration-identity");
  await expect(card).toBeVisible({ timeout: 15000 });
  await card.getByRole("button", { name: /configure/i }).click();
  await page.getByLabel("Sender name").fill("Alice Tan");
  await page.getByLabel("Sender email").fill("alice@example.com");
  await page.getByLabel("Physical address").fill("1 Marina Boulevard, Singapore");
  await page.getByRole("button", { name: /save & test connection/i }).click();
  await expect(page.getByTestId("integration-identity").getByText("Connected")).toBeVisible({ timeout: 15000 });
});
