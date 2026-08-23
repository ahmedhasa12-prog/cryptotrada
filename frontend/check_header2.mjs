import pkg from '/Users/ahmedabdelwahid/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.js';
const { chromium } = pkg;
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.setViewportSize({ width: 390, height: 200 });
await page.goto('http://localhost:5173', { waitUntil: 'domcontentloaded', timeout: 15000 });
await page.waitForTimeout(3000);
await page.screenshot({ path: '/tmp/header2.png' });
// also print header HTML
const headerHTML = await page.locator('header.top-bar').innerHTML();
console.log('Header HTML:', headerHTML);
await browser.close();
