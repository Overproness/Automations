const { Builder, By, until } = require("selenium-webdriver");
const chrome = require("selenium-webdriver/chrome");
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// User credentials
const USERNAME = "chippu_photography";
const PASSWORD = "qwerty12345";

(async function instagramAutomation() {
  // Set up Chrome options (add user agent to bypass bot detection)
  let options = new chrome.Options();
  options.addArguments(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
  );

  // Initialize driver
  let driver = await new Builder()
    .forBrowser("chrome")
    .setChromeOptions(options)
    .build();

  try {
    // Navigate to Instagram login page
    await driver.get("https://www.instagram.com/accounts/login/");
    await sleep(2000); // Wait for page to load

    // Wait for username input field to be visible
    await driver.wait(until.elementLocated(By.name("username")), 10000);

    // Enter username and password
    await driver.findElement(By.name("username")).sendKeys(USERNAME);
    await driver.findElement(By.name("password")).sendKeys(PASSWORD);

    // Click the login button and wait for page load
    let loginButton = await driver.findElement(
      By.xpath('//button[@type="submit"]')
    );
    await driver.wait(until.elementIsVisible(loginButton), 5000); // Ensure button is clickable
    await loginButton.click();

    // Wait for the URL to change or login to complete
    await sleep(5000); // Increase wait time for login processing

    // Check if login was successful or if the login page is still displayed
    await driver.get("https://www.instagram.com/accounts/close_friends/");
    let currentUrl = await driver.getCurrentUrl();
    if (currentUrl.includes("instagram.com/accounts/login/")) {
      // Handle potential login errors
      try {
        // Check for any error message on the page (like invalid credentials or CAPTCHA)
        let errorMessage = await driver
          .findElement(By.xpath('//p[@id="slfErrorAlert"]'))
          .getText();
        console.log("Login Error: ", errorMessage);
        throw new Error("Login failed due to error: " + errorMessage);
      } catch (error) {
        console.log("No explicit error message found, login failed.");
        throw new Error("Login failed, page reloaded to login.");
      }
    } else {
      console.log("Login successful!");

      // Handle potential popups: "Save Login Info?" and cookies consent
      try {
        let notNowButton = await driver.findElement(
          By.xpath('//button[contains(text(), "Not Now")]')
        );
        await notNowButton.click();
        console.log("Dismissed 'Save Login Info' popup.");
      } catch (error) {
        console.log("No 'Save Login Info' popup.");
      }

      try {
        let cookieButton = await driver.findElement(
          By.xpath('//button[contains(text(), "Accept All")]')
        );
        await cookieButton.click();
        console.log("Accepted cookies.");
      } catch (error) {
        console.log("No cookie pop-up.");
      }

      // Navigate to Close Friends page
      await driver.get("https://www.instagram.com/accounts/close_friends/");
      await sleep(5000); // Wait for the Close Friends page to load

      let profilesAdded = 0;
      let profileIndex = 1; // Start from the first profile in the list

      while (profilesAdded < 25) {
        try {
          // Dynamic XPath for each profile's outer element
          let profileXPath = `/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/section/main/div/div[3]/div/div[2]/div/div/div[1]/div/div/div/div[2]/div[2]/div/div[1]/div[${profileIndex}]`;
          let buttonXPath = `${profileXPath}/div/div[2]/div/div/div`;

          // Find the profile element
          let profileElement = await driver.findElement(By.xpath(profileXPath));

          // Check if the button exists for adding to close friends
          let buttonElement;
          try {
            buttonElement = await driver.findElement(By.xpath(buttonXPath));
          } catch (error) {
            console.log(
              `No button found for profile at index ${profileIndex}: ${error}`
            );
            profileIndex += 1;
            continue;
          }

          // Get the aria-label attribute to check if already a Close Friend
          let buttonLabel = await buttonElement.getAttribute("aria-label");

          if (buttonLabel.includes("Add to Close Friends")) {
            // Click to add to Close Friends
            await buttonElement.click();
            profilesAdded += 1;
            console.log(`Added profile ${profilesAdded} to Close Friends.`);
            await sleep(1000); // Wait to avoid being rate-limited
          }

          // Move to the next profile
          profileIndex += 1;

          // Scroll down every 5 profiles to load more profiles
          if (profileIndex % 5 === 0) {
            await driver.executeScript(
              "window.scrollTo(0, document.body.scrollHeight);"
            );
            await sleep(3000); // Wait for new profiles to load
          }
        } catch (error) {
          console.log(
            `Error processing profile at index ${profileIndex}: ${error}`
          );
          profileIndex += 1; // Move to the next profile in case of an error
        }
      }

      console.log("Finished adding profiles to Close Friends.");
    }
  } catch (error) {
    console.error("Error: ", error);
  } finally {
    await sleep(10000); // Allow time to observe the results before closing
    await driver.quit(); // Close the browser
  }
})();
