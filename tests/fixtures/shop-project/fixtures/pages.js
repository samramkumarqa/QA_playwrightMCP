// @ts-check
/**
 * Page object fixtures: a test asks for { loginPage, inventoryPage, ... } by name
 * and gets a ready instance.
 */
const base = require('@playwright/test');
const { CommonPage } = require('../pages/CommonPage');
const { LoginPage } = require('../pages/LoginPage');
const { InventoryPage } = require('../pages/InventoryPage');
const { CartPage } = require('../pages/CartPage');
const { OrdersPage } = require('../pages/OrdersPage');
const { ItemPage } = require('../pages/ItemPage');
const { CheckoutStepOnePage } = require('../pages/CheckoutStepOnePage');

const test = base.test.extend({
  commonPage: async ({ page }, use) => { await use(new CommonPage(page)); },
  loginPage: async ({ page }, use) => { await use(new LoginPage(page)); },
  inventoryPage: async ({ page }, use) => { await use(new InventoryPage(page)); },
  cartPage: async ({ page }, use) => { await use(new CartPage(page)); },
  ordersPage: async ({ page }, use) => { await use(new OrdersPage(page)); },
  itemPage: async ({ page }, use) => { await use(new ItemPage(page)); },
  checkoutStepOnePage: async ({ page }, use) => { await use(new CheckoutStepOnePage(page)); },
});

module.exports = { test, expect: base.expect };
