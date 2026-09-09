#!/usr/bin/env python
# coding: utf-8
import pyautogui
import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains

# # Load Excel file and check for 'QR Codes' column
# print("Loading Excel file...")
# df = pd.read_excel('clients.xlsx', usecols=['Business', 'Name', 'Email', 'Bad Resolution', 'QR Codes'])



# Load Excel file without limiting to specific columns
print("Loading Excel file...")
df = pd.read_excel('clients.xlsx')  # Load the entire file, not just a subset of columns

print("Excel file loaded.")

# Initialize WebDriver
print("Initializing WebDriver...")
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


# Helper functions

def wait_and_click(xpath, timeout=10):
    """Wait for the element to be clickable and then click it."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        element.click()
    except TimeoutException:
        print(f"Element not found or clickable for XPath: {xpath}")


def safe_click(xpath, retries=3):
    """Handle stale element reference by retrying."""
    attempt = 0
    while attempt < retries:
        try:
            wait_and_click(xpath)
            break  # If successful, break out of the loop
        except StaleElementReferenceException:
            print(f"Stale element reference, retrying {attempt + 1}...")
            attempt += 1


def switch_to_iframe(iframe_xpath):
    """Switch to iframe if the element is inside one."""
    try:
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, iframe_xpath))
        )
        driver.switch_to.frame(iframe)
        print(f"Switched to iframe: {iframe_xpath}")
    except TimeoutException:
        print(f"Iframe not found for XPath: {iframe_xpath}")


def switch_to_default_content():
    """Switch back to the default content."""
    driver.switch_to.default_content()


# Function to switch to iframe if required
def check_iframe_and_switch():
    try:
        iframe = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        driver.switch_to.frame(iframe)
        print("Switched to iframe.")
    except TimeoutException:
        print("No iframe found, continuing without switching.")


# Function to click using JavaScript
def click_using_js(element):
    driver.execute_script("arguments[0].click();", element)


# Try different methods to click the Edit button
def click_edit_button():
    try:
        # Check if it's in an iframe
        check_iframe_and_switch()

        # Step 1: Try clicking using CSS selector
        print("Trying to click Edit button using CSS Selector...")
        edit_button_css = ".MuiButtonBase-root.MuiButton-root.MainButton.MuiButton-contained.MuiButton-containedPrimary"
        edit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, edit_button_css))
        )
        # Scroll into view and click using JavaScript for reliability
        click_using_js(edit_button)
        print("Edit button clicked successfully!")
    except TimeoutException:
        print("Edit button not clickable by CSS Selector, trying pyautogui...")

        # Step 2: Use pyautogui as a fallback
        print("Clicking 'Edit' button using pyautogui...")
        # pyautogui.moveTo(1277, 160)  # Adjust the coordinates as per the actual location
        # pyautogui.click()

    finally:
        # Switch back to the default content if you switched to an iframe
        driver.switch_to.default_content()


def try_clicking_element(css_selector, fallback_coords=None):
    try:
        # Check if it's in an iframe
        check_iframe_and_switch()

        # Step 1: Try clicking using CSS selector
        print(f"Trying to click element using CSS Selector: {css_selector}")
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
        )
        # Scroll into view and click using JavaScript for reliability
        click_using_js(element)
        print(f"Element with CSS Selector {css_selector} clicked successfully!")
    except TimeoutException:
        print(f"Element not clickable by CSS Selector: {css_selector}, trying pyautogui...")

        # if fallback_coords:
        #     # Step 2: Use pyautogui as a fallback if coordinates are provided
        #     print(f"Clicking element using pyautogui at coordinates {fallback_coords}...")
        #     pyautogui.moveTo(fallback_coords[0], fallback_coords[1])  # Adjust the coordinates as per the actual location
        #     pyautogui.click()

    finally:
        # Switch back to the default content if you switched to an iframe
        driver.switch_to.default_content()


def click_third_pencil_icon():
    try:
        # Check if it's in an iframe
        check_iframe_and_switch()

        # Step 1: Try to find all pencil icons
        print("Trying to find all pencil icons...")
        pencil_icons_xpath = "//div[contains(@class, 'MuiBox-root') and contains(@class, 'css-bgd8h9')]//button[contains(@class, 'MuiIconButton-root')]"
        pencil_icons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, pencil_icons_xpath))
        )

        print(f"Found {len(pencil_icons)} pencil icons.")

        # Step 2: Ensure there are at least 3 icons
        if len(pencil_icons) >= 3:
            third_pencil_icon = pencil_icons[2]  # Index 2 for the third item in the list
            # Scroll into view and click using JavaScript
            click_using_js(third_pencil_icon)
            print("Third pencil icon clicked successfully!")
        else:
            click_using_js(pencil_icons[0])  # Click the first pencil icon
            print("Less than 3 pencil icons found.")
    except TimeoutException:
        print("Pencil icons not found or not clickable.")

    finally:
        # Switch back to the default content if switched to an iframe
        driver.switch_to.default_content()


def toggle_video_button():
    try:
        # Check for iframe if necessary
        check_iframe_and_switch()

        # Step 1: Find all toggle buttons using a CSS selector
        print("Finding all toggle buttons...")
        toggle_inputs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "input.PrivateSwitchBase-input.MuiSwitch-input.css-1m9pwf3"))
        )

        # Ensure there are at least two toggle buttons
        if len(toggle_inputs) < 2:
            print("Less than two toggle buttons found!")
            return

        # Select the second toggle button
        second_toggle_input = toggle_inputs[1]  # Index 1 for the second element

        # Step 2: Try to click the checkbox directly using JavaScript
        print("Toggling second Video Testimonial using JavaScript click...")
        driver.execute_script("arguments[0].click();", second_toggle_input)
        print("Second Video Testimonial toggled successfully with JavaScript!")

    except Exception as e:
        print(f"JavaScript click failed: {e}. Trying send_keys...")

        # Step 3: Try to focus on the second checkbox and send the space key
        try:
            print("Focusing and sending keys to the second toggle button...")
            second_toggle_input.send_keys(Keys.SPACE)  # Press space to toggle
            print("Second Video Testimonial toggled successfully with send_keys!")
        except Exception as e:
            print(f"Failed to send keys: {e}. Trying pyautogui...")

            # Fallback: Click using pyautogui if all else fails
            print("Clicking second toggle button using pyautogui...")
            # pyautogui.moveTo(1557, 629)  # Adjust coordinates if needed
            # pyautogui.click()

    finally:
        # Switch back to the default content if switched to an iframe
        switch_to_default_content()


# Now let's implement the button clicks using this approach
def click_buttons():
    try:
        # Positive Experience Button
        positive_experience_button_css = ".MuiButtonBase-root.MuiButton-root.MainButton.MuiButton-contained.MuiButton-containedPrimary.MuiButton-sizeMedium.MuiButton-containedSizeMedium.MuiButton-colorPrimary.MuiButton-fullWidth.button-white-0.EditorRouterButton.css-h3yh1p"
        print("Clicking Positive Experience button...")
        try_clicking_element(positive_experience_button_css, fallback_coords=(1310, 300))

        # # Pencil Icon Button
        # pencil_icon_button_css = ".MuiButtonBase-root.MuiIconButton-root.MuiIconButton-sizeMedium.softButton.css-1jj06et"
        # print("Clicking Pencil Icon button...")
        # try_clicking_element(pencil_icon_button_css, fallback_coords=(1397, 725))

        time.sleep(4)

        click_third_pencil_icon()

        time.sleep(1)

        toggle_video_button()
        
        time.sleep(1)

        # Tick Button (Save Action)
        tick_button_css = ".MuiButtonBase-root.MuiIconButton-root.MuiIconButton-sizeMedium.saveButton.css-1jj06et"
        print("Clicking Tick Button...")
        try_clicking_element(tick_button_css, fallback_coords=(1415, 770))
        
        time.sleep(2)

    except Exception as e:
        print(f"An error occurred during button clicks: {e}")


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

# Initialize an empty list for skipped entries
skipped_entries = []

# Define a function to process each row (business/client)
def process_row(row, index):
    try:
        print(f"Processing client: {row['Name']}")
        
        driver.get('https://app.123-empfehlung.de/#/clients')
        time.sleep(5)

        try:
            # Add a client
            print("Clicking 'Add Client' button...")
            safe_click('/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div/div/div[1]/div[1]/div/div')
        except Exception as e:
            time.sleep(5)
            driver.refresh()
            time.sleep(5)
            print("Clicking 'Add Client' button...")
            safe_click('/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div/div/div[1]/div[1]/div/div')

        time.sleep(2)

        try:
            # Input Business Name
            print(f"Entering business name: {row['Name']}")
            # wait_and_click('/html/body/div[6]/div[3]/div/div/form/div/div[2]/div[1]/div[2]/div/input')
            business_input = driver.find_element(By.XPATH,
                                                '/html/body/div[7]/div[3]/div/div/form/div/div[2]/div[1]/div[2]/div/input')
            business_input.send_keys(row['Name'])

            time.sleep(1)
        except Exception as e:
            time.sleep(5)
            driver.refresh()
            time.sleep(5)
            try:
                # Add a client
                print("Clicking 'Add Client' button...")
                safe_click('/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div/div/div[1]/div[1]/div/div')
            except Exception as e:
                time.sleep(5)
                driver.refresh()
                time.sleep(5)
                print("Clicking 'Add Client' button...")
                safe_click('/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div/div/div[1]/div[1]/div/div')
            time.sleep(5)
            print(f"Entering business name: {row['Name']}")
            business_input = driver.find_element(By.XPATH,
                                                '/html/body/div[7]/div[3]/div/div/form/div/div[2]/div[1]/div[2]/div/input')
            business_input.send_keys(row['Name'])

            time.sleep(1)


    

        # Input Business Owner Email (optional)
        if 'Email' in row and pd.notna(row['Email']):  # Check if 'Email' exists in the row and is not empty
            print(f"Entering business owner email: {row['Email']}")
            business_owner_email_input = driver.find_element(By.XPATH, '/html/body/div[6]/div[3]/div/div/form/div/div[5]/div[2]/div[1]/div/div[2]/div/input')
            business_owner_email_input.send_keys(row['Email'])
        else:
            print(f"No business owner email provided for {row['Name']}. Skipping email input.")

        time.sleep(1)

        # Input Business Owner Name (optional)
        if 'Email' in row and pd.notna(row['Email']):  # Check if 'Name' exists in the row and is not empty
            print(f"Entering business owner name: {row['Name']}")
            business_owner_name_input = driver.find_element(By.XPATH, '/html/body/div[6]/div[3]/div/div/form/div/div[5]/div[2]/div[2]/div/div[2]/div/input')
            business_owner_name_input.send_keys(row['Name'])
        else:
            print(f"No business owner name provided for {row['Name']}. Skipping name input.")



        # Select Plan
        print("Selecting plan...")
        safe_click('/html/body/div[7]/div[3]/div/div/form/div/div[3]/div/div/div[2]')

        time.sleep(1)

        print("Selecting 'Free Trial'...")
        safe_click('/html/body/div[8]/div[3]/ul/li[1]')

        time.sleep(2)

        # Select Language
        print("Selecting language...")
        safe_click('/html/body/div[7]/div[3]/div/div/form/div/div[4]/div[1]/div[2]')

        time.sleep(2)

        print("Selecting 'German' language...")
        safe_click('/html/body/div[8]/div[3]/ul/div/div/div/div/div[1]/div[6]')

        time.sleep(2)

        # Add Logo
        print(f"Uploading logo from Bad Resolution: {row['Bad Resolution']}")

        # Add Logo (optional)
        if pd.notna(row['Bad Resolution']) and row['Bad Resolution'].strip():  # Check if 'Bad Resolution' is not NaN and is not empty
            print(f"Uploading logo from Bad Resolution: {row['Bad Resolution']}")

            # Step 1: Click the button to open the file input dialog (adjust the XPath as needed)
            logo_button_xpath = '/html/body/div[7]/div[3]/div/div/form/div/div[1]/div/div[2]/button'
            logo_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, logo_button_xpath))
            )
            logo_button.click()

            # Step 2: Use pyautogui to handle the file dialog (assumes the dialog appears right after clicking the button)
            time.sleep(1)  # Give some time for the file dialog to appear

            # Use pyautogui to type the file path and press "Enter"
            file_path = row['Bad Resolution'].strip()  # Strip whitespace to avoid issues
            pyautogui.write(file_path)  # Type the file path
            time.sleep(1)  # Small delay to ensure the typing is completed
            pyautogui.press('enter')  # Press 'Enter' to submit the file

        else:
            print(f"No logo path provided for {row['Name']}. Skipping logo upload.")


        # Optional: Add a small delay after uploading
        time.sleep(2)

        # Submit Add Client
        print("Submitting client...")
        safe_click('/html/body/div[7]/div[3]/div/div/button')

        time.sleep(7)

        try:
            # View Account
            print(f"Viewing account for: {row['Name']}")
            safe_click('/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div/div/div[2]/div/div/button')
        except Exception as e:
            time.sleep(5)
            driver.refresh()
            time.sleep(5)
            print(f"Viewing account for: {row['Name']}")
            safe_click('/html/body/div[1]/div[3]/div[1]/div/div[2]/div/div/div/div[1]/div[2]/div/div/div[2]/div/div/button')

        time.sleep(3)

        # Go to Integrations
        print("Navigating to Integrations...")
        driver.get('https://app.123-empfehlung.de/#/settings/integrations')
        

        time.sleep(3)
        
        

        try:
            # Click Google Button
            print("Clicking Google button...")
            driver.find_element(By.XPATH, '/html/body/div[1]/div[3]/div[1]/div/div[2]/div[2]/div[2]/div/div/div/div[4]/button').click()
        except Exception as e:
            driver.refresh()
            time.sleep(3)
            driver.get('https://app.123-empfehlung.de/#/settings/integrations')
            safe_click('/html/body/div[1]/div[3]/div[1]/div/div[2]/div[2]/div[2]/div/div/div/div[4]/button')

        time.sleep(2)

        try:
            # Click Public Access Button
            print("Clicking Public Access button...")
            driver.find_element(By.XPATH,'/html/body/div[6]/div[3]/div/div/div/div[4]/div/div/div[1]/div[2]/div/button[2]').click()
        except Exception as e:
            time.sleep(5)
            driver.refresh()
            time.sleep(7)
            print("Clicking Public Access button...")
            driver.get('https://app.123-empfehlung.de/#/settings/integrations')
            time.sleep(5)
            safe_click('/html/body/div[1]/div[3]/div[1]/div/div[2]/div[2]/div[2]/div/div/div/div[4]/button')
            time.sleep(2)
            safe_click('/html/body/div[6]/div[3]/div/div/div/div[4]/div/div/div[1]/div[2]/div/button[2]')

        time.sleep(1)

        # Select Location
        print("Selecting location...")
        safe_click('/html/body/div[6]/div[3]/div/div/div/div[4]/div/div/div[2]/div/div/div[3]/div/div')
        
        time.sleep(1)
        
        # """Handle stale element reference by retrying."""
        # attempt = 0
        # location_input
        # while attempt < 3:
        #     try:
        #         location_input = WebDriverWait(driver, 10).until(
        #             EC.presence_of_element_located((By.XPATH, '/html/body/div[7]/div[3]/ul/div[1]/div/div/input'))
        #         )
        #         break  # If successful, break out of the loop
        #     except StaleElementReferenceException:
        #         print(f"Stale element reference, retrying {attempt + 1}...")
        #         attempt += 1


        # Concatenate 'Name' and 'Business' fields with a comma and remove extra spaces
        combined_name_business = f"{row['Name'].strip()}, {row['Address'].strip()}"
        driver.find_element(By.XPATH, '/html/body/div[7]/div[3]/ul/div[1]/div/div/input').send_keys(combined_name_business)

        time.sleep(3)
        try:
            print(f"Waiting for location to appear for: {combined_name_business}...")
            location_from_list = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '/html/body/div[7]/div[3]/ul/div[2]/div/div/div/div[1]/div[1]/li'))
            )
            location_from_list.click()
            print("Location selected successfully.")
        except TimeoutException:
            print(f"Location not found for {combined_name_business}. Skipping this client.")
        time.sleep(2)

        # Integrate
        print("Clicking 'Integrate' button...")
        safe_click('/html/body/div[6]/div[3]/div/div/div/div[4]/div/div/div[2]/div/div/div[4]/button')

        time.sleep(3)

        # Review Links
        print("Opening review links...")
        
        try:
            driver.get('https://app.123-empfehlung.de/#/link/personalize')
        except Exception:
            safe_click('//*[@id="bottomSidebar"]/nav/div[4]/div/a')
        
        
        
        # Click on the Edit button
        print("Clicking 'Edit' button...")

        time.sleep(5)

        click_edit_button()

        click_buttons()

        # Define the download directory (adjust this to your actual download folder path)
        download_directory = os.path.join(os.path.expanduser('~'), 'Downloads')
        print(f"Download directory: {download_directory}")

        # # Function to safely click elements
        # def safe_click(xpath):
        #     try:
        #         element = driver.find_element(By.XPATH, xpath)
        #         element.click()
        #     except Exception as e:
        #         print(f"Error clicking element: {str(e)}")


        # Ensure QR Codes column exists
        if 'QR Codes' not in df.columns:
            df['QR Codes'] = None  # Initialize the column if it doesn't exist

        # After QR code download
        print("Downloading QR Code...")
        driver.get('https://app.123-empfehlung.de/#/send-requests')
        safe_click('//*[@id="contentWrapper"]/div/div/div[1]/div[7]/button/div')
        safe_click('//*[@id="contentWrapper"]/div/div/div[2]/div/div[4]/button/div')

        time.sleep(2)  # Wait for the QR code to download

        # Define the expected QR code file name (adjust based on how files are named)
        qr_code_filename = f"qrcode-reviews-{row['Name']}.png"
        print(qr_code_filename)
        qr_code_path = os.path.join(download_directory, qr_code_filename)

        print(f"QR code for {row['Name']} downloaded at: {qr_code_path}")

        # Append the QR code path to the 'QR Codes' column for the specific business
        existing_qr_codes = df.at[index, 'QR Codes']

        # Update the 'QR Codes' column
        if pd.isna(df.at[index, 'QR Codes']):
            df.at[index, 'QR Codes'] = qr_code_path  # Add path if column is empty
        else:
            df.at[index, 'QR Codes'] += f", {qr_code_path}"  # Append path if already exists

        # Save the updated DataFrame back to the Excel file
        # IMPORTANT: This will only modify the 'QR Codes' column without affecting other columns.
        clients_file = 'clients.xlsx'
        df.to_excel(clients_file, index=False)


        # Switch to Agency
        print("Switching to agency...")
        safe_click('/html/body/div[1]/div[2]/div/div/div/div[1]/div/div[1]/div/button')

        time.sleep(3)

        return True  # Indicate success

    except Exception as e:
        print(f"An error occurred for client {row['Name']}. Error: {e}")
        
        # Add to skipped entries for retry
        row_data = row.to_dict()
        row_data['Error'] = str(e)  # Log error message
        skipped_entries.append(row_data)  # Store failed row for retry
        return False  # Indicate failure

# Iterate over the dataframe
for index, row in df.iterrows():
    process_row(row, index)

# Retry mechanism for skipped entries
retry_limit = 2  # You can adjust the retry limit if needed
retry_count = 0

while skipped_entries and retry_count < retry_limit:
    print(f"\nRetrying skipped entries... Attempt {retry_count + 1}")
    
    # Copy the current skipped entries for processing
    retry_entries = skipped_entries[:]
    skipped_entries = []  # Reset skipped_entries for the next round

    # Retry each entry
    for entry in retry_entries:
        entry_series = pd.Series(entry)  # Convert back to Series to mimic original row structure
        process_row(entry_series, entry_series.name)

    retry_count += 1

# Final check after retry attempts
if skipped_entries:
    print(f"\nSome entries could not be processed after {retry_limit} retries.")
    skipped_df = pd.DataFrame(skipped_entries)
    skipped_df.to_csv('skipped.csv', index=False)
    print("Skipped entries have been saved to 'skipped.csv'.")

time.sleep(30)
# Close the browser after finishing all clients
print("Closing the browser...")
driver.quit()
