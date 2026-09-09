# ========================================================================
# DexScreener Token Monitor: Scrapes new tokens and sends alerts to Telegram
# ========================================================================

# --- External Libraries ---
import undetected_chromedriver as uc  # Anti-detection Chrome driver to avoid bot detection
from selenium.webdriver.chrome.options import Options  # Chrome browser configuration options
from selenium.webdriver.common.by import By  # Element locator strategies
from selenium.webdriver.support.ui import WebDriverWait  # Wait functionality for Selenium
from selenium.webdriver.support import expected_conditions as EC  # Conditions to wait for
import requests  # HTTP requests library
import time  # Time-related functions
import os  # OS-level operations (file paths, env vars)
import re  # Regular expressions for pattern matching
import json  # JSON processing
from telethon.sync import TelegramClient  # Telegram API client
import asyncio  # Async IO operations

# --- Configuration Constants ---
# Main URL to monitor for new token pairs
URL = "https://dexscreener.com/?rankBy=pairAge&order=asc"
# API keys for external services
API_KEY = ""
MOBULA_API = ""

# Telegram API credentials
API_ID =  
API_HASH = ''  

# Target chat ID to send messages to
# TARGET_CHAT_ID = -1001326481918  # Commented out alternative chat ID
TARGET_CHAT_ID =   # Current target chat

# --- Selenium Setup ---
def initialize_selenium_driver(headless=False):
    """
    Initialize and configure the Selenium web driver with undetected-chromedriver.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        
    Returns:
        WebDriver: Configured Chrome WebDriver instance
        
    Raises:
        Exception: If driver initialization fails
    """
    try:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Add user data directory and profile directory arguments
        # This is the typical path for Chrome profiles on Windows
        # For macOS, use: ~/Library/Application Support/Google/Chrome
        # For Linux, use: ~/.config/google-chrome
        
        # Get user home directory
        user_home = os.path.expanduser("~")
        
        # Set up the user data directory path based on OS
        if os.name == 'nt':  # Windows
            user_data_dir = os.path.join(user_home, 'AppData', 'Local', 'Google', 'Chrome', 'User Data')
        elif os.name == 'posix':  # macOS or Linux
            if os.path.exists(os.path.join(user_home, 'Library')):  # macOS
                user_data_dir = os.path.join(user_home, 'Library', 'Application Support', 'Google', 'Chrome')
            else:  # Linux
                user_data_dir = os.path.join(user_home, '.config', 'google-chrome')
        
        # Add the user data directory and profile arguments
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("--profile-directory=Default")  # Use Profile 1
        
        # Security and performance settings
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        
        # Use undetected-chromedriver to bypass detection
        driver = uc.Chrome(options=chrome_options)
        driver.maximize_window()
        print("✅ Selenium WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"[X] Error initializing Selenium WebDriver: {e}")
        raise

# --- URL Management Functions ---
def extract_all_existing_urls():
    """
    Extract previously processed URLs from storage file to avoid duplicates.
    
    Returns:
        list: List of previously processed URLs
    """
    if os.path.exists("existing_urls.txt"):
        with open("existing_urls.txt", "r") as file:
            existing_urls = file.read().splitlines()
    else:
        existing_urls = []
    return existing_urls

# --- Messaging Functions ---
async def send_telegram_message(driver, messages):
    """
    Send alert messages to Telegram using the Telethon client.
    
    Args:
        driver: Selenium WebDriver instance (unused but kept for compatibility)
        messages (list): List of messages to send
    """
    print("Sending Message ...")
    
    async with TelegramClient('telegram_session', API_ID, API_HASH) as client:
        for message_text in messages:
            try:
                await client.send_message(TARGET_CHAT_ID, message_text)
                print("Message sent successfully!")
            except Exception as e:
                print(f"Error while sending message: {e}")

# --- Data Collection Functions ---
def wallet_info(address):
    """
    Query the Mobula API to get wallet portfolio information.
    
    Args:
        address (str): Wallet address to check
        
    Returns:
        dict: Wallet portfolio data or None if request fails
    """
    try:
        url = f"https://api.mobula.io/api/1/wallet/portfolio?wallet={address}"
        headers = {
            "Authorization": MOBULA_API
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data  # Return the actual data object, not the string
        else:
            print(f"Error fetching wallet info: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception in wallet_info: {e}")
        return None

def get_info(driver, url):
    """
    Extract detailed information about a token pair from both API and web sources.
    
    This function:
    1. Extracts network and address from the DexScreener URL
    2. Opens a new tab to get additional metadata from DexScreener's JSON API
    3. Also queries the main DexScreener API for standardized data
    
    Args:
        driver: Selenium WebDriver instance
        url (str): DexScreener URL to analyze
        
    Returns:
        tuple: (API data, Additional metadata, URL parameters) or False on failure
    """
    try:
        # Extracting info from the url using regex pattern
        pattern = r"https://dexscreener\.com/([^/]+)/([^/]+)"
        match = re.match(pattern, url)
        parameters = {}
        
        if not match:
            print("Address extraction unsuccessful")
            return False
            
        parameters["network"] = match.group(1)
        parameters["address"] = match.group(2)

        # Opening new tab and getting additional JSON data directly from DexScreener's internal API
        tab_url = f"https://io.dexscreener.com/dex/pair-details/v2/{parameters['network']}/{parameters['address']}"
        original_window = driver.current_window_handle
        data_dict = None
        
        try:
            # Open new tab and navigate to internal API endpoint
            driver.switch_to.new_window('tab')
            driver.get(tab_url)

            # Wait for the <pre> tag containing JSON data to be present
            try:
                pre_tag = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "pre"))
                )
                pre_text = pre_tag.text
                data_dict = json.loads(pre_text)  # Parse JSON from the page
            except Exception as e:
                print(f"Error finding or parsing tab content: {e}")
            finally:
                # Clean up by closing the tab and returning to original window
                driver.close()
                driver.switch_to.window(original_window)
        except Exception as e:
            print(f"Error managing browser tabs: {e}")
            # Try to return to original window if possible
            try:
                driver.switch_to.window(original_window)
            except:
                pass

        # Get token info from public DexScreener API
        api_url = f"https://api.dexscreener.com/latest/dex/pairs/{parameters['network']}/{parameters['address']}"
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return (data, data_dict, parameters)
            else:
                print(f"API Error: {response.status_code}")
                return False
        except Exception as e:
            print(f"Exception in API request: {e}")
            return False
            
    except Exception as e:
        print(f"General exception in get_info: {e}")
        return False  

