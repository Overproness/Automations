const { Builder, By, Key, until } = require("selenium-webdriver");
const chrome = require("selenium-webdriver/chrome");
const fs = require("fs");
const xlsx = require("xlsx");
const readline = require("readline");
// const clipboard = require("clipboardy");
const clipboard = import("clipboardy");
const path = require("path");
const csv = require("csv-parser"); // Add this for CSV parsing

// Create readline interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

// Function to prompt for input
function prompt(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

// Function to load proxies from CSV file
async function loadProxies() {
  return new Promise((resolve, reject) => {
    const proxies = [];

    // Check if file exists
    if (!fs.existsSync("proxies.csv")) {
      console.error("❌ Proxies file 'proxies.csv' not found!");
      proxies.push(
        {
          entryPoint: "dc.oxylabs.io",
          port: "8001",
          country: "United States of America",
          ip: "93.115.200.159",
          usageCount: 0,
        },
        {
          entryPoint: "dc.oxylabs.io",
          port: "8002",
          country: "United States of America",
          ip: "93.115.200.158",
          usageCount: 0,
        },
        {
          entryPoint: "dc.oxylabs.io",
          port: "8003",
          country: "United States of America",
          ip: "93.115.200.157",
          usageCount: 0,
        },
        {
          entryPoint: "dc.oxylabs.io",
          port: "8004",
          country: "United States of America",
          ip: "93.115.200.156",
          usageCount: 0,
        },
        {
          entryPoint: "dc.oxylabs.io",
          port: "8005",
          country: "United States of America",
          ip: "93.115.200.155",
          usageCount: 0,
        },
      );
      console.log(`📋 Loaded ${proxies.length} proxies`);
      resolve(proxies);
      return;
    }

    fs.createReadStream("proxies.csv")
      .pipe(csv())
      .on("data", (row) => {
        // Extract proxy details from CSV row
        // Assuming CSV has columns: entryPoint, port, country, ip
        if (row.entryPoint && row.port && row.ip) {
          proxies.push({
            entryPoint: row.entryPoint,
            port: row.port,
            country: row.country || "Unknown",
            ip: row.ip,
            usageCount: 0, // Track how many times this proxy has been used
          });
        }
      })
      .on("end", () => {
        if (proxies.length === 0) {
          // If CSV parsing didn't work, use the hardcoded proxies
          console.log("📋 Using hardcoded proxy list...");
          proxies.push(
            {
              entryPoint: "dc.oxylabs.io",
              port: "8001",
              country: "United States of America",
              ip: "93.115.200.159",
              usageCount: 0,
            },
            {
              entryPoint: "dc.oxylabs.io",
              port: "8002",
              country: "United States of America",
              ip: "93.115.200.158",
              usageCount: 0,
            },
            {
              entryPoint: "dc.oxylabs.io",
              port: "8003",
              country: "United States of America",
              ip: "93.115.200.157",
              usageCount: 0,
            },
            {
              entryPoint: "dc.oxylabs.io",
              port: "8004",
              country: "United States of America",
              ip: "93.115.200.156",
              usageCount: 0,
            },
            {
              entryPoint: "dc.oxylabs.io",
              port: "8005",
              country: "United States of America",
              ip: "93.115.200.155",
              usageCount: 0,
            },
          );
        }

        console.log(`📋 Loaded ${proxies.length} proxies`);
        resolve(proxies);
      })
      .on("error", (error) => {
        console.error(`❌ Error loading proxies: ${error.message}`);
        reject(error);
      });
  });
}

// Function to get the next available proxy
function getNextProxy(proxies, currentProxyIndex) {
  // If we've used the current proxy twice, move to the next one
  if (currentProxyIndex >= 0 && proxies[currentProxyIndex].usageCount >= 2) {
    currentProxyIndex = (currentProxyIndex + 1) % proxies.length;
  } else if (currentProxyIndex < 0) {
    // First run, start with the first proxy
    currentProxyIndex = 0;
  }

  // Increment usage count for the selected proxy
  proxies[currentProxyIndex].usageCount++;

  return {
    proxy: proxies[currentProxyIndex],
    newIndex: currentProxyIndex,
  };
}

async function main() {
  // User inputs
  const numAccounts = 2;
  const baseUsername = "fjdkslajfncvm23";
  const useProxies = true;
  const proxyUsername = "";
  const proxyPassword = "_Test1234567";
  const stdPassword = "";
  const excelFilename = "accounts.xlsx";

  const chromeProfilePath =
    "C:\\Users\\resea\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 10";

  // Load proxies if needed
  let proxies = [];
  let currentProxyIndex = -1;

  if (useProxies) {
    try {
      proxies = await loadProxies();
      if (proxies.length === 0) {
        console.error("❌ No proxies available. Exiting...");
        rl.close();
        return;
      }
    } catch (error) {
      console.error(`❌ Failed to load proxies: ${error.message}`);
      rl.close();
      return;
    }
  }

  // Initialize Excel file
  let workbook;
  if (!fs.existsSync(excelFilename)) {
    workbook = xlsx.utils.book_new();
    const sheet = xlsx.utils.aoa_to_sheet([
      ["Email", "Password", "Verification Email", "Status", "Proxy Used"],
    ]);
    xlsx.utils.book_append_sheet(workbook, sheet, "Accounts");
    xlsx.writeFile(workbook, excelFilename);
  } else {
    workbook = xlsx.readFile(excelFilename);
    let sheet = workbook.Sheets["Accounts"];

    // Check if the sheet has the correct headers
    if (!sheet["A1"] || sheet["A1"].v !== "Email") {
      // Add header row
      const data = xlsx.utils.sheet_to_json(sheet);
      const newSheet = xlsx.utils.aoa_to_sheet([
        ["Email", "Password", "Verification Email", "Status", "Proxy Used"],
      ]);
      xlsx.utils.sheet_add_json(newSheet, data, { origin: "A2" });
      workbook.Sheets["Accounts"] = newSheet;
      xlsx.writeFile(workbook, excelFilename);
    }
  }

  // Main account creation process
  for (let i = 0; i < numAccounts; i++) {
    let driver = null;
    let currentProxy = null;

    try {
      // Configure Chrome options
      const options = new chrome.Options();
      options.addArguments(`--user-data-dir=${chromeProfilePath}`);

      // Set up proxy if enabled
      if (useProxies) {
        const proxyResult = getNextProxy(proxies, currentProxyIndex);
        currentProxy = proxyResult.proxy;
        currentProxyIndex = proxyResult.newIndex;

        console.log(
          `🌐 Using proxy: ${currentProxy.entryPoint}:${currentProxy.port} (${currentProxy.ip})`,
        );

        // Set up proxy with authentication
        if (proxyUsername && proxyPassword) {
          // Method 1: Set up proxy with authentication in URL format
          const proxyUrl = `http://${proxyUsername}:${proxyPassword}@${currentProxy.entryPoint}:${currentProxy.port}`;
          options.addArguments(`--proxy-server=${proxyUrl}`);

          // Additional arguments that might help with proxy authentication
          options.addArguments("--no-sandbox");
          options.addArguments("--disable-dev-shm-usage");
        } else {
          // Method 2: Set up proxy without authentication
          options.addArguments(
            `--proxy-server=http://${currentProxy.entryPoint}:${currentProxy.port}`,
          );
        }
      }

      // Launch Chrome browser
      driver = await new Builder()
        .forBrowser("chrome")
        .setChromeOptions(options)
        .build();

      await driver.manage().window().maximize();

      // Helper function to wait for an element
      async function waitForElement(xpath, timeout = 10000) {
        try {
          const element = await driver.wait(
            until.elementLocated(By.xpath(xpath)),
            timeout,
          );
          return element;
        } catch (error) {
          console.log(
            `Element with xpath ${xpath} not found within ${
              timeout / 1000
            } seconds`,
          );
          return null;
        }
      }

      // Function to get temporary email
      async function getTempEmail() {
        await driver.executeScript(
          "window.open('https://temp-mail.io/en', 'temp_mail');",
        );
        await driver.switchTo().window("temp_mail");
        await driver.sleep(10000);

        try {
          // Wait for the copy button and click it
          const copyButton = await waitForElement(
            "/html/body/div[1]/div/header/div[2]/button[1]",
            15000,
          );
          if (copyButton) {
            await copyButton.click();
            await driver.sleep(1000); // Wait for copy to clipboard
            const tempEmail = await clipboard.read();
            console.log(`Temporary email obtained: ${tempEmail}`);
            return tempEmail;
          } else {
            console.log("Could not find copy button on temp-mail.io");
            return null;
          }
        } catch (error) {
          console.log(`Error getting temporary email: ${error}`);
          return null;
        }
      }

      // Function to extract OTP from email
      async function extractOtpFromEmail() {
        const maxAttempts = 10;
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
          try {
            // Try to find the email in the inbox
            const emailItems = await driver.findElements(
              By.xpath("//ul/li[contains(@class, 'email-list-item')]"),
            );
            if (emailItems.length > 0) {
              // Click on the first email (which should be from Proton)
              await emailItems[0].click();
              await driver.sleep(2000);

              // Get the email content
              const emailContentElement = await driver.findElement(
                By.xpath("//div[contains(@class, 'email-body')]"),
              );
              const emailContent = await emailContentElement.getText();

              // Extract OTP using regex
              const otpMatch = emailContent.match(
                /code to finish the process:\s*(\d+)/,
              );
              if (otpMatch) {
                const otp = otpMatch[1];
                console.log(`OTP extracted: ${otp}`);
                return otp;
              }
            }

            console.log(
              `OTP not found yet, attempt ${attempt + 1}/${maxAttempts}`,
            );
            await driver.sleep(5000); // Wait 5 seconds before checking again

            // Refresh the inbox
            const refreshButton = await driver.findElement(
              By.xpath("//button[contains(@class, 'refresh')]"),
            );
            if (refreshButton) {
              await refreshButton.click();
              await driver.sleep(2000);
            }
          } catch (error) {
            console.log(`Error extracting OTP: ${error}`);
          }
        }

        console.log("Failed to extract OTP after multiple attempts");
        return null;
      }

      // Function to complete signup
      async function completeSignup(tempEmail, username, password) {
        try {
          // Get all window handles
          const handles = await driver.getAllWindowHandles();

          // Switch back to Proton tab (first tab)
          await driver.switchTo().window(handles[0]);

          // Enter verification email
          const verificationInput = await waitForElement(
            "//input[@placeholder='Recovery email address']",
            10000,
          );
          if (verificationInput) {
            await verificationInput.clear();
            await verificationInput.sendKeys(tempEmail);
            await driver.sleep(1000);

            // Continue with verification
            const nextButton = await waitForElement(
              "//button[contains(text(), 'Next')]",
              5000,
            );
            if (nextButton) {
              await nextButton.click();
              await driver.sleep(3000);

              // Switch to temp-mail tab
              await driver.switchTo().window(handles[1]);
              const otp = await extractOtpFromEmail();

              if (otp) {
                // Switch back to Proton tab
                await driver.switchTo().window(handles[0]);

                // Enter OTP
                const otpInput = await waitForElement(
                  "//input[@placeholder='Verification code']",
                  10000,
                );
                if (otpInput) {
                  await otpInput.clear();
                  await otpInput.sendKeys(otp);
                  await driver.sleep(1000);

                  // Complete verification
                  const verifyButton = await waitForElement(
                    "//button[contains(text(), 'Verify')]",
                    5000,
                  );
                  if (verifyButton) {
                    await verifyButton.click();
                    await driver.sleep(5000);

                    // Complete any remaining steps
                    try {
                      const skipButton = await waitForElement(
                        "//button[contains(text(), 'Skip')]",
                        10000,
                      );
                      if (skipButton) {
                        await skipButton.click();
                        await driver.sleep(2000);
                      }
                    } catch (error) {
                      console.log("No skip button found, continuing...");
                    }

                    return true;
                  }
                }
              }
            }
          }
        } catch (error) {
          console.log(`Error during signup completion: ${error}`);
        }

        return false;
      }

      // Open Proton signup page
      await driver.get(
        "https://account.proton.me/mail/signup?plan=free&ref=mail_plus_intro-mailpricing-2",
      );

      // Check if we need to handle proxy authentication dialog
      if (useProxies && proxyUsername && proxyPassword) {
        console.log(
          "Waiting for the page to load (might include proxy authentication)...",
        );
        await driver.sleep(8000); // Allow time for proxy auth if needed
      }

      await driver.sleep(5000); // Wait for page to load

      console.log("Entering account details...");

      const username = `${baseUsername}${i}`; // Generate unique username
      const emailAddress = `${username}`;

      // Try to enter username into the username field
      try {
        // First try clicking the field
        const usernameField = await waitForElement(
          "//input[@name='username']",
          10000,
        );
        if (usernameField) {
          await usernameField.click();
          await usernameField.clear();
          await usernameField.sendKeys(username);
          console.log("Username entered with direct field access");
        } else {
          // If field not found, try sending keys directly
          await driver.actions().sendKeys(username).perform();
          console.log("Username entered with actions API");
        }
        await driver.sleep(1000);
      } catch (error) {
        console.log(`Error entering username: ${error}`);
      }

      // Enter password
      const passwordInput = await waitForElement(
        "//input[@id='password']",
        10000,
      );
      if (passwordInput) {
        await passwordInput.clear();
        await passwordInput.sendKeys(stdPassword);
        await driver.sleep(1000);
        console.log("Password entered");
      } else {
        console.log(
          "Password field not found - page might not have loaded correctly",
        );

        // Take a screenshot to debug the issue
        const screenshot = await driver.takeScreenshot();
        const screenshotPath = `debug_screenshot_${i}.png`;
        fs.writeFileSync(screenshotPath, screenshot, "base64");
        console.log(`Screenshot saved to ${screenshotPath}`);

        // Get current URL to help with debugging
        const currentUrl = await driver.getCurrentUrl();
        console.log(`Current URL: ${currentUrl}`);

        throw new Error(
          "Password field not found - possible proxy or page loading issue",
        );
      }

      // Repeat password
      const repeatPasswordInput = await waitForElement(
        "//input[@id='repeat-password']",
        10000,
      );
      if (repeatPasswordInput) {
        await repeatPasswordInput.clear();
        await repeatPasswordInput.sendKeys(stdPassword);
        await driver.sleep(1000);
        console.log("Repeat password entered");
      }

      // Click "Create Account" button
      const createAccountBtn = await waitForElement(
        "//button[@type='submit']",
        10000,
      );
      if (createAccountBtn) {
        await createAccountBtn.click();
        await driver.sleep(15000); // Wait for next page
        console.log("Create account button clicked");
      }

      // Get temporary email for verification
      console.log("Getting temporary email...");
      const tempEmail = await getTempEmail();
      if (tempEmail) {
        // Complete the signup process
        console.log("Completing signup with verification...");
        const success = await completeSignup(tempEmail, username, stdPassword);

        // Save credentials to Excel
        const workbook = xlsx.readFile(excelFilename);
        const sheet = workbook.Sheets["Accounts"];
        const data = xlsx.utils.sheet_to_json(sheet);
        const status = success ? "Success" : "Failed";
        const proxyInfo = currentProxy
          ? `${currentProxy.entryPoint}:${currentProxy.port}`
          : "None";

        data.push({
          Email: emailAddress,
          Password: stdPassword,
          "Verification Email": tempEmail,
          Status: status,
          "Proxy Used": proxyInfo,
        });

        const newSheet = xlsx.utils.json_to_sheet(data);
        workbook.Sheets["Accounts"] = newSheet;
        xlsx.writeFile(workbook, excelFilename);

        console.log(
          `Account ${
            i + 1
          } created: ${emailAddress}, Status: ${status}, Proxy: ${proxyInfo}`,
        );

        // Close temp-mail tab to avoid having too many tabs open
        const handles = await driver.getAllWindowHandles();
        if (handles.length > 1) {
          await driver.switchTo().window(handles[1]);
          await driver.close();
          await driver.switchTo().window(handles[0]);
        }
      } else {
        console.log(`Failed to get temporary email for account ${i + 1}`);
        const workbook = xlsx.readFile(excelFilename);
        const sheet = workbook.Sheets["Accounts"];
        const data = xlsx.utils.sheet_to_json(sheet);
        const proxyInfo = currentProxy
          ? `${currentProxy.entryPoint}:${currentProxy.port}`
          : "None";

        data.push({
          Email: emailAddress,
          Password: stdPassword,
          "Verification Email": "N/A",
          Status: "Failed - No temp email",
          "Proxy Used": proxyInfo,
        });

        const newSheet = xlsx.utils.json_to_sheet(data);
        workbook.Sheets["Accounts"] = newSheet;
        xlsx.writeFile(workbook, excelFilename);
      }
    } catch (error) {
      console.log(`Error creating account ${i + 1}: ${error}`);
      // Save the failure to Excel
      try {
        const workbook = xlsx.readFile(excelFilename);
        const sheet = workbook.Sheets["Accounts"];
        const data = xlsx.utils.sheet_to_json(sheet);
        const proxyInfo = currentProxy
          ? `${currentProxy.entryPoint}:${currentProxy.port}`
          : "None";

        data.push({
          Email: `${baseUsername}${i}@proton.me`,
          Password: stdPassword,
          "Verification Email": "N/A",
          Status: `Failed - ${error.toString().substring(0, 50)}`,
          "Proxy Used": proxyInfo,
        });

        const newSheet = xlsx.utils.json_to_sheet(data);
        workbook.Sheets["Accounts"] = newSheet;
        xlsx.writeFile(workbook, excelFilename);
      } catch (excelError) {
        console.log(`Error saving failure to Excel: ${excelError}`);
      }
    } finally {
      if (driver) {
        try {
          await driver.quit();
          console.log("WebDriver closed successfully");
        } catch (driverError) {
          console.log(`Error closing WebDriver: ${driverError}`);
        }
      }
    }
  }

  console.log(
    `All account creation attempts have been completed and saved to ${excelFilename}`,
  );
  rl.close();
}

main().catch((error) => {
  console.error(`Main program error: ${error}`);
  rl.close();
});
