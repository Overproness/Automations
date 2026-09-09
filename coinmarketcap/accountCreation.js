const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
const fs = require("fs");
const path = require("path");
const axios = require("axios");
const FormData = require("form-data");
const sharp = require("sharp");
const { Buffer } = require("buffer");

// Use stealth plugin to avoid detection
puppeteer.use(StealthPlugin());

// 2Captcha API Key (reusing from existing code)
const TWO_CAPTCHA_API_KEY = "";

// Sleep function - kept for backward compatibility but we'll use page.waitForTimeout
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Load proxies from file
async function loadProxies() {
  try {
    const data = fs.readFileSync(path.join(__dirname, "proxies.txt"), "utf8");
    const proxies = data
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("//"))
      .map((line) => {
        const [ip, port] = line.split(":");
        return {
          ip,
          port,
          usageCount: 0,
        };
      });
    console.log(`✅ Loaded ${proxies.length} proxies.`);
    return proxies;
  } catch (err) {
    console.error(`❌ Error loading proxies: ${err.message}`);
    return [];
  }
}

// Get next proxy in rotation
function getNextProxy(proxies, currentIndex) {
  if (proxies.length === 0) return { proxy: null, newIndex: -1 };

  const newIndex = (currentIndex + 1) % proxies.length;
  const proxy = proxies[newIndex];
  proxy.usageCount++;

  return { proxy, newIndex };
}

// Save credentials to file
function saveCredentials(email) {
  const credentialsPath = path.join(__dirname, "credentials.txt");
  fs.appendFileSync(credentialsPath, `${email}:${email}\n`);
  console.log(`✅ Saved credentials to ${credentialsPath}`);
}

// Create directory for screenshots if it doesn't exist
function ensureDirectoryExists(directory) {
  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory, { recursive: true });
  }
}

// Create a task in the 2Captcha API (reused from original code)
async function createTask(param) {
  try {
    const baseUrl = "https://api.2captcha.com/createTask";
    const response = await axios.post(baseUrl, {
      clientKey: param.clientKey,
      task: {
        type: "GridTask",
        body: param.body,
        comment: param.comment,
        rows: 3,
        columns: 3,
      },
    });
    return response.data.taskId;
  } catch (err) {
    console.error(`Error in createTask: ${err}`);
    return null;
  }
}

// Get task results from the 2Captcha API - updated to use page.waitForTimeout
async function getTaskResults(p) {
  let taskResults = null;
  while (taskResults === null) {
    const baseUrl = "https://api.2captcha.com/getTaskResult";
    // Replaced sleep with direct Promise
    await new Promise((resolve) => setTimeout(resolve, 30000)); // Wait 30 seconds before checking
    try {
      const response = await axios.post(baseUrl, {
        clientKey: p.clientKey,
        taskId: p.taskId,
      });
      console.log(response.data);
      if (response.data.status === "ready") {
        taskResults = response.data;
      }
    } catch (err) {
      console.error(`Error in getTaskResults: ${err}`);
    }
  }
  return taskResults;
}

// Interact with the CAPTCHA on the page using the solution - updated for Puppeteer v24
async function solveCaptchaInteraction(page, solution) {
  try {
    await page.evaluate((solutionArr) => {
      console.log("Clicking on positions:", solutionArr);
      let images = Array.from(
        document.querySelectorAll("div.bcap-image-cell-image"),
      );
      if (images.length === 0) {
        images = Array.from(
          document.querySelectorAll("div[class*='task-image']"),
        );
      }
      solutionArr.forEach((sol) => {
        if (images[sol - 1]) {
          images[sol - 1].click();
        }
      });
    }, solution);
    console.log("✅ Clicked on CAPTCHA images at positions:", solution);
    await page.waitForTimeout(2000); // Updated from sleep(2000)

    // Click verify button
    await page.evaluate(() => {
      const verifyBtn = document.querySelector("div.bcap-verify-button");
      if (verifyBtn) verifyBtn.click();
    });
    console.log("✅ Clicked CAPTCHA verify button");
  } catch (error) {
    console.error(`❌ Error in solveCaptchaInteraction: ${error}`);
  }
}

// Improved CAPTCHA API solver with error handling
async function solveCaptchaWithApi(page, imageUrl, selectionCriteria) {
  try {
    console.log(`[+] Download and transform to base64 ==> ${imageUrl}`);

    // Get the image and convert it to base64
    const response = await axios.get(imageUrl, {
      responseType: "arraybuffer",
      timeout: 30000, // 30 second timeout for image download
    });

    if (response.status !== 200) {
      console.error(
        `❌ Failed to download CAPTCHA image. Status: ${response.status}`,
      );
      return false;
    }

    const imageBuffer = Buffer.from(response.data).toString("base64");

    // Create task with 2Captcha API
    const taskId = await createTask({
      body: imageBuffer,
      clientKey: TWO_CAPTCHA_API_KEY,
      comment: `select all ${selectionCriteria}`,
    });

    console.log(`[+] Task ID: ${taskId}`);

    if (!taskId) {
      console.error("❌ Failed to create task with 2Captcha API");
      return false;
    }

    // Get task results with improved error handling
    let results;
    try {
      results = await getTaskResultsWithTimeout({
        taskId: taskId,
        clientKey: TWO_CAPTCHA_API_KEY,
        maxWaitTime: 120000, // 2 minutes max wait time
      });
    } catch (e) {
      console.error(`❌ Error getting CAPTCHA solution: ${e.message}`);
      return false;
    }

    if (!results || !results.solution || !results.solution.click) {
      console.error("❌ Invalid or missing solution from 2Captcha");
      return false;
    }

    console.log(
      `[+] Returning Solution From 2Cap API === > :: ${results.solution.click}`,
    );

    // Interact with the CAPTCHA using the solution
    await solveCaptchaInteraction(page, results.solution.click);

    // Wait and check if CAPTCHA was solved successfully
    await page.waitForTimeout(20000); // Updated from sleep(20000)

    // Check if verify button still exists
    const verifyButtonStillExists = await page.evaluate(() => {
      return document.querySelector("div.bcap-verify-button") !== null;
    });

    if (verifyButtonStillExists) {
      console.log("❌ CAPTCHA verification failed");
      return false;
    } else {
      console.log("✅ CAPTCHA verification succeeded");
      return true;
    }
  } catch (e) {
    console.error(`❌ Error in solveCaptchaWithApi: ${e}`);
    return false;
  }
}

