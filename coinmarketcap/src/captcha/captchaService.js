const axios = require("axios");
const { Buffer } = require("buffer");
const { sleep } = require("../utils/browserUtils");
const config = require("../config");

/**
 * Create a task in the 2Captcha API
 */
async function createTask(param) {
  try {
    const baseUrl = "https://api.2captcha.com/createTask";
    const response = await axios.post(baseUrl, {
      clientKey: param.clientKey,
      task: {
        type: "GridTask",
        body: param.body,
        comment: param.comment,
        rows: 3,
        columns: 3,
      },
    });
    return response.data.taskId;
  } catch (err) {
    console.error(`❌ Error in createTask: ${err}`);
    return null;
  }
}

/**
 * Get task results from the 2Captcha API
 */
async function getTaskResults(p) {
  let taskResults = null;
  while (taskResults === null) {
    const baseUrl = "https://api.2captcha.com/getTaskResult";
    await sleep(30000); // Wait 30 seconds before checking
    try {
      const response = await axios.post(baseUrl, {
        clientKey: p.clientKey,
        taskId: p.taskId,
      });
      console.log(response.data);
      if (response.data.status === "ready") {
        taskResults = response.data;
      }
    } catch (err) {
      console.error(`❌ Error in getTaskResults: ${err}`);
    }
  }
  return taskResults;
}

/**
 * Get task results with timeout to avoid infinite waiting
 */
async function getTaskResultsWithTimeout(p) {
  const startTime = Date.now();
  const maxWaitTime = p.maxWaitTime || config.TIMEOUTS.CAPTCHA_TIMEOUT;
  const pollInterval = 10000; // Poll every 10 seconds

  let taskResults = null;

  while (Date.now() - startTime < maxWaitTime) {
    const baseUrl = "https://api.2captcha.com/getTaskResult";

    try {
      console.log(
        `[+] Checking CAPTCHA solution status (elapsed: ${Math.round(
          (Date.now() - startTime) / 1000
        )}s)...`
      );
      const response = await axios.post(baseUrl, {
        clientKey: p.clientKey,
        taskId: p.taskId,
      });

      console.log(response.data);

      // Check for specific error messages that indicate the CAPTCHA is unsolvable
      if (
        response.data.errorId === 12 ||
        (response.data.errorCode &&
          response.data.errorCode === "ERROR_CAPTCHA_UNSOLVABLE")
      ) {
        throw new Error("CAPTCHA unsolvable by 2Captcha");
      }

      if (response.data.status === "ready") {
        taskResults = response.data;
        break;
      }
    } catch (err) {
      console.error(`❌ Error in getTaskResultsWithTimeout: ${err}`);

      // If this is a specific error about the CAPTCHA being unsolvable, don't retry
      if (err.message === "CAPTCHA unsolvable by 2Captcha") {
        throw err; // Rethrow to signal we need to refresh the CAPTCHA
      }
    }

    // Wait before the next check
    await sleep(pollInterval);
  }

  if (!taskResults) {
    throw new Error(
      `Timeout waiting for CAPTCHA solution after ${maxWaitTime / 1000} seconds`
    );
  }

  return taskResults;
}

/**
 * Download CAPTCHA image and solve using 2Captcha
 */
async function solveCaptchaWithApi(page, imageUrl, selectionCriteria) {
  try {
    console.log(`[+] Download and transform to base64 ==> ${imageUrl}`);

    // Get the image and convert it to base64
    const response = await axios.get(imageUrl, {
      responseType: "arraybuffer",
      timeout: 30000, // 30 second timeout for image download
    });

    if (response.status !== 200) {
      console.error(
        `❌ Failed to download CAPTCHA image. Status: ${response.status}`
      );
      return false;
    }

    const imageBuffer = Buffer.from(response.data).toString("base64");

    // Create task with 2Captcha API
    const taskId = await createTask({
      body: imageBuffer,
      clientKey: config.TWO_CAPTCHA_API_KEY,
      comment: `select all ${selectionCriteria}`,
    });

    console.log(`[+] Task ID: ${taskId}`);

    if (!taskId) {
      console.error("❌ Failed to create task with 2Captcha API");
      return false;
    }

    // Get task results with improved error handling
    let results;
    try {
      results = await getTaskResultsWithTimeout({
        taskId: taskId,
        clientKey: config.TWO_CAPTCHA_API_KEY,
        maxWaitTime: config.TIMEOUTS.CAPTCHA_TIMEOUT,
      });
    } catch (e) {
      console.error(`❌ Error getting CAPTCHA solution: ${e.message}`);
      return false;
    }

    if (!results || !results.solution || !results.solution.click) {
      console.error("❌ Invalid or missing solution from 2Captcha");
      return false;
    }

    console.log(
      `[+] Returning Solution From 2Cap API === > :: ${results.solution.click}`
    );

    // Interact with the CAPTCHA using the solution
    await solveCaptchaInteraction(page, results.solution.click);

    // Wait and check if CAPTCHA was solved successfully
    await page.waitForTimeout(20000);

    // Check if verify button still exists
    const verifyButtonStillExists = await page.evaluate(() => {
      return document.querySelector("div.bcap-verify-button") !== null;
    });

    if (verifyButtonStillExists) {
      console.log("❌ CAPTCHA verification failed");
      return false;
    } else {
      console.log("✅ CAPTCHA verification succeeded");
      return true;
    }
  } catch (e) {
    console.error(`❌ Error in solveCaptchaWithApi: ${e}`);
    return false;
  }
}

/**
 * Interact with the CAPTCHA on the page using the solution
 */
async function solveCaptchaInteraction(page, solution) {
  try {
    await page.evaluate((solutionArr) => {
      console.log("Clicking on positions:", solutionArr);
      let images = Array.from(
        document.querySelectorAll("div.bcap-image-cell-image")
      );
      if (images.length === 0) {
        images = Array.from(
          document.querySelectorAll("div[class*='task-image']")
        );
      }
      solutionArr.forEach((sol) => {
        if (images[sol - 1]) {
          images[sol - 1].click();
        }
      });
    }, solution);
    console.log("✅ Clicked on CAPTCHA images at positions:", solution);
    await page.waitForTimeout(2000);

    // Click verify button
    await page.evaluate(() => {
      const verifyBtn = document.querySelector("div.bcap-verify-button");
      if (verifyBtn) verifyBtn.click();
    });
    console.log("✅ Clicked CAPTCHA verify button");
  } catch (error) {
    console.error(`❌ Error in solveCaptchaInteraction: ${error}`);
  }
}

module.exports = {
  solveCaptchaWithApi,
  solveCaptchaInteraction,
  createTask,
  getTaskResults,
  getTaskResultsWithTimeout,
};
