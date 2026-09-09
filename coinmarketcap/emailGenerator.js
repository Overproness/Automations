const { drive } = require("googleapis/build/src/apis/drive");
const { Builder, By, until } = require("selenium-webdriver");
const chrome = require("selenium-webdriver/chrome");
const XLSX = require("xlsx");
const fs = require("fs");

// Configuration
const GENERATE_EMAILS = 100;
const LOG_FILE = "email_generator.log";

// Icons for visual status indicators
const ICONS = {
  INFO: "ℹ️",
  SUCCESS: "✅",
  WARNING: "⚠️",
  ERROR: "❌",
  START: "🚀",
  FINISH: "🏁",
  WAIT: "⏳",
  SAVE: "💾",
  EMAIL: "📧",
  CLICK: "🖱️",
  BROWSER: "🌐",
  RECOVERY: "🔄",
  LOGIN: "🔑",
};

// Helper function for logging with timestamps and icons
function log(message, type = "INFO", consoleOnly = false, fileOnly = false) {
  const timestamp = new Date().toISOString();
  const icon = ICONS[type] || ICONS.INFO;
  const consoleMessage = `${icon} ${message}`;
  const fileMessage = `[${timestamp}] ${type}: ${message}`;

  // Log to console if not fileOnly
  if (!fileOnly) {
    if (type === "ERROR" || type === "WARNING") {
      console.error(consoleMessage);
    } else {
      console.log(consoleMessage);
    }
  }

  // Log to file if not consoleOnly
  if (!consoleOnly && LOG_FILE) {
    try {
      fs.appendFileSync(LOG_FILE, fileMessage + "\n");
    } catch (err) {
      console.error(
        `${ICONS.ERROR} Failed to write to log file: ${err.message}`
      );
    }
  }
}

