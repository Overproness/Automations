const fs = require("fs");
const path = require("path");

/**
 * Load proxies from file
 */
async function loadProxies() {
  try {
    const data = fs.readFileSync(
      path.join(__dirname, "../..", "proxies.txt"),
      "utf8"
    );
    const proxies = data
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("//"))
      .map((line) => {
        const [ip, port] = line.split(":");
        return {
          ip,
          port,
          usageCount: 0,
        };
      });
    console.log(`✅ Loaded ${proxies.length} proxies.`);
    return proxies;
  } catch (err) {
    console.error(`❌ Error loading proxies: ${err.message}`);
    return [];
  }
}

/**
 * Get next proxy in rotation
 */
function getNextProxy(proxies, currentIndex) {
  if (proxies.length === 0) return { proxy: null, newIndex: -1 };

  const newIndex = (currentIndex + 1) % proxies.length;
  const proxy = proxies[newIndex];
  proxy.usageCount++;

  return { proxy, newIndex };
}

/**
 * Get proxy arguments for browser launch
 */
function getProxyArgs(proxy) {
  if (!proxy || !proxy.ip || !proxy.port) {
    return [];
  }
  return [`--proxy-server=${proxy.ip}:${proxy.port}`];
}

module.exports = {
  loadProxies,
  getNextProxy,
  getProxyArgs,
};
