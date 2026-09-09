import logging 
import time
from typing import Optional
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from dolphin import DolphinBrowser
import threading
import undetected_chromedriver as uc


class PhoenixUniversityApplicationUtils:
    _setup_lock = threading.Lock()  # Class-level lock for chromedriver setup

    def __init__(self, api_token):
        # Configure logging
        class RequestFilter(logging.Filter):
            def filter(self, record):
                # List of strings to filter out
                filtered_strings = [
                    "Capturing request:",
                    "Capturing response:",
                    "Failed to resolve address",
                    "ERROR:services\\network\\p2p\\socket_manager",
                    "downloads?name=",
                    "optimizationguide-pa",
                    "idsync.rlcdn.com",
                    "cookielaw.org",
                    "ipapi.co",
                    "GroupMarkerNotSet",
                    "WebGL",
                    "swiftshader",
                    "stun." 
                ]
                message = record.getMessage()
                return not any(s in message for s in filtered_strings)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('phoenix_application.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.addFilter(RequestFilter())  
        self.driver = None
        self.wait = None
        self.dolphin = DolphinBrowser(api_token)  # Initialize Dolphin
        self.current_profile = None  # Track current profile
        self.headless = False

    def setup(self, profile_id=None, seleniumwire_options=None):
        """Initialize WebDriver with Dolphin profile if provided"""
        try:
            if profile_id:
                self.current_profile = profile_id
                self.driver = self.dolphin.get_driver(profile_id, self.headless)
                self.wait = WebDriverWait(self.driver, 20)
            else:
                options = uc.ChromeOptions()

                # Shared flags 
                options.add_argument('--disable-notifications')
                options.add_argument('--incognito')
                options.add_argument('--disable-gpu')  
                options.add_argument('--no-sandbox')

                if self.headless:
                    options.add_argument('--headless')
                    options.add_argument('--window-size=1920,1080')  
                else:
                    options.add_argument('--start-maximized')  
                    options.add_argument('--disable-dev-shm-usage')


                with self._setup_lock:  # Ensure only one thread sets up chromedriver at a time
                    max_retries = 1
                    retry_delay = 2
                    last_error = None

                    for attempt in range(max_retries):
                        try:
                            if seleniumwire_options and seleniumwire_options.get('proxy'):
                                self.logger.info("Setting up proxy with selenium-wire")
                                proxy_url = seleniumwire_options['proxy']['http']
                                seleniumwire_options = {
                                    'proxy': {
                                        'http': proxy_url,
                                        'https': proxy_url,
                                        'verify_ssl': False
                                    },
                                    'disable_capture': True
                                }
                                self.driver = uc.Chrome(options=options, seleniumwire_options=seleniumwire_options)
                            else:
                                self.driver = uc.Chrome(options=options)

                            self.wait = WebDriverWait(self.driver, 20)
                            self.logger.info("WebDriver initialized successfully")
                            break
                        except Exception as e:
                            last_error = e
                            if "Cannot create a file when that file already exists" in str(e):
                                # Wait and retry if file conflict occurs
                                self.logger.info(f"Setup attempt {attempt + 1} failed due to file conflict, retrying...")
                                time.sleep(retry_delay)
                                continue
                            raise  # Re-raise other exceptions
                    else:
                        raise Exception(f"Failed to initialize after {max_retries} attempts: {last_error}")

        except Exception as e:
            self.logger.error(f"Failed to initialize ChromeDriver: {str(e)}")
            raise

    def wait_and_find_element(self, by, value, timeout=20):
        """Wait for element to be present and return it"""
        try:
            # Add a small delay before finding elements
            time.sleep(1.5)
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.error(f"Element not found: {value}")
            # Take screenshot on element not found
            self.driver.save_screenshot(f"element_not_found_{value}.png")
            raise

    def solve_recaptcha(self, site_key, page_url):
        try:

            self.logger.info("Submitting captcha to 2Captcha")

            API_KEY = ""  

            # Submit captcha request
            response = requests.get(
                f"http://2captcha.com/in.php?key={API_KEY}&method=userrecaptcha&googlekey={site_key}&pageurl={page_url}&json=1"
            ).json()

            if response["status"] != 1:
                raise Exception(f"Failed to send captcha to 2Captcha: {response['request']}")

            captcha_id = response["request"]
            self.logger.info(f"Captcha submitted, ID: {captcha_id}, waiting for result...")

            # Poll for result
            for i in range(20):
                time.sleep(5)
                res = requests.get(
                    f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}&json=1"
                ).json()
                if res["status"] == 1:
                    self.logger.info("Captcha solved successfully")
                    return res["request"]
                elif res["request"] != "CAPCHA_NOT_READY":
                    raise Exception(f"Captcha error: {res['request']}")
        except Exception as e:
                self.logger.error(f"Failed to solve CAPTCHA: {str(e)}")
                raise Exception("Timed out waiting for captcha solution")


    def check_captcha_presence(self):
        """Check if CAPTCHA is present on the page"""
        self.logger.info("Checking for CAPTCHA presence on the page")
        try:
            # Wait for the CAPTCHA iframe to appear
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[title*='recaptcha']"))
            )
            self.logger.info("CAPTCHA detected by title selector")
            return True
        except TimeoutException:
            # Try alternative method based on iframe src
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for frame in frames:
                src = frame.get_attribute("src")
                if src and "recaptcha" in src:
                    self.logger.info("CAPTCHA detected by iframe src")
                    return True
            self.logger.info("No CAPTCHA found on page")
            return False
        except Exception as e:
            self.logger.warning(f"Error checking for CAPTCHA: {str(e)}")
            return False

    def remove_cookie_banner(self):
        # Handle OneTrust Cookie Banner
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            self.logger.info("Accepted cookie consent.")
        except:
            self.logger.info("No cookie banner found to accept.")

        # Wait for overlay to disappear if present
        try:
            WebDriverWait(self.driver, 10).until(
                EC.invisibility_of_element_located((By.ID, "onetrust-group-container"))
            )
        except:
            self.logger.info("No overlay to wait for or already gone.")

    def fill_personal_info(self, email, first_name, last_name, address, phone, password, city, state, zipcode):
        """Fill personal information form with explicit waits"""
        try:
            # Wait for page to fully load
            time.sleep(3)
            # Scroll to top of page
            self.driver.execute_script("window.scrollTo(0, 0)")

            # Email with retry mechanism
            max_retries = 1
            for attempt in range(max_retries):
                try:
                    email_field = self.wait_and_find_element(By.ID, "email")
                    email_field.clear()
                    email_field.send_keys(email)
                    
                    # Wait for continue button to be enabled
                    continue_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "continue"))
                    )
                    
                    # Scroll button into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", continue_btn)
                    time.sleep(1)
                    
                    # Try JavaScript click if regular click fails
                    try:
                        continue_btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", continue_btn)
                    
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2)
            
            # Wait for personal info form with retry
            time.sleep(2)
            
            # Names
            first_name_field = self.wait_and_find_element(By.ID, "first_name")
            first_name_field.send_keys(first_name)
            
            last_name_field = self.wait_and_find_element(By.ID, "last_name")
            last_name_field.send_keys(last_name)
            time.sleep(3)  # Wait for name fields to be processed
            # Cookie banner 
            try:
                cookie_banner = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "onetrust-banner-sdk"))
                )
                close_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "onetrust-close-btn-handler"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", close_btn)
                close_btn.click()
                self.logger.info("Closed cookie banner before address entry.")
                time.sleep(1)
            except:
                self.logger.info("No cookie banner appeared.")
            self.remove_cookie_banner()

            # Address
            address_field = self.wait_and_find_element(By.ID, "address_line")
            address_field.send_keys(address)
            
            # Select first address suggestion
            try:
                suggestion = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "address_line-option-0"))
                )
                suggestion.click()
            except:
                self.logger.warning("No address suggestions found — filling fields manually.")
                # City
                try:
                    city_field = self.wait_and_find_element(By.ID, "city")
                    city_field.clear()
                    city_field.send_keys(city)  # variable `city` must be passed to the function
                except Exception as e:
                    self.logger.error(f"Could not fill city: {e}")

                # State - if it's a dropdown
                try:
                    state_dropdown = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "state"))  # adjust ID if needed
                    )
                    Select(state_dropdown).select_by_visible_text(state)  # pass `state` to function
                except Exception as e:
                    self.logger.warning(f"Could not fill state using dropdown: {e}")
                    self.remove_cookie_banner()                
                # Zipcode
                try:
                    zip_field = self.wait_and_find_element(By.ID, "zipcode")
                    zip_field.clear()
                    zip_field.send_keys(zipcode)  # variable `zipcode` must be passed to the function
                except Exception as e:
                    self.logger.error(f"Could not fill zipcode: {e}")
            
            # Phone
            phone_field = self.wait_and_find_element(By.ID, "phone")
            phone_field.send_keys(phone)
            self.remove_cookie_banner()
            # Password
            password_field = self.wait_and_find_element(By.ID, "password")
            password_field.send_keys(password)
            
            confirm_password = self.wait_and_find_element(By.ID, "confirm_password")
            confirm_password.send_keys(password)
            self.remove_cookie_banner()
            # Wait for next button to be clickable
            next_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "next_step"))
            )
            
            # Scroll next button into view and click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(1)
            
            try:
                next_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", next_btn)
            
            self.logger.info("Personal information filled successfully")

            time.sleep(5)
            self.remove_cookie_banner()
            #CAPTCHA logic
            if self.check_captcha_presence():
                self.logger.info("Handling CAPTCHA...")
                
                # Get CAPTCHA details
                site_key = "6Lc5tu0pAAAAAGqWqWZZQd8j2VUvPEYJOPL2c8cU"
                page_url = self.driver.current_url

                # Solve CAPTCHA
                token = self.solve_recaptcha(site_key, page_url)

                # Inject the token into the hidden textarea
                self.driver.execute_script("""
                    document.getElementById("g-recaptcha-response").style.display = "block";
                    document.getElementById("g-recaptcha-response").value = arguments[0];
                """, token)

                # Trigger callback if needed
                self.driver.execute_script("""
                    if (typeof handleReCaptchaTokenV2 === 'function') {
                        handleReCaptchaTokenV2(arguments[0]);
                    }
                """, token)

                time.sleep(10)  # Give reCAPTCHA time to process
            else:
                self.logger.info("No CAPTCHA found, proceeding with form submission")
                time.sleep(10)  # Wait for any potential animations or transitions
            # Wait for next page to load
            self.logger.info("Personal information filled successfully")

        except Exception as e:
            self.logger.error(f"Error filling personal information: {str(e)}")
            self.cleanup()
            self.driver.save_screenshot("error_filling_form.png")
            raise    
    
    def fill_additional_info(self, dob, gender, ssn):
        """Fill the additional information form"""
        try:
            # Wait for page to load after personal info submission
            self.logger.info("Waiting for additional information page to load")
            time.sleep(10)
            #  Wait until the dateOfBirth input is present and visible
            dob_field = WebDriverWait(self.driver, 60).until(
                EC.visibility_of_element_located((By.ID, "dateOfBirth"))
            )
            self.logger.info("Additional information page loaded successfully.")


            # Date of Birth
            dob_field = self.wait_and_find_element(By.ID, "dateOfBirth")
            dob_field.clear()
            dob_field.send_keys(dob)

            # Gender
            gender_dropdown = self.wait_and_find_element(By.ID, "gender")
            gender_select = Select(gender_dropdown)
            gender_select.select_by_visible_text(gender)

            # SSN
            ssn_field = self.wait_and_find_element(By.ID, "ssn")
            ssn_field.clear()
            ssn_field.send_keys(ssn)

            # Citizenship
            citizenship_yes = self.wait_and_find_element(
                By.CSS_SELECTOR,
                "#hasCitizenship-input > .MuiFormControlLabel-root:nth-child(1)"
            )
            citizenship_yes.click()

            time.sleep(2)  # Wait for the click to register
            devices = ["laptop", "tablet", "mobile"]
            for device in devices:
                try:
                    # Wait for the checkbox input by ID
                    checkbox_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, device))
                    )

                    # Get the clickable wrapper span (MuiButtonBase-root)
                    wrapper_span = checkbox_input.find_element(
                        By.XPATH, "./ancestor::span[contains(@class, 'MuiButtonBase-root')]"
                    )

                    # Scroll it into view (centered to avoid header/footer obstruction)
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", wrapper_span)
                    time.sleep(0.3)

                    # Use JavaScript click for better headless mode stability
                    self.driver.execute_script("arguments[0].click();", wrapper_span)
                    self.logger.info(f"Clicked checkbox for device: {device}")

                    time.sleep(0.5)  # Give UI time to update

                except Exception as e:
                    self.logger.warning(f"Failed to click checkbox for device '{device}': {str(e)}")
                    self.driver.save_screenshot(f"error_checkbox_device_{device}.png")



            # Scroll to "Next" button before clicking
            next_btn = self.wait_and_find_element(By.ID, "next_step")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
            time.sleep(1)
            next_btn.click()

            self.logger.info("Additional information filled successfully")

        except Exception as e:
            self.logger.error(f"Error filling additional information: {str(e)}")
            self.cleanup()
            self.driver.save_screenshot("error_additional_info.png")
            raise


    def fill_military_info(self, military_status="No"):
        """Fill military information form and ensure navigation to next page."""
        
        try:
            # Early exit if already on the next page
            try:
                if self.driver.find_element(By.ID, "degree-level-input"):
                    self.logger.info("Already on education section, skipping military info.")
                    return
            except:
                pass

            
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, "militaryServiceHeader"))
            )
            self.logger.info("Military info page loaded")

            def click_until_selected(element_id, max_retries=5):
                for attempt in range(max_retries):
                    try:
                        element = self.wait_and_find_element(By.ID, element_id)
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        self.driver.execute_script("arguments[0].click();", element)
                        time.sleep(0.5)
                        
                        # For React/Material, check aria-pressed or attribute changes
                        selected = (
                            element.is_selected()
                            or element.get_attribute("checked") == "true"
                            or element.get_attribute("aria-pressed") == "true"
                            or "Mui-checked" in element.get_attribute("class")
                        )
                        if selected:
                            self.logger.info(f"{element_id} selected on attempt {attempt+1}")
                            return True
                    except Exception as e:
                        self.logger.warning(f"Attempt {attempt+1} failed for {element_id}: {e}")
                        time.sleep(0.5)
                self.logger.warning(f"Failed to select {element_id} after {max_retries} tries.")
                return False

            if military_status.lower() == "no":
                for full_attempt in range(3):  # Retry the full logic 3 times
                    self.logger.info(f"Military info selection attempt {full_attempt+1}/3")
                    military_ok = click_until_selected("has_military_info-no")
                    dod_ok = click_until_selected("hasDodCgInfo-no")

                    # Reconfirm military 
                    military_ok = click_until_selected("has_military_info-no")

                    if military_ok and dod_ok:
                        break
                    else:
                        time.sleep(1)
                else:
                    raise Exception("Could not select both military and DoD info as 'No'")

            # Handle possible cookie banner again
            try:
                cookie_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                )
                cookie_btn.click()
                self.logger.info("Cookie banner accepted during military section")
            except:
                pass

            # Scroll and click next
            next_btn = self.wait_and_find_element(By.ID, "next_step")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
            time.sleep(0.5)

            try:
                next_btn.click()
                time.sleep(15)  # Wait for any animations
            except Exception as e:
                self.logger.warning(f"Standard click failed on Next: {e}, trying JS click.")
                self.driver.execute_script("arguments[0].click();", next_btn)

            # Verify navigation
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "degree-level-input"))
                )
                self.logger.info("Military info submitted and navigated to education section.")
            except TimeoutException:
                self.logger.warning("Still on military info page. Retrying...")
                return self.fill_military_info(military_status)

        except Exception as e:
            self.logger.error(f"Error filling military information: {str(e)}")
            self.driver.save_screenshot("error_military_info.png")
            raise


    def handle_program_requirements_popup(self):
            """Handle the program requirements popup if it appears"""
            try:
                # Check if the popup is present
                popup_container = self.driver.find_element(By.ID, "pendo-guide-container")
                
                if popup_container.is_displayed():
                    self.logger.info("Program requirements popup detected")
                    
                    # Look for the "Got it" button
                    got_it_button = self.driver.find_element(By.ID, "pendo-button-5e16740d")
                    
                    # Click the "Got it" button
                    self.driver.execute_script("arguments[0].click();", got_it_button)
                    self.logger.info("Clicked 'Got it' button on program requirements popup")
                    
                    # Wait for popup to disappear
                    time.sleep(2)
                    
                    return True
                    
            except NoSuchElementException:
                # Popup not present, continue normally
                self.logger.debug("No program requirements popup found")
                return False
            except Exception as e:
                self.logger.warning(f"Error handling popup: {str(e)}")
                return False
    
    def fill_program_info(self, degree_level, certificate_level="Undergraduate certificate", area_of_interest=None,    
                      program_name=None, start_date=None, learning_format="Online"):
        """Fill program information form with parameterized inputs"""
        try:
            # Wait for page to load
            time.sleep(15)
            self.driver.execute_script("window.scrollTo(0, 200)")

            # Select Degree Level
            degree_level_select = Select(self.wait_and_find_element(By.ID, "degree-level-input"))
            degree_level_select.select_by_visible_text(degree_level)
            time.sleep(2)  # Let dependent dropdowns load


            # Handle certificate-level if needed
            if degree_level.lower() == "certificate" and certificate_level:
                cert_select = Select(self.wait_and_find_element(By.ID, "certificate-level-input"))
                cert_select.select_by_visible_text(certificate_level)
                time.sleep(1)

            # Select Area of Interest
            if area_of_interest:
                area_select = Select(self.wait_and_find_element(By.ID, "area-of-interest-input"))
                area_select.select_by_visible_text(area_of_interest)
                time.sleep(2)  # Wait for program options to load

            # Select program by name using the table with radio buttons
            try:
                # Find the row that matches the desired program
                program_rows = self.driver.find_elements(By.XPATH, "//tr[@role='radio']")

                matched = False
                for row in program_rows:
                    program_text = row.get_attribute("data-name")
                    if program_name.lower() in program_text.lower():
                        # Click the radio input within this row
                        radio_button = row.find_element(By.XPATH, ".//input[@type='radio']")
                        self.driver.execute_script("arguments[0].click();", radio_button)
                        self.logger.info(f"Selected program: {program_text}")
                        matched = True
                        break

                if not matched:
                    self.logger.warning(f"Program not found: {program_name}")

            except Exception as e:
                self.logger.warning(f"Program selection failed: {str(e)}")


            # Select Learning Format 
            if learning_format:
                try:
                    learning_select = Select(self.wait_and_find_element(By.ID, "learning-format-input"))
                    learning_select.select_by_visible_text(learning_format)
                except Exception:
                    self.logger.warning("Learning format selection failed or not found.")

            # Select Start Date
            if start_date:
                date_select = Select(self.wait_and_find_element(By.ID, "startdate"))
                date_select.select_by_visible_text(start_date)

            # Final popup check before clicking Next
            self.handle_program_requirements_popup()

            # Click Next
            next_btn = self.wait_and_find_element(By.ID, "next_step")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(1)

            try:
                next_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", next_btn)

            self.logger.info("Program information filled successfully")

        except Exception as e:
            self.logger.error(f"Error filling program information: {str(e)}")
            self.driver.save_screenshot("error_program_info.png")
            raise

    def fill_high_school_info(self, state: str, school_name: str, city: str, month: str, year: str):
        try: 
            # Wait for the select element to be present and visible
            dropdown = self.wait.until(EC.visibility_of_element_located((By.ID, "secondaryEducation.secondaryType")))

            # Scroll to it
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown)
            time.sleep(1)

            # Try selecting "High School Diploma" with retries
            selected = False
            for attempt in range(3):
                try:
                    Select(dropdown).select_by_visible_text("High School Diploma")
                    self.logger.info("Successfully selected High School Diploma using standard Select.")
                    selected = True
                    break
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1}: Failed to select using standard Select. Retrying... {str(e)}")
                    time.sleep(1)

            # If still not selected, try using ActionChains
            if not selected:
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(dropdown).click().perform()
                    Select(dropdown).select_by_visible_text("High School Diploma")
                    self.logger.info("Successfully selected High School Diploma using ActionChains.")
                    selected = True
                except Exception as e:
                    self.logger.warning(f"ActionChains selection failed: {str(e)}")

            # If still not selected, use JavaScript to set value (if <select>)
            if not selected:
                try:
                    self.driver.execute_script("""
                        let select = arguments[0];
                        for (let i = 0; i < select.options.length; i++) {
                            if (select.options[i].text === 'High School Diploma') {
                                select.selectedIndex = i;
                                select.dispatchEvent(new Event('change'));
                                break;
                            }
                        }
                    """, dropdown)
                    self.logger.info("Successfully selected High School Diploma using JavaScript fallback.")
                except Exception as e:
                    self.logger.error(f"JavaScript selection also failed: {str(e)}")
                    raise
            
            # Set Address Type to "U.S." 
            address_type_dropdown = self.driver.find_element(By.ID, "secondaryEducation.addressType")
            Select(address_type_dropdown).select_by_visible_text("U.S.")

            # Select the state 
            state_dropdown = self.driver.find_element(By.ID, "secondaryEducation.state")
            Select(state_dropdown).select_by_visible_text(state)

            # Fill in School Name
            school_input = self.driver.find_element(By.ID, "autocomplete-secondaryEducation.institutionName")
            school_input.clear()
            school_input.send_keys(school_name)

            #select the first suggestion from the autocomplete dropdown
            try:
                suggestion = WebDriverWait(self.driver, 7).until(
                    EC.element_to_be_clickable((By.ID, "autocomplete-secondaryEducation.institutionName-option-0"))
                )
                suggestion.click()
                self.logger.info("First school suggestion selected.")
            except:
                self.logger.warning("No school suggestions found.")
                 # Fill in City
                city_input = self.driver.find_element(By.ID, "autocomplete-secondaryEducation.city")
                city_input.clear()
                city_input.send_keys(city)

          



            # Select Month of Completion 
            month_dropdown = self.driver.find_element(By.ID, "secondaryEducation.endMonth")
            Select(month_dropdown).select_by_visible_text(month)

            # Scroll to the dropdown
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                                    self.driver.find_element(By.ID, "secondaryEducation.endYear"))

            # Wait briefly for any animations to complete
            time.sleep(1)

            # Select Year of Completion
            year_dropdown = self.driver.find_element(By.ID, "secondaryEducation.endYear")
            Select(year_dropdown).select_by_visible_text(year)

            # Click the "Save and continue" button safely
            next_btn = self.wait_and_find_element(By.ID, "next_step")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
            time.sleep(1)

            try:
                # Try normal click first
                next_btn.click()
                self.logger.info("Successfully clicked 'Save and continue' button with regular click.")
            except Exception as e:
                self.logger.warning(f"Regular click failed on 'Save and continue': {str(e)}. Trying JavaScript click.")
                try:
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    self.logger.info("Successfully clicked 'Save and continue' using JavaScript.")
                except Exception as js_e:
                    self.logger.error(f"JavaScript click also failed: {str(js_e)}")
                raise
        
        except Exception as e:
            self.logger.error(f"Failed to select High School Diploma: {str(e)}")
            self.driver.save_screenshot("error_secondary_type.png")
            raise

    def fill_education_confirmation(self):
        """Fill education confirmation section by selecting 'No' for all options and clicking 'Save and continue'"""
        try:
            time.sleep(10)

            # 1. Have you taken courses at a college/university? => No
            try:
                higher_ed_no = WebDriverWait(self.driver, 30).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-cy='confirm-button-group-button-no']"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", higher_ed_no)
                time.sleep(0.5)
                try:
                    higher_ed_no.click()
                except:
                    self.driver.execute_script("arguments[0].click();", higher_ed_no)
                self.logger.info("Selected 'No' for higher education courses")
            except TimeoutException:
                self.logger.error("Timeout: Could not find the 'No' button for higher ed confirmation")
                raise

            # 2. Save and continue
            next_btn_first = self.wait_and_find_element(By.ID, "next_step")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn_first)
            time.sleep(0.5)
            try:
                next_btn_first.click()
            except:
                self.driver.execute_script("arguments[0].click();", next_btn_first)
            self.logger.info("Clicked Save and Continue after selecting 'No' for higher education courses")

            time.sleep(10)

            # 3. Have you taken tests to earn college credits? => No
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.ID, "creditsInfoConfirmation-no"))
                )

                clicked_credit_no = False
                for attempt in range(3):  # Increase attempts for robustness
                    try:
                        no_radio = WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located((By.ID, "creditsInfoConfirmation-no"))
                        )

                        # Click the PARENT label (2 levels up from input)
                        credit_label = no_radio.find_element(By.XPATH, "./ancestor::label[1]")

                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", credit_label)
                        self.driver.execute_script("window.scrollBy(0, -100);")
                        time.sleep(0.5)

                        try:
                            credit_label.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", credit_label)

                        self.logger.info("Selected 'No' for college credit tests")
                        clicked_credit_no = True
                        break

                    except TimeoutException:
                        self.logger.warning("Retrying: could not find 'No' button for credit tests")
                        time.sleep(2)

                if not clicked_credit_no:
                    raise Exception("Failed to select 'No' for college credit tests after retries.")

            except Exception as e:
                self.logger.error("Timeout: Could not find the 'No' button for college credit tests")
                self.driver.save_screenshot("missing_credits_no_button.png")
                raise
            
            # 4. Save and continue
            next_btn_second = self.wait_and_find_element(By.ID, "next_step")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn_second)
            time.sleep(0.5)
            try:
                next_btn_second.click()
            except:
                self.driver.execute_script("arguments[0].click();", next_btn_second)
            self.logger.info("Clicked Save and Continue after selecting 'No' for college credit tests")

        except Exception as e:
            self.logger.error(f"Error filling education confirmation: {str(e)}")
            raise


    def fill_work_info(self):
        try:
            # Wait for page load
            time.sleep(10)

            # 1. Select "No" for employment status
            employeed_btn = self.wait_and_find_element(
                By.CSS_SELECTOR, "[data-cy='confirm-button-group-button-no']"
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", employeed_btn)
            time.sleep(0.5)  # Small delay to ensure visibility

            try:
                employeed_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", employeed_btn)
            self.logger.info("Selected 'No' for employment status")

            # 2. Click "Save and continue" (First button)
            next_btn_first = self.wait_and_find_element(By.ID, "next_step")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn_first)
            time.sleep(0.5)

            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "next_step")))

            try:
                next_btn_first.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", next_btn_first)

            self.logger.info("Clicked 'Save and Continue' after selecting 'No' for employment status")

        except Exception as e:
            self.logger.error(f"Error filling work info: {str(e)}")
            self.driver.save_screenshot("error_work_info.png")
            raise


    def fill_financial_plan(self):
        """Handle the financial plan section"""
        try:
            # Wait for page load (maximum wait of 5 seconds)
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.ID, "federalGrantsSelection")))

            # 1. Select "I have plans to use federal grants"
            try:
                # Find the checkbox container
                federal_grants = self.wait_and_find_element(By.ID, "federalGrantsSelection")

                # Scroll to the element to ensure it's in view
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", federal_grants)

                # Wait until the element is clickable
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(federal_grants))

                # Click the element
                federal_grants.click()
                self.logger.info("Selected federal grants option")

                time.sleep(5) 
                # Scroll to the "Start estimate" button
                start_btn = self.wait_and_find_element(By.ID, "next_step")
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", start_btn)

                # Wait until it's clickable and then click the button
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(start_btn))
                start_btn.click()
                self.logger.info("Clicked Start estimate button")

            except Exception as e:
                self.logger.warning(f"Failed to select federal grants: {str(e)}")
                # Try clicking with JavaScript as a fallback
                self.driver.execute_script("arguments[0].click();", federal_grants)
                self.logger.info("Clicked federal grants option using JavaScript")
            
            # 3. Skip first step
            try:
                time.sleep(2)  # Wait for the page to load
                skip_btn = self.wait_and_find_element(By.ID, "skip_btn")

                # Scroll to the "Skip this step" button
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", skip_btn)

                # If scrollIntoView doesn't bring it to a clickable state, try scrolling to the bottom of the page
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(skip_btn))
                skip_btn.click()
                self.logger.info("Clicked first skip button")
            except Exception as e:
                self.logger.warning(f"Failed to click first skip button: {str(e)}")
                # Scroll to the bottom of the page and try again
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(skip_btn))
                skip_btn.click()
                self.logger.info("Clicked first skip button after scrolling to the bottom")

            # 4. Handle the Pop-up Dialog
            try:
                # Wait for the dialog to appear and check if the "Yes, skip this page" button is present
                dialog = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiDialog-root"))
                )

                # Scroll to the pop-up to ensure it's in view
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", dialog)

                # Find and click the "Yes, skip this page" button
                yes_btn = self.wait_and_find_element(By.ID, "skipSetpButton")
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", yes_btn)
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(yes_btn))
                yes_btn.click()
                self.logger.info("Clicked 'Yes, skip this page' button")
            except Exception as e:
                self.logger.warning(f"Failed to handle pop-up dialog: {str(e)}")

            # 5. Select 'No' and continue
            try:
                time.sleep(2)
                no_btn = self.wait_and_find_element(
                    By.CSS_SELECTOR, ".MuiButtonBase-root:nth-child(2) > .MuiToggleButton-label"
                )

                # Scroll into view (centered)
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", no_btn)
                time.sleep(0.5)

                # Slight upward scroll in case a sticky header overlaps
                self.driver.execute_script("window.scrollBy(0, -80);")

                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(no_btn))
                    no_btn.click()
                except Exception:
                    # Fallback: click using JS
                    self.driver.execute_script("arguments[0].click();", no_btn)

                self.logger.info("Selected 'No' option")
            except Exception as e:
                self.logger.warning(f"Failed to select 'No' option: {str(e)}")
                self.driver.save_screenshot("error_no_option_click.png")
                raise

            # 6. Click Save and Continue
            try:
                # Scroll into view and offset upward to avoid fixed header/footer overlap
                next_btn = self.wait_and_find_element(By.ID, "next_step")
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
                self.driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(0.5)

                # Wait for button to be clickable
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "next_step")))

                # Try to click, with JS fallback
                try:
                    next_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", next_btn)

                self.logger.info("Clicked Save and continue button")
                time.sleep(5)
                self.logger.info("Clicked Save and continue button")
                time.sleep(5)  # Wait for the next page to load
            except Exception as e:
                self.logger.warning(f"Failed to click Save and Continue button: {str(e)}")
                raise

            # 7. Handle Federal Student Loan radio button and continue
            try:
                # Wait for the radio input to appear (ensures the group is loaded)
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.ID, "federalStudentLoanWillApply-input"))
                )

                # Wait for the 'No' label to be clickable
                no_radio_label = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//label[@data-radio='No']"))
                )

                # Scroll into view and offset upward slightly (prevent header overlap)
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", no_radio_label)
                self.driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(0.5)

                no_radio_label.click()
                self.logger.info("Selected 'No' for federal student loan application")

                # Click Save and Continue
                next_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "next_step"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
                self.driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(0.5)

                try:
                    next_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", next_btn)

                self.logger.info("Clicked Save and continue after federal student loan selection")
                time.sleep(5)

            except Exception as e:
                self.logger.warning(f"Failed to handle federal student loan selection: {str(e)}")
                self.driver.save_screenshot("error_federal_loan.png")
                raise


            time.sleep(20)  # Wait for the next page to load
            # 8. Click Save and Continue (final step)
            try:
                next_btn = self.wait_and_find_element(By.ID, "next_step")

                # Scroll into view and adjust to prevent overlaps
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                self.driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(0.5)

                # Wait until it's enabled and not disabled
                WebDriverWait(self.driver, 10).until(lambda d: (
                    next_btn.is_displayed() and
                    next_btn.is_enabled() and
                    "Mui-disabled" not in next_btn.get_attribute("class")
                ))

                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "next_step")))
                    next_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", next_btn)

                self.logger.info("Clicked final 'Save and continue' button")
                time.sleep(5)

            except Exception as e:
                self.logger.warning(f"Failed to click final 'Save and continue': {e}")
                self.driver.save_screenshot("error_final_continue.png")
                raise

        except Exception as e:
            self.logger.error(f"Error filling financial plan: {str(e)}")
            self.driver.save_screenshot("error_financial_plan.png")
            raise

    def close_other_tabs_except_current(self):
        """Close all browser tabs except the currently active one."""
        try:
            current_handle = self.driver.current_window_handle
            all_handles = self.driver.window_handles

            self.logger.info(f"Closing {len(all_handles) - 1} other tab(s).")

            for handle in all_handles:
                if handle != current_handle:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
                    self.logger.info(f"Closed tab: {handle}")

            # Switch back to the original tab (if needed)
            self.driver.switch_to.window(current_handle)
            self.logger.info(f"Switched back to main tab: {current_handle}")

        except Exception as e:
            self.logger.error(f"Failed to close other tabs: {str(e)}")
            self.driver.save_screenshot("close_other_tabs_error.png")
            raise
    
    def open_profile_info(self):
        """Open the profile information page in a new tab"""
        try:
            # Get current window handles before opening new tab
            original_tabs = self.driver.window_handles
            self.logger.info(f"Current tab count: {len(original_tabs)}")

            # Use JavaScript to open new tab
            self.driver.switch_to.new_window('tab')
            self.driver.get("https://my.phoenix.edu/profile")
            self.logger.info("Opened profile information page in a new tab")    
            
            # Wait for new tab to appear (up to 10 seconds)
            WebDriverWait(self.driver, 10).until(
                lambda driver: len(driver.window_handles) > len(original_tabs)
            )
            
            # Get all current tabs and find the new one
            all_tabs = self.driver.window_handles
            new_tab = [tab for tab in all_tabs if tab not in original_tabs][0]
            
            # Switch to the new tab
            self.driver.switch_to.window(new_tab)
            self.logger.info(f"Successfully switched to new tab. Total tabs: {len(all_tabs)}")
            
            # Wait for page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self.logger.info("Profile page loaded successfully")

        except TimeoutException:
            self.logger.error("Timeout waiting for new tab or page to load")
            self.driver.save_screenshot("new_tab_timeout.png")
            raise
        except Exception as e:
            self.logger.error(f"Failed to open profile in new tab: {str(e)}")
            self.driver.save_screenshot("new_tab_error.png")
            raise

    def switch_to_first_tab(self):
        """Switch focus to the first (original) browser tab."""
        try:
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.logger.info("Switched to the first tab.")
        except Exception as e:
            self.logger.error(f"Failed to switch to the first tab: {str(e)}")
            raise

    def switch_to_second_tab(self):
        """Switch focus to the second tab (typically the newly opened one)."""
        try:
            if len(self.driver.window_handles) < 2:
                raise Exception("Second tab is not open.")
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.logger.info("Switched to the second tab.")
        except Exception as e:
            self.logger.error(f"Failed to switch to the second tab: {str(e)}")
            raise
    
    def edit_email_address(self, new_domain: str):
        """
        Edits the personal email address, replacing the domain with the provided one.
        Example: new_domain='phnxsys.xyz' → email becomes something@phnxsys.xyz
        """
        try:
            time.sleep(15)  # Wait for page to load

            # Step 1: Wait for and scroll to the Edit button
            edit_btn = self.wait.until(EC.presence_of_element_located((By.ID, "email-section")))
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", edit_btn)
            self.driver.execute_script("window.scrollBy(0, -100);")  # adjust for sticky header
            time.sleep(1)

            # Optional: Wait for overlay to disappear if it exists
            try:
                WebDriverWait(self.driver, 5).until_not(
                    EC.presence_of_element_located((By.CLASS_NAME, "css-rgffns"))
                )
            except:
                self.logger.warning("Overlay did not disappear. Proceeding anyway.")

            # Try to click the edit button
            try:
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "email-section")))
                edit_btn.click()
            except Exception:
                self.logger.warning("Standard click failed. Trying JavaScript click.")
                self.driver.execute_script("arguments[0].click();", edit_btn)

            self.logger.info("Clicked edit email button.")

            # Step 2: Wait for input field
            input_field = self.wait.until(EC.presence_of_element_located((By.ID, "Personal email address")))
            current_email = input_field.get_attribute("value")
            self.logger.info(f"Current email: {current_email}")

            if '@' not in current_email:
                raise ValueError("Current email is malformed or missing '@'")

            local_part = current_email.split('@')[0]
            new_email = f"{local_part}@{new_domain}"
            self.logger.info(f"Updating email to: {new_email}")

            # Step 3: Clear and type new email
            input_field.clear()
            input_field.send_keys(Keys.CONTROL + "a")
            input_field.send_keys(Keys.BACKSPACE)
            input_field.send_keys(new_email)

            # Step 4: Click Save button
            save_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='save']")))
            save_btn.click()
            self.logger.info("Email updated and save button clicked.")

        except Exception as e:
            self.logger.error(f"Error editing email: {str(e)}")
            self.driver.save_screenshot("error_edit_email.png")
            raise

    def refresh_page(self, max_retries=3, timeout=20):
        """Refresh the current page and wait for it to load completely."""
        try:
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"Refreshing page (attempt {attempt + 1}/{max_retries})")
                    self.driver.refresh()
                    time.sleep(10)  # Allow time for the refresh to start
                    # Wait for page load
                    WebDriverWait(self.driver, timeout).until(
                        lambda driver: driver.execute_script('return document.readyState') == 'complete'
                    )
                    
                    # Additional wait for any dynamic content
                    time.sleep(2)
                    
                    # Verify page loaded successfully
                    if "error" not in self.driver.title.lower():
                        self.logger.info("Page refreshed successfully")
                        return True
                    
                except Exception as e:
                    self.logger.warning(f"Refresh attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2)
            
            return False

        except Exception as e:
            self.logger.error(f"Failed to refresh page: {str(e)}")
            self.close_other_tabs_except_current()

            self.driver.save_screenshot("refresh_error.png")
            raise
    
    def refresh_signpage(self, max_retries=3, timeout=20):
        """Refresh the current page and wait for it to load completely."""
        try:
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"Refreshing page (attempt {attempt + 1}/{max_retries})")

                    self.driver.refresh()
                    time.sleep(10)  # Let the page start loading

                    # Simulate "stop" if it's hanging
                    if attempt > 0:
                        self.logger.info("Attempting to stop hung load before reloading again...")
                        self.driver.execute_script("window.stop();")
                        time.sleep(2)
                        self.driver.refresh()
                        self.logger.info("Triggered manual reload after stopping hung state.")
                        time.sleep(10)

                    # Wait until page load is complete
                    WebDriverWait(self.driver, timeout).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )

                    # Additional buffer
                    time.sleep(2)

                    # Check if title has any error pattern
                    if "error" not in self.driver.title.lower():
                        self.logger.info("Page refreshed successfully")
                        return True

                except Exception as e:
                    self.logger.warning(f"Refresh attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2)

            return False

        except Exception as e:
            self.logger.error(f"Failed to refresh page: {str(e)}")
            self.close_other_tabs_except_current()
            self.driver.save_screenshot("refresh_error.png")
            raise

    def review_section(self, timeout=5):
        """
        Click the 'Save and continue' button in the review section and completes it.
        """
        try:
            time.sleep(15)  # Wait for the page to load
            # Find the button element
            next_btn = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, "next_step"))
            )

            # Scroll to the button smoothly and center it in the viewport
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn
            )
            time.sleep(2)  # Give time for scroll animation (optional)

            # Wait until the button is clickable
            WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(next_btn))

            # Click the button
            next_btn.click()

            self.logger.info("Clicked 'Save and continue' button")
            time.sleep(5)  # Wait for page transition/load (adjust if needed)

            # Step 0: Click the "View Agreements & Guides" button to open the modal
            view_btn = WebDriverWait(self.driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'View Agreements & Guides')]]"))
            )

        except Exception as e:
            self.logger.warning(f"Failed to click 'Save and continue' button: {e}")
            self.close_other_tabs_except_current()
            raise

    def acknowledge_fill(self):
        try:
            # Step 0: Click the "View Agreements & Guides" button to open the modal
            view_btn = WebDriverWait(self.driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'View Agreements & Guides')]]"))
            )
            view_btn.click()
            self.logger.info("Clicked 'View Agreements & Guides' button")

            # Step 1: Wait for modal to appear and scrollable element to be visible
            scrollable_modal = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "document-page"))  
            )

            # Step 2: Scroll to the bottom
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_modal)
            time.sleep(1)

            pos = self.driver.execute_script("return arguments[0].scrollTop", scrollable_modal)
            height = self.driver.execute_script("return arguments[0].scrollHeight", scrollable_modal)
            self.logger.info(f"Scrolled to: {pos} / {height}")

            # Step 3: Click "Return to review and sign"
            return_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Return to review and sign')]"))
            )
            try:
                return_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", return_btn)
            self.logger.info("Clicked 'Return to review and sign'")

            # Step 4: Wait for checkboxes to appear and click the wrapper spans instead of <input>
            checkbox_ids = ["e-sign-checkbox", "program-admission-requirements", "agreements"]
            for cb_id in checkbox_ids:
                try:
                    # Locate the input element first
                    input_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, cb_id))
                    )

                    # Check if input is already checked (via attribute or property)
                    is_checked = input_elem.get_attribute("checked") or input_elem.is_selected()
                    if is_checked:
                        self.logger.info(f"Checkbox with ID '{cb_id}' is already checked. Skipping.")
                        continue

                    # If not checked, click the nearest clickable span
                    clickable_span = input_elem.find_element(By.XPATH, "./ancestor::span[contains(@class, 'MuiButtonBase-root')]")
                    self.driver.execute_script("arguments[0].click();", clickable_span)
                    self.logger.info(f"Clicked checkbox wrapper for ID: {cb_id}")

                except Exception as e:
                    self.logger.error(f"Failed to click checkbox {cb_id}: {str(e)}")
                    self.driver.save_screenshot(f"error_checkbox_{cb_id}.png")
                    raise

            # Step 5: Click "Save and continue to next step"
            next_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "next_step"))
            )
            try:
                next_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", next_btn)
            self.logger.info("Clicked 'Save and continue to next step'")
            time.sleep(10)  # Wait for the next page to load

        except Exception as e:
            self.logger.error(f"Verification asked")
            self.logger.error(f"Error during acknowledge fill: {str(e)}")
            self.close_other_tabs_except_current()
            self.driver.save_screenshot("error_acknowledge_fill.png")
            raise

    def sign_application(self, first_name: str, last_name: str):
        try:
            time.sleep(3)  # Wait for the page to load
            # Step 0: Click the "View Agreements & Guides" button to open the modal
            view_btn = WebDriverWait(self.driver, 200).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Review forms')]]"))
            )
            view_btn.click()
            self.logger.info("Clicked 'Review Forms' button")

            # Step 1: Wait for modal to appear and scrollable element to be visible
            scrollable_modal = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "document-page"))  
            )

            # Step 2: Scroll to the bottom
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_modal)
            time.sleep(1)

            pos = self.driver.execute_script("return arguments[0].scrollTop", scrollable_modal)
            height = self.driver.execute_script("return arguments[0].scrollHeight", scrollable_modal)
            self.logger.info(f"Scrolled to: {pos} / {height}")

            # Step 3: Click "Return to review and sign"
            return_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Return to sign')]"))
            )
            try:
                return_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", return_btn)
            self.logger.info("Clicked 'Return to sign'")

            time.sleep(2)  # Wait for the page to load

            first_name_field = self.wait_and_find_element(By.ID, "first-name")
            first_name_field.send_keys(first_name)

            last_name_field = self.wait_and_find_element(By.ID, "last-name")
            last_name_field.send_keys(last_name)

        except Exception as e:
            self.logger.error(f"Error during acknowledge fill: {str(e)}")
            self.close_other_tabs_except_current()
            self.driver.save_screenshot("error_acknowledge_fill.png")
            raise

    def submit_application(self):
        """Submit the application by clicking the final submit button."""
        try:
            # Step 5: Click "Save and continue to next step"
            next_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "next_step"))
            )
            try:
                self.safe_click(next_btn, "'Save and continue to next step'")
            except Exception:
                self.driver.execute_script("arguments[0].click();", next_btn)
            self.logger.info("Clicked 'submit applicaion' button")
            time.sleep(10)  # Wait for the next page to load
        except Exception as e:
            self.logger.error(f"Error during application submission: {str(e)}")
            self.driver.save_screenshot("error_submit_application.png")
            raise

    def update_loan(self):
        """Handle the financial plan section"""
        try:
            self.switch_to_second_tab()  # Switch to the second tab (tab2)

            # Track current tabs before opening the new one
            original_tabs = self.driver.window_handles
            current_tab = self.driver.current_window_handle  # tab2
            self.logger.info(f"Tab count before opening new: {len(original_tabs)}")

            # Open new tab (tab3)
            self.driver.switch_to.new_window('tab')
            self.driver.get("https://www.phoenix.edu/application/admissions/financial/loan")
            self.logger.info("Opened Loan information page in a new tab")

            # Wait for new tab to appear and identify it
            WebDriverWait(self.driver, 10).until(
                lambda driver: len(driver.window_handles) > len(original_tabs)
            )
            new_tabs = self.driver.window_handles
            new_tab = [tab for tab in new_tabs if tab not in original_tabs][0]

            # Switch to the new tab (tab3)
            self.driver.switch_to.window(new_tab)
            self.logger.info(f"Switched to new tab (tab3): {new_tab}")

            # Wait for content (adjust the locator as needed)
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self.logger.info("Loan page loaded in new tab")

            # Handle Federal Student Loan radio button and continue
            try:
                # Wait for the radio group to load fully
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.ID, "federalStudentLoanWillApply-input"))
                )

                # Wait for the 'Yes' label to be clickable
                yes_radio_label = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//label[@data-radio='Yes']"))
                )

                # Scroll into view and offset to avoid header/nav interference
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", yes_radio_label)
                self.driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(0.5)

                # Click "Yes"
                try:
                    yes_radio_label.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", yes_radio_label)
                self.logger.info("Selected 'Yes' for federal student loan application")

                # Click Save and Continue
                next_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "next_step"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
                self.driver.execute_script("window.scrollBy(0, -100);")
                time.sleep(0.5)

                try:
                    next_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", next_btn)

                self.logger.info("Clicked Save and continue after federal student loan selection")
                time.sleep(5)

            except Exception as e:
                self.logger.warning(f"Failed to handle federal student loan selection: {str(e)}")
                self.driver.save_screenshot("error_federal_loan_yes.png")
                raise
            
            time.sleep(3.25)  # Wait for the page to process

            # Wait for the dialog and click "Got it"
            try:
                got_it_btn = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@id='next_step' and .//span[text()='Got it']]"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", got_it_btn)
                got_it_btn.click()
                self.logger.info("Clicked 'Got it' button in the financial plan dialog")

            except Exception as e:
                self.logger.warning(f"Got it modal not found or not clickable: {str(e)}")
                self.driver.save_screenshot("got_it_click_failed.png")

            time.sleep(5)  # Wait for the page to process
            
            
            # Click Save and Continue (final step)
            try:
                # Wait for the button to be present
                next_btn = self.wait_and_find_element(By.ID, "next_step")
                
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)

                # Wait until the button becomes enabled (not 'aria-disabled' or 'Mui-disabled')
                WebDriverWait(self.driver, 10).until(lambda d: (
                    next_btn.is_displayed() and 
                    next_btn.is_enabled() and 
                    "Mui-disabled" not in next_btn.get_attribute("class")
                ))

                # Make sure nothing is overlapping
                self.driver.execute_script("window.scrollBy(0, -100);")  # scroll slightly above if nav is fixed

                # Try clicking normally first
                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "next_step")))
                    next_btn.click()
                except Exception:
                    # Fallback: JavaScript click in case of overlay
                    self.driver.execute_script("arguments[0].click();", next_btn)

                self.logger.info("Clicked final 'Save and continue' button")
            except Exception as e:
                self.logger.warning(f"Failed to click final 'Save and continue': {e}")
                raise           # 8. Click Save and Continue (final step)
            
            
            # Close tab3
            self.driver.close()
            self.logger.info("Closed new tab (tab3)")

            # Switch back to tab2
            self.driver.switch_to.window(current_tab)
            self.logger.info(f"Switched back to previous tab (tab2): {current_tab}")

        except TimeoutException:
            self.logger.error("Timeout while handling update_loan tab")
            self.close_other_tabs_except_current()
            self.driver.save_screenshot("update_loan_timeout.png")
            raise
        except Exception as e:
            self.logger.error(f"Failed in update_loan: {str(e)}")
            self.close_other_tabs_except_current()
            self.driver.save_screenshot("update_loan_error.png")
            raise

    def action_items(self, demograph):# ye main hai
        """Handle action items section"""
        try:
            # Wait for the "Start" button to be clickable and click it
            start_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.ID, "goToActionItems"))
            )
            start_button.click()
            self.logger.info("Clicked 'Start' button on action items page")

            self.complete_optional_action_items(demograph)  # Handle optional action items

        except Exception as e:
            self.logger.error(f"Error handling action items: {str(e)}")
            self.close_other_tabs_except_current()
            self.driver.save_screenshot("error_action_items.png")
            raise
    
    def complete_optional_action_items(self, demograph):
        """Expand optional action items, mark all of them as completed, and extract the link from second last item"""
        try:
            #  Step 1: Expand  dropdowns 
            expand_buttons = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'MuiAccordionSummary-expandIcon')]"))
            )
            if len(expand_buttons) < 6:
                raise Exception("Not enough dropdowns found")

            for i in range(4):
                section_button = expand_buttons[i]

                # Expand section
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", section_button)
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, "(//div[contains(@class, 'MuiAccordionSummary-expandIcon')])[" + str(i+1) + "]")))
                self.safe_click(section_button, f"expand optional section #{i + 1}")
                time.sleep(1)

                # Find section container for scoped checkbox search
                container = section_button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'MuiAccordion-root')]")

                # Mark checkbox inside expanded section
                self._mark_checkbox_by_label("Mark as completed", within_element=container)
                time.sleep(1)

                # Collapse the section by clicking the same button again
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", section_button)
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(section_button))
                self.safe_click(section_button, f"collapse optional section #{i + 1}")
                time.sleep(1)


            last_section_button = expand_buttons[5]
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", last_section_button)
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(last_section_button))
            self.safe_click(last_section_button, "expand last optional section")
            self.logger.info("Expanded last optional action item")
            time.sleep(1)

            container = last_section_button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'MuiAccordion-root')]")
            self._mark_checkbox_by_label("Mark as completed", within_element=container)

            # Optional: collapse last section
            self.safe_click(last_section_button, "collapse last optional section")


            # Step 4: Get link from 'Provide your info' button 
            provide_info_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@aria-label, 'Provide your info')]"))
            )
            href = provide_info_button.get_attribute("href")
            self.logger.info(f"Extracted link from 'Provide your info': {href}")

            link =  href
            self.logger.info(f"Link extracted: {link}")
            self.fill_demograhics(link, demograph)

        except Exception as e:
            self.logger.error(f"Failed to complete optional action items: {str(e)}")
            self.close_other_tabs_except_current()
            self.driver.save_screenshot("optional_items_error.png")
            raise



    # helper function to reuse checkbox logic
    def _mark_checkbox_by_label(self, label_text, within_element=None):
        try:
            if within_element:
                checkbox_input = WebDriverWait(within_element, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH, f".//label[contains(., '{label_text}')]//input[@type='checkbox']"
                    ))
                )
            else:
                checkbox_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH, f"//label[contains(., '{label_text}')]//input[@type='checkbox']"
                    ))
                )

            wrapper_span = checkbox_input.find_element(
                By.XPATH, "./ancestor::span[contains(@class, 'MuiButtonBase-root')]"
            )
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", wrapper_span)
            self.safe_click(wrapper_span, f"checkbox labeled '{label_text}'")
            self.logger.info(f"Clicked checkbox labeled '{label_text}'")
            time.sleep(2)
        except Exception as e:
            self.logger.error(f"Failed to click checkbox labeled '{label_text}': {str(e)}")
    # helper function 
    def safe_click(self, element, description="element"):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            self.driver.execute_script("window.scrollBy(0, -100);")  # adjust for sticky header
            WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(element))
            element.click()
            self.logger.info(f"Clicked {description} using normal click.")
        except Exception:
            self.logger.warning(f"Normal click failed for {description}. Trying JavaScript click.")
            self.driver.execute_script("arguments[0].click();", element)
            self.logger.info(f"Clicked {description} using JS fallback.")
    
    
    def fill_demograhics(self, link, demograph):
        try:
            # Track current tabs before opening the new one
            original_tabs = self.driver.window_handles
            current_tab = self.driver.current_window_handle  # tab1
            self.logger.info(f"Tab count before opening new: {len(original_tabs)}")

            # Open new tab (tab3)
            self.driver.switch_to.new_window('tab')
            self.driver.get(link)
            self.logger.info("Opened  demographics information page in a new tab")

            # Wait for new tab to appear and identify it
            WebDriverWait(self.driver, 10).until(
                lambda driver: len(driver.window_handles) > len(original_tabs)
            )
            new_tabs = self.driver.window_handles
            new_tab = [tab for tab in new_tabs if tab not in original_tabs][0]

            # Switch to the new tab (tab3)
            self.driver.switch_to.window(new_tab)
            self.logger.info(f"Switched to new tab (tab3): {new_tab}")
            time.sleep(5)  # Wait for the page to load

            # Wait for content (adjust the locator as needed)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self.logger.info("demographics page loaded in new tab")

            #check the  box
            self._mark_checkbox_by_label(demograph)
            self.logger.info("Checked the proper checkbox")

            try:
                save_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Save and return']"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", save_btn)
                self.safe_click(save_btn, "'Save and return' button")
                self.logger.info("Clicked 'Save and return' button.")
                time.sleep(2)  
            except Exception as e:
                self.logger.error(f"Failed to click 'Save and return' button: {str(e)}")



        except TimeoutException:
            self.logger.error("Timeout while handling demographics page")
            self.driver.save_screenshot("update_loan_timeout.png")
            raise
        except Exception as e:
            self.logger.error(f"Failed in demographics page: {str(e)}")
            self.close_other_tabs_except_current()
            self.driver.save_screenshot("demographics page.png")
            raise
    

    def cleanup(self):
        """Clean up resources and close browser"""
        try:
            if self.driver:
                if self.current_profile:
                    # Stop the Dolphin profile
                    self.close_other_tabs_except_current()
                    self.dolphin.stop_profile(self.current_profile, self.driver)
                    self.dolphin.close_browser(self.driver)
                    self.current_profile = None
                    self.logger.info("WebDriver closed successfully")
                else:
                    self.driver.quit()
                    self.logger.info("WebDriver closed successfully")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
