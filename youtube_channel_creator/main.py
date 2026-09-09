import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import pandas as pd
import time


def login(driver, email, password):
    driver.get("https://www.youtube.com/create_channel")
    time.sleep(2)
    # driver.find_element(By.XPATH, '//*[@id="gb"]/div/div[2]/a').click()
    time.sleep(2)

    email_input = driver.find_element(By.XPATH, '//*[@id="identifierId"]')
    email_input.send_keys(email)
    driver.find_element(By.XPATH, '//*[@id="identifierNext"]/div/button').click()
    time.sleep(30)

    password_input = driver.find_element(By.XPATH, '//*[@id="password"]/div[1]/div/div[1]/input')
    password_input.send_keys(password)
    driver.find_element(By.XPATH, '//*[@id="passwordNext"]/div/button').click()
    
    try:
        time.sleep(10)
        not_now_button = driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[3]/div/div[2]/div/div/button')
        not_now_button.click()
        time.sleep(5)
        driver.execute_script("arguments[0].click();", not_now_button)
    except Exception as e:
        print(f"Error: {e}")
        
    time.sleep(10)
    
    driver.find_element(By.XPATH, '/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-channel-creation-dialog-renderer/div/div[6]/ytd-button-renderer[2]/yt-button-shape/button/yt-touch-feedback-shape/div').click()
    time.sleep(5)



def main():
    accounts_df = pd.read_excel("accounts.xlsx")
    options = uc.ChromeOptions()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")


    try:
        for i in range(len(accounts_df)):
            driver = uc.Chrome(options=options)
            email = accounts_df.loc[i, 'email']
            password = accounts_df.loc[i, 'pass']
            print(f"Logging in with: {email}")

            login(driver, email, password)
            time.sleep(3)
            driver.close()
            print(f"Channel created for: {email}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
