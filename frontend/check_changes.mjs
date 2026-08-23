import pkg from '/Users/ahmedabdelwahid/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.js';
const { chromium } = pkg;
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.setViewportSize({ width: 390, height: 844 });

// Check English tab order + header
await page.goto('http://localhost:8000', { waitUntil: 'domcontentloaded', timeout: 15000 });
await page.waitForTimeout(2000);
await page.screenshot({ path: '/tmp/en_tabs.png' });

// Switch to Arabic
await page.click('button.lang-btn');
await page.waitForTimeout(1000);
await page.screenshot({ path: '/tmp/ar_tabs.png' });

// Go to Spot tab (first) and check CoinDetail
await page.locator('.tab-btn').first().click();
await page.waitForTimeout(1000);
await page.screenshot({ path: '/tmp/ar_spot.png' });

await browser.close();
console.log('done');
