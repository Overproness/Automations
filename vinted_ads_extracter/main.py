import time
import openpyxl
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# Function to check if an element exists
def check_element_exists(driver, xpath):
    try:
        driver.find_element(By.XPATH, xpath)
        return True  # Element exists
    except NoSuchElementException:
        return False  # Element does not exist

# Function to load keywords from an Excel file and filter out invalid ones
def load_keywords(file_path):
    print("Loading keywords from Excel file...")
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    keywords = []

    for row in sheet.iter_rows(min_row=2, min_col=1, max_col=1, values_only=True):
        keyword = row[0]
        if keyword and keyword.strip():
            keywords.append(keyword)
    print(f"Loaded {len(keywords)} keywords: {keywords}")
    return keywords

# Function to create or open the results Excel file
def create_results_file():
    print("Creating results Excel file...")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Results"
    sheet.append(['Keyword', 'Seller URL', 'Product URL'])
    return workbook, sheet

# Function to check the seller and process the products
def check_seller(driver, xpath_of_seller, keyword, seller_hashmap, results_sheet, workbook):
    try:
        print(f"Checking seller for keyword: {keyword}")
        seller = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath_of_seller))
        )
        href_value = seller.get_attribute('href')
        print(f"Found seller: {href_value}")

        driver.execute_script(f"window.open('{href_value}', '_blank');")
        time.sleep(5)
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(5)

        product_links = []
        count = 1

        while check_element_exists(driver, f'/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/div/div[3]/div[3]/div[1]/div[{count}]/div/div/div/div/div[1]/a'):
            print(f"Processing product {count} for seller: {href_value}")
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                product = WebDriverWait(driver,5).until(EC.presence_of_element_located((By.XPATH, f'/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/div/div[3]/div[3]/div[1]/div[{count}]/div/div/div/div/div[1]/a')))
                link_of_product = product.get_attribute('href')
                print(f"Found product: {link_of_product}")

                driver.execute_script(f"window.open('{link_of_product}', '_blank');")
                time.sleep(3)
                driver.switch_to.window(driver.window_handles[2])

                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH,
                        '//*[@id="sidebar"]/div[1]/div[2]/div/div/div/div/div/div[1]/div[1]/div[1]/span'))
                    )
                except Exception as e:
                    try:
                        element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH,
                            '//*[@id="sidebar"]/div[1]/div[1]/div/div/div/div/div/div[1]/div[1]/div[1]/span'))
                        )
                    except Exception as e:
                        try:
                            element = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH,
                                "//div[@class='summary-max-lines-4']/following-sibling::span[contains(@class, 'web_ui__Text__title')]"))
                            )
                        except Exception as e:
                            print(f"XPath failed, retrying with class name: {e}")
                            continue
                
                text = element.text
                print(f"Product description: {text}")
                text = text.lower()

                search_words = keyword.lower().split()
                if all(word in text for word in search_words):
                    print(f"Keyword '{keyword}' matches product: {link_of_product}")
                    product_links.append(link_of_product)
                    results_sheet.append([keyword, href_value, link_of_product])
                    workbook.save('results.xlsx')
                else:
                    print(f"Keyword '{keyword}' does not match product: {link_of_product}")

                driver.close()
                time.sleep(1)
                count += 1
                driver.switch_to.window(driver.window_handles[1])
                if len(driver.window_handles) > 2:
                    for handle in driver.window_handles[2:]:
                        driver.switch_to.window(handle)
                        driver.close()
                driver.switch_to.window(driver.window_handles[1])
            except Exception as e:
                print(f"Error processing product {count}: {e}")
                count+=1
                if len(driver.window_handles) > 2:
                    for handle in driver.window_handles[2:]:
                        driver.switch_to.window(handle)
                        driver.close()
                driver.switch_to.window(driver.window_handles[1])

        if keyword not in seller_hashmap:
            seller_hashmap[keyword] = {}
        if href_value not in seller_hashmap[keyword]:
            seller_hashmap[keyword][href_value] = []
        seller_hashmap[keyword][href_value].extend(product_links)

        driver.close()
        time.sleep(1)
        driver.switch_to.window(driver.window_handles[0])
        if len(driver.window_handles) > 1:
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(driver.window_handles[0])
    except Exception as e:
        print(f"Error in check_seller for keyword '{keyword}': {e}")
        if len(driver.window_handles) > 1:
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(driver.window_handles[0])

# Main program logic
def main():
    print("Starting main program...")
    keywords = load_keywords('keywords.xlsx')
    if not keywords:
        print("No valid keywords found. Exiting program.")
        return

    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get('https://www.vinted.it/')
    time.sleep(3)

    italia_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div/div/div/div[3]/div[13]/div/div/a")))
    italia_button.click()
    time.sleep(3)

    reject_all_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[7]/div[2]/div/div[1]/div/div[2]/div/button[2]")))
    reject_all_button.click()
    time.sleep(3)

    workbook, results_sheet = create_results_file()
    seller_hashmap = {}

    for keyword in keywords:
        print(f"Searching for keyword: {keyword}")
        driver.get(f'https://www.vinted.it/catalog?search_text={keyword}')
        time.sleep(2)

        italia_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div/div/div/div[3]/div[13]/div/div/a")))
        italia_button.click()
        time.sleep(3)

        page_num = 1
        while True:
            print(f"Processing page {page_num} for keyword '{keyword}'")
            for i in range(1, 101):
                xpath_of_seller = f'/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/section/div[18]/div/div[{i}]/div/div/div/div[1]/a'
                check_seller(driver, xpath_of_seller, keyword, seller_hashmap, results_sheet, workbook)

            try:
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div/main/div/div[1]/div/div[2]/div/div/div/section/div[19]/nav/ul/li[8]/a"))
                )
                if 'aria-disabled' in next_page_button.get_attribute('outerHTML') and 'true' in next_page_button.get_attribute('outerHTML'):
                    print("No more pages available. Stopping search.")
                    break
                else:
                    next_page_button.click()
                    print("Navigating to next page...")
                    page_num += 1
                    time.sleep(3)
            except Exception as e:
                print("No next page button or error navigating pages:", e)
                break

    driver.quit()
    print("Program completed.")

if __name__ == "__main__":
    main()
