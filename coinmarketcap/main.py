import time
import undetected_chromedriver as uc
import pandas as pd
import requests
import cv2
import numpy as np
import base64
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from io import BytesIO
import re

# Load credentials
excel_file = 'credentials.xlsx'
df = pd.read_excel(excel_file)

options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")  # Makes Selenium less detectable
options.add_argument("--user-data-dir=C:\\Users\\resea\\AppData\\Local\\Google\\Chrome\\Profile 3")  # Use a real user profile
options.add_argument("--start-maximized")  # Open in full-screen
options.add_argument("--disable-popup-blocking")  # Allow popups

# Start driver with these settings
driver = uc.Chrome(options=options, use_subprocess=True)

# 2Captcha API Key
TWO_CAPTCHA_API_KEY = ""

def download_and_split_image(image_url):
    """Downloads the CAPTCHA image and splits it into 9 equal parts."""
    
    print(f"🔗 Attempting to download CAPTCHA image from: {image_url}")  

    # Step 1: Download Image
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to download CAPTCHA image. Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error downloading CAPTCHA image: {e}")
        return None

    # Step 2: Convert Image Data
    image_data = np.asarray(bytearray(response.content), dtype=np.uint8)
    image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

    if image is None:
        print("❌ Error: Could not decode CAPTCHA image. The file might be corrupted.")
        return None

    # Save the original image for debugging
    cv2.imwrite("captcha_image.png", image)
    print("✅ CAPTCHA image saved as captcha_image.png for verification.")

    # Step 3: Get Image Dimensions and Split into 9 Parts
    height, width = image.shape[:2]
    if height % 3 != 0 or width % 3 != 0:
        print(f"⚠ Warning: Image dimensions ({width}x{height}) are not perfectly divisible by 3.")
    
    cell_h, cell_w = height // 3, width // 3

    images = []
    padding = 50  # Adjust padding as needed

    for i in range(3):  # Rows
        for j in range(3):  # Columns
            # Extract each cell
            cell = image[i * cell_h : (i + 1) * cell_h, j * cell_w : (j + 1) * cell_w]

            # Add padding (white border)
            cell_padded = cv2.copyMakeBorder(cell, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=[255, 255, 255])

            # Save each cell for debugging
            cell_filename = f"captcha_part_{i}_{j}.png"
            cv2.imwrite(cell_filename, cell_padded, [cv2.IMWRITE_PNG_COMPRESSION, 0])  # No compression to increase size

            # Convert to PIL Image for better handling
            pil_img = Image.fromarray(cv2.cvtColor(cell_padded, cv2.COLOR_BGR2RGB))
            
            # Save to BytesIO with high quality
            buffer = BytesIO()
            pil_img.save(buffer, format="PNG", quality=100)
            img_bytes = buffer.getvalue()
            
            # Encode to base64 - this is what 2Captcha expects
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Validate image size
            if len(img_bytes) > 100:
                images.append({
                    "image": img_base64,
                    "position": i * 3 + j  # Store position for later reference
                })
                print(f"📷 Image ({i},{j}) processed successfully (Size: {len(img_bytes)} bytes)")
            else:
                print(f"❌ Warning: Image ({i},{j}) is too small (Size: {len(img_bytes)} bytes)")

    # Final Validation
    if len(images) != 9:
        print(f"❌ Error: Only {len(images)} images extracted instead of 9.")
        return None

    print("✅ Successfully processed all 9 images.")
    return images

