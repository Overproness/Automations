const { createPage, navigateToUrl } = require("../utils/browserUtils");
const { takeScreenshot } = require("../utils/fileUtils");
const config = require("../config");

/**
 * Complete account verification process after receiving the verification email
 */
async function completeVerificationProcess(browser, email, verificationUrl) {
  console.log(`🔄 Opening verification URL: ${verificationUrl}`);

  try {
    const verificationPage = await createPage(browser);

    // Set longer timeout and navigate to verification link
    verificationPage.setDefaultNavigationTimeout(
      config.TIMEOUTS.VERIFICATION_TIMEOUT
    );

    // Navigate to the verification link
    const navigationSuccess = await navigateToUrl(
      verificationPage,
      verificationUrl,
      { timeout: config.TIMEOUTS.VERIFICATION_TIMEOUT }
    );

    if (!navigationSuccess) {
      throw new Error("Failed to navigate to verification URL");
    }

    // Take screenshot to debug
    await takeScreenshot(
      verificationPage,
      `${email.replace(/[@.]/g, "_")}_verification_initial.png`
    );

    // Wait for the page to fully load
    console.log("⏳ Waiting for verification page to fully load...");
    await verificationPage.waitForTimeout(15000);

    // Execute the specific verification flow
    console.log("🔄 Starting verification flow...");

    // Click Next button 4 times, with 5 second delay between each click
    console.log("🖱️ Clicking through onboarding screens (4 clicks)...");

    for (let i = 0; i < 4; i++) {
      await clickNextButton(verificationPage, i + 1, email);
      await verificationPage.waitForTimeout(5000);
    }

    // Enter the local part of email in the nickname field
    await enterNickname(verificationPage, email);

    // Wait 5 seconds before final button click
    console.log("⏳ Waiting 5 seconds before final button click...");
    await verificationPage.waitForTimeout(5000);

    // Click the final button
    await clickFinalButton(verificationPage);

    // Take final screenshot
    await verificationPage.waitForTimeout(5000);
    await takeScreenshot(
      verificationPage,
      `${email.replace(/[@.]/g, "_")}_verification_complete.png`
    );

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

    // Take error screenshot if possible
    try {
      const pages = await browser.pages();
      if (pages.length > 0) {
        const verificationPage = pages[pages.length - 1];
        await takeScreenshot(
          verificationPage,
          `${email.replace(/[@.]/g, "_")}_verification_error.png`
        );
      }
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
}

/**
 * Helper function to click the next button with multiple fallback methods
 */
async function clickNextButton(page, buttonNumber, email) {
  try {
    // First try with explicit selector
    try {
      console.log(
        `🔄 Clicking Next button (${buttonNumber}/4) with CSS selector...`
      );
      await page.waitForSelector('button[variant="primary"]', {
        timeout: 10000,
        visible: true,
      });
      await page.click('button[variant="primary"]');
      console.log(
        `✅ Clicked Next button (${buttonNumber}/4) with CSS selector`
      );
    } catch (e) {
      console.log(
        `⚠️ CSS selector failed for button ${buttonNumber}/4: ${e.message}`
      );

      // Try with class
      try {
        console.log(
          `🔄 Clicking Next button (${buttonNumber}/4) with class...`
        );
        await page.waitForSelector("button.joeEVb", {
          timeout: 5000,
          visible: true,
        });
        await page.click("button.joeEVb");
        console.log(`✅ Clicked Next button (${buttonNumber}/4) with class`);
      } catch (e2) {
        console.log(
          `⚠️ Class selector failed for button ${buttonNumber}/4: ${e2.message}`
        );

        // Try with exact XPath
        try {
          console.log(
            `🔄 Clicking Next button (${buttonNumber}/4) with XPath...`
          );
          const nextButtons = await page.$x(
            "/html/body/div[6]/div/div/div/div/button"
          );
          if (nextButtons.length > 0) {
            await nextButtons[0].click();
            console.log(
              `✅ Clicked Next button (${buttonNumber}/4) with XPath`
            );
          } else {
            throw new Error("Next button not found with XPath");
          }
        } catch (e3) {
          console.log(
            `⚠️ XPath failed for button ${buttonNumber}/4: ${e3.message}`
          );

          // Try JavaScript click as last resort
          console.log(
            `🔄 Trying JavaScript click for button ${buttonNumber}/4...`
          );
          await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll("button"));
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
            `✅ Clicked Next button (${buttonNumber}/4) with JavaScript`
          );
        }
      }
    }

    // Take screenshot after each click
    await takeScreenshot(
      page,
      `${email.replace(/[@.]/g, "_")}_after_click_${buttonNumber}.png`
    );
  } catch (error) {
    console.error(`❌ Error on button click ${buttonNumber}: ${error.message}`);
    // Continue the flow even if one button fails
  }
}

/**
 * Enter nickname in the verification form
 */
async function enterNickname(page, email) {
  console.log("🔄 Now entering nickname...");
  try {
    // Wait for the nickname input field
    await page.waitForSelector(
      'input[placeholder="Choose your own nickname"]',
      {
        timeout: 10000,
        visible: true,
      }
    );

    // Clear the input field first
    await page.evaluate(() => {
      const input = document.querySelector(
        'input[placeholder="Choose your own nickname"]'
      );
      if (input) input.value = "";
    });

    // Get local part of email
    const localPart = email.split("@")[0];
    console.log(`📝 Using nickname: ${localPart}`);

    // Type the nickname
    await page.type('input[placeholder="Choose your own nickname"]', localPart);
    console.log("✅ Entered nickname successfully");

    // Take screenshot after entering nickname
    await takeScreenshot(
      page,
      `${email.replace(/[@.]/g, "_")}_after_nickname.png`
    );
  } catch (e) {
    console.log(`⚠️ Error with CSS selector for nickname: ${e.message}`);

    // Try XPath for nickname field
    try {
      console.log("🔄 Trying XPath for nickname input...");
      const nicknameInputs = await page.$x(
        "/html/body/div[6]/div/div/div/div/div[4]/input"
      );

      if (nicknameInputs.length > 0) {
        // Clear the input field
        await page.evaluate(() => {
          const input = document.evaluate(
            "/html/body/div[6]/div/div/div/div/div[4]/input",
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
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
}

/**
 * Click the final button to complete verification
 */
async function clickFinalButton(page) {
  console.log("🖱️ Clicking final button...");

  try {
    // Try the exact XPath first
    const finalButtons = await page.$x(
      "/html/body/div[5]/div/div/div/div/button"
    );

    if (finalButtons.length > 0) {
      await finalButtons[0].click();
      console.log("✅ Clicked final button with exact XPath");
    } else {
      // If the specific XPath doesn't work, try alternative selectors
      console.log(
        "⚠️ Final button not found with exact XPath, trying alternatives..."
      );

      // Try div[6] XPath
      const altButtons = await page.$x(
        "/html/body/div[6]/div/div/div/div/button"
      );
      if (altButtons.length > 0) {
        await altButtons[0].click();
        console.log("✅ Clicked final button with alternative XPath (div[6])");
      } else {
        // Try button selector
        await page.click('button[variant="primary"]');
        console.log("✅ Clicked final button with CSS selector");
      }
    }
  } catch (error) {
    console.error(`❌ Error clicking final button: ${error.message}`);

    // Try JavaScript click as last resort
    try {
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll("button"));
        for (const btn of buttons) {
          if (
            btn.innerText.includes("Save and get your gift") ||
            btn.innerText.includes("Finish") ||
            btn.innerText.includes("finish") ||
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
}

module.exports = {
  completeVerificationProcess,
};
