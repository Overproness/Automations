#!/usr/bin/env python
# coding: utf-8

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Replace these with your own credentials
USERNAME = 'chippu_photography'
PASSWORD = 'qwerty12345'

# Set up the WebDriver
driver = webdriver.Chrome()  # or webdriver.Firefox() for Firefox

# Maximize the browser window
driver.maximize_window()

def add_profiles_to_close_friends():
    profiles_added = 0
    profile_index = 1  # Start from the first profile in the list

    while profiles_added < 25:
        try:
            # Dynamic XPath for each profile's outer element, changing based on index
            profile_xpath = f'/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[1]/section/main/div/div[3]/div/div[2]/div/div/div[1]/div/div/div/div[2]/div[2]/div/div[1]/div[{profile_index}]'
            button_xpath = f'{profile_xpath}/div/div[2]/div/div/div'
            
            # Check if the profile element exists
            try:
                profile_element = driver.find_element(By.XPATH, profile_xpath)
            except Exception as e:
                print(f"No profile found at index {profile_index}: {e}")
                profile_index += 1
                continue  # Move to the next profile if this one doesn't exist

            # Check if the button element exists
            try:
                button_element = driver.find_element(By.XPATH, button_xpath)
            except Exception as e:
                print(f"No button found for profile at index {profile_index}: {e}")
                profile_index += 1
                continue  # Move to the next profile if button doesn't exist
            
            # Check if the person is already a close friend by examining the button's aria-label
            button_label = button_element.get_attribute("aria-label")  # Or check class

            if "Add to Close Friends" in button_label:  # If not a close friend
                button_element.click()  # Add to Close Friends
                profiles_added += 1
                print(f"Added profile {profiles_added} to Close Friends.")
                time.sleep(1)  # Wait briefly to avoid rate limiting

            # Move to the next profile
            profile_index += 1

            # Scroll down every 5 profiles to ensure more profiles load
            if profile_index % 5 == 0:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)  # Wait for new profiles to load

        except Exception as e:
            print(f"Error processing profile at index {profile_index}: {e}")
            profile_index += 1  # Move to the next profile in case of an error

try:
    # Navigate to Instagram login page
    driver.get('https://www.instagram.com/accounts/login/')
    time.sleep(2)  # Wait for the page to load

    # Find the username and password input fields
    username_input = driver.find_element(By.NAME, 'username')
    password_input = driver.find_element(By.NAME, 'password')

    # Enter your credentials
    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)

    # Submit the form
    password_input.send_keys(Keys.RETURN)

    # Wait for login to complete
    WebDriverWait(driver, 10).until(EC.url_changes('https://www.instagram.com/accounts/login/'))

    # Check if login was successful
    if "login" not in driver.current_url:
        print("Login successful!")

        # Directly navigate to the Close Friends page
        driver.get('https://www.instagram.com/accounts/close_friends/')
        time.sleep(5)  # Wait for the Close Friends page to load

        # Add profiles to Close Friends
        add_profiles_to_close_friends()

        print("Finished adding profiles to Close Friends.")
    else:
        print("Login failed!")

finally:
    # Close the browser after a while (optional)
    time.sleep(10)
    driver.quit()
