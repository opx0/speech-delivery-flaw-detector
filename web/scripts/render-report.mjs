import { readFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { execFileSync } from 'node:child_process';
import { chromium } from 'playwright';

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  throw new Error('Usage: node web/scripts/render-report.mjs input.html output.pdf');
}

const content = await readFile(input, 'utf8');
await mkdir(dirname(output), { recursive: true });
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">
    <style>
      body { font-family: Arial, sans-serif; font-size: 10pt; line-height: 1.35; color: #222; }
      h1 { font-size: 18pt; }
      h2 { font-size: 12pt; margin-top: 18pt; break-after: avoid; }
      table { border-collapse: collapse; width: 100%; font-size: 9pt; }
      th, td { border: 1px solid #bbb; padding: 5pt; text-align: left; }
      tr { break-inside: avoid; }
      code { font-size: 8pt; overflow-wrap: anywhere; }
      pre { white-space: pre-wrap; }
      a { color: #234; overflow-wrap: anywhere; }
    </style></head><body>${content}</body></html>`);
  await page.pdf({ path: output, format: 'A4', margin: { top: '15mm', right: '15mm', bottom: '15mm', left: '15mm' } });
} finally {
  await browser.close();
}

const info = execFileSync('pdfinfo', [output], { encoding: 'utf8' });
const pages = Number(info.match(/^Pages:\s+(\d+)/m)?.[1]);
if (!Number.isInteger(pages) || pages < 1 || pages > 6) {
  throw new Error(`Report exceeds the six-page limit or page count is invalid: ${pages}`);
}
console.log(`${output}: ${pages} pages, within the six-page limit.`);
