import sys
import time
import pyautogui
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
# from instabot import Bot

# Set up Chrome options for undetected-chromedriver
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Specify a path to save session data
profile_path = r"C:\Users\ryan_\AppData\Local\Google\Chrome\User Data\Profile 3"  # Update this path to a location on your computer
options.add_argument(f"--user-data-dir={profile_path}")

# Initialize the driver with the profile path to retain sessions
driver = uc.Chrome(options=options)

def click_element_js(selector, delay=5):
    while True:
        try:
            # Check if the element is present and clickable
            WebDriverWait(driver, delay).until(
                lambda d: d.execute_script(f"return document.querySelector('{selector}') !== null")
            )
            # Click using JavaScript
            driver.execute_script(f"document.querySelector('{selector}').click();")
            print(f"Clicked on element with JavaScript selector: {selector}")
            driver.find_element(By.CSS_SELECTOR, selector).click()
            time.sleep(delay)
            break  # Exit loop if the click was successful
        except Exception as e:
            print(f"Retrying to find and click element with selector {selector}: {e}")
            time.sleep(1)  # Retry every second until successful


def main(iterations):
    driver.get("https://web.like4like.com/user/verify")
    print("Opened the Like4Like verification page.")
    
    time.sleep(20)  # Wait for the page to load

    for _ in range(iterations):
        # driver.get('https://www.instagram.com/tjr/p/C1IAo4sO6qn/')  
        
        # Loop until content is loaded
        while True:
            try:
                # Wait for the content to load (replace 'unique_element_selector' with the selector of the loaded content)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body > div.views-wrapper > div.dashboard-view.generic.views-wrapper__view.animation--animate-in > div > div.views-wrapper > div.earn-likes-view.views-wrapper__view > div.screens-wrapper.liking.card > div.found-screen.animation--animate-in > div.found-screen__description > a"))
                )
                print("Content loaded.")
                break  # Exit loop once content has successfully loaded

            except Exception:
                # If "requesting new data" reappears, wait and retry
                print("Still loading... Waiting for content to appear.")
                time.sleep(10)  # Small delay before rechecking

        # Click on "open link" button using JavaScript selector
        # open_link_selector = "body > div.views-wrapper > div.dashboard-view.generic.views-wrapper__view.animation--animate-in > div > div.views-wrapper > div.earn-likes-view.views-wrapper__view > div.screens-wrapper.liking.card > div.found-screen.animation--animate-in > div.found-screen__description > a"
        # click_element_js(open_link_selector)
        
        pyautogui.click(992, 818)
        
        # Get all window handles
        window_handles = driver.window_handles

        # Switch to the new tab (usually the last handle in the list)
        driver.switch_to.window(window_handles[-1])

        
        for i in range(3):
            
            time.sleep(7)
            
            try:
                like_button = driver.find_element(By.CSS_SELECTOR, "svg[aria-label='Like'][width='24']")
                like_button.click()
                print("Clicked 'Like' button.")
            except Exception as e:
                print(f"Error clicking 'Like' button: {e}")
                
            driver.refresh()

        time.sleep(1)
        

        
        # Close the tab using PyAutoGUI
        print("Pressing Ctrl+W to close the tab...")
        pyautogui.hotkey('ctrl', 'w')
        time.sleep(2)
        
        # driver.close()
        
        # Optionally switch back to the original tab
        driver.switch_to.window(window_handles[0])
        
        time.sleep(2)
        
        haveLikeButton = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/div[3]/div[1]/div[2]/div[3]/div[2]/div[1]')
        haveLikeButton.click()

        # Click on "continue" button
        time.sleep(2)
        continue_button = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/div[3]/div[1]/div[2]/div[4]/div[3]')
        continue_button.click()

        print("Cycle completed. Repeating...")

    driver.quit()


if __name__ == "__main__":
    # Get the number of iterations from command-line arguments
    if len(sys.argv) > 1:
        iterations = int(sys.argv[1])
    else:
        iterations = 200  # Default to 5 if no argument provided

    main(iterations)