// Get task results with timeout to avoid infinite waiting
async function getTaskResultsWithTimeout(p) {
  const startTime = Date.now();
  const maxWaitTime = p.maxWaitTime || 120000; // Default 2 minutes
  const pollInterval = 10000; // Poll every 10 seconds

  let taskResults = null;

  while (Date.now() - startTime < maxWaitTime) {
    const baseUrl = "https://api.2captcha.com/getTaskResult";

    try {
      console.log(
        `[+] Checking CAPTCHA solution status (elapsed: ${Math.round(
          (Date.now() - startTime) / 1000,
        )}s)...`,
      );
      const response = await axios.post(baseUrl, {
        clientKey: p.clientKey,
        taskId: p.taskId,
      });

      console.log(response.data);

      // Check for specific error messages that indicate the CAPTCHA is unsolvable
      if (
        response.data.errorId === 12 ||
        (response.data.errorCode &&
          response.data.errorCode === "ERROR_CAPTCHA_UNSOLVABLE")
      ) {
        throw new Error("CAPTCHA unsolvable by 2Captcha");
      }

      if (response.data.status === "ready") {
        taskResults = response.data;
        break;
      }
    } catch (err) {
      console.error(`Error in getTaskResultsWithTimeout: ${err}`);

      // If this is a specific error about the CAPTCHA being unsolvable, don't retry
      if (err.message === "CAPTCHA unsolvable by 2Captcha") {
        throw err; // Rethrow to signal we need to refresh the CAPTCHA
      }
    }

    // Wait before the next check
    await new Promise((resolve) => setTimeout(resolve, pollInterval)); // Updated from sleep(pollInterval)
  }

  if (!taskResults) {
    throw new Error(
      `Timeout waiting for CAPTCHA solution after ${maxWaitTime / 1000} seconds`,
    );
  }

  return taskResults;
}

