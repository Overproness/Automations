/**
 * Configuration settings for the CoinMarketCap account creator
 */
module.exports = {
  // 2Captcha API Key
  TWO_CAPTCHA_API_KEY: "",

  // Browser settings
  BROWSER_CONFIG: {
    headless: false,
    defaultArgs: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--window-size=1920,1080",
    ],
    defaultViewport: null,
    protocolTimeout: 180000, // 3 min timeout
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  },

  // Timeouts and retries
  TIMEOUTS: {
    DEFAULT_NAVIGATION: 60000,
    DEFAULT_ELEMENT_WAIT: 15000,
    CAPTCHA_TIMEOUT: 120000,
    VERIFICATION_TIMEOUT: 120000,
  },

  // Email providers
  EMAIL_PROVIDERS: [
    {
      name: "temp-mail.org",
      url: "https://temp-mail.org/en/",
      emailSelector: "#mail",
      copyBtnSelector: "button.click-to-copy",
      copyBtnXPath:
        "/html/body/div[1]/div/div/div[2]/div[1]/form/div[2]/button",
      timeout: 45000,
    },
    {
      name: "mail.tm",
      url: "https://mail.tm/en/",
      emailSelector: "input#address",
      copyBtnSelector: "button.clipboard",
      copyBtnXPath: "//button[contains(@class, 'clipboard')]",
      timeout: 45000,
    },
    {
      name: "temp-mail.io",
      url: "https://temp-mail.io/en",
      emailSelector: "input#email",
      copyBtnSelector: "button.copy-button",
      copyBtnXPath: "//button[contains(@class, 'copy')]",
      timeout: 45000,
    },
  ],

  // Problematic CAPTCHA challenges
  PROBLEMATIC_CAPTCHAS: ["airplane", "bus", "train"],

  // Account creation settings
  NUMBER_OF_ACCOUNTS: 5,
  MAX_PROXY_ATTEMPTS: 3,
  MAX_SIGNUP_ATTEMPTS: 3,
  MAX_CAPTCHA_ATTEMPTS: 3,
};
