// @ts-check
const { CommonPage } = require("./CommonPage");
const repo = require("../object-repository/InventoryPage.json");

/** /inventory.html — Practice Shop */
class InventoryPage extends CommonPage {
  /** @param {import('@playwright/test').Page} page */
  constructor(page) {
    super(page, repo);
  }

  /** Link "Trail Backpack" */
  get trailBackpackLink() { return this.el("trailBackpackLink"); }

  /** Text "$29.99" */
  get inventoryItemPriceText() { return this.el("inventoryItemPriceText"); }

  /** Button "Add to cart" */
  get addToCartBackpackButton() { return this.el("addToCartBackpackButton"); }

  /** Link "Bike Light" */
  get bikeLightLink() { return this.el("bikeLightLink"); }

  /** Text "$9.99" */
  get inventoryItemPriceText2() { return this.el("inventoryItemPriceText2"); }

  /** Button "Add to cart" */
  get addToCartBikeLightButton() { return this.el("addToCartBikeLightButton"); }

  /** Link "Bolt T-Shirt" */
  get boltTShirtLink() { return this.el("boltTShirtLink"); }

  /** Text "$15.99" */
  get inventoryItemPriceText3() { return this.el("inventoryItemPriceText3"); }

  /** Button "Add to cart" */
  get addToCartBoltTshirtButton() { return this.el("addToCartBoltTshirtButton"); }
}

module.exports = { InventoryPage };
