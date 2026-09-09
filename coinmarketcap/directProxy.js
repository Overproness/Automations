/**
 * This is a tool to test proxies directly
 */
const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
const fs = require("fs");
const path = require("path");

// Use stealth plugin to avoid detection
puppeteer.use(StealthPlugin());

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
        return { ip, port };
      });
    console.log(`✅ Loaded ${proxies.length} proxies.`);
    return proxies;
  } catch (err) {
    console.error(`❌ Error loading proxies: ${err.message}`);
    return [];
  }
}

// Create directory for screenshots if it doesn't exist
function ensureDirectoryExists(directory) {
  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory, { recursive: true });
  }
}

// Test a single proxy
async function testProxy(proxy) {
  console.log(`🌐 Testing proxy: ${proxy.ip}:${proxy.port}`);
  let browser;

  try {
    // Launch browser with proxy
    browser = await puppeteer.launch({
      headless: false,
      args: [
        `--proxy-server=${proxy.ip}:${proxy.port}`,
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
      ],
      defaultViewport: null,
    });

    // Get the first page
    const page = (await browser.pages())[0];

    // Set user agent
    await page.setUserAgent(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
    );

    // Set a longer default navigation timeout
    page.setDefaultNavigationTimeout(60000);

    // Test sites
    const sites = [
      { name: "ipinfo.io", url: "https://ipinfo.io/json", jsonIp: true },
      { name: "google.com", url: "https://www.google.com" },
      { name: "temp-mail.org", url: "https://temp-mail.org/en/" },
      { name: "mail.tm", url: "https://mail.tm/en/" },
      { name: "coinmarketcap.com", url: "https://coinmarketcap.com/" },
    ];

    const results = {};
    const screenshotsDir = path.join(__dirname, "screenshots");
    ensureDirectoryExists(screenshotsDir);

    for (const site of sites) {
      console.log(`🔄 Testing ${site.name}...`);
      try {
        await page.goto(site.url, {
          waitUntil: "networkidle2",
          timeout: 30000,
        });

        // Get page title
        const title = await page.title();
        console.log(`✅ ${site.name} - Page title: ${title}`);

        // If it's the IP info site, extract our IP address
        if (site.jsonIp) {
          const ipData = await page.evaluate(() => {
            try {
              const pre = document.querySelector("pre");
              return pre ? JSON.parse(pre.textContent) : null;
            } catch (e) {
              return null;
            }
          });

          if (ipData && ipData.ip) {
            console.log(
              `✅ Current IP: ${ipData.ip} (${
                ipData.country || "Unknown country"
              })`
            );
            results[site.name] = {
              success: true,
              title,
              ip: ipData.ip,
              country: ipData.country,
            };
          } else {
            results[site.name] = { success: true, title, ip: "Unknown" };
          }
        } else {
          results[site.name] = { success: true, title };
        }

        // Take screenshot
        await page.screenshot({
          path: path.join(
            screenshotsDir,
            `${proxy.ip}_${proxy.port}_${site.name.replace(/\./g, "_")}.png`
          ),
          fullPage: false,
        });
      } catch (error) {
        console.error(`❌ Error testing ${site.name}: ${error.message}`);
        results[site.name] = { success: false, error: error.message };

        // Try to take a screenshot anyway
        try {
          await page.screenshot({
            path: path.join(
              screenshotsDir,
              `${proxy.ip}_${proxy.port}_${site.name.replace(
                /\./g,
                "_"
              )}_error.png`
            ),
            fullPage: false,
          });
        } catch (e) {
          console.log(`Could not take error screenshot for ${site.name}`);
        }
      }

      await sleep(3000); // Wait between site tests
    }

    console.log(`✅ Proxy test completed for ${proxy.ip}:${proxy.port}`);
    return {
      proxy,
      results,
      success: Object.values(results).some((r) => r.success),
    };
  } catch (error) {
    console.error(
      `❌ Error testing proxy ${proxy.ip}:${proxy.port}: ${error.message}`
    );
    return {
      proxy,
      error: error.message,
      success: false,
    };
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Main function
async function main() {
  // Load proxies
  const proxies = await loadProxies();
  if (proxies.length === 0) {
    console.error("❌ No proxies available. Exiting...");
    return;
  }

  // Test each proxy
  let successCount = 0;
  const results = [];

  for (let i = 0; i < proxies.length; i++) {
    const proxy = proxies[i];
    console.log(
      `\n🔄 Testing proxy ${i + 1}/${proxies.length}: ${proxy.ip}:${proxy.port}`
    );

    const result = await testProxy(proxy);
    results.push(result);

    if (result.success) {
      successCount++;
    }

    // Wait between tests
    if (i < proxies.length - 1) {
      const delay = 5000 + Math.random() * 3000;
      console.log(
        `⏳ Waiting ${Math.round(delay / 1000)}s before testing next proxy...`
      );
      await sleep(delay);
    }
  }

  // Create summary file
  const summaryPath = path.join(__dirname, "proxy_test_results.json");
  fs.writeFileSync(summaryPath, JSON.stringify(results, null, 2));

  // Log summary
  console.log(`\n=== PROXY TEST SUMMARY ===`);
  console.log(`Total proxies tested: ${proxies.length}`);
  console.log(`Working proxies: ${successCount}`);
  console.log(
    `Success rate: ${Math.round((successCount / proxies.length) * 100)}%`
  );

  // Show working proxies
  if (successCount > 0) {
    console.log(`\nWorking proxies:`);
    results.forEach((result) => {
      if (result.success) {
        console.log(`- ${result.proxy.ip}:${result.proxy.port}`);
        // Show which sites work with this proxy
        const workingSites = Object.entries(result.results)
          .filter(([_, r]) => r.success)
          .map(([site, _]) => site);
        console.log(`  Working sites: ${workingSites.join(", ")}`);

        // Show detected IP if available
        const ipInfo = result.results["ipinfo.io"];
        if (ipInfo && ipInfo.ip) {
          console.log(
            `  Detected IP: ${ipInfo.ip} (${ipInfo.country || "Unknown"})`
          );
        }
      }
    });
  }

  console.log(`\nDetailed results saved to: ${summaryPath}`);
  console.log(`Screenshots saved to: ${path.join(__dirname, "screenshots")}`);
}

// Run the main function
main().catch((error) => {
  console.error(`❌ Unhandled error in main function: ${error}`);
  process.exit(1);
});
