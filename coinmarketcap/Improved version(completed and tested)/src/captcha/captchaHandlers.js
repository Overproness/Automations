const { solveCaptchaWithApi } = require("./captchaService");
const config = require("../config");

/**
 * Helper function to refresh CAPTCHA
 */
async function refreshCaptcha(page) {
  // Try to click the refresh button using different methods
  let refreshed = false;

  // Method 1: Using class selector
  try {
    await page.waitForSelector("svg.bcap-icon-refresh", {
      timeout: 5000,
      visible: true,
    });
    await page.click("svg.bcap-icon-refresh");
    refreshed = true;
    console.log("✅ Clicked CAPTCHA refresh button using class selector");
  } catch (e) {
    console.log(
      "⚠️ Could not click refresh button with class selector, trying other methods..."
    );
  }

  // Method 2: Using compound class selector
  if (!refreshed) {
    try {
      await page.waitForSelector(".bcap-icon.bcap-icon-refresh", {
        timeout: 5000,
        visible: true,
      });
      await page.click(".bcap-icon.bcap-icon-refresh");
      refreshed = true;
      console.log(
        "✅ Clicked CAPTCHA refresh button using compound class selector"
      );
    } catch (e) {
      console.log(
        "⚠️ Could not click refresh button with compound selector, trying XPath..."
      );
    }
  }

  // Method 3: Using XPath
  if (!refreshed) {
    try {
      const refreshButtons = await page.$x(
        "/html/body/div[7]/div/div[2]/div/div[1]/svg[2]"
      );
      if (refreshButtons.length > 0) {
        await refreshButtons[0].click();
        refreshed = true;
        console.log("✅ Clicked CAPTCHA refresh button using XPath");
      }
    } catch (e) {
      console.log(
        "⚠️ Could not click refresh button with XPath, trying JavaScript..."
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
          document.querySelectorAll("*")
        ).filter(
          (el) =>
            el.getAttribute("aria-label") === "New Challenge" ||
            el.classList.contains("refresh") ||
            (el.textContent && el.textContent.includes("Refresh"))
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

/**
 * Handle CAPTCHA challenges
 */
async function handleCaptcha(page) {
  try {
    const maxCaptchaAttempts = config.MAX_CAPTCHA_ATTEMPTS; // Maximum number of CAPTCHA refresh attempts
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
        }/${maxCaptchaAttempts}`
      );
      await page.waitForTimeout(2000);

      // Get the type of CAPTCHA
      const typeOfBox = await page.evaluate(() => {
        const element = document.querySelector("div.bcap-text-message-title");
        return element ? element.innerText : "";
      });

      if (!typeOfBox.includes("Please select all images with")) {
        console.log("[+] Captcha without any Grid, manual intervention needed");
        // Wait for manual solving
        await page.waitForTimeout(30000);
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
          `⚠️ Same CAPTCHA challenge (${selectWhat}) detected ${consecutiveSameChallenge} times in a row`
        );

        // If we get the same challenge more than once, refresh immediately
        if (consecutiveSameChallenge > 0) {
          console.log(
            "🔄 Same challenge detected multiple times, refreshing immediately..."
          );
          await refreshCaptcha(page);
          await page.waitForTimeout(5000);

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
      if (
        config.PROBLEMATIC_CAPTCHAS.includes(selectWhat.toLowerCase()) &&
        captchaAttempt > 0
      ) {
        console.log(
          `⚠️ Problematic challenge type (${selectWhat}) detected, manual intervention may be needed`
        );
        console.log("🔄 Refreshing to get a different challenge...");

        if (await refreshCaptcha(page)) {
          await page.waitForTimeout(5000);
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
        selectWhat
      ).then((success) => ({ timedOut: false, success }));

      // Race the promises
      const result = await Promise.race([
        captchaTimeoutPromise,
        solvingPromise,
      ]);

      if (result.timedOut) {
        console.log("⏱️ CAPTCHA solving timed out, refreshing...");
        if (await refreshCaptcha(page)) {
          await page.waitForTimeout(5000);
          continue;
        }
      } else if (result.success) {
        console.log("✅ CAPTCHA solved successfully");
        return true;
      } else {
        console.log(
          `❌ CAPTCHA solution failed on attempt ${
            captchaAttempt + 1
          }/${maxCaptchaAttempts}`
        );

        // If we have more attempts, try refreshing the CAPTCHA
        if (captchaAttempt < maxCaptchaAttempts - 1) {
          console.log("🔄 Refreshing CAPTCHA and trying again...");
          if (await refreshCaptcha(page)) {
            await page.waitForTimeout(5000);
          } else {
            console.error("❌ Could not refresh CAPTCHA, skipping retry");
            break;
          }
        }
      }
    }

    // If we get here, we've failed all attempts
    console.log(
      "❌ Failed to solve CAPTCHA after multiple attempts with refresh"
    );

    // Give user a chance to solve manually
    console.log("⚠️ Waiting for possible manual CAPTCHA solving...");
    await page.waitForTimeout(45000);

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

module.exports = {
  handleCaptcha,
  refreshCaptcha,
};
