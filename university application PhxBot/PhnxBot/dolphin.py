import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

api_token = ''
class DolphinBrowser:
    def __init__(self, token = None):
        if not token:
            self.auth_token = api_token
        else:
            self.auth_token = token

        self.login_url = 'http://localhost:3001/v1.0/auth/login-with-token'

    def get_driver(self, profile_id, headless=False):
        """Initialize and return a WebDriver instance for a specific Dolphin profile"""
        max_retries = 1
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Add small random delay between profile starts
                time.sleep(random.uniform(1.0, 3.0))
                
                # Login request
                response = requests.post(
                    self.login_url,
                    json={'token': self.auth_token},
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code != 200:
                    raise Exception(f"Login failed with status code: {response.status_code}")

                # Start profile with unique debugging port
                port_offset = random.randint(0, 1000)  # Add random port offset
                if not headless:
                    start_url = f'http://localhost:3001/v1.0/browser_profiles/{profile_id}/start?automation=1&port={10000 + port_offset}'
                else:
                    start_url = f'http://localhost:3001/v1.0/browser_profiles/{profile_id}/start?automation=1&headless=1&port={10000 + port_offset}'

                response = requests.get(start_url)
                
                if response.status_code != 200:
                    raise Exception(f"Failed to start profile: {response.status_code}")

                response_json = response.json()
                if 'automation' not in response_json:
                    raise Exception("No automation data in response")

                # Get debugging port
                port = str(response_json['automation']['port'])

                # Setup Chrome options
                options = Options()
                options.debugger_address = f'127.0.0.1:{port}'

                # Common options
                options.add_argument('--start-maximized')
                options.add_argument('--disable-notifications')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--no-sandbox')
                options.add_argument('--incognito')  # Enable Incognito Mode (no cookies saved)
                options.add_argument('--disable-extensions')  # Disable Extensions
                options.add_argument('--disable-cache')  # Disable cache storage
                options.add_argument('--disable-application-cache')  # Disable application cache
                options.add_argument('--disable-offline-load-stale-cache')  # Disable offline loading

                # Headless-specific options
                if headless:
                    options.add_argument('--headless')
                    options.add_argument('--window-size=1920,1080')


                # Initialize WebDriver
                chrome_driver_path = ChromeDriverManager().install()
                driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
                return driver

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise Exception(f"Failed to initialize Dolphin browser after {max_retries} attempts: {str(e)}")


    def stop_profile(self, profile_id, driver):
        """Stop a running Dolphin profile"""
        try:
            stop_url = f'http://localhost:3001/v1.0/browser_profiles/{profile_id}/stop'
            response = requests.get(stop_url)
            # self.close_browser(driver)
            
            
            if response.status_code != 200:
                raise Exception(f"Failed to stop profile: {response.status_code}")
                
            return True
        except Exception as e:
            raise Exception(f"Failed to stop Dolphin profile: {str(e)}")
    
    def close_browser(self, driver):
        """Close the browser entirely"""
        try:
            driver.quit()
            print("Browser has been closed successfully.")
        except Exception as e:
            raise Exception(f"Failed to close the browser: {str(e)}")
        

# testing the DolphinBrowser class
if __name__ == "__main__":
    dolphin = DolphinBrowser()
    profile_id = '620600755'  # Replace with your actual profile ID
    try:
        driver = dolphin.get_driver(profile_id, headless=False)
        print("Dolphin browser started successfully.")
        
        # Example: Navigate to a website
        driver.get("https://www.google.com")
        time.sleep(5)  # Wait for a few seconds to see the page
        dolphin.stop_profile(profile_id, driver)
        time.sleep(10)  # Wait for a few seconds before stopping the profile

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        print("Dolphin profile stopped.")