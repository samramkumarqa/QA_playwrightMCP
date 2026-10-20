// @ts-check
// Generated from the approved test cases for FR-02.
const { test, expect } = require('../fixtures/pages');
const { getTestData, shouldRun } = require('../utils/testData');

test.describe("FR-02", () => {
  test("TC-003: Verify adding the backpack to the cart updates the cart badge", async ({ commonPage, inventoryPage, loginPage, page }) => {
    test.skip(!(await shouldRun("TC-003")), 'Run = N in test-data/TestData.xlsx');
    const data = await getTestData("TC-003");
    // Expected: The cart badge shows 1
    // User is logged in
    await loginPage.login();
    // Add the backpack to the cart
    await inventoryPage.waitForPage();
    await inventoryPage.addToCartBackpackButton.click();
    // Cart badge shows 1
    await expect(commonPage.shoppingCartBadgeText).toContainText(data.badgeCount);
  });
});