def get_output(driver, url):
    """
    Process token data and format it into a readable message for Telegram.
    
    Args:
        driver: Selenium WebDriver instance
        url (str): DexScreener URL to analyze
        
    Returns:
        str: Formatted message with token details or False on failure
    """
    raw_outputs = get_info(driver, url)

    if raw_outputs:
        pretty, pretty_extra, parameters = raw_outputs
        
        # Check if 'pairs' exists and is not empty
        if not pretty.get("pairs") or len(pretty["pairs"]) == 0:
            return "Error: No pairs data found"
            
        pair = pretty["pairs"][0]
        
        # Extract basic token data with safe defaults
        token_name = pair.get("baseToken", {}).get("name", "N/A")
        token_symbol = "$" + pair.get("baseToken", {}).get("symbol", "Unknown")
        token_exchange = pair.get("dexId", "N/A")
        token_blockchain = pair.get("chainId", "N/A")
        
        # Safely access nested dict keys for financial data
        token_liquidity = pair.get("liquidity", {}).get("usd", "N/A")
        token_price = pair.get("priceUsd", "N/A")
        token_market_cap = pair.get("marketCap", "N/A")

        # Initialize variables with default values
        total_holders = "N/A"
        percentage_output = "N/A"
        token_total_supply = "N/A"
        freeze_revoked = "N/A"
        c_total_balance = "N/A"
        c_sol_balance = "N/A"
        c_decent_money = "N/A"
        c_decent_history = "N/A"

        # Extract holders information if available
        if pretty_extra and isinstance(pretty_extra.get("holders"), dict):
            holders_info = pretty_extra["holders"]
            total_holders = holders_info.get("count", "N/A")

            # Process top holders data
            if isinstance(holders_info.get("holders"), list) and holders_info["holders"]:
                holders = holders_info["holders"]
                percentages = [holder.get("percentage", 0) for holder in holders]
                percentage_output = " | ".join([f"{p}%" for p in percentages])
                token_total_supply = holders_info.get("totalSupply", "N/A")

        # Check Solana-specific token attributes (freeze authority)
        if pretty_extra and isinstance(pretty_extra.get("ta"), dict):
            token_attributes = pretty_extra["ta"]
            if token_blockchain.lower() == "solana" and isinstance(token_attributes.get("solana"), dict):
                freeze_status = token_attributes["solana"].get("isFreezable", False)
                freeze_revoked = "❌" if freeze_status else "✅"

        # Only attempt to get creator info if we have holders data - with proper type checking
        holders_exist = (pretty_extra and 
                        isinstance(pretty_extra.get("holders"), dict) and 
                        isinstance(pretty_extra["holders"].get("holders"), list) and 
                        pretty_extra["holders"]["holders"])
                        
        # Process creator wallet information if available
        if holders_exist:
            try:
                # Assume first holder is creator (most common case for new tokens)
                creator_id = pretty_extra["holders"]["holders"][0].get("id")
                if creator_id:
                    creator_info_str = wallet_info(creator_id)
                    # Check if creator_info is valid JSON string and parse it
                    if creator_info_str:
                        if isinstance(creator_info_str, str):
                            try:
                                creator_info = json.loads(creator_info_str)
                            except json.JSONDecodeError:
                                creator_info = None
                        else:
                            creator_info = creator_info_str
                            
                        # Extract wallet data if properly structured
                        if isinstance(creator_info, dict) and "data" in creator_info:
                            c_total_balance = creator_info["data"].get("total_wallet_balance", "N/A")
                            
                            # Look for Solana in assets list (typically at index 21)
                            assets = creator_info["data"].get("assets", [])
                            if isinstance(assets, list) and len(assets) > 21:
                                c_sol_balance = assets[21].get("token_balance", "N/A")
                            
                            # Analyze wallet quality indicators
                            try:
                                total_balance_float = float(c_total_balance) if c_total_balance != "N/A" else 0
                                c_decent_money = "✅" if total_balance_float > 1000 else "❌"
                            except (ValueError, TypeError):
                                c_decent_money = "❓"
                                
                            # Check for wallet history - more assets indicate more history
                            c_decent_history = "✅" if isinstance(assets, list) and len(assets) > 3 else "❌"
            except Exception as e:
                print(f"Error processing creator info: {e}")

        # Format message with all the collected data
        message = f"""
        {token_name} ON {token_blockchain}({token_symbol})

        Exchange: {token_exchange}
        Market Cap: {token_market_cap}
        Liquidity: {token_liquidity}
        Token Price: {token_price}
        Total Supply: {token_total_supply}
        Holders: {total_holders}
        Top Holders: {percentage_output}

        Freeze authority revoked: {freeze_revoked}

        Creator Info:
        . Balance SOL: {c_sol_balance}
        . Balance USD: {c_total_balance}
        . Dev Wallet has enough money: {c_decent_money}
        . Dev Wallet has decent history: {c_decent_history}
        """

        return message
    else: 
        return False

