// @ts-check
const { CommonPage } = require("./CommonPage");
const repo = require("../object-repository/OrdersPage.json");

/** /orders.html — Practice Shop */
class OrdersPage extends CommonPage {
  /** @param {import('@playwright/test').Page} page */
  constructor(page) {
    super(page, repo);
  }

  /** Text "No orders yet" */
  get ordersEmptyText() { return this.el("ordersEmptyText"); }
}

module.exports = { OrdersPage };
