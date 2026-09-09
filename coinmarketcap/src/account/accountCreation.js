const {
  launchBrowser,
  createPage,
  safeClick,
  safeType,
  navigateToUrl,
} = require("../utils/browserUtils");
const { takeScreenshot } = require("../utils/fileUtils");
const { saveCredentials } = require("../utils/fileUtils");
const { getTempEmail } = require("../email/tempEmailService");
const { handleCaptcha } = require("../captcha/captchaHandlers");
const { checkForVerificationEmail } = require("../email/tempEmailService");
const { completeVerificationProcess } = require("./verificationProcess");
const config = require("../config");

/**
 * Create a CoinMarketCap account
 */
async function createAccount(proxy) {
  console.log(`🌐 Using proxy: ${proxy.ip}:${proxy.port}`);
  let browser;
  let email; // Declare email at function scope

  try {
    // Launch browser with proxy
    browser = await launchBrowser(proxy);

    // wait for 3 mins
    // await setTimeout(() => {}, 180000);

    // Step 1-3: Get temporary email
    const tempEmailData = await getTempEmail(browser, proxy);

    if (!tempEmailData) {
      throw new Error(
        "Failed to obtain a temporary email address from any provider"
      );
    }

    email = tempEmailData.email; // Set email for wider scope
    const { page: emailPage, provider } = tempEmailData;

    // Step 4-7: CoinMarketCap signup
    console.log("🔄 Opening CoinMarketCap in new tab for signup...");
    const cmcPage = await createPage(browser);

    // Set a longer navigation timeout
    cmcPage.setDefaultNavigationTimeout(60000);

    let signupSuccess = false;

    // Try signup with retry logic
    for (let attempt = 1; attempt <= config.MAX_SIGNUP_ATTEMPTS; attempt++) {
      try {
        console.log(
          `🔄 Signup attempt ${attempt}/${config.MAX_SIGNUP_ATTEMPTS}...`
        );

        // Navigate to CMC
        await navigateToUrl(cmcPage, "https://coinmarketcap.com/");

        // Click login button
        let loginClicked = await safeClick(
          cmcPage,
          'button[data-test="Log In"]',
          { timeout: 15000 }
        );

        if (!loginClicked) {
          // Try XPath as fallback
          const menuButtons = await cmcPage.$x(
            "/html/body/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div[2]/div[4]/button"
          );
          if (menuButtons.length > 0) {
            await menuButtons[0].click();
            loginClicked = true;
            console.log("✅ Clicked login button using XPath");
          } else {
            throw new Error("Could not find login button");
          }
        }
        await cmcPage.waitForTimeout(3000);

        // Try to reject cookies
        try {
          console.log("🖱️ Clicking reject cookies button...");
          const rejectButtons = await cmcPage.$x(
            "/html/body/div[5]/div[2]/div/div[1]/div/div[2]/div/button[2]"
          );
          if (rejectButtons.length > 0) {
            await rejectButtons[0].click();
            console.log("✅ Clicked reject cookies button");
          }
        } catch (error) {
          console.error("❌ Error clicking reject cookies button:", error);
        }
        await cmcPage.waitForTimeout(3000);

        // Click Sign Up button
        let signupClicked = await safeClick(
          cmcPage,
          'div[data-action="sign-up"]'
        );
        if (!signupClicked) {
          // Try XPath as fallback
          const signupButtons = await cmcPage.$x(
            "/html/body/div[6]/div/div/div/div/div[1]/div[2]"
          );
          if (signupButtons.length > 0) {
            await signupButtons[0].click();
            signupClicked = true;
            console.log("✅ Clicked signup button using XPath");
          } else {
            throw new Error("Could not find signup button");
          }
        }
        await cmcPage.waitForTimeout(3000);

        // Enter email
        console.log(`🔄 Entering email: ${email}`);
        let emailEntered = await safeType(
          cmcPage,
          'input[type="email"]',
          email
        );
        if (!emailEntered) {
          // Try XPath as fallback
          const emailInputs = await cmcPage.$x(
            "/html/body/div[6]/div/div/div/div/div[3]/div[3]/input"
          );
          if (emailInputs.length > 0) {
            await emailInputs[0].type(email);
            emailEntered = true;
            console.log("✅ Entered email using XPath");
          } else {
            throw new Error("Could not find email input");
          }
        }
        await cmcPage.waitForTimeout(2000);

        // Enter password
        let passwordEntered = await safeType(
          cmcPage,
          'input[type="password"]',
          email
        );
        if (!passwordEntered) {
          // Try XPath as fallback
          const passwordInputs = await cmcPage.$x(
            "/html/body/div[6]/div/div/div/div/div[3]/div[4]/div[2]/input"
          );
          if (passwordInputs.length > 0) {
            await passwordInputs[0].type(email);
            passwordEntered = true;
            console.log("✅ Entered password using XPath");
          } else {
            throw new Error("Could not find password input");
          }
        }
        await cmcPage.waitForTimeout(2000);

        // Click submit button
        let submitClicked = await safeClick(cmcPage, 'button[type="submit"]');
        if (!submitClicked) {
          // Try XPath as fallback
          const submitButtons = await cmcPage.$x(
            "/html/body/div[6]/div/div/div/div/div[3]/div[6]/button"
          );
          if (submitButtons.length > 0) {
            await submitButtons[0].click();
            submitClicked = true;
            console.log("✅ Clicked submit button using XPath");
          } else {
            throw new Error("Could not find submit button");
          }
        }

        // Wait for CAPTCHA to appear
        await cmcPage.waitForTimeout(15000);

        // Handle CAPTCHA
        console.log("🔄 Checking for CAPTCHA...");
        const captchaSolved = await handleCaptcha(cmcPage);

        if (!captchaSolved) {
          console.log(
            "⚠️ CAPTCHA not solved automatically, waiting for manual intervention..."
          );
          await cmcPage.waitForTimeout(45000);
        }

        // Check if signup was successful (logout button should be visible)
        try {
          const loginButtonStillExists = await cmcPage.evaluate(() => {
            return document.querySelector('button[data-role="login"]') !== null;
          });

          if (!loginButtonStillExists) {
            console.log(
              "✅ Login button disappeared - signup appears successful"
            );
            signupSuccess = true;
            break;
          } else {
            console.log(
              "⚠️ Login button still visible - signup may have failed"
            );
            await takeScreenshot(
              cmcPage,
              `${email.replace(/[@.]/g, "_")}_signup_attempt${attempt}.png`
            );

            if (attempt < config.MAX_SIGNUP_ATTEMPTS) {
              console.log(
                `⏳ Retrying signup (attempt ${attempt + 1}/${
                  config.MAX_SIGNUP_ATTEMPTS
                })...`
              );
              await cmcPage.waitForTimeout(10000);
            }
          }
        } catch (e) {
          console.error(`❌ Error checking signup status: ${e.message}`);
          if (attempt < config.MAX_SIGNUP_ATTEMPTS) {
            console.log(
              `⏳ Retrying signup (attempt ${attempt + 1}/${
                config.MAX_SIGNUP_ATTEMPTS
              })...`
            );
            await cmcPage.waitForTimeout(10000);
          }
        }
      } catch (error) {
        console.error(
          `❌ Error during signup attempt ${attempt}: ${error.message}`
        );
        if (attempt < config.MAX_SIGNUP_ATTEMPTS) {
          console.log(
            `⏳ Retrying signup (attempt ${attempt + 1}/${
              config.MAX_SIGNUP_ATTEMPTS
            })...`
          );
          await cmcPage.waitForTimeout(10000);
        }
      }
    }

    if (!signupSuccess) {
      console.error("❌ Failed to complete signup after multiple attempts");
      throw new Error("Signup process failed");
    }

    // Take screenshot after signup
    await takeScreenshot(
      cmcPage,
      `${email.replace(/[@.]/g, "_")}_signup_complete.png`
    );

    // Step 9-10: Check for verification email
    console.log("🔄 Checking for verification email...");
    await emailPage.bringToFront();

    const verificationUrl = await checkForVerificationEmail(
      emailPage,
      email,
      provider
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
    const verificationResult = await completeVerificationProcess(
      browser,
      email,
      verificationUrl
    );
    // Save credentials
    console.log("💾 Saving credentials...");
    saveCredentials(email);

    return verificationResult;
  } catch (error) {
    console.error(`❌ Error in account creation process: ${error.message}`);
    return {
      success: false,
      email: email || null,
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

module.exports = { createAccount };