# --- Main Scraping Function ---
def scrape(driver):
    """
    Main scraping function that monitors DexScreener for new tokens.
    
    This function:
    1. Loads the DexScreener page
    2. Extracts new token pairs
    3. Processes each new pair and sends alerts
    
    Args:
        driver: Selenium WebDriver instance
    """
    # Navigate to the main DexScreener page
    driver.get(URL)

    # Load existing URLs to avoid processing duplicates
    existing_urls = extract_all_existing_urls()

    # Wait for page to fully load
    time.sleep(20) 
    
    # Wait for body to load first
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    # Find all new token pair elements using XPath
    links = driver.find_elements(By.XPATH, "//a[contains(@class, 'ds-dex-table-row ds-dex-table-row-new')]")
    
    # Process each new token pair
    messages = []
    for link in links:
        href = link.get_attribute("href")
        if href not in existing_urls:
            # Store new URL to avoid processing it again
            existing_urls.append(href)
            with open("existing_urls.txt", "a") as file:
                file.write(href + "\n")
            print(f"New URL found: {href}")
            
            # Process token and get formatted message
            message = get_output(driver, href)
            if message:
                messages.append(message)
        else:
            # Stop processing if we hit an already processed URL
            print(f"URL already exists: {href}")
            break

        # Throttle requests to avoid overloading
        time.sleep(3)

    # Send all collected messages to Telegram
    asyncio.run(send_telegram_message(driver, messages))  # Run the async function

    # Clean up resources
    driver.quit()

# --- Main Runner ---
def run_scraper():
    """
    Main loop function that continuously runs the scraper with delay between runs.
    """
    driver = initialize_selenium_driver(headless=False)
    while True:
        scrape(driver)
        time.sleep(30)  # Wait 30 seconds between scraping runs

# --- Entry Point ---
if __name__ == "__main__":
    run_scraper()