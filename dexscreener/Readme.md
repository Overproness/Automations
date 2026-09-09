# Instructions for Running the DexScreener Monitoring Script

## Prerequisites

Before running this script, you'll need to set up the following on your computer:

- Python: Make sure Python 3.8+ is installed
- Chrome Browser: The script uses Chrome for automation
- Required Python libraries: Several libraries need to be installed

## Step-by-Step Setup Guide

### 1. Install Required Python Libraries

Open your terminal or command prompt and run:

```
pip install undetected-chromedriver selenium requests telethon asyncio
```

### 2. Configure Telegram API Credentials

The script sends alerts to Telegram, so you'll need to:

- Create a Telegram API application at https://my.telegram.org/apps
- Use the provided API_ID and API_HASH in the script or update them with your own
- Make sure you have access to the target chat (ID: -1002670598744)

### 3. Create Files and Directories

- Create a file named existing_urls.txt in the same directory as the script (can be empty initially)
- Make sure the directory is writable for storing the Telegram session file

### 4. Running the Script

- Save the code to a file named project.py
- Open your terminal or command prompt
- Navigate to the directory containing the script
- Run the script:

```
python project.py
```

## Important Notes

- **First Run Authentication**: The first time you run the script, Telegram will ask you to authenticate. You'll need to enter your phone number and the verification code sent to your Telegram account.
- **CAPTCHA Handling**: The script includes a 20-second wait time when loading DexScreener. Since the script uses your default Chrome profile, CAPTCHAs should typically be handled automatically. If a CAPTCHA does appear and isn't automatically solved, you may need to manually solve it once or twice. After that, the site should recognize your browser and run without requiring further CAPTCHA verification.
- **Chrome Profile**: The script uses your existing Chrome profile. Make sure you're logged into any necessary services in Chrome before running the script.
- **Continuous Operation**: The script is designed to run continuously, checking for new pairs every 30 seconds. You may want to run it in a dedicated terminal window or set up a proper daemon process for long-term use.

## Troubleshooting

If you encounter issues:

- Make sure all required libraries are installed
- Check that Chrome is properly installed and accessible
- Verify your internet connection
- Ensure your Telegram API credentials are correct
- If Chrome opens but fails to load pages, you may need to update undetected-chromedriver
- For persistent issues, check the error messages in the terminal for clues about what might be going wrong.
