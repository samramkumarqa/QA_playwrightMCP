# shop-project

Playwright (JavaScript) Page Object Model tests, generated on 2026-10-20 15:41
from 6 approved test cases and a crawl of http://localhost:8765.

## Setup

```bash
npm install
npx playwright install chromium
cp .env.example .env      # then set APP_USERNAME and APP_PASSWORD
```

## Run

```bash
npm test                  # headless
npm run test:headed       # watch it run
npm run test:ui           # Playwright UI mode
npm run report            # open the HTML report
```

### IntelliJ IDEA / WebStorm
Open this folder as a project, set **Settings → Languages & Frameworks → Node.js** to your Node
installation, then right-click `package.json` → *Show npm Scripts* and run `test`. With the
Playwright plugin (or WebStorm), tests can also be run from the gutter icons in the spec files.

## Structure

```
pages/              Page objects. BasePage resolves locators; CommonPage holds shared header/menu
                    elements; one class per crawled page (getters per element, LoginPage.login()).
object-repository/  Locators as JSON, one file per page. Fix a broken locator here, not in code.
tests/              One spec file per requirement, one test per test case.
fixtures/pages.js   Page objects as Playwright fixtures: async ({ loginPage, inventoryPage }) => ...
test-data/          TestData.xlsx: RunControl (Run Y/N per test) and TestData (key/value per test).
utils/testData.js   Reads TestData.xlsx.
playwright.config.js, .env.example, package.json
```

## Pages found

| Page object | URL | Elements |
|---|---|---|
| `CommonPage` | (every page) | 8 |
| `LoginPage` | `/index.html` | 5 |
| `InventoryPage` | `/inventory.html` | 9 |
| `CartPage` | `/cart.html` | 2 |
| `OrdersPage` | `/orders.html` | 1 |
| `ItemPage` | `/item.html` | 4 |
| `CheckoutStepOnePage` | `/checkout-step-one.html` | 6 |

Locator preference: `data-test` test IDs, then stable ids, then role + accessible
name, label, placeholder, then text. Every locator was checked to match exactly one element
when the page was crawled.

## Needs attention

Steps that couldn't be mapped to an element are left as `// TODO` comments in the specs.
Those tests still run their automated steps, then end as **fixme** (shown as skipped) until you
complete the TODOs and delete the `test.fixme(...)` line:

- **TC-005**: Check the product details (no specific value given)
- **TC-006**: Bogus step (no element 'noSuchElement' on CommonPage)

Links not followed during the crawl (kept read-only on purpose):

- None

Pages that only appear after submitting a form, or that need test data to exist, aren't reached
by the crawler; add them as page objects by hand if needed.
