// @ts-check
const { CommonPage } = require("./CommonPage");
const repo = require("../object-repository/CartPage.json");

/** /cart.html — Practice Shop */
class CartPage extends CommonPage {
  /** @param {import('@playwright/test').Page} page */
  constructor(page) {
    super(page, repo);
  }

  /** Button "Continue Shopping" */
  get continueShoppingButton() { return this.el("continueShoppingButton"); }

  /** Button "Checkout" */
  get checkoutButton() { return this.el("checkoutButton"); }
}

module.exports = { CartPage };
