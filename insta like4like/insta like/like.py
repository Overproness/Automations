import time
import pyautogui
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver

# Set up Chrome options for undetected-chromedriver
options = uc.ChromeOptions()
# options.add_argument("--headless")  # Comment this out if you want to see the Chrome window
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Specify a path to save session data
profile_path = r"C:\Users\resea\AppData\Local\Google\Chrome\User Data\Profile 3"  # Update this path to a location on your computer
options.add_argument(f"--user-data-dir={profile_path}")

# Initialize the driver with the profile path to retain sessions
driver = uc.Chrome(options=options)

def click_element(xpath, delay=5):
    try:
        element = driver.find_element(By.XPATH, xpath)
        element.click()
        print(f"Clicked on element with xpath: {xpath}")
        time.sleep(delay)
    except Exception as e:
        print(f"Error clicking element with xpath {xpath}: {e}")

def main():
    driver.get("https://web.like4like.com/user/verify")
    print("Opened the Like4Like verification page.")

    try:
        while True:
            time.sleep(200)  # Wait for the page to load
            
            # Click on "open link" button
            try:
                open_link_button = driver.find_element(By.XPATH, "/html/body/div[3]/div[3]/div/div[3]/div[1]/div[2]/div[3]/div[1]/a")
                driver.execute_script("arguments[0].click();", open_link_button)
                open_link_button.click()
                print("Clicked on 'Open Link' button.")
            except Exception as e:
                time.sleep(2)
                open_link_button = driver.find_element(By.XPATH, "/html/body/div[3]/div[3]/div/div[3]/div[1]/div[2]/div[3]/div[1]/a")
                open_link_button.click()
                print(f"Error clicking 'Open Link' button: {e}")
            
            # pyautogui.click(1050, 800)
            
            time.sleep(2)  # Wait for the page to load

            # Click at a specific location using PyAutoGUI
            print("Clicking at coordinates (1115, 603) using PyAutoGUI...")
            pyautogui.click(1200, 603)
            time.sleep(2)

            # Close the tab using PyAutoGUI
            print("Pressing Ctrl+W to close the tab...")
            pyautogui.hotkey('ctrl', 'w')
            time.sleep(2)

            # Click on the "I have liked" button
            try:
                liked_button = driver.find_element(By.XPATH, "/html/body/div[3]/div[3]/div/div[3]/div[1]/div[2]/div[3]/div[2]/div[1]")
                liked_button.click()
                print("Clicked on 'I have liked' button.")
            except Exception as e:
                print(f"Error clicking 'I have liked' button: {e}")
                pyautogui.click(952, 687)
                time.sleep(1)
                # Close the tab using PyAutoGUI
                print("Pressing Ctrl+W to close the tab...")
                pyautogui.hotkey('ctrl', 'w')
                time.sleep(2)
                liked_button = driver.find_element(By.XPATH, "/html/body/div[3]/div[3]/div/div[3]/div[1]/div[2]/div[3]/div[2]/div[1]")
                liked_button.click()
                print("Clicked on 'I have liked' button.")
                    

            # Click on "continue" button
            time.sleep(2)
            continue_button = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/div[3]/div[1]/div[2]/div[4]/div[3]')
            continue_button.click()
            

            print("Cycle completed. Repeating...")

    except KeyboardInterrupt:
        print("Script interrupted. Exiting...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