# def solve_captcha_with_2captcha(images, selection_criteria):
    """
    Solves the CAPTCHA using 2Captcha's image recognition service.
    
    Args:
        images: List of image data
        selection_criteria: Text describing what to select (e.g., "Select all images with pandas")
        
    Returns:
        List of indices (0-8) of images that match the criteria
    """
    if not images or len(images) != 9:
        print("❌ Error: No valid images to send to 2Captcha.")
        return []

    print(f"🔍 Sending CAPTCHA to 2Captcha for solving with criteria: '{selection_criteria}'")
    
    # For 2Captcha's GridCaptcha, we need to send the full image
    try:
        # Read the full captcha image
        with open("captcha_image.png", "rb") as img_file:
            img_bytes = img_file.read()
            
        # Convert to base64 for API submission
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # Check image size
        print(f"📊 Full CAPTCHA image size: {len(img_bytes)} bytes")
        
        if len(img_bytes) < 100:
            print("❌ Error: CAPTCHA image is too small for 2Captcha (less than 100 bytes)")
            return []
            
        # Prepare the 2Captcha payload for grid captcha
        payload = {
            'key': TWO_CAPTCHA_API_KEY,
            'method': 'post',
            'json': 1,
            'soft_id': '3359',  # Optional software ID
        }
        
        # For grid captcha, we use multipart/form-data
        files = {
            'file': ('captcha.png', img_bytes, 'image/png'),
            'method': (None, 'post'),
            'key': (None, TWO_CAPTCHA_API_KEY),
            'textinstructions': (None, selection_criteria),
            'json': (None, '1')
        }
        
        # Send the request to 2Captcha
        print("📤 Sending CAPTCHA to 2Captcha...")
        response = requests.post('https://2captcha.com/in.php', files=files)
        print(f"📥 2Captcha response: {response.text}")
        
        # Parse the response
        try:
            result = response.json()
        except json.JSONDecodeError:
            print(f"❌ Error: Invalid JSON response from 2Captcha: {response.text}")
            return []
            
        if result.get('status') != 1:
            print(f"❌ Error from 2Captcha: {result.get('request')}")
            return []
            
        # Get the captcha ID
        captcha_id = result.get('request')
        print(f"✅ CAPTCHA submitted successfully. ID: {captcha_id}")
        
        # Poll for the result
        for attempt in range(1, 31):  # Try for up to 30 attempts (150 seconds)
            print(f"⏳ Waiting for 2Captcha result (attempt {attempt}/30)...")
            time.sleep(5)  # Wait 5 seconds between polls
            
            # Check if the CAPTCHA is solved
            result_url = f"https://2captcha.com/res.php?key={TWO_CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1"
            result_response = requests.get(result_url)
            
            try:
                result_data = result_response.json()
            except json.JSONDecodeError:
                print(f"❌ Error: Invalid JSON in result response: {result_response.text}")
                continue
                
            if result_data.get('status') == 1:
                # CAPTCHA solved!
                solution = result_data.get('request')
                print(f"✅ 2Captcha solution received: {solution}")
                
                # Parse the solution - for 2Captcha, the solution format depends on the captcha type
                try:
                    return [int(d) for d in str(solution) if d.isdigit()]
                    # Check if the solution is a single number (indicating which images to select)
                    # if solution.isdigit():
                    #     print(f"📊 Solution is a digit string: {solution}")
                    #     selected_indices = []
                        
                    #     # Each digit in the solution represents a position (1-9)
                    #     # We need to convert to 0-based indices (0-8)
                    #     for digit in solution:
                    #         if digit.isdigit() and '1' <= digit <= '9':
                    #             # Convert from 1-9 to 0-8
                    #             index = int(digit) - 1
                    #             selected_indices.append(index)
                        
                    #     print(f" Selected indices: {selected_indices}")
                    #     return selected_indices
                    
                    # # If it's not a digit string, try parsing as coordinates
                    # else:
                    #     coordinates = [float(coord) for coord in solution.split(',')]
                        
                    #     # Get the dimensions of the original image
                    #     img = cv2.imread("captcha_image.png")
                    #     height, width = img.shape[:2]
                    #     cell_h, cell_w = height // 3, width // 3
                        
                    #     # Convert coordinates to grid indices
                    #     selected_indices = []
                    #     for i in range(0, len(coordinates), 2):
                    #         if i + 1 < len(coordinates):
                    #             x, y = coordinates[i], coordinates[i+1]
                                
                    #             # Calculate which cell this coordinate falls into
                    #             col = min(int(x / cell_w), 2)
                    #             row = min(int(y / cell_h), 2)
                                
                    #             # Convert to index (0-8)
                    #             index = row * 3 + col
                    #             if index not in selected_indices:
                    #                 selected_indices.append(index)
                        
                    #     print(f"🎯 Selected indices: {selected_indices}")
                    #     return selected_indices
                    
                except Exception as e:
                    print(f"❌ Error parsing 2Captcha solution: {e}")
                    print(f"❌ Solution was: {solution}")
                    # If all else fails, try to interpret the solution directly
                    try:
                        if solution.isdigit():
                            # If the solution is a single number like "1369", each digit represents a position
                            selected_indices = []
                            for char in solution:
                                if char.isdigit() and '1' <= char <= '9':
                                    # Convert from 1-9 to 0-8
                                    index = int(char) - 1
                                    selected_indices.append(index)
                            
                            print(f"🎯 Fallback selected indices: {selected_indices}")
                            return selected_indices
                    except Exception as nested_e:
                        print(f"❌ Fallback parsing also failed: {nested_e}")
                    
                    return []
            
            elif result_data.get('request') == 'CAPCHA_NOT_READY':
                # Still waiting
                continue
            else:
                # Error
                print(f"❌ Error from 2Captcha: {result_data.get('request')}")
                if attempt > 20:  # Give up after 20 attempts
                    break
        
        print("❌ Timed out waiting for 2Captcha solution")
        return []
        
    except Exception as e:
        print(f"❌ Error in solve_captcha_with_2captcha: {e}")
        return []

