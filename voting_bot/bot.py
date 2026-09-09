from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.webdriver.common.action_chains import ActionChains
import random
import string

# Function to generate a random string
def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_random_string_without_digits(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

# Use the function to generate a random email
random_string = generate_random_string()

try:
    for i in range(10000):  # Loop for 100 iterations
        # Set up the WebDriver (update the path to your WebDriver executable)
        driver = webdriver.Chrome()

        # Maximize the browser window
        driver.maximize_window()
        print(f"Iteration {i+1}/10,000")
        
        # Open the website
        driver.get('https://www.hobokengirl.com/best-of-hoboken-jersey-city-2024-guide-finalists/')
        time.sleep(12)

        try:
            cross_button_popup = driver.find_element(By.XPATH, '/html/body/div[9]/div[2]/div/div/button')
            cross_button_popup.click()
        except Exception as e:
            print("No popup found:", e)

        time.sleep(1)

        # Fill out the form
        first_name_input = driver.find_element(By.XPATH, '//*[@id="input_22_2_3"]')
        first_name_input.send_keys(generate_random_string_without_digits())
        time.sleep(1)

        last_name_input = driver.find_element(By.XPATH, '//*[@id="input_22_2_6"]')
        last_name_input.send_keys(generate_random_string_without_digits())
        time.sleep(1)

        email_input = driver.find_element(By.XPATH, '//*[@id="input_22_1"]')
        email_input.send_keys(f"{generate_random_string()}{i}@fjds.jcd")
        time.sleep(1)

        # city_input = driver.find_element(By.XPATH, '//*[@id="input_22_4"]')
        # city_input.click()
        # time.sleep(1)

        correct_city = driver.find_element(By.XPATH, '//*[@id="input_22_4"]/option[2]')
        correct_city.click()
        time.sleep(1)
        
        vote_now_button = driver.find_element(By.XPATH, '//*[@id="gform_submit_button_22"]')
        vote_now_button.click()
        
        time.sleep(10)

        # Voting process
        first_label = driver.find_element(By.XPATH, '/html/body/div[1]/div[4]/div/div/article/div[3]/div/div[10]/div/form/div[2]/div/div/div[2]/label[2]')
        driver.execute_script("arguments[0].scrollIntoView();", first_label)
        # first_label.click()
        driver.execute_script("arguments[0].click();", first_label)

        # # Use ActionChains to click if necessary
        # actions = ActionChains(driver)
        # actions.move_to_element(first_label).click().perform()

        # first_label.click()
        time.sleep(1)

        first_vote_button = driver.find_element(By.XPATH, '/html/body/div[1]/div[4]/div/div/article/div[3]/div/div[10]/div/form/div[4]/button')
        first_vote_button.click()
        time.sleep(5)

        second_label = driver.find_element(By.XPATH, '/html/body/div[1]/div[4]/div/div/article/div[3]/div/div[28]/div/form/div[2]/div/div/div[2]/label[3]')
        driver.execute_script("arguments[0].scrollIntoView();", second_label)
        # first_label.click()
        driver.execute_script("arguments[0].click();", second_label)
        time.sleep(1)

        second_vote_button = driver.find_element(By.XPATH, '/html/body/div[1]/div[4]/div/div/article/div[3]/div/div[28]/div/form/div[4]/button')
        second_vote_button.click()
        time.sleep(5)

        third_label = driver.find_element(By.XPATH, '/html/body/div[1]/div[4]/div/div/article/div[3]/div/div[34]/div/form/div[2]/div/div/div[2]/label[3]')
        driver.execute_script("arguments[0].scrollIntoView();", third_label)
        # first_label.click()
        driver.execute_script("arguments[0].click();", third_label)
        time.sleep(1)

        third_vote_button = driver.find_element(By.XPATH, '/html/body/div[1]/div[4]/div/div/article/div[3]/div/div[34]/div/form/div[4]/button')
        third_vote_button.click()
        time.sleep(5)

        print(f"Iteration {i+1} completed.")
        driver.quit()  # Ensure the driver quits at the end
        
except Exception as e:
    print("Error:", e)
    driver.quit()
