import csv
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time


# Read accounts from CSV
def read_accounts(file_path):
    accounts = []
    try:
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                accounts.append({'username': row['username'], 'password': row['password']})
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred while reading the accounts CSV: {e}")
    return accounts


# Read soundtracks from CSV
def read_soundtracks(file_path):
    soundtracks = []
    try:
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                soundtracks.append(row['link'])
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred while reading the soundtracks CSV: {e}")
    return soundtracks


# Login to the account
def login(driver, username, password):
    try:
        print(f"Logging in with username: {username}")
        driver.get('https://accounts.spotify.com/en/login')

        # Wait until the username input is present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'login-username'))
        )

        # Locate input fields by ID
        username_input = driver.find_element(By.ID, 'login-username')
        password_input = driver.find_element(By.ID, 'login-password')

        # Enter credentials and submit
        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)

        # Wait for login to complete
        time.sleep(5)  # Adjust sleep time as needed for login to process

    except Exception as e:
        print(f"An error occurred during login: {e}")


# Play soundtracks
def play_soundtrack(driver, soundtrack_link):
    try:
        print(f"Playing soundtrack: {soundtrack_link}")
        driver.get(soundtrack_link)

        time.sleep(5)

        pyautogui.press('enter')  # Bringing window to the front using PyAutoGUI (optional, for focus purposes)
        # You can use Selenium to directly click on play instead of using PyAutoGUI
        # Wait for the page to load and the play button to be clickable
        play_button_xpath = '/html/body/div[5]/div/div[2]/div[4]/div[1]/div[2]/div[2]/div/main/section/div[3]/div[2]/div/div/div/button/span'  # Adjust XPath based on the actual button

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, play_button_xpath))
        )

        # Click the play button
        play_button = driver.find_element(By.XPATH, play_button_xpath)
        play_button.click()
        print("Clicked the play button.")

    except Exception as e:
        print(f"An error occurred while playing soundtrack: {e}")


def main():
    while True:
        accounts = read_accounts('accounts.csv')
        soundtracks = read_soundtracks('soundtracks.csv')

        if not accounts or not soundtracks:
            print("No accounts or soundtracks to process. Please check your CSV files.")
            return

        # Process each soundtrack for each account
        for soundtrack in soundtracks:
            for account in accounts:
                options = Options()
                options.add_argument("--disable-blink-features=AutomationControlled")

                # Open browser maximized
                options.add_argument("--start-maximized")

                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

                # Bring the window to the front using PyAutoGUI
                pyautogui.getWindowsWithTitle("Chrome")[
                    0].activate()  # Assumes the browser window title contains "Chrome"
                time.sleep(1)  # Short delay to ensure the window is brought to the front

                # Login to the account
                login(driver, account['username'], account['password'])

                # Play the current soundtrack
                play_soundtrack(driver, soundtrack)

                # Wait for 10 minutes before closing the window
                time.sleep(600)  # 600 seconds = 10 minutes

                # Close the browser window
                driver.quit()

                # Move to the next account
                time.sleep(5)  # Short delay between opening windows to avoid potential rate-limiting issues

        # Print a message after processing all accounts for all soundtracks
        print("Completed processing all accounts and soundtracks. All windows remain open for 10 minutes.")

        # Wait for 5 minutes before starting the next cycle
        print("Waiting for 5 minutes before starting the next cycle...")
        time.sleep(300)  # 300 seconds = 5 minutes


if __name__ == "__main__":
    main()
