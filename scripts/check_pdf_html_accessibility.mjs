import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";

const target = process.argv[2];
if (!target) {
  console.error("Usage: npm run test:a11y -- <URL>");
  process.exit(2);
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.emulateMedia({ media: "print" });
  await page.goto(target, { waitUntil: "networkidle" });

  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter(
    ({ impact }) => impact === "critical" || impact === "serious",
  );

  if (blocking.length > 0) {
    for (const violation of blocking) {
      console.error(`${violation.impact}: ${violation.id} - ${violation.help}`);
      for (const node of violation.nodes) {
        console.error(`  ${node.target.join(", ")}: ${node.failureSummary}`);
      }
    }
    process.exitCode = 1;
  } else {
    console.log("PDF HTML has no serious or critical axe violations.");
  }
} finally {
  await browser.close();
}
