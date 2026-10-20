// @ts-check
/**
 * Base class for every page object.
 * Locators live in the object repository (object-repository/*.json), not in code,
 * so a changed locator is fixed in one JSON file.
 */
class BasePage {
  /**
   * @param {import('@playwright/test').Page} page
   * @param {{ page: string, url: string, elements: Record<string, any> }} repo
   */
  constructor(page, repo) {
    this.page = page;
    this.repo = repo;
  }

  /** Open this page (URL is relative to BASE_URL in .env). */
  async goto() {
    if (!this.repo.url) throw new Error(`${this.repo.page} has no URL`);
    await this.page.goto(this.repo.url);
  }

  /**
   * Wait until the browser is on this page. Specs call it after a click that navigates,
   * so the next step doesn't run against the previous page while it is still unloading.
   */
  async waitForPage() {
    if (!this.repo.url) return;
    const path = this.repo.url
      .split(':id')
      .map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .join('[^/?#]+');
    await this.page.waitForURL(new RegExp(`${path}(?:[?#].*)?$`, 'i'));
  }

  /**
   * Playwright locator for an element in the object repository.
   * @param {string} name
   * @returns {import('@playwright/test').Locator}
   */
  el(name) {
    const e = this.repo.elements[name];
    if (!e) throw new Error(`Element "${name}" is not in the ${this.repo.page} object repository`);
    switch (e.strategy) {
      case 'testId': return this.page.getByTestId(e.value);
      case 'role': return this.page.getByRole(e.role, { name: e.value, exact: true });
      case 'label': return this.page.getByLabel(e.value, { exact: true });
      case 'placeholder': return this.page.getByPlaceholder(e.value, { exact: true });
      case 'text': return this.page.getByText(e.value, { exact: true });
      default: return this.page.locator(e.value);
    }
  }
}

module.exports = { BasePage };
