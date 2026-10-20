// @ts-check
const { BasePage } = require("./BasePage");
const repo = require("../object-repository/LoginPage.json");

/** /index.html — Practice Shop */
class LoginPage extends BasePage {
  /** @param {import('@playwright/test').Page} page */
  constructor(page) {
    super(page, repo);
  }

  /** Text "Practice Shop" */
  get practiceShopText() { return this.el("practiceShopText"); }

  /** Input "Username" */
  get usernameInput() { return this.el("usernameInput"); }

  /** Input "Password" */
  get passwordInput() { return this.el("passwordInput"); }

  /** Text "error" (hidden until opened) */
  get errorText() { return this.el("errorText"); }

  /** Button "Login" */
  get loginButton() { return this.el("loginButton"); }

  /**
   * Log in. Defaults to APP_USERNAME / APP_PASSWORD from .env.
   * @param {string} [username]
   * @param {string} [password]
   */
  async login(username = process.env.APP_USERNAME ?? '', password = process.env.APP_PASSWORD ?? '') {
    if (!username || !password) {
      throw new Error('No login credentials: copy .env.example to .env and set APP_USERNAME and APP_PASSWORD');
    }
    await this.goto();
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
    // Fail here with a clear message, not 30 s later on the next page's first step.
    await this.passwordInput.waitFor({ state: 'hidden', timeout: 10_000 }).catch(() => {
      throw new Error(`Login as "${username}" didn't succeed: still on the login page. Check APP_USERNAME / APP_PASSWORD in .env`);
    });
  }
}

module.exports = { LoginPage };
