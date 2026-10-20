// @ts-check
const { CommonPage } = require("./CommonPage");
const repo = require("../object-repository/ItemPage.json");

/** /item.html — Practice Shop */
class ItemPage extends CommonPage {
  /** @param {import('@playwright/test').Page} page */
  constructor(page) {
    super(page, repo);
  }

  /** Button "Back to products" */
  get backToProductsButton() { return this.el("backToProductsButton"); }

  /** Text "Trail Backpack" */
  get inventoryItemNameText() { return this.el("inventoryItemNameText"); }

  /** Text "$29.99" */
  get inventoryItemPriceText() { return this.el("inventoryItemPriceText"); }

  /** Button "Add to cart" */
  get addToCartBackpackButton() { return this.el("addToCartBackpackButton"); }
}

module.exports = { ItemPage };
