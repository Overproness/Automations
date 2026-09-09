import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import os
import time
import threading
from seleniumbase import Driver
import re
from datetime import datetime
import glob

class BoltScraperAutomation:
    def __init__(self, root):
        self.root = root
        self.root.title("Bolt Scraper Automation Tool")
        self.root.geometry("800x700")
        
        # Variables
        self.excel_file_path = tk.StringVar()
        self.search_keyword = tk.StringVar()
        self.output_directory = tk.StringVar()
        self.zip_column = tk.StringVar()
        self.city_column = tk.StringVar()
        self.driver = None
        self.txt_files = []
        self.is_processing = False
        self.license_key = "GM-35YT-BV3J-C6Z4"
        
        # Set default output directory
        self.output_directory.set(os.path.join(os.getcwd(), "output"))
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Bolt Scraper Automation Tool", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="Excel/CSV File:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(file_frame, textvariable=self.excel_file_path, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=(0, 5))
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(row=0, column=2, pady=(0, 5))
        
        ttk.Label(file_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(file_frame, textvariable=self.output_directory, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=(0, 5))
        ttk.Button(file_frame, text="Browse", command=self.browse_output_dir).grid(row=1, column=2, pady=(0, 5))
        
        # Column mapping section
        column_frame = ttk.LabelFrame(main_frame, text="Column Mapping", padding="10")
        column_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        column_frame.columnconfigure(1, weight=1)
        
        ttk.Label(column_frame, text="Zip Code Column:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.zip_combo = ttk.Combobox(column_frame, textvariable=self.zip_column, width=30)
        self.zip_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(0, 5))
        
        ttk.Label(column_frame, text="City Column:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.city_combo = ttk.Combobox(column_frame, textvariable=self.city_column, width=30)
        self.city_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(0, 5))
        
        # Search keyword section
        keyword_frame = ttk.LabelFrame(main_frame, text="Search Configuration", padding="10")
        keyword_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        keyword_frame.columnconfigure(1, weight=1)
        
        ttk.Label(keyword_frame, text="Search Keyword:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(keyword_frame, textvariable=self.search_keyword, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(0, 5))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(0, 10))
        
        ttk.Button(button_frame, text="Load File & Preview", command=self.load_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Generate TXT Files", command=self.generate_txt_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Start Automation", command=self.start_automation).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Stop", command=self.stop_automation).pack(side=tk.LEFT)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Excel or CSV file",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.excel_file_path.set(file_path)
            self.log(f"Selected file: {file_path}")
            
    def browse_output_dir(self):
        dir_path = filedialog.askdirectory(title="Select output directory")
        if dir_path:
            self.output_directory.set(dir_path)
            self.log(f"Output directory set to: {dir_path}")
            
    def load_file(self):
        if not self.excel_file_path.get():
            messagebox.showerror("Error", "Please select a file first")
            self.log("Error: No file selected")
            return
            
        try:
            file_path = self.excel_file_path.get()
            self.log(f"Loading file: {file_path}")
            
            if file_path.endswith('.csv'):
                self.log("File type detected: CSV")
                self.df = pd.read_csv(file_path)
            else:
                self.log("File type detected: Excel")
                self.df = pd.read_excel(file_path)
                
            self.log("File loaded successfully, processing columns...")
            
            # Update column combo boxes
            columns = list(self.df.columns)
            self.zip_combo['values'] = columns
            self.city_combo['values'] = columns
            self.log(f"Updated column dropdowns with {len(columns)} columns")
            
            # Try to auto-detect columns
            self.log("Attempting to auto-detect zip and city columns...")
            zip_cols = [col for col in columns if 'zip' in col.lower()]
            city_cols = [col for col in columns if 'city' in col.lower() or 'name' in col.lower()]
            
            if zip_cols:
                self.zip_column.set(zip_cols[0])
                self.log(f"Auto-detected zip column: {zip_cols[0]}")
            if city_cols:
                self.city_column.set(city_cols[0])
                self.log(f"Auto-detected city column: {city_cols[0]}")
                
            self.log(f"Loaded file with {len(self.df)} rows and {len(self.df.columns)} columns")
            self.log(f"Columns: {', '.join(columns)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
            self.log(f"Error loading file: {str(e)}")
            
    def generate_txt_files(self):
        if not hasattr(self, 'df'):
            messagebox.showerror("Error", "Please load a file first")
            self.log("Error: No file loaded - cannot generate TXT files")
            return
            
        if not self.search_keyword.get():
            messagebox.showerror("Error", "Please enter a search keyword")
            self.log("Error: No search keyword provided")
            return
            
        if not self.zip_column.get() or not self.city_column.get():
            messagebox.showerror("Error", "Please select zip code and city columns")
            self.log("Error: Zip code and/or city column not selected")
            return
            
        try:
            self.log("Starting TXT file generation process...")
            # Create output directory
            output_dir = self.output_directory.get()
            self.log(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
            self.log("Output directory created successfully")
            
            # Generate search strings
            self.log("Generating search strings from data...")
            search_strings = []
            keyword = self.search_keyword.get().strip()
            self.log(f"Using search keyword: '{keyword}'")
            
            processed_count = 0
            skipped_count = 0
            
            for _, row in self.df.iterrows():
                zip_code = str(row[self.zip_column.get()]).strip()
                city_name = str(row[self.city_column.get()]).strip()
                
                if zip_code and city_name and zip_code != 'nan' and city_name != 'nan':
                    search_string = f"{keyword} in {zip_code} {city_name}"
                    search_strings.append(search_string)
                    processed_count += 1
                else:
                    skipped_count += 1
                    
            self.log(f"Processed {processed_count} valid entries, skipped {skipped_count} invalid entries")
            self.log(f"Generated {len(search_strings)} search strings")
            
            # Create TXT files with 1000 entries each
            self.log("Creating TXT files with batches of 1000 entries each...")
            self.txt_files = []
            batch_size = 1000
            
            for i in range(0, len(search_strings), batch_size):
                batch = search_strings[i:i+batch_size]
                file_index = i // batch_size + 1
                filename = f"search_strings_batch_{file_index}.txt"
                filepath = os.path.join(output_dir, filename)
                
                self.log(f"Writing batch {file_index} to {filename}...")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(', '.join(batch))
                    
                self.txt_files.append(filepath)
                self.log(f"Created {filename} with {len(batch)} entries")
                
            self.log(f"Successfully created {len(self.txt_files)} TXT files in {output_dir}")
            messagebox.showinfo("Success", f"Generated {len(self.txt_files)} TXT files successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate TXT files: {str(e)}")
            self.log(f"Error generating TXT files: {str(e)}")
            
    def start_automation(self):
        if self.is_processing:
            messagebox.showwarning("Warning", "Automation is already running")
            self.log("Warning: Automation already in progress")
            return
            
        # Check if TXT files exist, if not try to generate them
        if not self.txt_files:
            self.log("No TXT files found, attempting to generate them...")
            
            # Check if we have the necessary data to generate files
            if not hasattr(self, 'df'):
                self.log("No data loaded, attempting to load file...")
                if not self.excel_file_path.get():
                    messagebox.showerror("Error", "Please select an Excel/CSV file first")
                    self.log("Error: No file selected and no TXT files available")
                    return
                else:
                    # Try to load the file
                    try:
                        self.load_file()
                        if not hasattr(self, 'df'):
                            self.log("Failed to load file data")
                            return
                    except Exception as e:
                        self.log(f"Error auto-loading file: {str(e)}")
                        return
            
            # Check for required fields
            if not self.search_keyword.get():
                messagebox.showerror("Error", "Please enter a search keyword")
                self.log("Error: No search keyword provided")
                return
                
            if not self.zip_column.get() or not self.city_column.get():
                messagebox.showerror("Error", "Please select zip code and city columns")
                self.log("Error: Zip code and/or city column not selected")
                return
            
            # Generate TXT files automatically
            try:
                self.generate_txt_files()
                if not self.txt_files:
                    self.log("Failed to generate TXT files")
                    return
            except Exception as e:
                self.log(f"Error auto-generating TXT files: {str(e)}")
                return
            
        # Start automation in a separate thread
        self.log("Starting automation process with SeleniumBase extension loading...")
        self.is_processing = True
        threading.Thread(target=self.run_automation, daemon=True).start()
        
    def stop_automation(self):
        self.log("Stop automation requested")
        self.is_processing = False
        if self.driver:
            try:
                self.log("Closing browser...")
                self.driver.quit()
                self.log("Browser closed successfully")
            except Exception as e:
                self.log(f"Error closing browser: {str(e)}")
        self.status_label.config(text="Stopped")
        self.log("Automation stopped")
        
    def run_automation(self):
        try:
            self.log("Initializing automation process...")
            self.setup_driver()
            self.status_label.config(text="Running automation...")
            
            total_files = len(self.txt_files)
            self.log(f"Starting automation for {total_files} TXT files")
            self.progress_bar.config(maximum=total_files)
            
            for i, txt_file in enumerate(self.txt_files):
                if not self.is_processing:
                    self.log("Automation interrupted by user")
                    break
                    
                self.log(f"Processing file {i+1}/{total_files}: {os.path.basename(txt_file)}")
                self.process_txt_file(txt_file, i+1)
                
                self.progress_bar.config(value=i+1)
                self.root.update_idletasks()
                self.log(f"Completed processing file {i+1}/{total_files}")
                
            if self.is_processing:
                self.log("All files processed successfully!")
                self.log("Automation completed successfully!")
                messagebox.showinfo("Success", "Automation completed successfully!")
            else:
                self.log("Automation stopped by user")
                
        except Exception as e:
            self.log(f"Automation error: {str(e)}")
            messagebox.showerror("Error", f"Automation failed: {str(e)}")
        finally:
            self.is_processing = False
            if self.driver:
                try:
                    self.log("Cleaning up - closing browser...")
                    self.driver.quit()
                    self.log("Browser cleanup completed")
                except Exception as e:
                    self.log(f"Error during browser cleanup: {str(e)}")
            self.status_label.config(text="Ready")
            self.log("Automation process finished")
            
    def find_extension_zip(self):
        """Find the BoltScrapper extension zip file in the current directory"""
        current_dir = os.getcwd()
        self.log(f"Looking for extension zip files in: {current_dir}")
        
        # Look for common extension file patterns
        patterns = [
            "*.zip",
            "*bolt*.zip",
            "*scraper*.zip", 
            "*scrapper*.zip",
            "*.crx"
        ]
        
        for pattern in patterns:
            files = glob.glob(os.path.join(current_dir, pattern))
            for file in files:
                self.log(f"Found potential extension file: {os.path.basename(file)}")
                return file
                
        self.log("No extension zip files found in current directory")
        return None
            
    def setup_driver(self):
        try:
            self.log("Setting up Chrome browser with SeleniumBase...")
            
            # Try simple approach first - just open a fresh browser
            if self.try_simple_browser():
                self.log("Successfully started browser - checking for extension manually")
                return
                
            # If that fails, raise an error
            raise Exception("Failed to setup browser")
            
        except Exception as e:
            self.log(f"Failed to start Chrome with SeleniumBase: {str(e)}")
            raise
            
    def try_simple_browser(self):
        """Try to start a browser with automatic extension installation using SeleniumBase"""
        try:
            self.log("Starting Chrome browser with automatic extension installation...")
            
            # Check both possible extension locations
            possible_paths = [
                r"D:\GitHub\Dirk\boltScrapperAutomation\BoltScrapperExtension\Bolt's Google Maps Scraper v2.2.7",
                r"C:\BoltScrapperExtension\Bolt's Google Maps Scraper v2.2.7"
            ]
            
            extension_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    extension_path = path
                    self.log(f"Found extension at: {extension_path}")
                    break
                else:
                    self.log(f"Extension not found at: {path}")
            
            if not extension_path:
                self.log("Error: Extension not found at any of the expected locations:")
                for path in possible_paths:
                    self.log(f"  - {path}")
                raise Exception("BoltScrapper extension not found")
            
            self.log(f"Loading extension from: {extension_path}")
            
            # Create driver with extension_dir parameter
            self.driver = Driver(headless=False, extension_dir=extension_path)
            
            self.log("Browser started successfully with extension!")
            
            # Navigate to extension to verify installation
            extension_url = "chrome-extension://mjaecachebolhfiaodddibdjdfbanckk/html/newtab.html"
            self.log(f"Verifying extension installation at: {extension_url}")
            self.driver.get(extension_url)
            
            try:
                self.driver.wait_for_element("body", timeout=15)
                self.log("Extension loaded successfully - verifying interface...")
                
                # Try to activate license automatically
                if self.activate_license():
                    self.log("License activation successful!")
                    return True
                else:
                    self.log("License activation failed - checking if extension is accessible...")
                    # Check if extension is working anyway
                    try:
                        self.driver.wait_for_element("#clear-btn", timeout=5)
                        self.log("Extension is accessible - setup successful!")
                        return True
                    except:
                        self.log("Extension interface not accessible")
                        return False
                        
            except Exception as e:
                self.log(f"Extension verification failed: {str(e)}")
                return False
                
        except Exception as e:
            self.log(f"Error starting browser with extension: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            return False
            
    def activate_license(self):
        """Activate the license using the exact selectors provided"""
        try:
            self.log("Attempting to activate license with provided selectors...")
            
            # Navigate to extension to access license button
            extension_url = "chrome-extension://mjaecachebolhfiaodddibdjdfbanckk/html/newtab.html"
            self.driver.get(extension_url)
            
            # Wait for page to load
            self.driver.wait_for_element("body", timeout=10)
            self.log("Extension page loaded")
            
            # Step 1: Click license button
            self.log("Looking for license button...")
            try:
                self.driver.wait_for_element("#license-btn", timeout=10)
                self.log("Found license button, clicking...")
                self.driver.click("#license-btn")
                self.log("Clicked license button")
                time.sleep(3)  # Wait for modal to open
            except Exception as e:
                self.log(f"Could not find or click license button: {str(e)}")
                return False
            
            # Step 2: Enter license key
            self.log("Looking for license key input field...")
            try:
                self.driver.wait_for_element("#license-key-input", timeout=10)
                self.log("Found license key input, entering key...")
                self.driver.type("#license-key-input", self.license_key)
                self.log(f"Entered license key: {self.license_key}")
                time.sleep(2)
            except Exception as e:
                self.log(f"Could not find or use license key input: {str(e)}")
                return False
            
            # Step 3: Click activate button
            self.log("Looking for activate license button...")
            try:
                self.driver.wait_for_element("#activate-license-btn", timeout=10)
                self.log("Found activate button, clicking...")
                self.driver.click("#activate-license-btn")
                self.log("Clicked activate license button")
                time.sleep(5)  # Wait for activation
            except Exception as e:
                self.log(f"Could not find or click activate button: {str(e)}")
                return False
            
            # Step 4: Try to close modal if it exists
            self.log("Attempting to close any modal...")
            try:
                # Look for modal close button
                close_button = self.driver.find_element(".modal-close")
                if close_button:
                    self.log("Found modal close button, clicking...")
                    self.driver.click(".modal-close")
                    self.log("Clicked modal close button")
                    time.sleep(2)
            except:
                self.log("No modal close button found or already closed")
            
            # Step 5: Verify activation by checking if main interface is available
            self.log("Verifying license activation...")
            try:
                self.driver.wait_for_element("#clear-btn", timeout=10)
                self.log("License activation successful - main interface is accessible")
                return True
            except:
                self.log("License activation verification failed - main interface not accessible")
                return False
                
        except Exception as e:
            self.log(f"Error during license activation: {str(e)}")
            return False
            
    def process_txt_file(self, txt_file, file_number):
        try:
            self.log(f"Starting processing of TXT file: {os.path.basename(txt_file)}")
            # Read the TXT file content
            self.log("Reading TXT file content...")
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            self.log(f"Read {len(content)} characters from file")
                
            # Navigate to the extension
            extension_url = "chrome-extension://mjaecachebolhfiaodddibdjdfbanckk/html/newtab.html"
            self.log(f"Navigating to extension: {extension_url}")
            self.driver.get(extension_url)
            self.log(f"Opened extension tab")
            
            # Wait for page to load
            self.log("Waiting for page to load (looking for clear-btn)...")
            self.driver.wait_for_element("#clear-btn", timeout=10)
            self.log("Page loaded successfully - clear button found")
            
            # Step 1: Click clear results button
            self.log("Looking for clear results button...")
            self.log("Found clear results button, clicking...")
            self.driver.click("#clear-btn")
            self.log("Clicked clear results button, waiting for confirm modal...")
            
            # Wait for and click the confirm button in the modal
            try:
                self.log("Looking for confirm button in modal...")
                self.driver.wait_for_element("#confirm-modal-confirm-btn", timeout=10)
                self.log("Found confirm button, clicking...")
                self.driver.click("#confirm-modal-confirm-btn")
                self.log("Clicked confirm button, waiting 9 seconds...")
            except Exception:
                self.log("Warning: Confirm button not found or not clickable - continuing anyway")
            
            time.sleep(9)
            
            # Step 2: Enter keywords
            self.log("Looking for keyword input field...")
            self.driver.wait_for_element("#keywordInput", timeout=10)
            self.log("Found keyword input field, clearing existing content...")
            
            # Split content into smaller chunks to avoid timeout
            keywords = content.split(', ')
            total_keywords = len(keywords)
            self.log(f"Entering {total_keywords} keywords in chunks...")
            
            # Process keywords in chunks of 50 (reduced from 100)
            chunk_size = 50
            first_chunk = True
            for i in range(0, len(keywords), chunk_size):
                if not self.is_processing:
                    self.log("Automation stopped during keyword entry")
                    return
                    
                chunk = keywords[i:i+chunk_size]
                chunk_text = ', '.join(chunk)
                current_chunk = i // chunk_size + 1
                total_chunks = (len(keywords) + chunk_size - 1) // chunk_size
                
                self.log(f"Entering chunk {current_chunk}/{total_chunks} ({len(chunk)} keywords)...")
                
                # Add the chunk to the input field
                if i == 0:
                    # First chunk - use type to clear and enter the text
                    self.driver.type("#keywordInput", chunk_text)
                else:
                    # Subsequent chunks - add comma separator and the chunk
                    self.driver.send_keys("#keywordInput", ', ' + chunk_text)
                
                # Longer delay between chunks to prevent browser overload
                time.sleep(3)
                
                # Update UI
                self.root.update_idletasks()
                
            self.log(f"Successfully entered all {total_keywords} keywords in {total_chunks} chunks")
            
            # Wait a bit longer after entering all keywords before clicking scrape
            self.log("Waiting 15 seconds for browser to process all keywords...")
            time.sleep(15)
            
            # Step 3: Click scrape button
            self.log("Looking for scrape button...")
            self.driver.wait_for_element("#scrapeButton", timeout=10)
            self.log("Found scrape button, clicking to start scraping...")
            self.driver.click("#scrapeButton")
            self.log("Scrape button clicked - scraping process initiated")
            
            # Step 4: Wait for scraping to complete
            self.log("Waiting for scraping to complete...")
            self.wait_for_scraping_completion()
            
            # Step 5: Download CSV
            self.log("Scraping completed, looking for CSV download button...")
            try:
                self.driver.wait_for_element("#csv-btn", timeout=30)
                self.log("Found CSV download button, clicking to download...")
                self.driver.click("#csv-btn")
                self.log(f"Downloaded CSV for batch {file_number}")
            except Exception:
                self.log("Warning: CSV download button not found - scraping may not be complete")
                self.log("Checking if there are any results to download...")
                # Try to find any download button or continue anyway
                try:
                    # Look for alternative download elements or just continue
                    time.sleep(5)
                    self.log("Continuing with next file...")
                except:
                    pass
            
            # Wait a bit before processing next file
            self.log("Waiting 30 seconds before processing next file...")
            time.sleep(30)
            
        except Exception as e:
            self.log(f"Error processing file {txt_file}: {str(e)}")
            raise
            
    def wait_for_scraping_completion(self):
        try:
            # Wait longer for scraping to start (progress should be > 0)
            self.log("Waiting up to 60 seconds for scraping to start...")
            
            # Custom wait for progress to start
            start_time = time.time()
            while time.time() - start_time < 60:
                if self.get_progress_value() > 0:
                    break
                time.sleep(1)
                if not self.is_processing:
                    return
            
            if self.get_progress_value() == 0:
                self.log("Timeout waiting for scraping to start - extension may be overloaded")
                self.log("Attempting to continue anyway...")
                return
            
            self.log("Scraping started, waiting for completion...")
            
            # Wait for scraping to complete (progress = 100%)
            last_progress = 0
            stable_count = 0
            max_wait_time = 3600  # Maximum 1 hour wait
            wait_cycles = 0
            
            while self.is_processing and wait_cycles < max_wait_time // 9:
                try:
                    progress = self.get_progress_value()
                    
                    if progress >= 100:
                        self.log("Scraping completed (100%)")
                        break
                        
                    # Check if progress is stable (not changing)
                    if progress == last_progress:
                        stable_count += 1
                        if stable_count >= 30:  # 30 iterations of no change (270 seconds)
                            self.log(f"Progress stable at {progress}% for 270 seconds, checking scraping time...")
                            if self.is_scraping_time_stable():
                                self.log("Scraping appears to be complete based on stable timing")
                                break
                    else:
                        stable_count = 0
                        
                    last_progress = progress
                    self.log(f"Scraping progress: {progress}%")
                    
                except Exception as e:
                    self.log(f"Error checking progress: {str(e)}")
                    
                time.sleep(9)
                wait_cycles += 1
                
            if wait_cycles >= max_wait_time // 9:
                self.log("Maximum wait time reached - assuming scraping is complete")
                
        except Exception as e:
            self.log(f"Error in wait_for_scraping_completion: {str(e)}")
            self.log("Attempting to continue anyway...")
            
    def get_progress_value(self):
        try:
            progress_text = self.driver.get_text("#scrapingProgress")
            # Extract percentage value
            match = re.search(r'([\d.]+)%', progress_text)
            if match:
                return float(match.group(1))
            return 0
        except:
            return 0
            
    def is_scraping_time_stable(self):
        try:
            # Check if scraping time is stable for a few seconds
            self.log("Checking if scraping time is stable...")
            initial_time = self.driver.get_text("#scrapingTime")
            self.log(f"Initial scraping time: {initial_time}")
            
            self.log("Waiting 27 seconds to check time stability...")
            time.sleep(27)
            
            current_time = self.driver.get_text("#scrapingTime")
            self.log(f"Current scraping time after wait: {current_time}")
            
            is_stable = initial_time == current_time
            self.log(f"Time stability check result: {'Stable' if is_stable else 'Still changing'}")
            return is_stable
            
        except Exception as e:
            self.log(f"Error checking scraping time stability: {str(e)}")
            return False

def main():
    root = tk.Tk()
    app = BoltScraperAutomation(root)
    root.mainloop()

if __name__ == "__main__":
    main()