# Selenium
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException

# Chrome Driver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd
import time
from urllib.parse import urlparse

import os
import requests

import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def download_image(image_url, image_name, download_folder):
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Extract the image name from the URL
    image_path = os.path.join(download_folder, f'{image_name}.png')

    if os.path.exists(image_path):
        logging.info(f"Image already exists: {image_name}. Using existing image.")
        return image_path  # Return existing path, but still update the DataFrame

    try:
        response = requests.get(image_url)
        response.raise_for_status()  # Raise an error for bad status codes

        # Save the image to the 'download' folder
        with open(image_path, 'wb') as image_file:
            image_file.write(response.content)
        logging.info(f"Downloaded: {image_name}")
        return image_path  # Return the path of the newly downloaded image

    except requests.exceptions.RequestException as e:
        logging.info(f"Failed to download {image_url}. Error: {e}")
        return None  # Return None if download fails


class RestaurantExtractor:

    sheet_data = []
    total_links = 0

    def __init__(self):
        self.driver_options = Options()
        self.service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service, options=self.driver_options)

    def readFile(self):
        # Specify the path to your Excel file
        file_path = '20240924pictures.xlsx'

        # Read the Excel file into a DataFrame
        df = pd.read_excel(file_path, usecols=['Address', 'Website'])  # Specify columns to read
        df.fillna('', inplace=True)

        # Add a new column for Bad Resolution
        df['Bad Resolution'] = ''

        self.sheet_data = df.values.tolist()
        self.total_links = len(self.sheet_data)
        self.df = df  # Keep a reference to the DataFrame

    def process_links(self):
        for index, row in enumerate(self.sheet_data, start=1):
            address, link, *other_columns = row  # Unpack only the expected number of columns

            if link == "":
                logging.info("skipping blank field {}".format(link))
                continue

            facebook_link = None

            if "facebook.com" in link:
                # Split the URL by 'facebook.com/' and get the part after it
                facebook_link = link.split("facebook.com/")[1]
                # Removing trailing slashes if any
                facebook_link = facebook_link.rstrip('/')

            if facebook_link:
                search_text = facebook_link
            else:
                # Normal link
                parsed_url = urlparse(link)
                search_text = parsed_url.netloc.replace('www.', '')

            self.driver.get("https://www.google.com/maps")

            logging.info("{}/{} - Processing {}".format(index, self.total_links, search_text))

            # Find the search box
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )

            search_box.send_keys(search_text)

            try:
                # Try to find the element based on the unique class name, data attribute, or other attributes
                suggestions = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "cGyruf"))
                )

                # Check if element exists
                if len(suggestions) > 0:
                    if suggestions[0].text == "Add a missing place to Google Maps.":
                        raise Exception("Add a missing place to Google Maps.")

                    logging.info("No. of Suggestions: {}".format(len(suggestions)))
                    logging.info("Suggestion Found: {}".format(suggestions[0].text))
                    # If element exists, click on it
                    suggestions[0].click()
                    logging.info("Element clicked!")

            except Exception as e:
                logging.info("No suggestions found, so searching...")
                search_box.send_keys(Keys.ENTER)

            # Wait for the results to load
            time.sleep(1)

            try:
                # XPath for the image inside the button element
                image_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@class="ZKCDEc"]//img'))
                )
                # Get the URL of the image from the 'src' attribute
                image_url = image_element.get_attribute("src")

                # Download the image and get its path
                image_path = download_image(image_url, search_text, "downloads")

                # Update the 'Bad Resolution' column with the image path
                if image_path:
                    self.df.at[index - 1, 'Bad Resolution'] = image_path  # Update the DataFrame

                # Save the updated DataFrame back to the Excel file after each iteration
                self.df.to_excel('20240924pictures_updated.xlsx', index=False)

            except Exception as e:
                with open('output.txt', 'w') as file:  # Change 'a' to 'w' to overwrite
                    file.write("Error {}: {}\n".format(search_text, e))
                logging.info(f"Main Image Not Found...")

        self.driver.quit()


if __name__ == "__main__":
    extractor = RestaurantExtractor()
    extractor.readFile()
    extractor.process_links()
