"use strict";
import { test, expect } from "@playwright/test";
import { execFileSync } from "child_process";
import { createServer } from "http";

const BASE = "http://127.0.0.1:3006";

/** Tiny streaming mock that answers GET <base>/api/tags as a local Ollama. */
function startMockOllama() {
  return new Promise<{ port: number; close: () => void }>((resolve) => {
    const server = createServer((req, res) => {
      const url = req.url || "";
      res.setHeader("Content-Type", "application/json");
      if (url.endsWith("/api/tags")) {
        res.end(JSON.stringify({
          models: [
            { name: "qwen2.5:7b", modified_at: "2026-01-01T00:00:00Z" },
            { name: "llama3.2:3b", modified_at: "2026-01-01T00:00:00Z" },
          ],
        }));
        return;
      }
      res.statusCode = 404;
      res.end(JSON.stringify({ error: "not found" }));
    });
    server.listen(0, "127.0.0.1", () => {
      const port = (server.address() as { port: number }).port;
      resolve({ port, close: () => server.close() });
    });
  });
}

function reseedDemo() {
  const root = "E:\\build\\Leads generation\\backend";
  try {
    execFileSync(
      "C:\\Users\\Core_i\\AppData\\Local\\Programs\\DeepSeek Harness\\resources\\app.asar\\dsh\\..\\..\\..\\..\\..\\.venv\\Scripts\\python.exe",
      ["-m", "scripts.reset_db", "--seed"],
      { cwd: root, shell: false, stdio: "pipe" }
    );
  } catch (e) {
    // fallback: resolve the backend venv relative to cwd via full path
    const back = "E:\\build\\Leads generation\\backend";
    execFileSync(
      "E:\\build\\Leads generation\\backend\\.venv\\Scripts\\python.exe",
      ["-m", "scripts.reset_db", "--seed"],
      { cwd: back, shell: false, stdio: "pipe" }
    );
  }
}

test("configure Ollama (mocked HTTP) reports Connected", async ({ page }) => {
  const mock = await startMockOllama();
  try {
    await page.goto(BASE + "/integrations", { waitUntil: "networkidle" });
    const card = page.getByTestId("integration-llm");
    await expect(card).toBeVisible({ timeout: 15000 });
    await card.getByRole("button", { name: /configure/i }).click();
    await page.getByRole("combobox", { name: "Provider", exact: true }).click();
    await page.getByRole("option", { name: /Ollama/ }).click();
    await page.getByLabel("Base URL").fill("http://127.0.0.1:" + mock.port);
    // use the inline "Test connection" (not save) with unsaved values
    await page.getByRole("button", { name: /^Test connection$/ }).click();
    await expect(page.getByRole("dialog").getByText(/Ollama connected/i)).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("dialog").getByText(/qwen2.5:7b/)).toBeVisible({ timeout: 15000 });
  } finally {
    mock.close();
  }
});

test("wrong Ollama URL shows a clear Failed state", async ({ page }) => {
  await page.goto(BASE + "/integrations", { waitUntil: "networkidle" });
  const card = page.getByTestId("integration-llm");
  await expect(card).toBeVisible({ timeout: 15000 });
  await card.getByRole("button", { name: /configure/i }).click();
  await page.getByRole("combobox", { name: "Provider", exact: true }).click();
  await page.getByRole("option", { name: /Ollama/ }).click();
  // port 1 is never listening -> connection refused quickly
  await page.getByLabel("Base URL").fill("http://127.0.0.1:1");
  await page.getByRole("button", { name: /^Test connection$/ }).click();
  await expect(page.getByRole("dialog").getByText(/Ollama not running/i)).toBeVisible({ timeout: 20000 });
});

test("custom LLM provider exposes Base URL, key, model and headers", async ({ page }) => {
  await page.goto(BASE + "/integrations", { waitUntil: "networkidle" });
  const card = page.getByTestId("integration-llm");
  await expect(card).toBeVisible({ timeout: 15000 });
  await card.getByRole("button", { name: /configure/i }).click();
  await page.getByRole("combobox", { name: "Provider", exact: true }).click();
  await page.getByRole("option", { name: /Custom \(OpenAI-compatible\)/ }).click();
  await expect(page.getByLabel("Base URL")).toBeVisible();
  await expect(page.getByLabel(/API key/)).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Model", exact: true })).toBeVisible();
  await expect(page.getByLabel(/Model name/)).toBeVisible();
  await expect(page.getByLabel(/Extra headers/)).toBeVisible();
});

test("mock LLM provider is labelled demo and never reports a real connection", async ({ page }) => {
  await page.goto(BASE + "/integrations", { waitUntil: "networkidle" });
  const card = page.getByTestId("integration-llm");
  await expect(card).toBeVisible({ timeout: 15000 });
  await card.getByRole("button", { name: /configure/i }).click();
  await page.getByRole("combobox", { name: "Provider", exact: true }).click();
  await page.getByRole("option", { name: /Mock \(demo\)/ }).click();
  await page.getByRole("button", { name: /^Test connection$/ }).click();
  await expect(page.getByRole("dialog").getByText(/Mock, no real service/i)).toBeVisible({ timeout: 15000 });
  // card itself shows the DEMO DATA badge once the provider is mock
  await page.getByRole("button", { name: /save & test connection/i }).click();
  await expect(page.getByTestId("integration-llm").getByText("DEMO DATA", { exact: true })).toBeVisible({ timeout: 15000 });
});

test("demo banner is visible on overview and Clear demo data works", async ({ page }) => {
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  const banner = page.getByRole("alert", { name: "Demo data present" });
  await expect(banner).toBeVisible({ timeout: 15000 });
  await banner.getByRole("button", { name: /Clear demo data/ }).click();
  // confirm dialog
  await page.getByRole("alertdialog").getByRole("button", { name: /^Clear demo data$/ }).click();
  await expect(page.getByText(/Demo data cleared/i)).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole("alert", { name: "Demo data present" })).toHaveCount(0, { timeout: 15000 });
  // leads page shows an empty state (no demo leads)
  await page.goto(BASE + "/leads", { waitUntil: "networkidle" });
  await expect(page.getByText(/no .* leads/i).first()).toBeVisible({ timeout: 15000 });
  reseedDemo();
});
