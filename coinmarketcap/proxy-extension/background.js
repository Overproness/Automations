
    var config = {
      mode: "fixed_servers",
      rules: {
        singleProxy: {
          scheme: "http",
          host: "dc.oxylabs.io",
          port: parseInt(8001)
        },
        bypassList: ["localhost"]
      }
    };
    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
    function callbackFn(details) {
      return {
        authCredentials: {
          username: "fivacc8_h19HR",
          password: "_Test1234567"
        }
      };
    }
    chrome.webRequest.onAuthRequired.addListener(
      callbackFn,
      {urls: ["<all_urls>"]},
      ['blocking']
    );
  