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
from flask import Flask, request, jsonify
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scraper")

# --- Constants ---
MOBULA_API = ""

# Telegram API credentials
API_ID =  
API_HASH = ''  

# Target chat ID to send messages to
TARGET_CHAT_ID = 

# --- Telegram Integration Functions ---
async def send_telegram_message(message):
    """
    Send alert messages to Telegram using the Telethon client.
    
    Args:
        message (str): Message to send
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    logger.info("Sending message to Telegram...")
    
    try:
        async with TelegramClient('telegram_session', API_ID, API_HASH) as client:
            await client.send_message(TARGET_CHAT_ID, message)
            logger.info("Message sent successfully!")
            return True
    except Exception as e:
        logger.error(f"Error while sending message: {e}")
        logger.debug(traceback.format_exc())
        return False

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
        logger.info("Initializing Selenium WebDriver...")
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
        logger.info("✅ Selenium WebDriver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"[X] Error initializing Selenium WebDriver: {e}")
        logger.debug(traceback.format_exc())
        raise

# --- File Operations ---
def extract_all_existing_addresses():
    """
    Extract previously processed (pool_address, mint_address) pairs 
    from storage file to avoid duplicates.

    Returns:
        list of tuples: [(pool_address, mint_address), ...]
    """
    existing_addresses = []
    
    try:
        if os.path.exists("existing_urls.txt"):
            with open("existing_urls.txt", "r") as file:
                for line in file:
                    try:
                        parts = line.strip().split("|")
                        pool = parts[0].split("Pool Address:")[1].strip()
                        mint = parts[1].split("Mint Address:")[1].strip()
                        existing_addresses.append((pool, mint))
                    except (IndexError, ValueError) as e:
                        # Ignore malformed lines
                        logger.warning(f"Skipping malformed line in existing_urls.txt: {line.strip()}")
                        continue
        logger.info(f"Loaded {len(existing_addresses)} existing addresses")
    except Exception as e:
        logger.error(f"Error reading existing addresses: {e}")
        logger.debug(traceback.format_exc())
    
    return existing_addresses

def write_address(pool_address, mint_address):
    """
    Append a new (pool_address, mint_address) pair to the storage file.

    Args:
        pool_address (str): The pool address.
        mint_address (str): The mint address.
        
    Returns:
        bool: True if write was successful, False otherwise
    """
    try:
        with open("existing_urls.txt", "a") as file:
            file.write(f"Pool Address: {pool_address} | Mint Address: {mint_address}\n")
        logger.info(f"Successfully recorded new address pair: {pool_address} / {mint_address}")
        return True
    except Exception as e:
        logger.error(f"Error writing address to file: {e}")
        logger.debug(traceback.format_exc())
        return False

# --- Data Extraction Functions ---
def extract_info_from_dexscreener(driver, address):
    """
    Extract detailed token information from DexScreener's internal API.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance
        address (str): Token address to look up
        
    Returns:
        dict: Token data dictionary or None if extraction fails
    """
    tab_url = f"https://io.dexscreener.com/dex/pair-details/v2/solana/{address}"
    original_window = driver.current_window_handle
    data_dict = None
    
    try:
        logger.info(f"Fetching DexScreener data for address: {address}")
        
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
            logger.info("Successfully extracted DexScreener data")
            return data_dict
        except Exception as e:
            logger.error(f"Error finding or parsing tab content: {e}")
            logger.debug(traceback.format_exc())
            return None
        finally:
            # Clean up by closing the tab and returning to original window
            try:
                driver.close()
                driver.switch_to.window(original_window)
            except Exception as tab_e:
                logger.error(f"Error closing tab: {tab_e}")
    except Exception as e:
        logger.error(f"Error managing browser tabs: {e}")
        logger.debug(traceback.format_exc())
        # Try to return to original window if possible
        try:
            driver.switch_to.window(original_window)
        except Exception as switch_e:
            logger.error(f"Error switching back to original window: {switch_e}")
        return None

def wallet_info(address):
    """
    Query the Mobula API to get wallet portfolio information.
    
    Args:
        address (str): Wallet address to check
        
    Returns:
        dict: Wallet portfolio data or None if request fails
    """
    try:
        logger.info(f"Fetching wallet info for: {address}")
        url = f"https://api.mobula.io/api/1/wallet/portfolio?wallet={address}"
        headers = {
            "Authorization": MOBULA_API
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info("Successfully retrieved wallet info")
            return data
        else:
            logger.error(f"Error fetching wallet info: {response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"Network error in wallet_info: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in wallet_info: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected exception in wallet_info: {e}")
        logger.debug(traceback.format_exc())
        return None

def extract_info_from_cmc(driver, url):
    """
    Extract token information from CoinMarketCap.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance
        url (str): CoinMarketCap URL to scrape
        
    Returns:
        dict: Token data dictionary or None if extraction fails
    """
    # Define XPaths for various token information elements
    x_paths = {
        "token_symbol": "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[1]/div[2]/div[1]/div/div/h1/span[1]/div/div/span",
        "token_name": "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[1]/div[2]/div[1]/div/div/div/div[1]/span",
        "token_liquidity": "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[2]/dl/div[6]/dd/div[1]/div/span",
        "token_total_supply": "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[2]/div[8]/div/div[1]/dl[2]/span/span/dd/span",
        "token_price": "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[2]/dl/div[1]/dd/div[1]/div/span",
        "token_exchange": "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[1]/div[1]/a[2]/div/div",
        "token_market_cap": "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[2]/dl/div[3]/dd/div[1]/div/span"
    }

    output = {}
    try: 
        logger.info(f"Loading CMC page: {url}")
        driver.get(url)
        time.sleep(5)  # Allow time for page to load

        # Wait for page body to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Extract each token information field
        for key, path in x_paths.items():
            if key == "token_price":
                continue  # skip token_price for now

            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, path))
                )
                output[key] = element.text
                logger.debug(f"Extracted {key}: {element.text}")
            except Exception as e:
                logger.warning(f"Failed to get {key}: {e}")
                output[key] = "N/A"
        
        logger.info("Successfully extracted CMC data")
        return output

    except Exception as e:
        logger.error(f"Error loading CMC page: {e}")
        logger.debug(traceback.format_exc())
        return None

# --- Message Construction ---
def make_output(cmc_output, dex_output):
    """
    Create a formatted message from the extracted token data.
    
    Args:
        cmc_output (dict): Token data from CoinMarketCap
        dex_output (dict): Token data from DexScreener
        
    Returns:
        str: Formatted message for Telegram
    """
    try:
        logger.info("Generating output message from extracted data")
        
        # Default values in case data is missing
        token_defaults = {
            "token_symbol": "Unknown",
            "token_name": "Unknown",
            "token_liquidity": "N/A",
            "token_total_supply": "N/A",
            "token_exchange": "N/A",
            "token_market_cap": "N/A"
        }
        
        # Apply defaults for missing CMC data
        if not cmc_output:
            cmc_output = {}
        token_data = {**token_defaults, **cmc_output}
        
        # Extract values from token_data
        token_symbol = token_data["token_symbol"]
        token_name = token_data["token_name"]
        token_liquidity = token_data["token_liquidity"]
        token_total_supply = token_data["token_total_supply"]
        token_exchange = token_data["token_exchange"]
        token_market_cap = token_data["token_market_cap"]
        token_blockchain = "solana"

        # Initialize additional fields with default values
        total_holders = "N/A"
        percentage_output = "N/A"
        freeze_revoked = "N/A"
        c_total_balance = "N/A"
        c_sol_balance = "N/A"
        c_decent_money = "N/A"
        c_decent_history = "N/A"

        # Extract holders information if available
        if dex_output and isinstance(dex_output.get("holders"), dict):
            holders_info = dex_output["holders"]
            total_holders = holders_info.get("count", "N/A")

            # Process top holders data
            if isinstance(holders_info.get("holders"), list) and holders_info["holders"]:
                holders = holders_info["holders"]
                percentages = [holder.get("percentage", 0) for holder in holders]
                percentage_output = " | ".join([f"{p}%" for p in percentages])

        # Check Solana-specific token attributes (freeze authority)
        if dex_output and isinstance(dex_output.get("ta"), dict):
            token_attributes = dex_output["ta"]
            if token_blockchain.lower() == "solana" and isinstance(token_attributes.get("solana"), dict):
                freeze_status = token_attributes["solana"].get("isFreezable", False)
                freeze_revoked = "❌" if freeze_status else "✅"

        # Check for valid holders data structure
        holders_exist = (dex_output and 
                        isinstance(dex_output.get("holders"), dict) and 
                        isinstance(dex_output["holders"].get("holders"), list) and 
                        dex_output["holders"]["holders"])

        # Process creator wallet information if available
        if holders_exist:
            try:
                # Assume first holder is creator (most common case for new tokens)
                creator_id = dex_output["holders"]["holders"][0].get("id")
                if creator_id:
                    creator_info = wallet_info(creator_id)
                    
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
                logger.error(f"Error processing creator info: {e}")
                logger.debug(traceback.format_exc())

        # Construct the final message
        message = f"""
            {token_name} ON {token_blockchain}({token_symbol})

            Exchange: {token_exchange}
            Market Cap: {token_market_cap}
            Liquidity: {token_liquidity}
            Token Price: "not done yet"
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

        logger.info("Message generated successfully")
        return message
    
    except Exception as e:
        logger.error(f"Error generating output message: {e}")
        logger.debug(traceback.format_exc())
        return "Error generating token analysis. Please check logs."

