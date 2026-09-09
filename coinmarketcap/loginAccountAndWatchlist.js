const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
const fs = require("fs");
const path = require("path");
const axios = require("axios");
const FormData = require("form-data");
const sharp = require("sharp");
const { Buffer } = require("buffer");
const csv = require("csv-parser");

// Use stealth plugin to avoid detection
puppeteer.use(StealthPlugin());

// 2Captcha API Key (reusing from existing code)
const TWO_CAPTCHA_API_KEY = "";

// Sleep function
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

// Get task results from the 2Captcha API (reused from original code)
async function getTaskResults(p) {
  let taskResults = null;
  while (taskResults === null) {
    const baseUrl = "https://api.2captcha.com/getTaskResult";
    await sleep(30000); // Wait 30 seconds before checking
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

// Interact with the CAPTCHA on the page using the solution (adapted for Puppeteer)
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
    await sleep(2000);

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
    await sleep(20000);

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
    await sleep(pollInterval);
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
      await sleep(2000);

      // Get the type of CAPTCHA
      const typeOfBox = await page.evaluate(() => {
        const element = document.querySelector("div.bcap-text-message-title");
        return element ? element.innerText : "";
      });

      if (!typeOfBox.includes("Please select all images with")) {
        console.log("[+] Captcha without any Grid, manual intervention needed");
        // Wait for manual solving
        await sleep(30000);
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
          await sleep(5000); // Wait for new CAPTCHA to load

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
          await sleep(5000); // Wait for new CAPTCHA to load
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
          await sleep(5000);
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
            await sleep(5000);
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
    await sleep(45000);

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

// Helper function to refresh CAPTCHA
async function refreshCaptcha(page) {
  // Try to click the refresh button using different methods
  let refreshed = false;

  // Method 1: Using class selector
  try {
    await page.waitForSelector("svg.bcap-icon-refresh", {
      timeout: 5000,
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

  // Method 3: Using XPath
  if (!refreshed) {
    try {
      const [refreshButton] = await page.$x(
        "/html/body/div[7]/div/div[2]/div/div[1]/svg[2]",
      );
      if (refreshButton) {
        await refreshButton.click();
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

// Main function
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

async function addToWatchList(driver, searchTerm, count) {
  try {
    // Navigate to the site
    await driver.get("https://coinmarketcap.com/");
    await sleep(2000);

    // Search for the coin
    try {
      const searchInput = await driver.wait(
        until.elementLocated(
          By.xpath(
            "/html/body/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div[2]/div[2]/div/div[1]",
          ),
        ),
        10000,
      );
      await searchInput.click();
      // if (count != 1) {
      //   await searchInput.click();
      // }
      const seachBar = await driver.wait(
        until.elementLocated(
          By.xpath(
            "/html/body/div[3]/div[6]/div/div/div/div[1]/div[1]/div[1]/input",
          ),
        ),
        10000,
      );
      await seachBar.sendKeys(searchTerm);
      await sleep(2000);

      const firstEntry = await driver.wait(
        until.elementLocated(
          By.xpath(
            "/html/body/div[3]/div[6]/div/div/div/div[1]/div[3]/div[1]/a[1]",
          ),
        ),
        10000,
      );
      await firstEntry.click();
      await sleep(5000);

      try {
        const starIcon = await driver.wait(
          until.elementLocated(
            By.xpath(
              "/html/body/div[1]/div[2]/div/div[2]/div/div/div[1]/div/section/div/div[1]/div[2]/button",
            ),
          ),
          10000,
        );
        await starIcon.click();
        await sleep(5000);
        console.log(`✅ Added ${searchTerm} to watchlist`);
      } catch (e) {
        console.error(`❌ Error clicking star icon: ${e}`);
        return;
      }
    } catch (e) {
      console.error(`❌ Error searching for coin: ${e}`);
      return;
    }
  } catch (e) {
    console.error(`❌ Error in addToWatchList: ${e}`);
  }
}

function readSearchTerms() {
  return new Promise((resolve, reject) => {
    const searchTerms = [];

    // Check if file exists
    if (!fs.existsSync("searchTerm.csv")) {
      console.error("❌ Search terms file 'searchTerm.csv' not found!");
      resolve([]); // Return empty array if file doesn't exist
      return;
    }

    fs.createReadStream("searchTerm.csv")
      .pipe(csv())
      .on("data", (row) => {
        // Extract searchTerm from the first column
        if (row.searchTerm) {
          searchTerms.push(row.searchTerm);
        }
      })
      .on("end", () => {
        console.log(`📋 Loaded ${searchTerms.length} search terms`);
        resolve(searchTerms);
      })
      .on("error", (error) => {
        console.error(`❌ Error loading search terms: ${error.message}`);
        reject(error);
      });
  });
}

// Function to read emails from credentials.txt
async function readCredentials() {
  try {
    const filePath = path.join(__dirname, "credentials.txt");

    if (!fs.existsSync(filePath)) {
      console.error("❌ credentials.txt not found");
      return [];
    }

    const data = fs.readFileSync(filePath, "utf8");

    // Extract emails (skip lines with # as they are comments)
    const emails = data
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"));

    console.log(`✅ Loaded ${emails.length} accounts from credentials.txt`);
    return emails;
  } catch (err) {
    console.error(`❌ Error reading credentials: ${err.message}`);
    return [];
  }
}

// Function to read search terms from searchTerm.txt
async function readSearchTerms() {
  try {
    const filePath = path.join(__dirname, "searchTerm.txt");

    if (!fs.existsSync(filePath)) {
      console.error("❌ searchTerm.txt not found, checking for CSV...");
      return readSearchTermsFromCSV();
    }

    const data = fs.readFileSync(filePath, "utf8");

    // Extract search terms (one per line)
    const searchTerms = data
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"));

    console.log(
      `✅ Loaded ${searchTerms.length} search terms from searchTerm.txt`,
    );
    return searchTerms;
  } catch (err) {
    console.error(`❌ Error reading search terms: ${err.message}`);
    return [];
  }
}

// Fallback function to read search terms from CSV
function readSearchTermsFromCSV() {
  return new Promise((resolve, reject) => {
    const searchTerms = [];
    const filePath = path.join(__dirname, "searchTerm.csv");

    // Check if file exists
    if (!fs.existsSync(filePath)) {
      console.error("❌ Search terms file 'searchTerm.csv' not found!");
      resolve([]); // Return empty array if file doesn't exist
      return;
    }

    fs.createReadStream(filePath)
      .pipe(csv())
      .on("data", (row) => {
        // Extract searchTerm from the first column
        if (row.searchTerm) {
          searchTerms.push(row.searchTerm);
        }
      })
      .on("end", () => {
        console.log(`📋 Loaded ${searchTerms.length} search terms from CSV`);
        resolve(searchTerms);
      })
      .on("error", (error) => {
        console.error(
          `❌ Error loading search terms from CSV: ${error.message}`,
        );
        reject(error);
      });
  });
}

// Function to detect and handle slider CAPTCHA
async function handleSliderCaptcha(page) {
  try {
    // Check for slider CAPTCHA
    const hasSlider = await page.evaluate(() => {
      return (
        document.querySelector(".captcha-slider") !== null ||
        document.querySelector(".slidercaptcha") !== null ||
        document.querySelector(".slider-captcha") !== null
      );
    });

    if (hasSlider) {
      console.log("⚠️ Slider CAPTCHA detected - requires manual intervention");
      console.log("🕒 Waiting 60 seconds for manual solving...");
      await sleep(60000);

      // Take screenshot for debugging
      const screenshotsDir = path.join(__dirname, "screenshots");
      ensureDirectoryExists(screenshotsDir);
      await page.screenshot({
        path: path.join(
          screenshotsDir,
          `slider_captcha_${new Date().toISOString().replace(/:/g, "-")}.png`,
        ),
      });

      return true; // Assume it was solved manually
    }

    return false; // No slider CAPTCHA found
  } catch (error) {
    console.error(`❌ Error detecting slider CAPTCHA: ${error.message}`);
    return false;
  }
}

// Main login function
async function loginAccount(browser, email, proxy) {
  console.log(`🔄 Attempting to login with account: ${email}`);
  let page;

  try {
    // Get page from existing browser or create a new one
    try {
      page = (await browser.pages())[0];
      if (!page) throw new Error("No existing page");
    } catch (e) {
      console.log("Creating a new page for login...");
      page = await browser.newPage();
    }

    await page.setUserAgent(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    );

    // Set a longer default navigation timeout
    page.setDefaultNavigationTimeout(60000);

    // Navigate to CoinMarketCap
    console.log("🌐 Navigating to CoinMarketCap...");
    await page.goto("https://coinmarketcap.com/", {
      waitUntil: "networkidle2",
      timeout: 60000,
    });

    // Click login button
    try {
      console.log("🖱️ Clicking login button...");
      await page.waitForSelector('button[data-role="login"]', {
        timeout: 15000,
      });
      await page.click('button[data-role="login"]');
    } catch (error) {
      console.error("❌ Error clicking login button:", error);
      // Try XPath
      try {
        const [menuButton] = await page.$x(
          "/html/body/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div[2]/div[4]/button",
        );
        if (menuButton) {
          await menuButton.click();
          console.log("✅ Clicked login button using XPath");
        } else {
          throw new Error("Could not find login button");
        }
      } catch (e) {
        console.error("❌ Failed with XPath too:", e);
        throw e;
      }
    }
    await sleep(3000);

    // reject cookies if present
    try {
      console.log("🖱️ Checking for cookie popup...");
      const [rejectButton] = await page.$x(
        "/html/body/div[5]/div[2]/div/div[1]/div/div[2]/div/button[2]",
      );
      if (rejectButton) {
        await rejectButton.click();
        console.log("✅ Clicked reject cookies button");
      }
    } catch (error) {
      console.log("ℹ️ No cookie popup found or error clicking it:", error);
    }
    await sleep(1000);

    // Fill in email
    try {
      console.log(`🔄 Entering email: ${email}`);
      await page.waitForSelector('input[type="email"]', {
        timeout: 15000,
      });
      await page.type('input[type="email"]', email);
    } catch (error) {
      console.error("❌ Error entering email:", error);
      // Try XPath
      try {
        const [emailInput] = await page.$x("//input[@type='email']");
        if (emailInput) {
          await emailInput.type(email);
          console.log("✅ Entered email using XPath");
        } else {
          throw new Error("Could not find email input");
        }
      } catch (e) {
        console.error("❌ Failed with XPath too:", e);
        throw e;
      }
    }
    await sleep(1000);

    // Fill in password (same as email)
    try {
      console.log("🔄 Entering password...");
      await page.waitForSelector('input[type="password"]', {
        timeout: 15000,
      });
      await page.type('input[type="password"]', email);
    } catch (error) {
      console.error("❌ Error entering password:", error);
      // Try XPath
      try {
        const [passwordInput] = await page.$x("//input[@type='password']");
        if (passwordInput) {
          await passwordInput.type(email);
          console.log("✅ Entered password using XPath");
        } else {
          throw new Error("Could not find password input");
        }
      } catch (e) {
        console.error("❌ Failed with XPath too:", e);
        throw e;
      }
    }
    await sleep(1000);

    // Click login/submit button
    try {
      console.log("🖱️ Clicking submit button...");
      await page.waitForSelector('button[type="submit"]', {
        timeout: 15000,
      });
      await page.click('button[type="submit"]');
    } catch (error) {
      console.error("❌ Error clicking submit button:", error);
      // Try XPath
      try {
        const [submitButton] = await page.$x("//button[@type='submit']");
        if (submitButton) {
          await submitButton.click();
          console.log("✅ Clicked submit button using XPath");
        } else {
          throw new Error("Could not find submit button");
        }
      } catch (e) {
        console.error("❌ Failed with XPath too:", e);
        throw e;
      }
    }

    // Wait for CAPTCHA or successful login
    console.log("⏳ Waiting for CAPTCHA or successful login...");
    await sleep(5000);

    // Check for slider CAPTCHA first (it's rarer)
    const hasSliderCaptcha = await handleSliderCaptcha(page);

    if (!hasSliderCaptcha) {
      // Check for standard image CAPTCHA
      console.log("🔄 Checking for standard CAPTCHA...");
      const captchaSolved = await handleCaptcha(page);

      if (!captchaSolved) {
        console.log(
          "⚠️ CAPTCHA not solved automatically, waiting for manual intervention...",
        );
        // Give some time for manual solving
        await sleep(45000);
      }
    }

    // Check if login was successful
    const loginSuccess = await verifyLoginSuccess(page);

    if (loginSuccess) {
      console.log(`✅ Successfully logged in with account: ${email}`);
      return { success: true, page, message: "Login successful" };
    } else {
      console.error(`❌ Failed to login with account: ${email}`);
      return { success: false, error: "Login failed after CAPTCHA" };
    }
  } catch (error) {
    console.error(`❌ Error during login process: ${error.message}`);
    return { success: false, error: error.message };
  }
}

// Verify login success by checking if the login button is gone
async function verifyLoginSuccess(page) {
  try {
    await sleep(5000); // Wait for potential redirects

    // Check if login button is still present (indicating failed login)
    const loginButtonExists = await page.evaluate(() => {
      return document.querySelector('button[data-role="login"]') !== null;
    });

    if (!loginButtonExists) {
      // Check for user icon or profile menu as positive confirmation
      const userIconExists = await page.evaluate(() => {
        // Look for any common elements that appear when logged in
        return (
          document.querySelector('button[data-role="user-avatar"]') !== null ||
          document.querySelector('div[data-role="account-menu"]') !== null ||
          document.querySelector("div.accountDropdownButton") !== null ||
          document.querySelector("div.dropdown-toggle-user") !== null
        );
      });

      if (userIconExists) {
        console.log("✅ User icon detected - login confirmed");
        return true;
      }

      console.log(
        "⚠️ Login button gone but user icon not found - uncertain login status",
      );
      return true; // Assume success if login button is gone
    }

    console.log("❌ Login button still present - login failed");
    return false;
  } catch (error) {
    console.error(`❌ Error verifying login: ${error.message}`);
    return false;
  }
}

// Function to add a search term to watchlist
async function addToWatchlist(page, searchTerm) {
  try {
    console.log(`🔍 Adding "${searchTerm}" to watchlist...`);

    // Click search bar
    try {
      console.log("🖱️ Clicking search bar...");

      // Try using multiple possible selectors for the search bar
      const searchSelectors = [
        ".search-input",
        ".searchBox",
        ".cmc-header-search",
        'input[placeholder*="Search"]',
        'div[data-role="search"]',
      ];

      let searchClicked = false;

      for (const selector of searchSelectors) {
        try {
          await page.waitForSelector(selector, { timeout: 5000 });
          await page.click(selector);
          searchClicked = true;
          console.log(`✅ Clicked search using selector: ${selector}`);
          break;
        } catch (e) {
          // Try next selector
        }
      }

      // If none of the selectors worked, try XPath
      if (!searchClicked) {
        try {
          const [searchButton] = await page.$x(
            "/html/body/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div[2]/div[2]/div/div[1]",
          );
          if (searchButton) {
            await searchButton.click();
            searchClicked = true;
            console.log("✅ Clicked search using XPath");
          } else {
            throw new Error("Could not find search button with XPath");
          }
        } catch (e) {
          console.error(`❌ Error clicking search with XPath: ${e.message}`);
        }
      }

      if (!searchClicked) {
        throw new Error("Failed to click search with all methods");
      }
    } catch (error) {
      console.error(`❌ Error clicking search: ${error.message}`);
      return false;
    }

    await sleep(2000);

    // Type search term in search input
    try {
      // Try multiple possible selectors for the search input
      const inputSelectors = [
        'input[placeholder*="Search"]',
        ".searchInput",
        ".sc-bdvvtL",
      ];

      let searchTyped = false;

      for (const selector of inputSelectors) {
        try {
          await page.waitForSelector(selector, { timeout: 5000 });
          await page.type(selector, searchTerm);
          searchTyped = true;
          console.log(`✅ Typed search term using selector: ${selector}`);
          break;
        } catch (e) {
          // Try next selector
        }
      }

      // If none of the selectors worked, try XPath
      if (!searchTyped) {
        try {
          const [searchInput] = await page.$x(
            "/html/body/div[3]/div[6]/div/div/div/div[1]/div[1]/div[1]/input",
          );
          if (searchInput) {
            await searchInput.type(searchTerm);
            searchTyped = true;
            console.log("✅ Typed search term using XPath");
          } else {
            throw new Error("Could not find search input with XPath");
          }
        } catch (e) {
          console.error(`❌ Error typing search with XPath: ${e.message}`);
        }
      }

      if (!searchTyped) {
        throw new Error("Failed to type search with all methods");
      }
    } catch (error) {
      console.error(`❌ Error typing search term: ${error.message}`);
      return false;
    }

    await sleep(3000);

    // Click on first search result
    try {
      console.log("🖱️ Clicking first search result...");

      // Try using multiple possible selectors for the first result
      const resultSelectors = [
        ".searchDropdown a:first-child",
        ".searchResults a:first-child",
        "a.cmc-link:first-child",
      ];

      let resultClicked = false;

      for (const selector of resultSelectors) {
        try {
          await page.waitForSelector(selector, { timeout: 5000 });
          await page.click(selector);
          resultClicked = true;
          console.log(`✅ Clicked search result using selector: ${selector}`);
          break;
        } catch (e) {
          // Try next selector
        }
      }

      // If none of the selectors worked, try XPath
      if (!resultClicked) {
        try {
          const [firstResult] = await page.$x(
            "/html/body/div[3]/div[6]/div/div/div/div[1]/div[3]/div[1]/a[1]",
          );
          if (firstResult) {
            await firstResult.click();
            resultClicked = true;
            console.log("✅ Clicked search result using XPath");
          } else {
            throw new Error("Could not find search result with XPath");
          }
        } catch (e) {
          console.error(`❌ Error clicking result with XPath: ${e.message}`);
        }
      }

      if (!resultClicked) {
        throw new Error("Failed to click search result with all methods");
      }
    } catch (error) {
      console.error(`❌ Error clicking search result: ${error.message}`);
      return false;
    }

    await sleep(5000);

    // Click on star icon to add to watchlist
    try {
      console.log("🖱️ Clicking star icon to add to watchlist...");

      // Try using multiple possible selectors for the star icon
      const starSelectors = [
        "button.watchlistStar",
        "button.favorite-button",
        'button[data-role="watchlist"]',
        "button.sc-4anpgtl",
      ];

      let starClicked = false;

      for (const selector of starSelectors) {
        try {
          await page.waitForSelector(selector, { timeout: 5000 });
          await page.click(selector);
          starClicked = true;
          console.log(`✅ Clicked star icon using selector: ${selector}`);
          break;
        } catch (e) {
          // Try next selector
        }
      }

      // If none of the selectors worked, try XPath
      if (!starClicked) {
        try {
          const starXPaths = [
            "/html/body/div[1]/div[2]/div/div[2]/div/div/div[1]/div/section/div/div[1]/div[2]/button",
            "//button[contains(@class, 'favorite') or contains(@class, 'watchlist')]",
          ];

          for (const xpath of starXPaths) {
            try {
              const [starIcon] = await page.$x(xpath);
              if (starIcon) {
                await starIcon.click();
                starClicked = true;
                console.log(`✅ Clicked star icon using XPath: ${xpath}`);
                break;
              }
            } catch (e) {
              // Try next xpath
            }
          }

          if (!starClicked) {
            throw new Error("Could not find star icon with XPath");
          }
        } catch (e) {
          console.error(`❌ Error clicking star with XPath: ${e.message}`);
        }
      }

      if (!starClicked) {
        throw new Error("Failed to click star icon with all methods");
      }
    } catch (error) {
      console.error(`❌ Error clicking star icon: ${error.message}`);
      return false;
    }

    console.log(`✅ Successfully added "${searchTerm}" to watchlist`);
    await sleep(2000);
    return true;
  } catch (error) {
    console.error(
      `❌ Error adding "${searchTerm}" to watchlist: ${error.message}`,
    );
    return false;
  }
}

// Main function to process all accounts and search terms
async function main() {
  // Create results directory
  const resultsDir = path.join(__dirname, "results");
  ensureDirectoryExists(resultsDir);

  // Create log file
  const logFile = path.join(
    resultsDir,
    `login_watchlist_log_${new Date().toISOString().replace(/:/g, "-")}.txt`,
  );
  fs.writeFileSync(
    logFile,
    `Login and Watchlist Log - Started at ${new Date().toISOString()}\n\n`,
  );

  // Load credentials
  const accounts = await readCredentials();

  if (accounts.length === 0) {
    console.error("❌ No accounts found in credentials.txt");
    return;
  }

  // Load search terms
  const searchTerms = await readSearchTerms();

  if (searchTerms.length === 0) {
    console.error(
      "❌ No search terms found in searchTerm.txt or searchTerm.csv",
    );
    return;
  }

  // Load proxies
  const proxies = await loadProxies();
  if (proxies.length === 0) {
    console.error("❌ No proxies available. Using direct connection...");
  }

  let currentProxyIndex = -1;
  let successCount = 0;
  let failureCount = 0;

  // Process each account
  for (let i = 0; i < accounts.length; i++) {
    const email = accounts[i];
    console.log(
      `\n🔄 Processing account ${i + 1}/${accounts.length}: ${email}`,
    );

    // Get next proxy
    let proxy = null;
    if (proxies.length > 0) {
      const proxyResult = getNextProxy(proxies, currentProxyIndex);
      proxy = proxyResult.proxy;
      currentProxyIndex = proxyResult.newIndex;
      console.log(`🌐 Using proxy: ${proxy.ip}:${proxy.port}`);
    }

    let browser;
    try {
      // Launch browser with proxy if available
      const browserArgs = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
      ];

      if (proxy) {
        browserArgs.push(`--proxy-server=${proxy.ip}:${proxy.port}`);
      }

      browser = await puppeteer.launch({
        headless: false,
        args: browserArgs,
        defaultViewport: null,
      });

      // Login to the account
      const loginResult = await loginAccount(browser, email, proxy);

      if (loginResult.success) {
        // Add search terms to watchlist
        const page = loginResult.page;
        let watchlistSuccess = 0;

        for (let j = 0; j < searchTerms.length; j++) {
          const searchTerm = searchTerms[j];
          console.log(
            `\n🔍 Adding term ${j + 1}/${searchTerms.length}: ${searchTerm}`,
          );

          const addResult = await addToWatchlist(page, searchTerm);

          if (addResult) {
            watchlistSuccess++;
            console.log(`✅ Successfully added "${searchTerm}" to watchlist`);
          } else {
            console.log(`❌ Failed to add "${searchTerm}" to watchlist`);
          }

          // Add a random delay between search term processing
          if (j < searchTerms.length - 1) {
            const delay = 5000 + Math.random() * 5000; // 5-10 seconds
            console.log(
              `⏳ Waiting ${Math.round(
                delay / 1000,
              )} seconds before next search term...`,
            );
            await sleep(delay);
          }
        }

        // Log results
        const accountLog = `[${new Date().toISOString()}] Account: ${email} - Login: SUCCESS - Watchlist: ${watchlistSuccess}/${
          searchTerms.length
        } items added\n`;
        fs.appendFileSync(logFile, accountLog);

        successCount++;
      } else {
        // Log failure
        const accountLog = `[${new Date().toISOString()}] Account: ${email} - Login: FAILED - Error: ${
          loginResult.error
        }\n`;
        fs.appendFileSync(logFile, accountLog);

        failureCount++;
      }
    } catch (error) {
      console.error(`❌ Error processing account ${email}: ${error.message}`);

      // Log error
      const accountLog = `[${new Date().toISOString()}] Account: ${email} - ERROR: ${
        error.message
      }\n`;
      fs.appendFileSync(logFile, accountLog);

      failureCount++;
    } finally {
      // Close the browser
      if (browser) {
        console.log("🚪 Closing browser...");
        await browser.close();
      }
    }

    // Add a delay between accounts
    if (i < accounts.length - 1) {
      const delay = 10000 + Math.random() * 10000; // 10-20 seconds
      console.log(
        `⏳ Waiting ${Math.round(delay / 1000)} seconds before next account...`,
      );
      await sleep(delay);
    }
  }

  // Log summary
  const summary = `
=== SUMMARY ===
Total accounts processed: ${accounts.length}
Successful: ${successCount}
Failed: ${failureCount}
Success rate: ${Math.round((successCount / accounts.length) * 100)}%
Completed at: ${new Date().toISOString()}
===============
`;

  console.log(summary);
  fs.appendFileSync(logFile, summary);
  console.log(`📝 Full log saved to: ${logFile}`);
}

// Run the main function
if (require.main === module) {
  main().catch((error) => {
    console.error(`❌ Unhandled error in main function: ${error}`);
    process.exit(1);
  });
}

// Export functions for potential reuse
module.exports = {
  loginAccount,
  addToWatchlist,
  readCredentials,
  readSearchTerms,
};
