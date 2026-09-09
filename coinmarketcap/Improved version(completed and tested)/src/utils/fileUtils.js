const fs = require("fs");
const path = require("path");

/**
 * Create directory if it doesn't exist
 */
function ensureDirectoryExists(directory) {
  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory, { recursive: true });
  }
}

/**
 * Save credentials to file
 */
function saveCredentials(email) {
  const credentialsPath = path.join(__dirname, "../..", "credentials.txt");
  fs.appendFileSync(credentialsPath, `${email}:${email}\n`);
  console.log(`✅ Saved credentials to ${credentialsPath}`);
}

/**
 * Initialize log file
 */
function initLogFile() {
  const resultsDir = path.join(__dirname, "../..", "results");
  ensureDirectoryExists(resultsDir);

  const logFile = path.join(
    resultsDir,
    `account_creation_log_${new Date().toISOString().replace(/:/g, "-")}.txt`
  );

  fs.writeFileSync(
    logFile,
    `Account Creation Log - Started at ${new Date().toISOString()}\n\n`
  );

  return logFile;
}

/**
 * Create credentials file if it doesn't exist
 */
function initCredentialsFile() {
  const credentialsPath = path.join(__dirname, "../..", "credentials.txt");
  if (!fs.existsSync(credentialsPath)) {
    fs.writeFileSync(credentialsPath, "# CoinMarketCap Credentials\n");
  }
}

/**
 * Append to log file
 */
function appendToLog(logFile, message) {
  fs.appendFileSync(logFile, `[${new Date().toISOString()}] ${message}\n`);
}

/**
 * Take screenshot and save to file
 */
async function takeScreenshot(page, filename) {
  try {
    const screenshotsDir = path.join(__dirname, "../..", "screenshots");
    ensureDirectoryExists(screenshotsDir);
    await page.screenshot({
      path: path.join(screenshotsDir, filename),
    });
    return true;
  } catch (err) {
    console.error(`❌ Could not take screenshot: ${err.message}`);
    return false;
  }
}

module.exports = {
  ensureDirectoryExists,
  saveCredentials,
  initLogFile,
  initCredentialsFile,
  appendToLog,
  takeScreenshot,
};
