import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import pandas as pd
import time


def login(driver, email, password):
    driver.get("https://www.google.com")
    time.sleep(2)
    driver.find_element(By.XPATH, '//*[@id="gb"]/div/div[2]/a').click()
    time.sleep(2)

    email_input = driver.find_element(By.XPATH, '//*[@id="identifierId"]')
    email_input.send_keys(email)
    driver.find_element(By.XPATH, '//*[@id="identifierNext"]/div/button').click()
    time.sleep(2)

    password_input = driver.find_element(By.XPATH, '//*[@id="password"]/div[1]/div/div[1]/input')
    password_input.send_keys(password)
    driver.find_element(By.XPATH, '//*[@id="passwordNext"]/div/button').click()
    time.sleep(3)


def post_review(driver, link, review):
    driver.get(link)
    time.sleep(5)

    try:
        driver.find_element(By.XPATH, '//*[@id="wrkpb"]').click()
        time.sleep(2)
        driver.find_element(By.XPATH, '//*[@id="kCvOeb"]/div[1]/div[3]/div[1]/div[2]/div/div[5]').click()
        time.sleep(1)

        review_input = driver.find_element(By.XPATH, '//*[@id="c2"]')
        review_input.send_keys(review)

        driver.find_element(By.XPATH,
                            '/html/body/div/c-wiz/div/div/div/c-wiz/div/div[2]/div/div[2]/div/button/div[3]').click()
        time.sleep(2)
    except Exception as e:
        print(f"Error posting review: {e}")


def main():
    accounts_df = pd.read_excel("accounts.xlsx")
    links_df = pd.read_excel("Links.xlsx")
    reviews_df = pd.read_excel("Reviews.xlsx")

    driver = uc.Chrome()

    try:
        for i in range(len(accounts_df)):
            email = accounts_df.loc[i, 'Email']
            password = accounts_df.loc[i, 'Password']
            print(f"Logging in with: {email}")

            login(driver, email, password)
            time.sleep(3)

            for j in range(len(links_df)):
                link = links_df.loc[j, 'Links']
                review = reviews_df.loc[j, 'Reviews']
                print(f"Posting review for link: {link}")
                post_review(driver, link, review)
                time.sleep(2)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
