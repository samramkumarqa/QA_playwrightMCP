// @ts-check
// Generated from the approved test cases for FR-04.
const { test, expect } = require('../fixtures/pages');
const { getTestData, shouldRun } = require('../utils/testData');

test.describe("FR-04", () => {
  test("TC-005: Verify the product details page opens from the product list", async ({ inventoryPage, itemPage, loginPage, page }) => {
    test.skip(!(await shouldRun("TC-005")), 'Run = N in test-data/TestData.xlsx');
    const data = await getTestData("TC-005");
    // Expected: Product name is shown on the details page; Back to products returns to the Products page
    // User is logged in
    await loginPage.login();
    // Click the backpack product name
    await inventoryPage.waitForPage();
    await inventoryPage.trailBackpackLink.click();
    // Product name is shown
    await itemPage.waitForPage();
    await expect(itemPage.inventoryItemNameText).toBeVisible();
    // Click Back to products
    await itemPage.backToProductsButton.click();
    // Back on the Products page
    await expect(page).toHaveURL(new RegExp("inventory"));
    // TODO (not automated): Check the product details (no specific value given)
    test.fixme(true, "1 step(s) not automated yet: complete the TODOs above");
  });
});
