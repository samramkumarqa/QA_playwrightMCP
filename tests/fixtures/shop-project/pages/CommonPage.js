// @ts-check
const { BasePage } = require('./BasePage');
const commonRepo = require('../object-repository/CommonPage.json');

/**
 * Elements shared by the pages after login (header, menu, cart ...).
 * Every page class extends this, so these getters are available on all of them.
 */
class CommonPage extends BasePage {
  /**
   * @param {import('@playwright/test').Page} page
   * @param {any} [repo] the page's own object repository
   */
  constructor(page, repo = commonRepo) {
    super(page, { ...repo, elements: { ...commonRepo.elements, ...repo.elements } });
  }

  /** Button "Open Menu" */
  get openMenuButton() { return this.el("openMenuButton"); }

  /** Button "Cart" */
  get shoppingCartLink() { return this.el("shoppingCartLink"); }

  /** Text "0" (hidden until opened) */
  get shoppingCartBadgeText() { return this.el("shoppingCartBadgeText"); }

  /** Button "All Items" (hidden until opened) */
  get inventorySidebarLink() { return this.el("inventorySidebarLink"); }

  /** Button "Orders" (hidden until opened) */
  get ordersSidebarLink() { return this.el("ordersSidebarLink"); }

  /** Button "Logout" (hidden until opened) */
  get logoutSidebarLink() { return this.el("logoutSidebarLink"); }

  /** Button "Reset App State" (hidden until opened) */
  get resetSidebarLink() { return this.el("resetSidebarLink"); }

  /** Text "Products" */
  get titleText() { return this.el("titleText"); }
}

module.exports = { CommonPage };