// Improved CAPTCHA handling with refresh retry mechanism and tracking of previous challenges
async function handleCaptcha(page) {
  try {
    const maxCaptchaAttempts = 3; // Maximum number of CAPTCHA refresh attempts
    let previousChallenge = null; // Track the previous CAPTCHA challenge
    let previousImageUrl = null; // Track the previous image URL to detect duplicates
    let consecutiveSameChallenge = 0; // Count consecutive same challenges

    for (
      let captchaAttempt = 0;
      captchaAttempt < maxCaptchaAttempts;
      captchaAttempt++
    ) {
      // Check if CAPTCHA is present
      const captchaExists = await page.evaluate(() => {
        return document.querySelector("#tagLabel") !== null;
      });

      if (!captchaExists) {
        console.log("[+] No CAPTCHA detected");
        return true;
      }

      console.log(
        `[+] CAPTCHA detected, attempt ${
          captchaAttempt + 1
        }/${maxCaptchaAttempts}`,
      );
      await page.waitForTimeout(2000); // Updated from sleep(2000)

      // Get the type of CAPTCHA
      const typeOfBox = await page.evaluate(() => {
        const element = document.querySelector("div.bcap-text-message-title");
        return element ? element.innerText : "";
      });

      if (!typeOfBox.includes("Please select all images with")) {
        console.log("[+] Captcha without any Grid, manual intervention needed");
        // Wait for manual solving
        await page.waitForTimeout(30000); // Updated from sleep(30000)
        return true;
      }

      console.log("[+] Captcha With Grid detected");

      // Get what to select
      const selectWhat = await page.evaluate(() => {
        const element = document.querySelector("div.bcap-text-message-title2");
        return element ? element.innerText : "";
      });

      console.log(`[+] Please Select ALL Images with :: ${selectWhat}`);

      // Get the image URL from the style
      const imageUrl = await page.evaluate(() => {
        const images = document.querySelectorAll("div.bcap-image-cell-image");
        if (images.length === 0) return null;

        const style = images[0].getAttribute("style") || "";
        const urlMatch = style.match(/url\(['"]?(.*?)['"]?\)/);
        return urlMatch ? urlMatch[1] : null;
      });

      if (!imageUrl) {
        console.error("❌ Could not extract image URL from style");
        return false;
      }

      console.log(`[+] Got CAPTCHA image URL: ${imageUrl}`);

      // Check if we got the same CAPTCHA challenge multiple times
      const isSameChallenge =
        selectWhat === previousChallenge && imageUrl === previousImageUrl;
      if (isSameChallenge) {
        consecutiveSameChallenge++;
        console.log(
          `⚠️ Same CAPTCHA challenge (${selectWhat}) detected ${consecutiveSameChallenge} times in a row`,
        );

        // If we get the same challenge more than once, refresh immediately
        if (consecutiveSameChallenge > 0) {
          console.log(
            "🔄 Same challenge detected multiple times, refreshing immediately...",
          );
          await refreshCaptcha(page);
          await page.waitForTimeout(5000); // Updated from sleep(5000)

          // Reset previous challenge but keep count
          previousChallenge = null;
          previousImageUrl = null;
          continue;
        }
      } else {
        consecutiveSameChallenge = 0;
      }

      // Update previous challenge
      previousChallenge = selectWhat;
      previousImageUrl = imageUrl;

      // For challenges that often fail, try to manually solve or refresh immediately
      const problematicChallenges = ["airplane", "bus", "train"];
      if (
        problematicChallenges.includes(selectWhat.toLowerCase()) &&
        captchaAttempt > 0
      ) {
        console.log(
          `⚠️ Problematic challenge type (${selectWhat}) detected, manual intervention may be needed`,
        );
        console.log("🔄 Refreshing to get a different challenge...");

        if (await refreshCaptcha(page)) {
          await page.waitForTimeout(5000); // Updated from sleep(5000)
          continue;
        }
      }

      // Set a timeout for 2Captcha to prevent too long waiting
      const captchaTimeoutPromise = new Promise((resolve) => {
        setTimeout(() => resolve({ timedOut: true }), 90000); // 1.5 minute timeout
      });

      // Start the CAPTCHA solving process
      const solvingPromise = solveCaptchaWithApi(
        page,
        imageUrl,
        selectWhat,
      ).then((success) => ({ timedOut: false, success }));

      // Race the promises
      const result = await Promise.race([
        captchaTimeoutPromise,
        solvingPromise,
      ]);

      if (result.timedOut) {
        console.log("⏱️ CAPTCHA solving timed out, refreshing...");
        if (await refreshCaptcha(page)) {
          await page.waitForTimeout(5000); // Updated from sleep(5000)
          continue;
        }
      } else if (result.success) {
        console.log("✅ CAPTCHA solved successfully");
        return true;
      } else {
        console.log(
          `❌ CAPTCHA solution failed on attempt ${
            captchaAttempt + 1
          }/${maxCaptchaAttempts}`,
        );

        // If we have more attempts, try refreshing the CAPTCHA
        if (captchaAttempt < maxCaptchaAttempts - 1) {
          console.log("🔄 Refreshing CAPTCHA and trying again...");
          if (await refreshCaptcha(page)) {
            await page.waitForTimeout(5000); // Updated from sleep(5000)
          } else {
            console.error("❌ Could not refresh CAPTCHA, skipping retry");
            break;
          }
        }
      }
    }

    // If we get here, we've failed all attempts
    console.log(
      "❌ Failed to solve CAPTCHA after multiple attempts with refresh",
    );

    // Give user a chance to solve manually
    console.log("⚠️ Waiting for possible manual CAPTCHA solving...");
    await page.waitForTimeout(45000); // Updated from sleep(45000)

    // Check if the CAPTCHA verify button is still present
    const verifyButtonStillExists = await page.evaluate(() => {
      return document.querySelector("div.bcap-verify-button") !== null;
    });

    if (!verifyButtonStillExists) {
      console.log("✅ CAPTCHA appears to have been solved manually");
      return true;
    }

    return false;
  } catch (e) {
    console.error(`❌ Error in handleCaptcha: ${e}`);
    return false;
  }
}

// Helper function to refresh CAPTCHA - updated for Puppeteer v24
async function refreshCaptcha(page) {
  // Try to click the refresh button using different methods
  let refreshed = false;

  // Method 1: Using class selector
  try {
    await page.waitForSelector("svg.bcap-icon-refresh", {
      timeout: 5000,
      visible: true, // Added visible option for modern Puppeteer
    });
    await page.click("svg.bcap-icon-refresh");
    refreshed = true;
    console.log("✅ Clicked CAPTCHA refresh button using class selector");
  } catch (e) {
    console.log(
      "⚠️ Could not click refresh button with class selector, trying other methods...",
    );
  }

  // Method 2: Using compound class selector
  if (!refreshed) {
    try {
      await page.waitForSelector(".bcap-icon.bcap-icon-refresh", {
        timeout: 5000,
        visible: true, // Added visible option for modern Puppeteer
      });
      await page.click(".bcap-icon.bcap-icon-refresh");
      refreshed = true;
      console.log(
        "✅ Clicked CAPTCHA refresh button using compound class selector",
      );
    } catch (e) {
      console.log(
        "⚠️ Could not click refresh button with compound selector, trying XPath...",
      );
    }
  }

  // Method 3: Using XPath - updated to use modern page.$x handling
  if (!refreshed) {
    try {
      const refreshButtons = await page.$x(
        "/html/body/div[7]/div/div[2]/div/div[1]/svg[2]",
      );
      if (refreshButtons.length > 0) {
        await refreshButtons[0].click();
        refreshed = true;
        console.log("✅ Clicked CAPTCHA refresh button using XPath");
      }
    } catch (e) {
      console.log(
        "⚠️ Could not click refresh button with XPath, trying JavaScript...",
      );
    }
  }

  // Method 4: Using JavaScript evaluation
  if (!refreshed) {
    try {
      refreshed = await page.evaluate(() => {
        // Try to find and click the refresh button by icon and attributes
        const svgs = Array.from(document.querySelectorAll("svg"));
        for (const svg of svgs) {
          if (
            svg.classList.contains("bcap-icon-refresh") ||
            (svg.classList.contains("bcap-icon") &&
              svg.parentElement &&
              svg.parentElement.getAttribute("aria-label") === "New Challenge")
          ) {
            svg.click();
            return true;
          }
        }

        // Look for other refresh elements
        const refreshElements = Array.from(
          document.querySelectorAll("*"),
        ).filter(
          (el) =>
            el.getAttribute("aria-label") === "New Challenge" ||
            el.classList.contains("refresh") ||
            (el.textContent && el.textContent.includes("Refresh")),
        );

        if (refreshElements.length > 0) {
          refreshElements[0].click();
          return true;
        }

        return false;
      });

      if (refreshed) {
        console.log("✅ Clicked CAPTCHA refresh button using JavaScript");
      }
    } catch (e) {
      console.log("⚠️ Could not click refresh button with JavaScript");
    }
  }

  return refreshed;
}

// New function to get a temporary email - updated for Puppeteer v24
async function getTempEmail(browser, proxy) {
  console.log("🔄 Attempting to get a temporary email address...");
  const providers = [
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
  ];

  // Get page from existing browser or create a new one
  let page;
  try {
    const pages = await browser.pages();
    page = pages[0];
  } catch (e) {
    console.log("Creating a new browser instance for temp email...");
    // Updated browser launch parameters for v24.7.2
    browser = await puppeteer.launch({
      headless: false,
      args: [
        `--proxy-server=${proxy.ip}:${proxy.port}`,
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
      ],
      defaultViewport: null,
      protocolTimeout: 180000, // Added 3 min protocol timeout (new in v24)
    });
    const pages = await browser.pages();
    page = pages[0];
  }

  await page.setUserAgent(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  );

  // Set a longer default navigation timeout
  page.setDefaultNavigationTimeout(60000);

  // Try each provider until successful
  for (const provider of providers) {
    try {
      console.log(`🔄 Trying ${provider.name}...`);
      await page.goto(provider.url, {
        waitUntil: "networkidle2",
        timeout: provider.timeout,
      });

      // Wait 10 seconds for page to fully load
      console.log(`⏳ Waiting for ${provider.name} to load...`);
      await page.waitForTimeout(10000); // Updated from sleep(10000)

      // Check if the page loaded correctly
      const pageTitle = await page.title();
      console.log(`📄 Page title: ${pageTitle}`);

      if (
        pageTitle.includes("Access denied") ||
        pageTitle.includes("Blocked")
      ) {
        console.error(
          `❌ Access to ${provider.name} is blocked from this proxy`,
        );
        continue; // Try next provider
      }

      // Wait for email field to be available - updated to use modern waitForSelector
      await page.waitForSelector(provider.emailSelector, {
        timeout: 15000,
        visible: true,
      });

      // Additional wait for temp-mail.org which can take time to generate
      if (provider.name === "temp-mail.org") {
        console.log("⏳ Waiting 20 seconds for email generation...");
        await page.waitForTimeout(20000); // Updated from sleep(20000)
      } else {
        await page.waitForTimeout(5000); // Updated from sleep(5000)
      }

      // Get the email
      const email = await page.evaluate((selector) => {
        const element = document.querySelector(selector);
        return element ? element.value : null;
      }, provider.emailSelector);

      if (!email || !email.includes("@")) {
        console.error(`❌ Could not find valid email on ${provider.name}`);

        // Take screenshot for debugging
        const screenshotsDir = path.join(__dirname, "screenshots");
        ensureDirectoryExists(screenshotsDir);
        await page.screenshot({
          path: path.join(
            screenshotsDir,
            `${provider.name.replace(/\./g, "_")}_error.png`,
          ),
        });

        continue; // Try next provider
      }

      console.log(`📧 Found email: ${email}`);

      // Try to click copy button (not required but convenient)
      try {
        // First try CSS selector - updated to use modern waitForSelector
        await page.waitForSelector(provider.copyBtnSelector, {
          timeout: 5000,
          visible: true,
        });
        await page.click(provider.copyBtnSelector);
        console.log("✅ Clicked copy button using CSS selector");
      } catch (e) {
        try {
          // Then try XPath - updated to use modern page.$x handling
          const copyButtons = await page.$x(provider.copyBtnXPath);
          if (copyButtons.length > 0) {
            await copyButtons[0].click();
            console.log("✅ Clicked copy button using XPath");
          }
        } catch (e) {
          console.log("⚠️ Could not click copy button - continuing anyway");
        }
      }

      return {
        email,
        page,
        provider,
      };
    } catch (error) {
      console.error(`❌ Error with ${provider.name}: ${error.message}`);

      // Take screenshot to debug the issue
      try {
        const screenshotsDir = path.join(__dirname, "screenshots");
        ensureDirectoryExists(screenshotsDir);
        await page.screenshot({
          path: path.join(
            screenshotsDir,
            `${provider.name.replace(/\./g, "_")}_error.png`,
          ),
        });
      } catch (e) {
        console.error(`❌ Could not take screenshot: ${e.message}`);
      }
    }
  }

  // If all providers failed, return null
  return null;
}

// Improved verification email checker - updated for Puppeteer v24
async function checkForVerificationEmail(page, email, provider) {
  console.log(`🔍 Looking for verification email for ${email}...`);

  const maxRetries = 5;
  let retryCount = 0;
  let verificationUrl = null;

  // First, check if we're already on a verification page
  const currentUrl = await page.url();
  console.log(`📄 Current page URL: ${currentUrl}`);

  if (currentUrl.includes("link.coinmarketcap.com")) {
    console.log(`✅ Already on CoinMarketCap verification link page!`);
    return currentUrl;
  }

  while (retryCount < maxRetries && !verificationUrl) {
    try {
      // Get the current URL again in case it changed
      const checkUrl = await page.url();
      if (checkUrl.includes("link.coinmarketcap.com")) {
        console.log(
          `✅ Already on CoinMarketCap verification link: ${checkUrl}`,
        );
        return checkUrl;
      }

      // Refresh the page for each retry except the first
      if (retryCount > 0) {
        console.log(
          `🔄 Refreshing inbox (attempt ${retryCount + 1}/${maxRetries})...`,
        );
        await page.reload({
          waitUntil: "networkidle2",
          timeout: 30000,
        });
      }

      await page.waitForTimeout(10000); // Updated from sleep(10000)

      // Look for any coinmarketcap links on the page - THIS IS THE MOST IMPORTANT PART
      try {
        const cmcLinks = await page.evaluate(() => {
          // Get all links that contain coinmarketcap
          const links = Array.from(
            document.querySelectorAll('a[href*="coinmarketcap"]'),
          );
          return links.map((link) => link.href);
        });

        if (cmcLinks.length > 0) {
          console.log(
            `✅ Found ${cmcLinks.length} CoinMarketCap links on page`,
          );
          // Filter links to prioritize verification links
          const verificationLinks = cmcLinks.filter(
            (link) =>
              link.includes("link.coinmarketcap.com") ||
              link.includes("verify") ||
              link.includes("account-verification"),
          );

          // Use verification link if found, otherwise use first link
          const linkToUse =
            verificationLinks.length > 0 ? verificationLinks[0] : cmcLinks[0];
          console.log(`📋 Using link: ${linkToUse}`);

          // Return the link directly without navigating to it
          // The verification process will use this link in the next step
          return linkToUse;
        }
      } catch (e) {
        console.log(`❌ Error finding CoinMarketCap links: ${e.message}`);
      }

      // Direct XPath approach as fallback - updated to use modern page.$x handling
      try {
        const verificationLinks = await page.$x(
          "/html/body/main/div[1]/div/div[2]/div[2]/div/div[1]/div/div[4]/ul/li[2]/div[2]/span/a",
        );
        if (verificationLinks.length > 0) {
          console.log("✅ Found verification email with direct XPath");

          // Extract href without clicking
          const linkHref = await page.evaluate(
            (el) => el.href,
            verificationLinks[0],
          );
          console.log(`🔗 Link href: ${linkHref}`);

          // If it's a coinmarketcap link, return it directly
          if (linkHref.includes("coinmarketcap.com")) {
            return linkHref;
          }

          // Otherwise click it to see where it goes
          await verificationLinks[0].click();
          console.log("✅ Clicked verification email link");
          await page.waitForTimeout(5000); // Updated from sleep(5000)

          // Check if we navigated to a CoinMarketCap page
          const newUrl = await page.url();
          if (
            newUrl.includes("coinmarketcap.com") ||
            newUrl.includes("link.coinmarketcap.com")
          ) {
            return newUrl;
          }
        }
      } catch (e) {
        console.log(`❌ Error with XPath approach: ${e.message}`);
      }

      // General link finding approach as last resort
      try {
        const allLinks = await page.evaluate(() => {
          return Array.from(document.querySelectorAll("a"))
            .filter(
              (link) =>
                link.textContent.toLowerCase().includes("verify") ||
                link.textContent.toLowerCase().includes("confirm") ||
                link.href.includes("coinmarketcap"),
            )
            .map((link) => link.href);
        });

        if (allLinks.length > 0) {
          console.log(
            `✅ Found ${allLinks.length} potential verification links`,
          );
          return allLinks[0]; // Return the link directly
        }
      } catch (e) {
        console.log(`❌ Error with general link approach: ${e.message}`);
      }

      retryCount++;
      console.log(
        `⏳ Waiting 10 seconds before retry ${retryCount}/${maxRetries}...`,
      );
      await page.waitForTimeout(10000); // Updated from sleep(10000)
    } catch (error) {
      console.error(`❌ Error in verification email check: ${error.message}`);
      retryCount++;
      await page.waitForTimeout(5000); // Updated from sleep(5000)
    }
  }

  console.error(
    `❌ Failed to find verification link after ${maxRetries} attempts`,
  );
  return null;
}

// Main account creation process - updated for Puppeteer v24.7.2
async function createAccount(proxy) {
  console.log(`🌐 Using proxy: ${proxy.ip}:${proxy.port}`);
  let browser;
  let email; // Declare email at the function scope level so it's available in catch blocks

  try {
    // Launch browser with proxy - updated for v24.7.2
    browser = await puppeteer.launch({
      headless: false,
      args: [
        `--proxy-server=${proxy.ip}:${proxy.port}`, // Uncommented proxy line
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
      ],
      defaultViewport: null,
      protocolTimeout: 180000, // Added 3 min protocol timeout (new in v24)
    });

    // Step 1-3: Get temporary email
    const tempEmailData = await getTempEmail(browser, proxy);

    if (!tempEmailData) {
      throw new Error(
        "Failed to obtain a temporary email address from any provider",
      );
    }

    email = tempEmailData.email; // Set email for wider scope
    const { page: emailPage, provider } = tempEmailData;

    // Step 4-7: CoinMarketCap signup
    console.log("🔄 Opening CoinMarketCap in new tab for signup...");
    const cmcPage = await browser.newPage();
    await cmcPage.setUserAgent(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    );

    // Set a longer navigation timeout
    cmcPage.setDefaultNavigationTimeout(60000);

    let signupSuccess = false;

    // Try signup with retry logic
    const maxSignupAttempts = 3;
    for (let attempt = 1; attempt <= maxSignupAttempts; attempt++) {
      try {
        console.log(`🔄 Signup attempt ${attempt}/${maxSignupAttempts}...`);

        // Navigate to CMC - updated for v24.7.2
        await cmcPage.goto("https://coinmarketcap.com/", {
          waitUntil: "networkidle2",
          timeout: 60000,
        });

        // Click login button - updated waitForSelector
        try {
          console.log("🖱️ Clicking login button...");
          await cmcPage.waitForSelector('button[data-test="Log In"]', {
            timeout: 15000,
            visible: true,
          });
          await cmcPage.click('button[data-test="Log In"]');
        } catch (error) {
          console.error("❌ Error clicking login button:", error);
          // Try XPath - updated for v24.7.2
          try {
            const menuButtons = await cmcPage.$x(
              "/html/body/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div[2]/div[4]/button",
            );
            if (menuButtons.length > 0) {
              await menuButtons[0].click();
              console.log("✅ Clicked login button using XPath");
            } else {
              throw new Error("Could not find login button");
            }
          } catch (e) {
            console.error("❌ Failed with XPath too:", e);
            throw e;
          }
        }
        await cmcPage.waitForTimeout(3000); // Use cmcPage instead of page

        // reject cookies - updated for v24.7.2
        try {
          console.log("🖱️ Clicking reject cookies button...");
          const rejectButtons = await cmcPage.$x(
            "/html/body/div[5]/div[2]/div/div[1]/div/div[2]/div/button[2]",
          );
          if (rejectButtons.length > 0) {
            await rejectButtons[0].click();
            console.log("✅ Clicked reject cookies button");
          }
        } catch (error) {
          console.error("❌ Error clicking reject cookies button:", error);
        }
        await cmcPage.waitForTimeout(3000); // Use cmcPage instead of page

        // Click Sign Up button - updated waitForSelector
        try {
          console.log("🖱️ Clicking signup button...");
          await cmcPage.waitForSelector('div[data-action="sign-up"]', {
            timeout: 15000,
            visible: true,
          });
          await cmcPage.click('div[data-action="sign-up"]');
        } catch (error) {
          console.error("❌ Error clicking signup button:", error);
          // Try XPath - updated for v24.7.2
          try {
            const signupButtons = await cmcPage.$x(
              "/html/body/div[6]/div/div/div/div/div[1]/div[2]",
            );
            if (signupButtons.length > 0) {
              await signupButtons[0].click();
              console.log("✅ Clicked signup button using XPath");
            } else {
              throw new Error("Could not find signup button");
            }
          } catch (e) {
            console.error("❌ Failed with XPath too:", e);
            throw e;
          }
        }
        await cmcPage.waitForTimeout(3000); // Use cmcPage instead of page

        // Enter email - updated waitForSelector
        try {
          console.log(`🔄 Entering email: ${email}`);
          await cmcPage.waitForSelector('input[type="email"]', {
            timeout: 15000,
            visible: true,
          });
          await cmcPage.type('input[type="email"]', email);
        } catch (error) {
          console.error("❌ Error entering email:", error);
          // Try XPath - updated for v24.7.2
          try {
            const emailInputs = await cmcPage.$x(
              "/html/body/div[6]/div/div/div/div/div[3]/div[3]/input",
            );
            if (emailInputs.length > 0) {
              await emailInputs[0].type(email);
              console.log("✅ Entered email using XPath");
            } else {
              throw new Error("Could not find email input");
            }
          } catch (e) {
            console.error("❌ Failed with XPath too:", e);
            throw e;
          }
        }
        await cmcPage.waitForTimeout(2000); // Use cmcPage instead of page

        // Enter password (same as email) - updated waitForSelector
        try {
          console.log("🔄 Entering password...");
          await cmcPage.waitForSelector('input[type="password"]', {
            timeout: 15000,
            visible: true,
          });
          await cmcPage.type('input[type="password"]', email);
        } catch (error) {
          console.error("❌ Error entering password:", error);
          // Try XPath - updated for v24.7.2
          try {
            const passwordInputs = await cmcPage.$x(
              "/html/body/div[6]/div/div/div/div/div[3]/div[4]/div[2]/input",
            );
            if (passwordInputs.length > 0) {
              await passwordInputs[0].type(email);
              console.log("✅ Entered password using XPath");
            } else {
              throw new Error("Could not find password input");
            }
          } catch (e) {
            console.error("❌ Failed with XPath too:", e);
            throw e;
          }
        }
        await cmcPage.waitForTimeout(2000); // Use cmcPage instead of page

        // Click submit button - updated waitForSelector
        try {
          console.log("🖱️ Clicking submit button...");
          await cmcPage.waitForSelector('button[type="submit"]', {
            timeout: 15000,
            visible: true,
          });
          await cmcPage.click('button[type="submit"]');
        } catch (error) {
          console.error("❌ Error clicking submit button:", error);
          // Try XPath - updated for v24.7.2
          try {
            const submitButtons = await cmcPage.$x(
              "/html/body/div[6]/div/div/div/div/div[3]/div[6]/button",
            );
            if (submitButtons.length > 0) {
              await submitButtons[0].click();
              console.log("✅ Clicked submit button using XPath");
            } else {
              throw new Error("Could not find submit button");
            }
          } catch (e) {
            console.error("❌ Failed with XPath too:", e);
            throw e;
          }
        }

        // Wait longer for CAPTCHA to appear if needed
        await cmcPage.waitForTimeout(15000); // Use cmcPage instead of page

        // Handle CAPTCHA
        console.log("🔄 Checking for CAPTCHA...");
        const captchaSolved = await handleCaptcha(cmcPage);

        if (!captchaSolved) {
          console.log(
            "⚠️ CAPTCHA not solved automatically, waiting for manual intervention...",
          );
          // Give some time for manual solving
          await cmcPage.waitForTimeout(45000); // Use cmcPage instead of page
        }

        // Check if signup was successful (logout button should be visible)
        try {
          // Wait for login button to disappear
          const loginButtonStillExists = await cmcPage.evaluate(() => {
            return document.querySelector('button[data-role="login"]') !== null;
          });

          if (!loginButtonStillExists) {
            console.log(
              "✅ Login button disappeared - signup appears successful",
            );
            signupSuccess = true;
            break;
          } else {
            console.log(
              "⚠️ Login button still visible - signup may have failed",
            );
            // Take screenshot for debugging
            const screenshotsDir = path.join(__dirname, "screenshots");
            ensureDirectoryExists(screenshotsDir);
            await cmcPage.screenshot({
              path: path.join(
                screenshotsDir,
                `${email.replace(/[@.]/g, "_")}_signup_attempt${attempt}.png`,
              ),
            });

            if (attempt < maxSignupAttempts) {
              console.log(
                `⏳ Retrying signup (attempt ${
                  attempt + 1
                }/${maxSignupAttempts})...`,
              );
              await cmcPage.waitForTimeout(10000); // Use cmcPage instead of page
            }
          }
        } catch (e) {
          console.error(`❌ Error checking signup status: ${e.message}`);
          if (attempt < maxSignupAttempts) {
            console.log(
              `⏳ Retrying signup (attempt ${
                attempt + 1
              }/${maxSignupAttempts})...`,
            );
            await cmcPage.waitForTimeout(10000); // Use cmcPage instead of page
          }
        }
      } catch (error) {
        console.error(
          `❌ Error during signup attempt ${attempt}: ${error.message}`,
        );
        if (attempt < maxSignupAttempts) {
          console.log(
            `⏳ Retrying signup (attempt ${
              attempt + 1
            }/${maxSignupAttempts})...`,
          );
          await cmcPage.waitForTimeout(10000); // Use cmcPage instead of page
        }
      }
    }

    if (!signupSuccess) {
      console.error("❌ Failed to complete signup after multiple attempts");
      throw new Error("Signup process failed");
    }

    // Take screenshot after signup
    const screenshotsDir = path.join(__dirname, "screenshots");
    ensureDirectoryExists(screenshotsDir);
    await cmcPage.screenshot({
      path: path.join(
        screenshotsDir,
        `${email.replace(/[@.]/g, "_")}_signup_complete.png`,
      ),
    });

    // Save credentials
    console.log("💾 Saving credentials...");
    saveCredentials(email);

    // Step 9-10: Check for verification email
    console.log("🔄 Checking for verification email...");
    await emailPage.bringToFront();

    const verificationUrl = await checkForVerificationEmail(
      emailPage,
      email,
      provider,
    );

    if (!verificationUrl) {
      console.error("❌ Could not find verification email/link");
      return {
        success: false,
        email,
        error: "Verification email not found",
        stage: "verification_email",
      };
    }

    // Step 11-15: Complete verification process with the found link
    console.log(`🔄 Opening verification URL: ${verificationUrl}`);
    const verificationPage = await browser.newPage();
    await verificationPage.setUserAgent(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    );

    // Set longer timeout and navigate to verification link
    verificationPage.setDefaultNavigationTimeout(120000); // 2 minutes

    try {
      // Navigate to the verification link
      await verificationPage.goto(verificationUrl, {
        waitUntil: "networkidle2",
        timeout: 120000,
      });

      // Take screenshot to debug
      const screenshotsDir = path.join(__dirname, "screenshots");
      ensureDirectoryExists(screenshotsDir);
      await verificationPage.screenshot({
        path: path.join(
          screenshotsDir,
          `${email.replace(/[@.]/g, "_")}_verification_initial.png`,
        ),
      });

      // Wait for the page to fully load
      console.log("⏳ Waiting for verification page to fully load...");
      await verificationPage.waitForTimeout(15000); // Use verificationPage instead of page

      // Execute the specific verification flow exactly as provided
      console.log("🔄 Starting verification flow...");

      // Click Next button 4 times, with 5 second delay between each click
      console.log("🖱️ Clicking through onboarding screens (4 clicks)...");

      for (let i = 0; i < 4; i++) {
        try {
          // First try with explicit selector - updated waitForSelector
          try {
            console.log(
              `🔄 Clicking Next button (${i + 1}/4) with CSS selector...`,
            );
            await verificationPage.waitForSelector(
              'button[variant="primary"]',
              { timeout: 10000, visible: true },
            );
            await verificationPage.click('button[variant="primary"]');
            console.log(
              `✅ Clicked Next button (${i + 1}/4) with CSS selector`,
            );
          } catch (e) {
            console.log(
              `⚠️ CSS selector failed for button ${i + 1}/4: ${e.message}`,
            );

            // Try with class - updated waitForSelector
            try {
              console.log(`🔄 Clicking Next button (${i + 1}/4) with class...`);
              await verificationPage.waitForSelector("button.joeEVb", {
                timeout: 5000,
                visible: true,
              });
              await verificationPage.click("button.joeEVb");
              console.log(`✅ Clicked Next button (${i + 1}/4) with class`);
            } catch (e2) {
              console.log(
                `⚠️ Class selector failed for button ${i + 1}/4: ${e2.message}`,
              );

              // Try with exact XPath - updated for v24.7.2
              try {
                console.log(
                  `🔄 Clicking Next button (${i + 1}/4) with XPath...`,
                );
                const nextButtons = await verificationPage.$x(
                  "/html/body/div[6]/div/div/div/div/button",
                );
                if (nextButtons.length > 0) {
                  await nextButtons[0].click();
                  console.log(`✅ Clicked Next button (${i + 1}/4) with XPath`);
                } else {
                  throw new Error("Next button not found with XPath");
                }
              } catch (e3) {
                console.log(
                  `⚠️ XPath failed for button ${i + 1}/4: ${e3.message}`,
                );

                // Try JavaScript click as last resort
                console.log(
                  `🔄 Trying JavaScript click for button ${i + 1}/4...`,
                );
                await verificationPage.evaluate(() => {
                  const buttons = Array.from(
                    document.querySelectorAll("button"),
                  );
                  for (const btn of buttons) {
                    if (
                      btn.innerText.includes("Next") ||
                      btn.getAttribute("variant") === "primary"
                    ) {
                      btn.click();
                      return;
                    }
                  }
                  throw new Error("No Next button found with JavaScript");
                });
                console.log(
                  `✅ Clicked Next button (${i + 1}/4) with JavaScript`,
                );
              }
            }
          }

          // Take screenshot after each click
          await verificationPage.screenshot({
            path: path.join(
              screenshotsDir,
              `${email.replace(/[@.]/g, "_")}_after_click_${i + 1}.png`,
            ),
          });

          // Wait exactly 5 seconds between clicks as specified
          console.log(`⏳ Waiting 5 seconds before next action...`);
          await verificationPage.waitForTimeout(5000); // Use verificationPage instead of page
        } catch (error) {
          console.error(`❌ Error on button click ${i + 1}: ${error.message}`);

          // Try to continue with the flow even if one button fails
          await verificationPage.waitForTimeout(5000); // Use verificationPage instead of page
        }
      }

      // Enter the local part of email in the nickname field
      console.log("🔄 Now entering nickname...");
      try {
        // Wait for the nickname input field - updated waitForSelector
        await verificationPage.waitForSelector(
          'input[placeholder="Choose your own nickname"]',
          {
            timeout: 10000,
            visible: true,
          },
        );

        // Clear the input field first
        await verificationPage.evaluate(() => {
          const input = document.querySelector(
            'input[placeholder="Choose your own nickname"]',
          );
          if (input) input.value = "";
        });

        // Get local part of email
        const localPart = email.split("@")[0];
        console.log(`📝 Using nickname: ${localPart}`);

        // Type the nickname
        await verificationPage.type(
          'input[placeholder="Choose your own nickname"]',
          localPart,
        );
        console.log("✅ Entered nickname successfully");

        // Take screenshot after entering nickname
        await verificationPage.screenshot({
          path: path.join(
            screenshotsDir,
            `${email.replace(/[@.]/g, "_")}_after_nickname.png`,
          ),
        });
      } catch (e) {
        console.log(`⚠️ Error with CSS selector for nickname: ${e.message}`);

        // Try XPath for nickname field - updated for v24.7.2
        try {
          console.log("🔄 Trying XPath for nickname input...");
          const nicknameInputs = await verificationPage.$x(
            "/html/body/div[6]/div/div/div/div/div[4]/input",
          );

          if (nicknameInputs.length > 0) {
            // Clear the input field
            await verificationPage.evaluate(() => {
              const input = document.evaluate(
                "/html/body/div[6]/div/div/div/div/div[4]/input",
                document,
                null,
                XPathResult.FIRST_ORDERED_NODE_TYPE,
                null,
              ).singleNodeValue;
              if (input) input.value = "";
            });

            // Type nickname
            const localPart = email.split("@")[0];
            await nicknameInputs[0].type(localPart);
            console.log("✅ Entered nickname using XPath");
          } else {
            throw new Error("Nickname input not found with XPath");
          }
        } catch (e2) {
          console.error(`❌ Failed to enter nickname: ${e2.message}`);
        }
      }

      // Wait 5 seconds before final button click
      console.log("⏳ Waiting 5 seconds before final button click...");
      await verificationPage.waitForTimeout(5000); // Use verificationPage instead of page

      // Click the final button (specified as /html/body/div[5]/div/div/div/div/button)
      console.log("🖱️ Clicking final button...");
      try {
        // Try the exact XPath first - updated for v24.7.2
        const finalButtons = await verificationPage.$x(
          "/html/body/div[5]/div/div/div/div/button",
        );

        if (finalButtons.length > 0) {
          await finalButtons[0].click();
          console.log("✅ Clicked final button with exact XPath");
        } else {
          // If the specific XPath doesn't work, try alternative selectors
          console.log(
            "⚠️ Final button not found with exact XPath, trying alternatives...",
          );

          // Try div[6] XPath - updated for v24.7.2
          const altButtons = await verificationPage.$x(
            "/html/body/div[6]/div/div/div/div/button",
          );
          if (altButtons.length > 0) {
            await altButtons[0].click();
            console.log(
              "✅ Clicked final button with alternative XPath (div[6])",
            );
          } else {
            // Try button selector
            await verificationPage.click('button[variant="primary"]');
            console.log("✅ Clicked final button with CSS selector");
          }
        }

        // Take final screenshot
        await verificationPage.waitForTimeout(5000); // Use verificationPage instead of page
        await verificationPage.screenshot({
          path: path.join(
            screenshotsDir,
            `${email.replace(/[@.]/g, "_")}_verification_complete.png`,
          ),
        });
      } catch (error) {
        console.error(`❌ Error clicking final button: ${error.message}`);

        // Try JavaScript click as last resort
        try {
          await verificationPage.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll("button"));
            for (const btn of buttons) {
              if (
                btn.innerText.includes("Next") ||
                btn.innerText.includes("Done") ||
                btn.innerText.includes("Continue") ||
                btn.getAttribute("variant") === "primary"
              ) {
                btn.click();
                return;
              }
            }
          });
          console.log("✅ Clicked final button with JavaScript");
        } catch (jsError) {
          console.error(`❌ JavaScript click also failed: ${jsError.message}`);
        }
      }

      // Verification process complete
      console.log("✅ Account creation and verification process completed");

      // Return success result
      return {
        success: true,
        email: email,
        message: "Account created and verified successfully",
      };
    } catch (error) {
      console.error(`❌ Error during verification process: ${error.message}`);

      // Take error screenshot
      try {
        const screenshotsDir = path.join(__dirname, "screenshots");
        ensureDirectoryExists(screenshotsDir);
        await verificationPage.screenshot({
          path: path.join(
            screenshotsDir,
            `${email.replace(/[@.]/g, "_")}_verification_error.png`,
          ),
        });
      } catch (e) {
        console.error(`❌ Could not take error screenshot: ${e.message}`);
      }

      return {
        success: false,
        email: email,
        error: `Verification process error: ${error.message}`,
        stage: "verification_process",
      };
    }
  } catch (error) {
    console.error(`❌ Error in account creation process: ${error.message}`);
    return {
      success: false,
      email: email || null, // Handle potential undefined email
      error: error.message,
      stage: "account_creation",
    };
  } finally {
    // Only close the browser at the very end
    if (browser) {
      console.log("🚪 Closing browser...");
      await browser.close();
    }
  }
}

