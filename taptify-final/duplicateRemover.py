from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


# Start the webdriver
driver = webdriver.Chrome()

# Navigate to the Taptify website
print("Navigating to Taptify website...")
driver.get('https://app.123-empfehlung.de/#/')
time.sleep(3)

# Login to the website
print("Logging in...")
email_input = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located(
        (By.XPATH, '//*[@id="contentWrapper"]/div/div/div/div/div/div[2]/form/div/div[1]/div/div[2]/div/input'))
)
password_input = driver.find_element(By.XPATH,
                                     '//*[@id="contentWrapper"]/div/div/div/div/div/div[2]/form/div/div[2]/div/div[2]/div/input')
login_button = driver.find_element(By.XPATH, '//*[@id="loginButton"]')

email_input.send_keys('dirk.ahlemeyer@gmail.com')
password_input.send_keys('Niederlande12345')
login_button.click()

# Wait for the page to load after login
print("Waiting for login to complete...")
time.sleep(5)

driver.get('https://app.123-empfehlung.de/#/clients')
time.sleep(5)


# Function to scroll to the bottom
def scroll_to_bottom():
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

# Set to store names of entries
names_set = set()

# Function to get entries
def get_entries():
    return driver.find_elements(By.XPATH, '/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div/div/div[1]/*[starts-with(@class, "entry")]')

# Function to delete an entry by clicking its delete button and confirming
def delete_entry(entry_xpath):
    # Click the delete button
    delete_button = driver.find_element(By.XPATH, entry_xpath + '/div/div/div[1]/div[1]/div/div/div[2]/button')
    delete_button.click()

    # Wait for the delete confirmation input field to appear
    time.sleep(1)  # Adjust if necessary
    delete_input = driver.find_element(By.XPATH, '/html/body/div[7]/div[3]/div/div/div[4]/form/div/div/div/div/div/input')
    delete_input.send_keys("delete permanently")

    # Click the permanently delete button
    confirm_button = driver.find_element(By.XPATH, '/html/body/div[7]/div[3]/div/div/button')
    confirm_button.click()

    # Wait for deletion to complete
    time.sleep(2)  # Adjust if necessary

# Function to handle each entry
def process_entry(entry, entry_xpath):
    name_xpath = entry_xpath + '/div/div/div[1]/div[2]/div[1]/div'
    entry_name = driver.find_element(By.XPATH, name_xpath).text

    # If name is already in the set, delete it
    if entry_name in names_set:
        delete_entry(entry_xpath)
        return False  # Entry was deleted, skip adding it to the set
    else:
        # Add name to the set
        names_set.add(entry_name)
        return True  # Entry was processed and added to the set

# Main loop
while True:
    initial_length = len(get_entries())  # Track the number of loaded entries

    # Loop over each entry
    for index, entry in enumerate(get_entries(), start=2):
        entry_xpath = f'/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div/div/div[1]/div[{index}]'

        # If process_entry returns False, skip this entry and continue from the next
        if not process_entry(entry, entry_xpath):
            continue

    # Scroll to the bottom to load more entries
    scroll_to_bottom()
    time.sleep(3)  # Wait for new entries to load

    # Check if new entries were loaded by comparing the length of the entries
    if len(get_entries()) == initial_length:
        # Wait for 10 seconds to check if more entries are still loading
        time.sleep(10)
        if len(get_entries()) == initial_length:
            # No new entries were loaded, stop the loop
            break
        
        
        
time.sleep(30)
# Close the browser after finishing all clients
print("Closing the browser...")
driver.quit()