def solve_captcha_with_2captcha(images, selection_criteria, max_retries=3):
    """
    Solves the CAPTCHA using 2Captcha's image recognition service with retry logic.
    Now with improved error handling for server errors and fallback options.
    """
    url = "http://2captcha.com/in.php"
    payload = {
        "key": TWO_CAPTCHA_API_KEY,
        "method": "grid",
        "rows": 3,
        "cols": 3,
        "textinstructions": selection_criteria,
        "coordinatescaptcha": 1,
        "numeric": 1,  # Enforce numeric answer (strict digit-based)
        "lang": "en",  # Ensure English-based interpretation
        "min_len": 1,  # Adjust min_len according to the expected answer
        "max_len": 9,  # Adjust max_len based on expected length
        "visual": 1,  # Enable AI-Solver Mode
        "json": 1
    }
    
    # Prepare files for upload
    files = {}
    for i, img in enumerate(images):
        try:
            img_data = base64.b64decode(img["image"])
            files[f"file[{i}]"] = (f"image_{i}.png", img_data)
        except Exception as e:
            print(f"❌ Error preparing image {i} for upload: {e}")
            return None
    
    for attempt in range(max_retries):
        try:
            # Submit CAPTCHA
            print(f"🔄 Attempt {attempt + 1}: Submitting CAPTCHA to 2Captcha...")
            
            # Set a longer timeout for the request
            response = requests.post(url, data=payload, files=files, timeout=30)
            
            print(response)
            
            # Check for HTTP errors first
            if response.status_code >= 500:
                print(f"❌ 2Captcha server error (HTTP {response.status_code}). Retrying in 5 seconds...")
                time.sleep(5)
                continue
                
            # Check if response is valid JSON
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON response from 2Captcha: {response.text}")
                print(f"❌ JSON Error: {e}")
                
                # If we're getting consistent 500 errors, try an alternative approach
                if "500 Internal Server Error" in response.text and attempt == max_retries - 1:
                    print("⚠️ Consistent 500 errors from 2Captcha API. Trying alternative method...")
                    return try_alternative_captcha_solution(selection_criteria)
                    
                time.sleep(5)  # Longer wait time for server issues
                continue
            
            if result.get("status") != 1:
                print(f"❌ Attempt {attempt + 1}: Error submitting CAPTCHA to 2Captcha - {result.get('request')}")
                time.sleep(3)  # Wait before retrying
                continue
            
            captcha_id = result.get("request")
            print(f"✅ CAPTCHA submitted successfully. ID: {captcha_id}")
            print("⏳ Waiting for CAPTCHA solution...")
            
            # Retrieve solution
            solution_url = f"http://2captcha.com/res.php?key={TWO_CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1"
            solution_found = False
            
            for poll_attempt in range(30):  # Max wait time ~150s (30 attempts * 5s)
                time.sleep(5)
                try:
                    solution_response = requests.get(solution_url, timeout=30)
                    
                    # Check for HTTP errors
                    if solution_response.status_code >= 500:
                        print(f"❌ 2Captcha server error during polling (HTTP {solution_response.status_code}). Retrying...")
                        time.sleep(3)
                        continue
                        
                    solution_data = solution_response.json()
                    
                    if solution_data.get("status") == 1:
                        solution = solution_data.get("request")
                        solution_found = True
                        print(f"✅ 2Captcha solution received: {solution}")
                        break
                    elif solution_data.get("request") == "CAPCHA_NOT_READY":
                        print(f"⏳ CAPTCHA not ready yet (attempt {poll_attempt + 1}/30)...")
                    else:
                        print(f"❌ Error from 2Captcha: {solution_data.get('request')}")
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON in solution response: {solution_response.text}")
                    print(f"❌ JSON Error: {e}")
                    time.sleep(2)
                except Exception as e:
                    print(f"❌ Error retrieving solution: {e}")
                    time.sleep(2)
            
            if not solution_found:
                print("❌ CAPTCHA solving timed out or failed")
                continue
            
            # Extract indices from the solution
            try:
                # Different 2Captcha response formats handling
                if ',' in solution:
                    # Format: "1,4,7"
                    positions = [int(pos) for pos in solution.split(",")]
                elif solution.isdigit():
                    # Format: "147"
                    positions = [int(pos) for pos in solution]
                else:
                    # Try to extract any numbers from the string
                    positions = [int(d) for d in re.findall(r'\d', solution)]
                
                # Ensure positions are 1-based (for the select_captcha_images function)
                positions = [pos if pos > 0 else pos + 1 for pos in positions]
                
                print(f"✅ CAPTCHA solved. Clicking on positions: {positions}")
                return positions
            except Exception as e:
                print(f"❌ Attempt {attempt + 1}: Error parsing CAPTCHA solution - {e}")
                print(f"❌ Raw solution was: {solution}")
                time.sleep(3)  # Wait before retrying
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error connecting to 2Captcha: {e}")
            time.sleep(5)  # Longer wait for network issues
        except Exception as e:
            print(f"❌ Unexpected error in solve_captcha_with_2captcha: {e}")
            time.sleep(3)
    
    print("❌ All attempts failed. CAPTCHA could not be solved correctly.")
    print("⚠️ Trying alternative CAPTCHA solution method...")
    
    # Try alternative solution as a last resort
    return try_alternative_captcha_solution(selection_criteria)

