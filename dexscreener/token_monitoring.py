import requests
import time
import schedule
import json
import logging
from datetime import datetime
import scrape
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("token_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("token_monitor")

def fetch_latest_crypto_tokens():
    """
    Fetch the latest crypto tokens from the callback service.
    
    Returns:
        list: A list of token dictionaries containing pool_address and mint_address
        None: If an error occurred during fetching
    """
    url = ""
    
    try:
        # Make the GET request to the endpoint with a timeout
        logger.info(f"Fetching tokens from {url}")
        response = requests.get(url, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            tokens = data.get('tokens', [])
            count = data.get('count', 0)
            
            # Current timestamp for logging
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if count > 0:
                logger.info(f"[{current_time}] Found {count} new crypto tokens!")
                return tokens
            else:
                logger.info(f"[{current_time}] No new crypto tokens found.")
                return []
        else:
            logger.error(f"Failed to fetch tokens. Status code: {response.status_code}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Network error fetching crypto tokens: {e}")
        return None
    except json.JSONDecodeError:
        logger.error("Error parsing response as JSON")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
        return None

def process_tokens_batch(tokens):
    """
    Process a batch of tokens using a single Selenium driver instance.
    
    Args:
        tokens (list): List of token dictionaries with pool_address and mint_address
    """
    if not tokens:
        logger.info("No tokens to process")
        return
    
    # Get the list of tokens that need to be scraped (not already processed)
    tokens_to_scrape = []
    existing_addresses = scrape.extract_all_existing_addresses()
    
    for token in tokens:
        pool_address = token.get('pool_address', 'Unknown')
        mint_address = token.get('mint_address', 'Unknown')
        
        if (pool_address, mint_address) not in existing_addresses:
            tokens_to_scrape.append((pool_address, mint_address))
        else:
            logger.info(f"Token already scraped, skipping: {pool_address} / {mint_address}")
    
    if not tokens_to_scrape:
        logger.info("All tokens have already been processed")
        return
    
    # Initialize a single driver for all tokens
    try:
        logger.info(f"Initializing Selenium for batch processing of {len(tokens_to_scrape)} tokens")
        driver = scrape.initialize_selenium_driver()
        
        # Process each token with the same driver
        for pool_address, mint_address in tokens_to_scrape:
            try:
                logger.info(f"Processing token: {pool_address} / {mint_address}")
                scrape.process_token(driver, pool_address, mint_address)
            except Exception as e:
                logger.error(f"Error processing token {mint_address}: {e}")
                logger.debug(traceback.format_exc())
        
        # Close the driver after all tokens are processed
        logger.info("Closing Selenium driver after batch processing")
        driver.quit()
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        logger.debug(traceback.format_exc())
        # Try to close the driver if it exists
        try:
            if 'driver' in locals():
                driver.quit()
        except:
            pass

def start_token_monitoring():
    """
    Start monitoring for new crypto tokens by polling at regular intervals.
    Processes tokens in batches to improve efficiency.
    """
    logger.info("Starting crypto token monitoring...")
    logger.info("Will check for new tokens every 5 seconds")

    try:
        while True:
            try:
                # Fetch and process tokens
                tokens = fetch_latest_crypto_tokens()
                if tokens:
                    process_tokens_batch(tokens)
                
                # Wait before next check
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                logger.debug(traceback.format_exc())
                # Continue the loop despite errors
                time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Token monitoring stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error in monitoring process: {e}")
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    # Start the monitoring process
    start_token_monitoring()