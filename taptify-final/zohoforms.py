import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains

# Provide your email and password here
email = 'dirk.ahlemeyer@gmail.com'
password = 'Niederlande12345'

# Read the Excel file
df = pd.read_excel('company.xlsx')

# # Filter rows where 'Address' column is not empty
# df = df[df['Address'].notna()]

# Initialize the WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
actions = ActionChains(driver)

# Open the Zoho Forms login page
driver.get("https://forms.zoho.eu/")

# Login process
driver.find_element(By.XPATH, '//*[@id="header"]/div[3]/div[3]/a[1]').click()  # Click sign-in
time.sleep(2)  # Wait for page to load
driver.find_element(By.XPATH, '//*[@id="login_id"]').send_keys(email)  # Enter email
driver.find_element(By.XPATH, '//*[@id="nextbtn"]').click()  # Click next
time.sleep(2)  # Wait for password page
driver.find_element(By.XPATH, '//*[@id="password"]').send_keys(password)  # Enter password
driver.find_element(By.XPATH, '//*[@id="nextbtn"]').click()  # Sign in
time.sleep(5)  # Wait for login to complete

# Navigate to the forms page
driver.get('https://forms.zoho.eu/dirk679756859/home#myforms')
time.sleep(5)  # Wait for forms page to load

# Iterate over the rows in the DataFrame
for index, row in df.iterrows():
    company_name = row['Company Name']

    # Step 1: Hover over the specific form (li[6])
    form_element = driver.find_element(By.XPATH, '//*[@id="listing-container"]/li[6]')
    actions.move_to_element(form_element).perform()  # Hover over the form
    time.sleep(2)  # Wait for the three-dot menu to appear

    # Step 2: Hover over the three-dot menu
    three_dot_menu = driver.find_element(By.XPATH, '//*[@id="listing-container"]/li[6]/div[4]/ul/li[5]/div')
    actions.move_to_element(three_dot_menu).perform()  # Hover over the three-dot menu
    time.sleep(2)  # Wait for the duplicate option to appear

    # Step 3: Click on the duplicate option
    duplicate_option = driver.find_element(By.XPATH, '//*[@id="listing-container"]/li[4]/div[4]/ul/li[5]/div/div/ul/li[5]')
    duplicate_option.click()
    time.sleep(2)

    # Enter form name
    form_name_input = driver.find_element(By.XPATH, '//*[@id="duplicate-form-inp"]')
    form_name_input.clear()
    form_name_input.send_keys(company_name)

    # Click on create button
    driver.find_element(By.XPATH, '//*[@id="duplicateFormBtn"]').click()
    time.sleep(5)  # Wait for form creation

    # Share the form
    driver.find_element(By.XPATH, '//*[@id="tab-strip"]/div/div[1]/ul/li[6]/a').click()
    time.sleep(2)

    # Shorten the URL
    driver.find_element(By.XPATH, '//*[@id="genshrturlbtn"]/span[1]').click()
    time.sleep(2)

    # Copy the shortened URL
    short_url_element = driver.find_element(By.XPATH, '//*[@id="shorturldiv"]/textarea')
    short_url = short_url_element.get_attribute('value')

    # Paste the URL into the 'Form Link' column
    df.at[index, 'Form Link'] = short_url

    # Save the updated Excel file after each row
    df.to_excel('updated_excel_file.xlsx', index=False)

# Close the browser
driver.quit()