const { createPage, navigateToUrl } = require("../utils/browserUtils");
const { takeScreenshot } = require("../utils/fileUtils");
const config = require("../config");

/**
 * Get a temporary email address from various providers
 */
async function getTempEmail(browser, proxy) {
  console.log("🔄 Attempting to get a temporary email address...");
  const providers = config.EMAIL_PROVIDERS;

  // Get page from existing browser or create a new one
  let page;
  try {
    const pages = await browser.pages();
    page = pages[0];
  } catch (e) {
    console.log("Creating a new page for temp email...");
    page = await createPage(browser);
  }

  // Try each provider until successful
  for (const provider of providers) {
    try {
      console.log(`🔄 Trying ${provider.name}...`);
      const navigationSuccess = await navigateToUrl(page, provider.url, {
        timeout: provider.timeout,
      });

      if (!navigationSuccess) {
        console.error(`❌ Failed to navigate to ${provider.name}`);
        continue;
      }

      // Wait for page to fully load
      console.log(`⏳ Waiting for ${provider.name} to load...`);
      await page.waitForTimeout(10000);

      // Check if the page loaded correctly
      const pageTitle = await page.title();
      console.log(`📄 Page title: ${pageTitle}`);

      if (
        pageTitle.includes("Access denied") ||
        pageTitle.includes("Blocked")
      ) {
        console.error(
          `❌ Access to ${provider.name} is blocked from this proxy`
        );
        continue; // Try next provider
      }

      // Wait for email field to be available
      await page.waitForSelector(provider.emailSelector, {
        timeout: 15000,
        visible: true,
      });

      // Additional wait for temp-mail.org which can take time to generate
      if (provider.name === "temp-mail.org") {
        console.log("⏳ Waiting 20 seconds for email generation...");
        await page.waitForTimeout(20000);
      } else {
        await page.waitForTimeout(5000);
      }

      // Get the email
      const email = await page.evaluate((selector) => {
        const element = document.querySelector(selector);
        return element ? element.value : null;
      }, provider.emailSelector);

      if (!email || !email.includes("@")) {
        console.error(`❌ Could not find valid email on ${provider.name}`);
        await takeScreenshot(
          page,
          `${provider.name.replace(/\./g, "_")}_error.png`
        );
        continue; // Try next provider
      }

      console.log(`📧 Found email: ${email}`);

      // Try to click copy button (not required but convenient)
      try {
        // First try CSS selector
        await page.waitForSelector(provider.copyBtnSelector, {
          timeout: 5000,
          visible: true,
        });
        await page.click(provider.copyBtnSelector);
        console.log("✅ Clicked copy button using CSS selector");
      } catch (e) {
        try {
          // Then try XPath
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
      await takeScreenshot(
        page,
        `${provider.name.replace(/\./g, "_")}_error.png`
      );
    }
  }

  // If all providers failed, return null
  return null;
}

/**
 * Check for verification email and extract link
 */
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
          `✅ Already on CoinMarketCap verification link: ${checkUrl}`
        );
        return checkUrl;
      }

      // Refresh the page for each retry except the first
      if (retryCount > 0) {
        console.log(
          `🔄 Refreshing inbox (attempt ${retryCount + 1}/${maxRetries})...`
        );
        await page.reload({
          waitUntil: "networkidle2",
          timeout: 30000,
        });
      }

      await page.waitForTimeout(10000);

      // Determine which XPath to use based on the current URL
      const currentPageUrl = await page.url();
      let xpathToUse;

      if (currentPageUrl.includes("temp-mail.io")) {
        console.log("🔍 Using temp-mail.io specific XPath...");
        xpathToUse =
          "/html/body/div[1]/div/main/div/div/div[6]/aside/div/div[3]/div/ul/li";
      } else {
        // Default XPath for other providers
        xpathToUse =
          "/html/body/main/div[1]/div/div[2]/div[2]/div/div[1]/div/div[4]/ul/li[2]/div[2]/span/a";
      }

      // Try to find the email using the appropriate XPath
      console.log(
        `🔍 Looking for verification email using XPath for ${
          currentPageUrl.includes("temp-mail.io")
            ? "temp-mail.io"
            : "other provider"
        }...`
      );
      try {
        // Check if any element matches the XPath
        const emailElements = await page.$x(xpathToUse);

        if (emailElements.length > 0) {
          console.log(
            `✅ Found ${emailElements.length} emails with XPath. Clicking first one...`
          );
          await emailElements[0].click();
          console.log("⏳ Waiting for email content to load...");
          await page.waitForTimeout(5000);

          // Now look for verification link in the opened email
          const cmcLinks = await page.evaluate(() => {
            const links = Array.from(
              document.querySelectorAll('a[href*="coinmarketcap"]')
            );
            return links.map((link) => link.href);
          });

          if (cmcLinks.length > 0) {
            console.log(
              `✅ Found ${cmcLinks.length} CoinMarketCap links in email content`
            );
            // Filter links to prioritize verification links
            const verificationLinks = cmcLinks.filter(
              (link) =>
                link.includes("link.coinmarketcap.com") ||
                link.includes("verify") ||
                link.includes("account-verification")
            );

            const linkToUse =
              verificationLinks.length > 0 ? verificationLinks[0] : cmcLinks[0];
            console.log(`📋 Using verification link: ${linkToUse}`);
            return linkToUse;
          } else {
            console.log("❌ No CoinMarketCap links found in the opened email");
          }
        } else {
          console.log("❌ No email found with the provided XPath");
        }
      } catch (e) {
        console.log(`❌ Error using XPath to find email: ${e.message}`);
      }

      // Try finding emails by checking for text containing 'coinmarketcap' in the email list
      try {
        console.log("🔍 Looking for emails by content...");
        const emailsWithCMCText = await page.evaluate(() => {
          // For temp-mail.io, target the email list items
          const emailItems = document.querySelectorAll("li.overflow-hidden");
          const matchingItems = Array.from(emailItems).filter(
            (item) =>
              item.textContent &&
              (item.textContent.toLowerCase().includes("coinmarketcap") ||
                item.textContent.toLowerCase().includes("coin market cap"))
          );

          return matchingItems.length;
        });

        if (emailsWithCMCText > 0) {
          console.log(
            `✅ Found ${emailsWithCMCText} emails with CoinMarketCap text`
          );

          // Click on the first matching email
          await page.evaluate(() => {
            const emailItems = document.querySelectorAll("li.overflow-hidden");
            const matchingItem = Array.from(emailItems).find(
              (item) =>
                item.textContent &&
                (item.textContent.toLowerCase().includes("coinmarketcap") ||
                  item.textContent.toLowerCase().includes("coin market cap"))
            );

            if (matchingItem) {
              matchingItem.click();
              return true;
            }
            return false;
          });

          console.log("⏳ Waiting for email content to load...");
          await page.waitForTimeout(5000);
        }
      } catch (e) {
        console.log(`❌ Error finding emails by content: ${e.message}`);
      }

      // Look for any coinmarketcap links on the page
      try {
        const cmcLinks = await page.evaluate(() => {
          const links = Array.from(
            document.querySelectorAll('a[href*="coinmarketcap"]')
          );
          return links.map((link) => link.href);
        });

        if (cmcLinks.length > 0) {
          console.log(
            `✅ Found ${cmcLinks.length} CoinMarketCap links on page`
          );
          // Filter links to prioritize verification links
          const verificationLinks = cmcLinks.filter(
            (link) =>
              link.includes("link.coinmarketcap.com") ||
              link.includes("verify") ||
              link.includes("account-verification")
          );

          // Use verification link if found, otherwise use first link
          const linkToUse =
            verificationLinks.length > 0 ? verificationLinks[0] : cmcLinks[0];
          console.log(`📋 Using link: ${linkToUse}`);
          return linkToUse;
        }
      } catch (e) {
        console.log(`❌ Error finding CoinMarketCap links: ${e.message}`);
      }

      // Try looking for emails from CoinMarketCap in the inbox list
      try {
        console.log("🔍 Looking for emails from CoinMarketCap in inbox...");
        // Check for elements containing "CoinMarketCap" text
        const emailsFromCMC = await page.evaluate(() => {
          const elements = Array.from(document.querySelectorAll("*"));
          return elements
            .filter(
              (el) =>
                el.textContent &&
                (el.textContent.includes("CoinMarketCap") ||
                  el.textContent.includes("coinmarketcap"))
            )
            .map((el) => ({
              text: el.textContent.trim(),
              isLink: el.tagName === "A",
            }));
        });

        if (emailsFromCMC.length > 0) {
          console.log(
            `✅ Found ${emailsFromCMC.length} elements with CoinMarketCap text`
          );

          for (const item of emailsFromCMC) {
            console.log(`📧 Found: ${item.text.substring(0, 50)}...`);
          }

          // Try clicking on the first item that looks like an email
          await page.evaluate(() => {
            const elements = Array.from(document.querySelectorAll("*"));
            const cmcElements = elements.filter(
              (el) =>
                el.textContent &&
                (el.textContent.includes("CoinMarketCap") ||
                  el.textContent.includes("coinmarketcap"))
            );

            if (cmcElements.length > 0) {
              // Try to find a clickable parent
              let elementToClick = cmcElements[0];

              // Check if the element is clickable
              while (elementToClick && elementToClick !== document.body) {
                if (
                  elementToClick.tagName === "A" ||
                  elementToClick.onclick ||
                  elementToClick.role === "button"
                ) {
                  elementToClick.click();
                  return true;
                }
                elementToClick = elementToClick.parentElement;
              }

              // If no clickable parent found, try direct click
              cmcElements[0].click();
              return true;
            }
            return false;
          });

          console.log(
            "⏳ Clicked on potential CoinMarketCap email, waiting for content..."
          );
          await page.waitForTimeout(5000);
        }
      } catch (e) {
        console.log(`❌ Error finding CoinMarketCap emails: ${e.message}`);
      }

      retryCount++;
      console.log(
        `⏳ Waiting 10 seconds before retry ${retryCount}/${maxRetries}...`
      );
      await page.waitForTimeout(10000);
    } catch (error) {
      console.error(`❌ Error in verification email check: ${error.message}`);
      retryCount++;
      await page.waitForTimeout(5000);
    }
  }

  console.error(
    `❌ Failed to find verification link after ${maxRetries} attempts`
  );
  await takeScreenshot(page, "verification_failed.png");
  return null;
}

module.exports = {
  getTempEmail,
  checkForVerificationEmail,
};
