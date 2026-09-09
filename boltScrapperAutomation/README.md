# Bolt Scraper Automation Tool - User Guide

## Prerequisites

1. **Chrome Browser**: Make sure Google Chrome is installed and updated
2. **ChromeDriver**: Download and install ChromeDriver from https://chromedriver.chromium.org/
3. **Bolt Scraper Extension**: Install the Bolt Scraper extension in Chrome
4. **Python Packages**: All required packages should be installed automatically

## Setup Instructions

### 1. Install the Bolt Scraper Extension

- Open Chrome and go to the Chrome Web Store
- Search for "Bolt Scraper" and install the extension
- Make sure the extension is enabled

### 2. Verify Extension ID

- Right-click on the Bolt Scraper extension icon
- Click "Manage extension"
- Check the extension ID (should be: mjaecachebolhfiaodddibdjdfbanckk)
- If different, update the extension_url in the code

## How to Use

### 1. Prepare Your Data File

- Create an Excel (.xlsx, .xls) or CSV file with:
  - A column containing zip codes
  - A column containing city names
- Example:
  ```
  City Name    | Zip Code
  New York     | 10001
  Los Angeles  | 90210
  Chicago      | 60601
  ```

### 2. Run the Application

```bash
python main.py
```

### 3. Load Your Data

1. Click "Browse" next to "Excel/CSV File" and select your data file
2. Click "Load File & Preview"
3. Select the correct columns for "Zip Code Column" and "City Column"
4. Enter your search keyword (e.g., "restaurant", "hotel", "dentist")

### 4. Generate Search Files

1. Click "Generate TXT Files"
2. The tool will create batches of 1000 search strings each
3. Files will be saved in the output directory

### 5. Test Chrome Connection

1. **IMPORTANT**: Close all Chrome windows before testing
2. Click "Test Chrome Connection"
3. The tool will:
   - Kill any existing Chrome processes
   - Start Chrome with the correct profile
   - Test if the Bolt Scraper extension is accessible
   - Report which elements are found/missing

### 6. Run Automation

1. If the test passes, click "Start Automation"
2. The tool will:
   - Process each TXT file batch
   - Clear previous results
   - Enter keywords
   - Start scraping
   - Wait for completion
   - Download CSV results

## Troubleshooting

### Chrome Connection Issues

- **Error**: "DevToolsActivePort file doesn't exist"

  - Close ALL Chrome windows and browser instances
  - Wait 10 seconds, then try again
  - Check if another automation tool is using Chrome

- **Error**: "Extension not found"
  - Verify the Bolt Scraper extension is installed
  - Check the extension ID in Chrome extensions page
  - Make sure you're using the correct Chrome profile

### Extension Access Issues

- **Problem**: Extension elements not found
  - Open Chrome manually and navigate to the extension
  - Verify it loads correctly
  - Check if extension needs permissions or updates

### Performance Tips

- **Large datasets**: Files are automatically split into 1000-entry batches
- **Processing speed**: Each batch typically takes 5-15 minutes depending on keyword complexity
- **Memory usage**: Close other applications during large automation runs

## File Structure

```
project_folder/
├── main.py                    # Main application
├── requirements.txt           # Python dependencies
├── output/                    # Generated files and results
│   ├── search_strings_batch_1.txt
│   ├── search_strings_batch_2.txt
│   └── downloaded_csvs/       # Scraped results
└── temp_user_data/           # Temporary Chrome profile (auto-created)
```

## Advanced Configuration

### Batch Size

To change the batch size from 1000 entries, modify this line in `generate_txt_files()`:

```python
batch_size = 1000  # Change to desired size
```

### Extension URL

If using a different Bolt Scraper extension, update the extension ID:

```python
extension_url = "chrome-extension://YOUR_EXTENSION_ID/html/newtab.html"
```

### Timeout Settings

To adjust waiting times, modify these values in the code:

- `WebDriverWait` timeout: Default 10-30 seconds
- Progress check interval: Default 1 second
- Stable time check: Default 3 seconds

## Logs and Debugging

- All actions are logged in the application window
- Check logs for detailed error messages
- Common log messages:
  - "✓" indicates success
  - "✗" indicates failure or missing elements
  - "⚠️" indicates warnings

## Support

If you encounter issues:

1. Check the logs in the application
2. Verify all prerequisites are met
3. Try the Chrome connection test first
4. Ensure no other automation tools are running
