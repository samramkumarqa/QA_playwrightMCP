// @ts-check
// Generated from the approved test cases for FR-03.
const { test, expect } = require('../fixtures/pages');
const { getTestData, shouldRun } = require('../utils/testData');

test.describe("FR-03", () => {
  test("TC-004: Verify checkout requires the first name", async ({ cartPage, checkoutStepOnePage, commonPage, inventoryPage, loginPage, page }) => {
    test.skip(!(await shouldRun("TC-004")), 'Run = N in test-data/TestData.xlsx');
    const data = await getTestData("TC-004");
    // Expected: Error 'Error: First Name is required' is shown
    // User is logged in
    await loginPage.login();
    // Add the backpack
    await inventoryPage.waitForPage();
    await inventoryPage.addToCartBackpackButton.click();
    // Open the cart
    await commonPage.shoppingCartLink.click();
    // Click Checkout
    await cartPage.waitForPage();
    await cartPage.checkoutButton.click();
    // Enter last name
    await checkoutStepOnePage.waitForPage();
    await checkoutStepOnePage.lastNameInput.fill(data.lastName);
    // Enter postal code
    await checkoutStepOnePage.postalCodeInput.fill(data.postalCode);
    // Click Continue
    await checkoutStepOnePage.continueButton.click();
    // First name error shown
    await expect(checkoutStepOnePage.errorText).toContainText(data.expectedError);
  });
});