// Main function - updated with proper error handling
async function main() {
  // Create results directory
  const resultsDir = path.join(__dirname, "results");
  ensureDirectoryExists(resultsDir);

  // Create credentials file if it doesn't exist
  const credentialsPath = path.join(__dirname, "credentials.txt");
  if (!fs.existsSync(credentialsPath)) {
    fs.writeFileSync(credentialsPath, "# CoinMarketCap Credentials\n");
  }

  // Create log file
  const logFile = path.join(
    resultsDir,
    `account_creation_log_${new Date().toISOString().replace(/:/g, "-")}.txt`,
  );
  fs.writeFileSync(
    logFile,
    `Account Creation Log - Started at ${new Date().toISOString()}\n\n`,
  );

  // Load proxies
  const proxies = await loadProxies();
  if (proxies.length === 0) {
    console.error("❌ No proxies available. Exiting...");
    return;
  }

  let currentProxyIndex = -1;
  let successCount = 0;
  let failureCount = 0;
  let proxyFailures = {};

  // Number of accounts to create (can be modified)
  const numberOfAccounts = 5;

  // Track failing proxies
  proxies.forEach((p) => {
    proxyFailures[`${p.ip}:${p.port}`] = 0;
  });

  for (let i = 0; i < numberOfAccounts; i++) {
    console.log(`\n🔄 Creating account ${i + 1}/${numberOfAccounts}`);

    let accountCreated = false;
    let proxyAttempts = 0;
    const maxProxyAttempts = Math.min(3, proxies.length); // Try up to 3 different proxies

    while (!accountCreated && proxyAttempts < maxProxyAttempts) {
      // Get next proxy
      const { proxy, newIndex } = getNextProxy(proxies, currentProxyIndex);
      currentProxyIndex = newIndex;

      // Skip proxies that have failed too many times
      const proxyKey = `${proxy.ip}:${proxy.port}`;
      if (proxyFailures[proxyKey] >= 2) {
        console.log(
          `⚠️ Skipping proxy ${proxyKey} - failed ${proxyFailures[proxyKey]} times previously`,
        );
        continue;
      }

      // Log the proxy usage
      const logEntry = `[${new Date().toISOString()}] Using proxy: ${
        proxy.ip
      }:${proxy.port} - Usage count: ${proxy.usageCount}\n`;
      fs.appendFileSync(logFile, logEntry);
      console.log(logEntry.trim());

      // Create account
      const result = await createAccount(proxy);

      if (result.success) {
        successCount++;
        accountCreated = true;
        fs.appendFileSync(
          logFile,
          `[${new Date().toISOString()}] SUCCESS: Account created for ${
            result.email
          }\n`,
        );
      } else {
        // Track proxy failure
        proxyFailures[proxyKey] = (proxyFailures[proxyKey] || 0) + 1;

        fs.appendFileSync(
          logFile,
          `[${new Date().toISOString()}] FAILURE with proxy ${proxyKey}: ${
            result.error || "Unknown error"
          }\n`,
        );

        proxyAttempts++;
        console.log(
          `⚠️ Account creation failed with proxy ${proxyKey}. Attempts: ${proxyAttempts}/${maxProxyAttempts}`,
        );

        if (proxyAttempts < maxProxyAttempts) {
          console.log(`🔄 Trying with a different proxy...`);
        } else {
          failureCount++;
          console.error(
            `❌ Failed to create account after trying ${maxProxyAttempts} different proxies`,
          );
        }
      }
    }

    // Add a delay between account creation attempts
    if (i < numberOfAccounts - 1) {
      const delayTime = 15000 + Math.random() * 10000; // 15-25 seconds
      console.log(
        `⏳ Waiting ${Math.round(
          delayTime / 1000,
        )} seconds before next account...`,
      );
      await sleep(delayTime);
    }
  }

  // Log summary with proxy status
  const summary = `
=== SUMMARY ===
Total accounts attempted: ${numberOfAccounts}
Successful: ${successCount}
Failed: ${failureCount}
Success rate: ${Math.round((successCount / numberOfAccounts) * 100)}%
Completed at: ${new Date().toISOString()}

=== PROXY USAGE ===
${proxies
  .map((p) => {
    const proxyKey = `${p.ip}:${p.port}`;
    return `${proxyKey} - Used ${p.usageCount} times - Failures: ${
      proxyFailures[proxyKey] || 0
    }`;
  })
  .join("\n")}
===============
`;

  console.log(summary);
  fs.appendFileSync(logFile, summary);
  console.log(`📝 Full log saved to: ${logFile}`);
}

// Run the main function
main().catch((error) => {
  console.error(`❌ Unhandled error in main function: ${error}`);
  process.exit(1);
});
