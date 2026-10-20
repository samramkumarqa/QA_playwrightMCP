// @ts-check
const { CommonPage } = require("./CommonPage");
const repo = require("../object-repository/CheckoutStepOnePage.json");

/** /checkout-step-one.html — Practice Shop */
class CheckoutStepOnePage extends CommonPage {
  /** @param {import('@playwright/test').Page} page */
  constructor(page) {
    super(page, repo);
  }

  /** Input "First Name" */
  get firstNameInput() { return this.el("firstNameInput"); }

  /** Input "Last Name" */
  get lastNameInput() { return this.el("lastNameInput"); }

  /** Input "Zip/Postal Code" */
  get postalCodeInput() { return this.el("postalCodeInput"); }

  /** Text "error" (hidden until opened) */
  get errorText() { return this.el("errorText"); }

  /** Button "Cancel" */
  get cancelButton() { return this.el("cancelButton"); }

  /** Button "Continue" */
  get continueButton() { return this.el("continueButton"); }
}

module.exports = { CheckoutStepOnePage };
