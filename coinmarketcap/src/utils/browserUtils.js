const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
const { getProxyArgs } = require("./proxyUtils");
const config = require("../config");

// Use stealth plugin to avoid detection
puppeteer.use(StealthPlugin());

/**
 * Sleep function
 */
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Launch browser with configured settings
 */
async function launchBrowser(proxy) {
  const browserArgs = [
    ...config.BROWSER_CONFIG.defaultArgs,
    // ...getProxyArgs(proxy),
  ];

  console.log(
    `🌐 Launching browser${
      proxy ? ` with proxy: ${proxy.ip}:${proxy.port}` : ""
    }`
  );

  const browser = await puppeteer.launch({
    headless: config.BROWSER_CONFIG.headless,
    args: browserArgs,
    defaultViewport: config.BROWSER_CONFIG.defaultViewport,
    protocolTimeout: config.BROWSER_CONFIG.protocolTimeout,
  });

  return browser;
}

/**
 * Create and configure new page
 */
async function createPage(browser) {
  const page = await browser.newPage();
  await page.setUserAgent(config.BROWSER_CONFIG.userAgent);
  page.setDefaultNavigationTimeout(config.TIMEOUTS.DEFAULT_NAVIGATION);
  return page;
}

/**
 * Safely navigate to URL with retry
 */
async function navigateToUrl(page, url, options = {}) {
  const maxRetries = options.maxRetries || 2;
  const waitUntil = options.waitUntil || "networkidle2";
  const timeout = options.timeout || config.TIMEOUTS.DEFAULT_NAVIGATION;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      await page.goto(url, { waitUntil, timeout });
      return true;
    } catch (err) {
      console.error(
        `❌ Navigation error (attempt ${attempt}/${maxRetries}): ${err.message}`
      );
      if (attempt === maxRetries) return false;
      await sleep(3000);
    }
  }

  return false;
}

/**
 * Safely click an element with retry
 */
async function safeClick(page, selector, options = {}) {
  const { timeout = config.TIMEOUTS.DEFAULT_ELEMENT_WAIT, visible = true } =
    options;

  try {
    await page.waitForSelector(selector, { timeout, visible });
    await page.click(selector);
    return true;
  } catch (error) {
    console.error(`❌ Error clicking element ${selector}: ${error.message}`);
    return false;
  }
}

/**
 * Safely click using XPath
 */
async function safeClickByXPath(page, xpath) {
  try {
    const elements = await page.$x(xpath);
    if (elements.length > 0) {
      await elements[0].click();
      return true;
    }
    return false;
  } catch (error) {
    console.error(`❌ Error clicking XPath ${xpath}: ${error.message}`);
    return false;
  }
}

/**
 * Type text into an element
 */
async function safeType(page, selector, text, options = {}) {
  const { timeout = config.TIMEOUTS.DEFAULT_ELEMENT_WAIT, visible = true } =
    options;

  try {
    await page.waitForSelector(selector, { timeout, visible });
    await page.type(selector, text);
    return true;
  } catch (error) {
    console.error(`❌ Error typing into ${selector}: ${error.message}`);
    return false;
  }
}

module.exports = {
  sleep,
  launchBrowser,
  createPage,
  navigateToUrl,
  safeClick,
  safeClickByXPath,
  safeType,
};
