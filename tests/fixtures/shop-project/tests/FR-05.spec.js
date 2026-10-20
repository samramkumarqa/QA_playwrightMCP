// @ts-check
// Generated from the approved test cases for FR-05.
const { test, expect } = require('../fixtures/pages');
const { getTestData, shouldRun } = require('../utils/testData');

test.describe("FR-05", () => {
  test("TC-006: Verify the user can log out", async ({ commonPage, loginPage, page }) => {
    test.skip(!(await shouldRun("TC-006")), 'Run = N in test-data/TestData.xlsx');
    const data = await getTestData("TC-006");
    // Expected: The login page is shown
    // User is logged in
    await loginPage.login();
    // Open the menu
    await commonPage.openMenuButton.click();
    // Click Logout
    await commonPage.logoutSidebarLink.click();
    // Login page is shown
    await loginPage.waitForPage();
    await expect(loginPage.loginButton).toBeVisible();
    // TODO (not automated): Bogus step (no element 'noSuchElement' on CommonPage)
    test.fixme(true, "1 step(s) not automated yet: complete the TODOs above");
  });
});
