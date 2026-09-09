/**
 * Main entry point for CoinMarketCap account creator
 *
 * This script orchestrates the creation of CoinMarketCap accounts
 * using temporary email addresses and automated browser interaction.
 */

const { loadProxies, getNextProxy } = require("./src/utils/proxyUtils");
const {
  initLogFile,
  initCredentialsFile,
  appendToLog,
} = require("./src/utils/fileUtils");
const { sleep } = require("./src/utils/browserUtils");
const { createAccount } = require("./src/account/accountCreation");
const config = require("./src/config");

/**
 * Main function that runs the account creation process
 */
async function main() {
  // Initialize files and directories
  const logFile = initLogFile();
  initCredentialsFile();

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

  // Number of accounts to create
  const numberOfAccounts = config.NUMBER_OF_ACCOUNTS;

  // Track failing proxies
  proxies.forEach((p) => {
    proxyFailures[`${p.ip}:${p.port}`] = 0;
  });

  for (let i = 0; i < numberOfAccounts; i++) {
    console.log(`\n🔄 Creating account ${i + 1}/${numberOfAccounts}`);

    let accountCreated = false;
    let proxyAttempts = 0;
    const maxProxyAttempts = Math.min(
      config.MAX_PROXY_ATTEMPTS,
      proxies.length
    );

    while (!accountCreated && proxyAttempts < maxProxyAttempts) {
      // Get next proxy
      const { proxy, newIndex } = getNextProxy(proxies, currentProxyIndex);
      currentProxyIndex = newIndex;

      // Skip proxies that have failed too many times
      const proxyKey = `${proxy.ip}:${proxy.port}`;
      if (proxyFailures[proxyKey] >= 2) {
        console.log(
          `⚠️ Skipping proxy ${proxyKey} - failed ${proxyFailures[proxyKey]} times previously`
        );
        continue;
      }

      // Log the proxy usage
      const logEntry = `Using proxy: ${proxy.ip}:${proxy.port} - Usage count: ${proxy.usageCount}`;
      appendToLog(logFile, logEntry);
      console.log(logEntry);

      // Create account
      const result = await createAccount(proxy);

      if (result.success) {
        successCount++;
        accountCreated = true;
        appendToLog(logFile, `SUCCESS: Account created for ${result.email}`);
      } else {
        // Track proxy failure
        proxyFailures[proxyKey] = (proxyFailures[proxyKey] || 0) + 1;

        appendToLog(
          logFile,
          `FAILURE with proxy ${proxyKey}: ${result.error || "Unknown error"}`
        );

        proxyAttempts++;
        console.log(
          `⚠️ Account creation failed with proxy ${proxyKey}. Attempts: ${proxyAttempts}/${maxProxyAttempts}`
        );

        if (proxyAttempts < maxProxyAttempts) {
          console.log(`🔄 Trying with a different proxy...`);
        } else {
          failureCount++;
          console.error(
            `❌ Failed to create account after trying ${maxProxyAttempts} different proxies`
          );
        }
      }
    }

    // Add a delay between account creation attempts
    if (i < numberOfAccounts - 1) {
      const delayTime = 15000 + Math.random() * 10000; // 15-25 seconds
      console.log(
        `⏳ Waiting ${Math.round(
          delayTime / 1000
        )} seconds before next account...`
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
  appendToLog(logFile, summary);
  console.log(`📝 Full log saved to: ${logFile}`);
}

// Run the main function
main().catch((error) => {
  console.error(`❌ Unhandled error in main function: ${error}`);
  process.exit(1);
});
