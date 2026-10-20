// @ts-check
// Generated from the approved test cases for FR-01.
const { test, expect } = require('../fixtures/pages');
const { getTestData, shouldRun } = require('../utils/testData');

test.describe("FR-01", () => {
  test("TC-001: Verify successful login with valid credentials", async ({ inventoryPage, loginPage, page }) => {
    test.skip(!(await shouldRun("TC-001")), 'Run = N in test-data/TestData.xlsx');
    const data = await getTestData("TC-001");
    // Expected: The Products page is displayed
    // Open the login page
    await loginPage.goto();
    // Enter username
    await loginPage.usernameInput.fill(data.username);
    // Enter password
    await loginPage.passwordInput.fill(data.password);
    // Click the Login button
    await loginPage.loginButton.click();
    // Products page is displayed
    await expect(page).toHaveURL(new RegExp("inventory"));
    // Products are listed
    await inventoryPage.waitForPage();
    await expect(inventoryPage.addToCartBackpackButton).toBeVisible();
  });

  test("TC-002: Verify a locked out user cannot log in", async ({ loginPage, page }) => {
    test.skip(!(await shouldRun("TC-002")), 'Run = N in test-data/TestData.xlsx');
    const data = await getTestData("TC-002");
    // Expected: Error 'Epic sadface: Sorry, this user has been locked out.' is shown
    // Open the login page
    await loginPage.goto();
    // Enter locked out username
    await loginPage.usernameInput.fill(data.username);
    // Enter password
    await loginPage.passwordInput.fill(data.password);
    // Click Login
    await loginPage.loginButton.click();
    // Locked out error shown
    await expect(loginPage.errorText).toContainText(data.expectedError);
  });
});