def try_alternative_captcha_solution(selection_criteria):
    """
    Fallback method when 2Captcha is having server issues.
    Uses a simple heuristic based on the selection criteria.
    """
    print("🔄 Using alternative CAPTCHA solution method...")
    
    # Map common CAPTCHA objects to likely positions
    # This is a very simple heuristic and won't be accurate for all CAPTCHAs
    # But it's better than nothing when the API is down
    common_objects = {
        "airplane": [5],  # Center image often contains the target object
        "bicycle": [5],
        "boat": [5],
        "bus": [5],
        "car": [5],
        "motorcycle": [5],
        "train": [5],
        "truck": [5],
        "traffic light": [2, 5, 8],  # Often in vertical arrangement
        "fire hydrant": [4, 5, 6],  # Often in horizontal arrangement
        "stop sign": [5],
        "parking meter": [5],
        "bench": [4, 5, 6],
        "bird": [5],
        "cat": [5],
        "dog": [5],
        "horse": [5],
        "sheep": [5],
        "cow": [5],
        "elephant": [5],
        "bear": [5],
        "zebra": [5],
        "giraffe": [5],
        "panda": [5],
    }
    
    # Extract the object type from the selection criteria
    for obj in common_objects.keys():
        if obj in selection_criteria.lower():
            print(f"🔍 Found object type '{obj}' in selection criteria")
            positions = common_objects[obj]
            print(f"⚠️ Using fallback positions: {positions}")
            return positions
    
    # If no specific object is found, return the center position as a default
    print("⚠️ No specific object found in criteria. Using center position as fallback.")
    return [5]  # Center position (1-based)

