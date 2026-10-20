// Opens one page of the app with the project's own Playwright and lists its elements with
// working locators. Run from the project folder: node inspect_page.js <path> <login:0|1>
// Prints JSON to stdout. Credentials come from the project's .env and never leave this process.
const path = require('path');
const cwd = process.cwd();
const req = (m) => require(require.resolve(m, { paths: [cwd] }));

(async () => {
  const [, , target = '/', login = '1'] = process.argv;
  try { req('dotenv').config({ path: path.join(cwd, '.env') }); } catch (e) { /* optional */ }
  const { chromium, selectors } = req('@playwright/test');
  let cfg = {};
  try { cfg = require(path.join(cwd, 'playwright.config.js')); } catch (e) { /* defaults */ }
  const use = (cfg && cfg.use) || {};
  const baseURL = process.env.BASE_URL || use.baseURL || '';
  const testIdAttr = use.testIdAttribute || 'data-testid';
  selectors.setTestIdAttribute(testIdAttr);

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();
  const out = { requested: target, testIdAttribute: testIdAttr, loggedIn: false };
  try {
    if (login === '1') {
      let LoginPage;
      try { ({ LoginPage } = require(path.join(cwd, 'pages', 'LoginPage.js'))); } catch (e) { /* none */ }
      if (LoginPage) {
        await new LoginPage(page).login();
        out.loggedIn = true;
      }
    }
    await page.goto(target);
    await page.waitForLoadState('domcontentloaded');
    out.url = page.url();
    out.title = await page.title();
    const raw = await page.evaluate((attr) => {
      const sel = 'a,button,input,select,textarea,[role=button],[role=link],[role=tab],[role=checkbox],' +
        `h1,h2,h3,[${attr}],[data-testid],[data-test],[data-qa],[data-cy]`;
      const seen = new Set();
      const items = [];
      for (const el of document.querySelectorAll(sel)) {
        if (seen.has(el)) continue;
        seen.add(el);
        const r = el.getBoundingClientRect();
        const st = getComputedStyle(el);
        const visible = r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none';
        const text = (el.innerText || el.value || '').trim().replace(/\s+/g, ' ').slice(0, 60);
        const label = el.getAttribute('aria-label') || (el.labels && el.labels[0] && el.labels[0].innerText.trim()) ||
          el.getAttribute('placeholder') || '';
        items.push({
          tag: el.tagName.toLowerCase(), type: el.getAttribute('type') || '', text, label,
          testId: el.getAttribute(attr) || '', id: el.id || '', visible,
        });
        if (items.length >= 150) break;
      }
      return items;
    }, testIdAttr);
    const elements = [];
    for (const e of raw) {
      let locator = '';
      let count = 0;
      if (e.testId) { locator = `getByTestId('${e.testId}')`; count = await page.getByTestId(e.testId).count(); }
      else if (e.id) { locator = `locator('#${e.id}')`; count = await page.locator(`[id="${e.id}"]`).count(); }
      else if (e.label) { locator = `getByLabel('${e.label}')`; count = await page.getByLabel(e.label, { exact: true }).count(); }
      else if (e.text) { locator = `getByText('${e.text}')`; count = await page.getByText(e.text, { exact: true }).count(); }
      if (!locator) continue;
      elements.push({ ...e, locator, unique: count === 1, matches: count });
    }
    out.elements = elements;
  } catch (err) {
    out.error = String(err && err.message || err).split('\n')[0];
    out.url = page.url();
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify(out));
})();