# --- Main Processing Functions ---
def process_token(driver, pool_address, mint_address):
    """
    Process a single token by extracting data and sending a message.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance
        pool_address (str): Token pool address
        mint_address (str): Token mint address
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        logger.info(f"Processing token: {pool_address} / {mint_address}")
        
        # Extract information from both sources
        url = f"https://coinmarketcap.com/dexscan/solana/{pool_address}/"
        output1 = extract_info_from_cmc(driver, url)
        output2 = extract_info_from_dexscreener(driver, mint_address)
        
        # Generate and send message
        message = make_output(output1, output2)
        asyncio.run(send_telegram_message(message))
        
        # Record the processed address
        write_address(pool_address, mint_address)
        logger.info(f"Successfully processed token: {mint_address}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing token {mint_address}: {e}")
        logger.debug(traceback.format_exc())
        return False

def main(pool_address, mint_address):
    """
    Main entry point for processing a single token with its own driver.
    Use this function for individual token processing only.
    For batch processing, use process_token with a shared driver.
    
    Args:
        pool_address (str): Token pool address
        mint_address (str): Token mint address
    """
    logger.info(f"Starting single token processing for {mint_address}")
    
    try:
        # Check if token has already been processed
        existing_addresses = extract_all_existing_addresses()
        if (pool_address, mint_address) not in existing_addresses:
            # Initialize driver, process token, and clean up
            driver = initialize_selenium_driver()
            try:
                process_token(driver, pool_address, mint_address)
            finally:
                driver.quit()
                logger.info("Selenium driver closed")
        else:
            logger.info(f"Token already scraped, skipping: {mint_address}")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        logger.debug(traceback.format_exc())

# For script testing
if __name__ == "__main__":
    # Example usage
    logger.info("Running script in standalone mode for testing")
    test_pool = "YOUR_TEST_POOL_ADDRESS"
    test_mint = "YOUR_TEST_MINT_ADDRESS"
    main(test_pool, test_mint)




