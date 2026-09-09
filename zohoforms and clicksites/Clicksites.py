import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from selenium.webdriver.common.keys import Keys
import pyautogui
import pyperclip
import re

# Function to replace links and paste updated HTML
def replace_link(driver, new_link):
    time.sleep(3)

    # Ensure new_link is a string
    new_link = str(new_link)
    print(f"Replacing with new link: {new_link}")

    try:
        # Scroll to the container element and click the starting line
        starting_line_xpath = '/html/body/div[2]/div[91]/div[2]/div[1]/div/div[1]/div[2]/div[1]/div[4]/div[1]'
        retries = 3  # Retry clicking in case of a stale element
        for attempt in range(retries):
            try:
                line = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, starting_line_xpath))
                )
                line.click()
                print('Clicked on the starting line.')
                break
            except StaleElementReferenceException:
                if attempt < retries - 1:
                    print("Retrying due to stale element...")
                    time.sleep(1)
                else:
                    print("Failed to interact with the line due to stale element.")
                    return

        # Copy all code with Ctrl+A, Ctrl+C
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.hotkey('ctrl', 'c')
        print("Copied the HTML content.")
        time.sleep(1)
        
        # Get the copied HTML content using pyperclip
        copied_html = pyperclip.paste()
        
        # Use regex to replace the entire link starting with "https://zfrmz.eu/" followed by any characters
        modified_html = re.sub(r"https://zfrmz\.eu/\S+", new_link, copied_html)
        
        
        # Paste back with Ctrl+A, Ctrl+V
        pyautogui.hotkey('ctrl', 'a')
        pyperclip.copy(modified_html)  # Copy modified HTML to clipboard
        pyautogui.hotkey('ctrl', 'v')  # Paste the modified HTML
        print("Pasted the modified HTML content.")
        
    except Exception as e:
        print(f"Error during the operation: {e}")



# Load the Excel file using pandas
excel_path = 'company.xlsx'
df = pd.read_excel(excel_path)
print("Excel file loaded successfully.")

# Setup WebDriver
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 20)
print("WebDriver setup completed.")

# Login process
print("Starting login process.")
driver.get('https://app.clicksites.ai/pages')
wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="login-form_email"]'))).send_keys('dirk.ahlemeyer@gmail.com')
driver.find_element(By.XPATH, '//*[@id="login-form_password"]').send_keys('Niederlande12345')
driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div/div[2]/div/div/form/div[3]/div/div/div/div/button').click()
print("Login submitted.")

time.sleep(10)

# Process each row in the DataFrame
for index, row in df.iterrows():
    print(f"Processing row {index + 1}: {row}")
    web_page = row['Web Path']
    form_link = row['Form Link']
    company_name = row['Company Name']
    
    # Open the cloning page
    driver.get('https://app.clicksites.ai/pages')
    time.sleep(7)
    
    # Search and select the template
    print("Searching for the template.")
    search_input = driver.find_element(By.XPATH, '/html/body/div/div/div/div[2]/div/div/main/div[1]/div[2]/div/div[3]/span/span/input')
    search_input.click()
    time.sleep(2)
    search_input.send_keys('Toom')
    time.sleep(1)
    search_button = driver.find_element(By.XPATH, '/html/body/div/div/div/div[2]/div/div/main/div[1]/div[2]/div/div[3]/span/span/span/button')
    search_button.click()
    time.sleep(7)
    
    # Clone the template
    print("Cloning the template.")
    wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div/main/div[2]/div/div/div/div/div[1]/div/div/div/div/div/div[5]/div/div[4]/button'))).click()
    time.sleep(3)
    
    # Select from dropdown
    print("Expanding dropdown.")
    dropdown_toggle_xpath = '/html/body/div[2]/div/div[2]/div/div[2]/div[2]/form/div[1]/div/div[2]/div/div/div/div/span[1]/input'
    dropdown_toggle = driver.find_element(By.XPATH, dropdown_toggle_xpath)
    dropdown_toggle.click()
    time.sleep(2)
    
    last_dropdown_element_xpath = "(//div[@class='ant-select-item ant-select-item-option'])[last()]"
    last_element = driver.find_element(By.XPATH, last_dropdown_element_xpath)
    driver.execute_script("arguments[0].scrollIntoView(true);", last_element)
    time.sleep(1)
    last_element.click()
    print("Last dropdown element selected.")
    
    # Input slug
    print(f"Entering slug: {web_page}")
    slug_input = driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div[2]/div[2]/form/div[2]/div[1]/div[2]/div[1]/div/input')
    driver.execute_script("arguments[0].select();", slug_input)
    slug_input.clear()
    slug_input.send_keys(web_page)
    time.sleep(3)
    
    # Navigate and edit the page
    print("Navigating to edit page.")
    driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div[2]/div[3]/button[2]').click()
    time.sleep(7)
    
    wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div/div[1]/section/button'))).click()
    time.sleep(5)
    
    # Switch to iframe and locate element
    print("Switching to iframe for editing.")
    driver.switch_to.frame(driver.find_element(By.XPATH, '/html/body/div[2]/div[9]/div/iframe'))
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/div[1]/div[2]/div[4]/div[1]/div/div')))
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    element.click()
    driver.switch_to.default_content()
    time.sleep(5)

    # Click edit code button
    print("Clicking Edit Code button.")
    edit_code_button = driver.find_element(By.XPATH, '/html/body/div[3]/div/div[3]/div/div[1]/button')
    try:
        edit_code_button.click()
        print("Edit Code button clicked.")
        time.sleep(3)
    except Exception as e:
        driver.execute_script("arguments[0].click();", edit_code_button)
        print("Edit Code button clicked using JavaScript.")
    
    # Replace links in lines 57 and 87
    print("Replacing links in code.")
    time.sleep(15)
    replace_link(driver, form_link)
    replace_link(driver, form_link)
    

    # Save and update the company name
    print("Clicking OK button.")
    ok_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div[91]/div[2]/div[2]/button[2]')))
    driver.execute_script("arguments[0].click();", ok_button)
    time.sleep(3)
    
    print("Updating company name.")
    driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div/div/div[3]/div[2]/div/div[1]/button').click()
    name_input = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="name"]')))
    name_input.clear()
    name_input.send_keys(company_name)
    time.sleep(2)
    
    update_button = driver.find_element(By.XPATH, '/html/body/div[5]/div/div[2]/div/div[2]/div/div/div[2]/form/div[3]/div/div/div/div/button')
    driver.execute_script("arguments[0].click();", update_button)
    time.sleep(5)
    
    close_button = driver.find_element(By.XPATH, '/html/body/div[5]/div/div[2]/div/div[2]/button')
    close_button.click()
    time.sleep(3)
    
    # Publish and get link
    print("Publishing the page.")
    driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div/div/div[3]/div[2]/div/div[2]/button').click()
    time.sleep(3)
    save_button = driver.find_element(By.XPATH, '/html/body/div[6]/div/div[2]/div/div[2]/div[2]/button[2]')
    driver.execute_script("arguments[0].click();", save_button)
    time.sleep(3)
    
    driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div/div/div[3]/div[2]/div/div[2]/button').click()
    time.sleep(3)
    
    # Copy publish link
    print("Copying publish link.")
    publish_link = driver.find_element(By.XPATH, '/html/body/div[6]/div/div[2]/div/div[2]/div[1]/div/div/form/div[4]/div/div/div/div/a').get_attribute('href')
    df.at[index, 'Review Page Url'] = publish_link

# Save updated Excel file
print("Saving updated Excel file.")
df.to_excel(excel_path, index=False)

# Close the browser
print("Closing browser.")
driver.quit()