def select_captcha_images(driver, indices):
    """Clicks on the CAPTCHA images at the specified indices."""
    if not indices:
        print("❌ No indices provided to click on")
        return
        
    print(f"🖱 Attempting to click on images at indices: {indices}")
    
    # Try different XPath patterns for the CAPTCHA grid
    xpath_patterns = [
        # Pattern 1: Standard grid
        "/html/body/div[7]/div/div[1]/div[2]/div[1]/div[1]/div[{row}]/div[{col}]/div",
        # Pattern 2: Alternative grid structure
        "//div[contains(@class, 'task-grid')]/div[{index}]",
        # Pattern 3: Another common structure
        "//div[contains(@class, 'bcap-image-cell')][{index}]"
    ]
    
    # Try to find the grid first to determine which pattern to use
    grid_found = False
    
    for idx in indices:
        clicked = False
        
        # Convert to 0-based for calculation, but display as 1-based
        idx_0based = idx - 1 if idx > 0 else idx
        row, col = divmod(idx_0based, 3)
        
        # Add 1 to convert back to 1-based for XPath
        row += 1
        col += 1
        
        # Try each XPath pattern
        for pattern in xpath_patterns:
            try:
                if "{row}" in pattern and "{col}" in pattern:
                    xpath = pattern.format(row=row, col=col)
                else:
                    xpath = pattern.format(index=idx)
                
                print(f"🔍 Trying XPath: {xpath}")
                
                # Wait for element to be clickable
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                
                # Scroll to element to ensure it's visible
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Click the element
                element.click()
                print(f"✅ Clicked on image at position {idx} (row={row}, col={col})")
                clicked = True
                grid_found = True
                time.sleep(0.5)
                break
                
            except Exception as e:
                # Only print detailed error for the last pattern attempt
                if pattern == xpath_patterns[-1] and not clicked:
                    print(f"❌ Failed to click on image at position {idx} (row={row}, col={col}): {e}")
        
        # If we found a working pattern, stick with it for remaining clicks
        if grid_found:
            break
    
    # If we couldn't find any grid elements, try a more dynamic approach
    if not grid_found:
        try:
            print("🔍 Trying to find CAPTCHA images by class name...")
            # Find all image cells
            image_cells = driver.find_elements(By.CSS_SELECTOR, "div[class*='image-cell'], div[class*='task-image']")
            
            if image_cells:
                print(f"✅ Found {len(image_cells)} image cells")
                
                # Click on the specified indices
                for idx in indices:
                    # Adjust index to be 0-based for list access
                    idx_0based = idx - 1 if idx > 0 else idx
                    
                    if 0 <= idx_0based < len(image_cells):
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", image_cells[idx_0based])
                            time.sleep(0.5)
                            image_cells[idx_0based].click()
                            print(f"✅ Clicked on image at position {idx}")
                            time.sleep(0.5)
                        except Exception as e:
                            print(f"❌ Failed to click on image at position {idx}: {e}")
                    else:
                        print(f"❌ Index {idx} is out of range (0-{len(image_cells)-1})")
            else:
                print("❌ Could not find any CAPTCHA image cells")
                
        except Exception as e:
            print(f"❌ Error in dynamic image selection: {e}")

