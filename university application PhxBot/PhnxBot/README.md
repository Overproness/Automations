# Phoenix University Application Bot

This bot automates the application process for Phoenix University using Selenium WebDriver.

## System Requirements

- Windows 10/11
- Python 3.8 or higher
- Google Chrome browser installed
- Dolphin Anty Browser installed and running
- Minimum 8GB RAM
- Stable internet connection
- Please note that crashes might occur if the proxies hinder the internet connection, which may lead to pages not loading.
- IT IS RECOMENDED TO RUN 3 INSTANCES, as running more will slow the internet connection causeing time outs.
- The proxies(through profile ids) and API of the dolphin browser should be changed regurarly to avoid verification.

## Required Files

1. Code files (in PhnxBot\):
   - main.py (Main entry point)
   - PhoenixApplicationGUI.py (GUI interface)
   - PhoenixUniversityApplicationUtils.py (Core automation)
   - Gsheets.py (Google Sheets integration)
   - dolphin.py (Dolphin browser automation)

2. API Credentials:
   - phoenix-462906-c4271d0cdf4b.json (Google Sheets API credentials)
   - Dolphin Anty API token (Required for browser automation)

3. Google Sheet:
   - Spreadsheet ID:
   - Required columns:
     - email
     - ssn
     - name
     - address
     - city
     - state
     - zip
     - phone number
     - password
     - dob
     - Gender
     - degree level
     - Area of Interest
     - program name
     - Start dates
     - high school
     - completion year
     - high school completion month
     - demographics
     - STATUS (for tracking progress)

## Python Package Requirements

Install required packages using pip:

```bash
pip install selenium
pip install undetected-chromedriver
pip install webdriver-manager
pip install requests
pip install gspread
pip install oauth2client
pip install tkinter
```

## Configuration

1. **Dolphin Anty Setup:**
   - Install Dolphin Anty
   - Start the local API (default port 3001)
   - Get your API token from Dolphin Anty dashboard
   - Create browser profiles and note their IDs
   - Add your default API in the dolphin.py file

2. **Google Sheets API:**
   - Place the credentials JSON file in the project directory
   - Share the Google Sheet with the service account email

3. **Capthca API:**
   - Placed in the PhoenixUniversityApplicationUtils.py

## Running the Bot

1. Start Dolphin Anty and ensure the local API is running

2. Launch the application:

   ```bash
   python main.py
   ```

3. In the GUI:
   - Enter Dolphin API token
   - (Optional) Enter profile IDs if using Dolphin profiles
   - Set number of concurrent instances
   - Toggle headless mode if needed
   - Click Start to begin automation

## Important Notes

- The bot uses 2captcha for CAPTCHA solving (API key configured in PhoenixUniversityApplicationUtils.py)
- Each instance requires approximately 1GB of RAM
- Run in visible mode first to ensure everything works before using headless mode
- Monitor the logs for any errors or issues
- The STATUS column in Google Sheets will be updated with:
  - IN_PROGRESS: Currently processing
  - COMPLETED: Successfully completed
  - FAILED: Error occurred during processing

## Troubleshooting

1. If Dolphin connection fails:
   - Ensure Dolphin Anty is running
   - Check if the local API is accessible (default: http://localhost:3001)
   - Verify API token is valid

2. If Google Sheets fails:
   - Verify credentials JSON file is present
   - Check if service account has access to the sheet
   - Ensure required columns exist in the sheet

3. For browser automation issues:
   - Clear browser cache and cookies
   - Try with a fresh Dolphin profile
   - Check if site structure has changed
   - Verify internet connection stability