async function runSimpleLoginBot() {
  log("=== EMAIL GENERATOR SCRIPT STARTED ===", "START");
  log(`Target: Generate ${GENERATE_EMAILS} emails`, "INFO");

  // Set up Chrome options
  const options = new chrome.Options();
  // Uncomment for headless mode if needed
  // options.addArguments('--headless');

  log("Initializing Chrome WebDriver...", "BROWSER");
  let driver;

  try {
    // Create the driver
    driver = await new Builder()
      .forBrowser("chrome")
      .setChromeOptions(options)
      .build();

    log("WebDriver initialized successfully", "SUCCESS");
    await driver.manage().window().maximize();

    // Navigate to the login page
    log("Navigating to SimpleLogin page", "BROWSER");
    await driver.get("https://app.simplelogin.io/auth/login");

    // Wait for page to load and elements to be visible
    await driver.wait(
      until.elementLocated(By.xpath('//*[@id="email"]')),
      10000
    );

    // Enter credentials and login
    log("Logging in to SimpleLogin", "LOGIN");
    await driver
      .findElement(By.xpath('//*[@id="email"]'))
      .sendKeys("fivacc8@gmail.com");

    await driver
      .findElement(By.xpath('//*[@id="password"]'))
      .sendKeys("test1234");

    await driver
      .findElement(
        By.xpath(
          "/html/body/div/div[2]/div/div/div/div[2]/div/form/div[3]/button"
        )
      )
      .click();

    // Wait for the page to load after login
    await driver.sleep(5000);

    // Check if login was successful
    try {
      await driver.findElement(By.xpath("//a[contains(@href, '/dashboard')]"));
      log("Login successful", "SUCCESS");
    } catch (error) {
      log("Could not verify successful login. Continuing anyway...", "WARNING");
    }

    // Prepare for email generation
    const buttonXPath =
      "/html/body/div/div[2]/div[3]/div/div[1]/div/div/div[1]/div/div/form/button";

    log("Waiting for email generation button", "INFO");
    await driver.wait(until.elementLocated(By.xpath(buttonXPath)), 15000);

    log(
      `Starting email generation process (${GENERATE_EMAILS} emails)`,
      "START"
    );
    let successCount = 0;
    let failureCount = 0;

    for (let i = 1; i < GENERATE_EMAILS; i++) {
      log(`Email generation attempt ${i}/${GENERATE_EMAILS - 1}`, "INFO", true);

      try {
        // Handle rate limiting pauses
        if (i % 1 === 0) {
          log(`Rate limit pause after ${i} iterations`, "WAIT");
          await driver.get("https://app.simplelogin.io/dashboard/");
          await driver.sleep(30000);
          log("Pause completed", "INFO", true);
        }

        if (i % 50 === 0) {
          log(`Extended pause after ${i} iterations`, "WAIT");
          await driver.get("https://app.simplelogin.io/dashboard/");
          await driver.sleep(300000);
          log("Extended pause completed", "INFO", true);
          continue;
        }

        // Try to click the button to generate a new email
        try {
          const button = await driver.findElement(By.xpath(buttonXPath));
          await driver.wait(until.elementIsVisible(button), 5000);

          // Get button text for debugging (log to file only)
          try {
            const buttonText = await button.getText();
            log(`Button text: "${buttonText}"`, "INFO", false, true);
          } catch (err) {
            log("Could not get button text", "INFO", false, true);
          }

          await button.click();
          log(`Click successful (${i})`, "CLICK", true);
          await driver.sleep(5000);
        } catch (error) {
          log(`Click failed (${i}): ${error.message}`, "ERROR");

          // Take screenshot on error (log to file only)
          try {
            const screenshot = await driver.takeScreenshot();
            const screenshotPath = `error_screenshot_${i}.png`;
            fs.writeFileSync(screenshotPath, screenshot, "base64");
            log(`Screenshot saved: ${screenshotPath}`, "INFO", false, true);
          } catch (screenshotError) {
            log(
              `Failed to take screenshot: ${screenshotError.message}`,
              "ERROR",
              false,
              true
            );
          }

          // Fallback click attempt
          try {
            log("Attempting fallback click", "RECOVERY", true);
            await driver.findElement(By.css('data-toggle="tooltip"')).click();
            log("Fallback click succeeded", "SUCCESS", true);
            await driver.sleep(5000);
          } catch (fallbackError) {
            log(`Fallback click failed`, "ERROR");
            failureCount++;
            continue; // Skip to next iteration
          }
        }

        // Try to get the new email address
        try {
          const newEmail = await driver
            .findElement(
              By.xpath(
                "/html/body/div/div[2]/div[3]/div/div[2]/div[1]/div/div[1]/div[1]/span"
              )
            )
            .getText();

          log(`New email: ${newEmail}`, "EMAIL");

          // Load or create the Excel file (detailed logs to file only)
          log("Updating Excel file", "SAVE", true);
          let workbook;
          if (fs.existsSync("credentials.xlsx")) {
            log("Loading existing Excel file", "INFO", false, true);
            workbook = XLSX.readFile("credentials.xlsx");
          } else {
            log("Creating new Excel file", "INFO", false, true);
            workbook = XLSX.utils.book_new();
          }

          let sheetName = "Sheet1";
          let worksheet =
            workbook.Sheets[sheetName] || XLSX.utils.aoa_to_sheet([]);

          // Append the new email
          const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
          data.push([newEmail]);

          // Write back to the file
          const newWorksheet = XLSX.utils.aoa_to_sheet(data);
          workbook.Sheets[sheetName] = newWorksheet;
          XLSX.writeFile(workbook, "credentials.xlsx");

          log(`Email #${data.length} saved successfully`, "SUCCESS");
          successCount++;
        } catch (emailError) {
          log(`Failed to save email: ${emailError.message}`, "ERROR");
          failureCount++;
        }
      } catch (iterationError) {
        log(`Iteration ${i} failed completely`, "ERROR");
        log(`Error details: ${iterationError.message}`, "ERROR", false, true);
        failureCount++;

        // Try to recover
        try {
          log("Attempting recovery", "RECOVERY");
          await driver.get("https://app.simplelogin.io/dashboard/");
          await driver.sleep(10000);
        } catch (recoveryError) {
          log(`Recovery failed`, "ERROR");
        }
      }

      await driver.sleep(5000); // Pause between iterations
    }

    log("Email generation process completed", "FINISH");
    log(
      `SUMMARY: ✅ ${successCount} emails generated | ❌ ${failureCount} failures`,
      "INFO"
    );
  } catch (error) {
    log(`CRITICAL ERROR: ${error.message}`, "ERROR");
    log(`Error stack: ${error.stack}`, "ERROR", false, true);

    // Take final error screenshot
    try {
      if (driver) {
        const screenshot = await driver.takeScreenshot();
        fs.writeFileSync("critical_error_screenshot.png", screenshot, "base64");
        log("Critical error screenshot saved", "INFO", false, true);
      }
    } catch (screenshotError) {
      log(`Failed to take critical error screenshot`, "ERROR");
    }
  } finally {
    // Close the browser
    if (driver) {
      log("Closing browser", "BROWSER");
      try {
        await driver.quit();
        log("Browser closed successfully", "SUCCESS");
      } catch (quitError) {
        log(`Failed to close browser`, "ERROR");
      }
    }
    log("Script execution finished", "FINISH");
  }
}

// Run the script
runSimpleLoginBot().catch((err) => {
  log(`Unhandled error: ${err.message}`, "ERROR");
  log(`Error stack: ${err.stack}`, "ERROR", false, true);
});
