import requests
import pandas as pd
import os
from openpyxl import load_workbook
import time
import json

def create_simplelogin_aliases(api_key, num_aliases=5):
    """Create random aliases on SimpleLogin using the API with persistent rate limit handling."""
    # API endpoint for SimpleLogin random alias creation
    url = "https://app.simplelogin.io/api/alias/random/new"
    
    # Try multiple authentication formats
    auth_headers = [
        {"Authorization": api_key},
        {"Api-Key": api_key},
        {"X-API-Key": api_key}
    ]
    
    aliases = []
    max_retries = 20  # Maximum number of retries for the entire operation
    retry_count = 0
    
    while len(aliases) < num_aliases and retry_count < max_retries:
        # Try each authentication method
        for headers in auth_headers:
            if len(aliases) >= num_aliases:
                break
            
            headers_copy = headers.copy()
            headers_copy["Content-Type"] = "application/json"
            note = f"Created by script on 2025-03-12"
            payload = {"note": note}
            
            try:
                print(f"Attempting to create alias {len(aliases)+1}/{num_aliases}...")
                response = requests.post(url, headers=headers_copy, json=payload)
                
                if response.status_code == 200 or response.status_code == 201:
                    # Success!
                    result = response.json()
                    
                    if 'email' in result:
                        alias_email = result['email']
                    elif 'alias' in result:
                        alias_email = result['alias']
                    else:
                        print(f"Unexpected response format: {result}")
                        continue  # Skip this iteration and try again
                        
                    aliases.append(alias_email)
                    print(f"Successfully created alias: {alias_email}")
                    # Wait a moment before the next request to avoid rate limiting
                    time.sleep(2)
                    break  # Break out of auth headers loop if successful
                
                elif response.status_code == 429:
                    # Rate limited
                    retry_after = 30  # Default to 30 seconds
                    
                    # Try to get retry-after header
                    if 'Retry-After' in response.headers:
                        try:
                            retry_after = int(response.headers['Retry-After'])
                        except (ValueError, TypeError):
                            pass
                        
                    print(f"Rate limited. Waiting {retry_after} seconds before retry...")
                    # Save progress
                    if aliases:
                        print(f"Currently have {len(aliases)}/{num_aliases} aliases. Saving progress...")
                        save_progress_to_excel(aliases)
                    
                    time.sleep(retry_after)
                    retry_count += 1
                    break  # Break out of auth headers loop
                
                else:
                    # Some other error
                    print(f"Error: {response.status_code} - {response.text}")
                    retry_count += 1
                    time.sleep(5)  # Wait 5 seconds before trying the next auth method
                
            except requests.exceptions.RequestException as e:
                print(f"Request exception: {e}")
                retry_count += 1
                time.sleep(5)  # Wait 5 seconds before trying the next auth method
        
        # If we've tried all auth methods and still couldn't get an alias, wait longer
        if len(aliases) < num_aliases and retry_count % 3 == 0:
            wait_time = min(60 * (retry_count // 3), 300)  # Cap at 5 minutes
            print(f"All authentication methods failed. Waiting {wait_time} seconds before trying again...")
            time.sleep(wait_time)
    
    if len(aliases) < num_aliases:
        print(f"Could only generate {len(aliases)}/{num_aliases} aliases after multiple attempts.")
    
    return aliases

def save_progress_to_excel(aliases, excel_file="credentials.xlsx"):
    """Save current progress to the Excel file."""
    append_to_excel(aliases, excel_file)
    print(f"Progress saved to {excel_file}")

def append_to_excel(aliases, excel_file="credentials.xlsx"):
    """Append aliases to the first column of the Excel file."""
    if not os.path.exists(excel_file):
        # Create new Excel file if it doesn't exist
        df = pd.DataFrame({
            'SimpleLogin Aliases': aliases
        })
        df.to_excel(excel_file, index=False)
        print(f"Created new Excel file: {excel_file}")
    else:
        # Load existing workbook
        workbook = load_workbook(excel_file)
        sheet = workbook.active
        
        # Find the last row with data in column A
        last_row = sheet.max_row
        
        # Append each alias to the first column (A)
        for i, alias in enumerate(aliases):
            sheet.cell(row=last_row + 1 + i, column=1, value=alias)
        
        # Save the workbook
        workbook.save(excel_file)
        print(f"Appended {len(aliases)} aliases to {excel_file}")

def main():
    print("SimpleLogin Alias Generator")
    print("==========================")
    
    api_key = "ppfuhgyhhdavrholijcvdiqusshbtqsdgbzcwglishwssorwmvmjzfbndfqq"

    if not api_key:
        print("API key is required. Exiting.")
        return
    
    try:
        num_aliases = int(input("How many aliases would you like to generate? (default: 5): "))
    except ValueError:
        num_aliases = 5
        print("Using default value of 5 aliases.")
    
    # Generate SimpleLogin aliases with persistent retry
    print(f"Generating {num_aliases} SimpleLogin aliases...")
    aliases = create_simplelogin_aliases(api_key, num_aliases)
    
    print("\nGenerated aliases:")
    for alias in aliases:
        print(f"- {alias}")
    
    # Final save to Excel file
    if aliases:
        append_to_excel(aliases)
        print(f"\nSuccessfully added {len(aliases)} aliases to credentials.xlsx")
    
    print("\nProcess completed.")

if __name__ == "__main__":
    main()