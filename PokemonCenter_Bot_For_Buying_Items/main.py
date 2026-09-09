import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# List of proxies
proxies = [
    "94.139.204.51:8081", "27.147.140.129:58080", "36.92.166.197:1080"
    # Add more proxies here
]

# URL and button XPath
url = "https://games-island.eu/Pokemon"
button_xpath = '/html/body/div[2]/main/div[1]/div[2]/div[2]/div[3]/button'

# def initialize_driver(proxy):
try:
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument(f"--proxy-server={proxy}")
    driver = uc.Chrome(options=options)
    driver.maximize_window()
except Exception as e:
    print(f"Failed to initialize driver with proxy: {e}")

def check_element(driver, xpath):
    try:
        element = driver.find_element(By.XPATH, xpath)
        return element.get_attribute("disabled") is not None
    except Exception as e:
        print(f"Error finding element: {e}")

# for proxy in proxies:
#     print(f"Trying proxy: {proxy}")
#     driver = initialize_driver(proxy)
#     if not driver:
#         continue  # Skip if driver initialization fails
    
try:
    driver.get(url)
    time.sleep(5)  # Wait for page to load
    
    if check_element(driver, button_xpath):
        time.sleep(5)  # Add delay before refreshing
        driver.refresh()
    else:
        print("The item is available!")
except Exception as e:
    print(f"Error checking proxy: {e}")
finally:
    try:
        driver.quit()
    except Exception as cleanup_error:
        print(f"Error during driver cleanup: {cleanup_error}")

print("Finished checking proxies.")
