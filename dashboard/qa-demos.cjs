const { chromium } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const tsv = fs.readFileSync("E:/build/Leads generation/evidence/demo-paths.tsv", "utf8");
const rows = tsv.trim().split("\n").map((l) => l.split("\t"));
const OUT = "E:/build/Leads generation/evidence/demo-screens";
fs.mkdirSync(OUT, { recursive: true });

const UNVERIFIED = [/\blaser\w*\b/i, /\bbest\b/i, /\bpaynow\b/i, /\bguranteed\b|\bguarantee\b/i, /\bestablished since\b/i, /\bspecialist\b/i];
const PLACEHOLDER = /demo@\w+\.example\.com|hello@\w+\.example\.com/;

async function main() {
  const browser = await chromium.launch();
  const results = [];
  for (const [theme, htmlPath] of rows) {
    if (!htmlPath || htmlPath === "NONE") continue;
    const html = fs.readFileSync(htmlPath, "utf8");
    const sizeKb = Buffer.byteLength(html, "utf8") / 1024;
    const fileUrl = "file:///" + htmlPath.replace(/\\/g, "/");
    for (const width of [390, 1440]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.goto(fileUrl, { waitUntil: "load" });
      await page.waitForTimeout(400);
      const metrics = await page.evaluate(() => ({
        scrollW: document.documentElement.scrollWidth,
        clientW: document.documentElement.clientWidth,
        h1: document.querySelectorAll("h1").length,
        sections: document.querySelectorAll("section").length,
        services: !!document.getElementById("h-services") || /h-services/.test(document.body.innerHTML),
        contact: !!document.getElementById("h-contact") || /h-contact/.test(document.body.innerHTML),
        hasCall: /href="tel:/.test(document.body.innerHTML),
        hasCta: /class="[^"]*btn/.test(document.body.innerHTML),
        text: document.body.innerText,
        bodyHtml: document.body.innerHTML,
        robots: !!document.querySelector('meta[name="robots"]'),
      }));
      const hScroll = metrics.scrollW > metrics.clientW + 1;
      const unverified = UNVERIFIED.filter((re) => re.test(metrics.text || "")).map((re) => re.toString());
      const placeholder = PLACEHOLDER.test(metrics.bodyHtml || "");
      const requiredSections = ["Services", "About", "Why", "Contact"];
      const missing = requiredSections.filter((s) => !(metrics.text || "").includes(s));
      const pass = !hScroll && metrics.h1 >= 1 && metrics.sections >= 3 && unverified.length === 0 && !placeholder && missing.length === 0 && sizeKb < 100;
      results.push({ theme, width, pass, hScroll, sizeKb: sizeKb.toFixed(1), unverified, placeholder, missing });
      const name = theme + "-" + width + ".png";
      await page.screenshot({ path: path.join(OUT, name), fullPage: false });
      await page.close();
    }
  }
  await browser.close();
  console.log("THEME\tWIDTH\tPASS\tHSCROLL\tKB\tUNVERIFIED\tPLACEHOLDER\tMISSING");
  let anyFail = false;
  for (const r of results) {
    if (!r.pass) anyFail = true;
    console.log(r.theme + "\t" + r.width + "\t" + (r.pass ? "PASS" : "FAIL") + "\t" + r.hScroll + "\t" + r.sizeKb + "\t" + r.unverified.join(",") + "\t" + r.placeholder + "\t" + r.missing.join(","));
  }
  console.log("SUMMARY: " + results.filter((r) => r.pass).length + "/" + results.length + " pass; " + (anyFail ? "FAILURES PRESENT" : "ALL PASS"));
  process.exit(anyFail ? 1 : 0);
}
main().catch((e) => { console.error(e); process.exit(2); });