def create_account(driver, email, password):
    """Creates a new account with the given email and password."""
    driver.get("https://coinmarketcap.com/")
    time.sleep(2)
    driver.delete_all_cookies()
    time.sleep(2)
    driver.get("https://coinmarketcap.com/")
    time.sleep(2)
    
    # Click menu button
    menu_button_xpath = '/html/body/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div[2]/div[4]/button'
    driver.find_element(By.XPATH, menu_button_xpath).click()
    time.sleep(3)

    # Click Signup button
    create_account_xpath = '/html/body/div[6]/div/div/div/div/div[1]/div[2]'
    driver.find_element(By.XPATH, create_account_xpath).click()
    time.sleep(3)

    # Enter email
    email_input_xpath = '/html/body/div[6]/div/div/div/div/div[3]/div[3]/input'
    driver.find_element(By.XPATH, email_input_xpath).send_keys(email)
    time.sleep(1)

    # Enter password
    password_input_xpath = '/html/body/div[6]/div/div/div/div/div[3]/div[4]/div[2]/input'
    driver.find_element(By.XPATH, password_input_xpath).send_keys(password)
    time.sleep(1)

    # Click create account button (this triggers the CAPTCHA)
    final_create_button_xpath = '/html/body/div[6]/div/div/div/div/div[3]/div[6]/button'
    driver.find_element(By.XPATH, final_create_button_xpath).click()
    time.sleep(10)
    
    # CAPTCHA Handling
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, '//*[@id="tagLabel"]')))
        time.sleep(1)
        print("🔒 CAPTCHA detected. Attempting to solve...")
        
        # Extract selection criteria
        criteria_xpath = '//*[@id="tagLabel"]'
        criteria_element = driver.find_element(By.XPATH, criteria_xpath)
        selection_criteria = criteria_element.text
        print(f"🔍 Selection Criteria: {selection_criteria}")
        
        # Find the first image to extract the URL
        first_image_xpath = "//div[contains(@class, 'bcap-image-cell-image')]"
        image_elements = driver.find_elements(By.XPATH, first_image_xpath)
        
        if not image_elements:
            # Try alternative XPath
            first_image_xpath = "//div[contains(@class, 'task-image')]"
            image_elements = driver.find_elements(By.XPATH, first_image_xpath)
            
        if not image_elements:
            print("❌ Could not find CAPTCHA images.")
            return
            
        print("🖼 Found CAPTCHA images. Processing...")
        style_attribute = image_elements[0].get_attribute("style")
        
        # Extract URL from style attribute
        if 'url("' in style_attribute:
            image_url = style_attribute.split('url("')[1].split('")')[0]
        elif "url('" in style_attribute:
            image_url = style_attribute.split("url('")[1].split("')")[0]
        else:
            print("❌ Could not extract image URL from style attribute.")
            return
        
        # Download and split the image
        images = download_and_split_image(image_url)
        if images:
            # Solve the CAPTCHA
            solution_indices = solve_captcha_with_2captcha(images, selection_criteria)
            if solution_indices:
                select_captcha_images(driver, solution_indices)
                
                # Submit CAPTCHA
                submit_button_xpath = '//div[contains(text(), "Verify")]'
                try:
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, submit_button_xpath))
                    ).click()
                    print("✅ CAPTCHA submitted")
                    time.sleep(5)
                except Exception as e:
                    print(f"❌ Error clicking verify button: {e}")
            else:
                print("❌ No solution indices returned from 2Captcha")
        else:
            print("❌ Failed to process CAPTCHA images")
    except Exception as e:
        print(f"❌ Error handling CAPTCHA: {e}")

# Loop through accounts
for _, row in df.iterrows():
    try:
        create_account(driver, row["Email"], row["Password"])
        print(f"✅ Processed account: {row['Email']}")
        time.sleep(10)  # Wait between accounts
    except Exception as e:
        print(f"❌ Error processing account {row['Email']}: {e}")

# Clean up
print("✅ All accounts processed. Closing browser...")
time.sleep(5)
driver.quit()