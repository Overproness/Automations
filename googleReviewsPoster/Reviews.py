import random
from itertools import cycle
import subprocess
import os
import shutil
import time
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import sys

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.configure(state='normal')
        self.text_widget.insert('end', string)
        self.text_widget.see('end')
        self.text_widget.configure(state='disabled')

    def flush(self):
        pass

class ReviewBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Review Bot Control Panel")
        self.root.geometry("800x600")
        
        self.accounts_path = tk.StringVar()
        self.review_links_path = tk.StringVar()
        self.comments_path = tk.StringVar()
        self.profile_path = tk.StringVar()
        self.proxies_path = tk.StringVar()
        
        self.create_gui()

    def create_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        files_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="5")
        files_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.create_file_input(files_frame, "Accounts File:", self.accounts_path, 0)
        self.create_file_input(files_frame, "Review Links File:", self.review_links_path, 1)
        self.create_file_input(files_frame, "Comments File:", self.comments_path, 2)
        self.create_file_input(files_frame, "Profile Path:", self.profile_path, 3)
        self.create_file_input(files_frame, "Proxies File:", self.proxies_path, 4)
        
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(buttons_frame, text="Start Bot", command=self.start_bot)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(buttons_frame, text="Stop Bot", command=self.stop_bot, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief="sunken")
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        console_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, width=80, height=20)
        self.console.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.console.configure(state='disabled')
        
        sys.stdout = RedirectText(self.console)
        
        self.bot_running = False
        self.bot_thread = None
        
    def create_file_input(self, frame, label_text, variable, row):
        ttk.Label(frame, text=label_text).grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=variable, width=50).grid(row=row, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(variable)).grid(row=row, column=2)

    def browse_file(self, string_var):
        filename = filedialog.askopenfilename(
            title="Select file",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filename:
            string_var.set(filename)
            
    def start_bot(self):
        if not all([self.accounts_path.get(), self.review_links_path.get(), self.comments_path.get(), 
                    self.profile_path.get(), self.proxies_path.get()]):
            print("Please select all required files first!")
            return
            
        self.start_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.bot_running = True
        self.status_var.set("Bot is running...")
        
        self.bot_thread = threading.Thread(target=self.run_bot)
        self.bot_thread.daemon = True
        self.bot_thread.start()
        
    def stop_bot(self):
        self.bot_running = False
        self.status_var.set("Stopping bot...")
        self.stop_button.configure(state='disabled')
        
    def run_bot(self):
        proxies = self.read_file_lines(self.proxies_path.get())
        review_links = self.read_file_lines(self.review_links_path.get())
        comments = self.read_file_lines(self.comments_path.get())
        
        print(f"Starting bot with Profile: {self.profile_path.get()}")
        proxy_cycle = cycle(proxies)
        completed_reviews = 0
        
        kill_chrome_processes()
        clean_profile(self.profile_path.get())
        
        for review_link in review_links:
            if not self.bot_running:
                break
            
            proxy = next(proxy_cycle)
            driver = None
            try:
                driver = start_chrome_with_proxy(self.profile_path.get(), proxy)
                if post_review(driver, review_link, comments):
                    completed_reviews += 1
                    print(f"Successfully posted review for: {review_link}")
            except Exception as e:
                print(f"Error occurred: {str(e)}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                kill_chrome_processes()
        
        print(f"\nBot finished. Total reviews completed: {completed_reviews}/{len(review_links)}")
        self.bot_running = False
        self.start_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        self.status_var.set("Ready")

    def read_file_lines(self, file_path):
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]

def kill_chrome_processes():
    print("Cleaning up Chrome processes...")
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except Exception as e:
        print(f"Error killing Chrome processes: {str(e)}")

def clean_profile(profile_path):
    print(f"Cleaning Chrome profile: {profile_path}")
    cleanup_items = [
        'Default/Cache',
        'Default/Code Cache',
        'Default/Service Worker',
        'SingletonLock',
        'SingletonCookie',
        'SingletonSocket',
        'DevToolsActivePort',
        'Default/Network',
        'Default/Session Storage',
        'Default/Local Storage'
    ]
    for item in cleanup_items:
        full_path = os.path.join(profile_path, item)
        try:
            if os.path.isfile(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path, ignore_errors=True)
        except Exception as e:
            print(f"Could not remove {item}: {str(e)}")

def start_chrome_with_proxy(profile_path, proxy):
    print(f"Initializing Chrome with proxy: {proxy}")
    
    kill_chrome_processes()
    clean_profile(profile_path)
    
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={profile_path}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("profile-directory=Profile 1")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")
    
    proxy_host, proxy_port, proxy_user, proxy_pass = proxy.split(":")
    proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
    chrome_options.add_argument(f"--proxy-server={proxy_url}")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def post_review(driver, review_link, comments):
    try:
        driver.get(review_link)
        time.sleep(5)
        review_button = driver.find_element(By.XPATH, "//button[.//div[contains(text(), 'Reviews')]]")
        review_button.click()
        time.sleep(3)

        write_review_button = driver.find_element(By.XPATH, "//button[@aria-label='Write a review']")
        write_review_button.click()
        time.sleep(5)

        five_star_button = driver.find_element(By.XPATH, '(//div[@class="s2xyy" and @aria-label="Five stars"])[1]')
        five_star_button.click()
        time.sleep(3)

        text_area = driver.find_element(By.XPATH, "//textarea[@aria-label='Enter review']")
        review = random.choice(comments)
        text_area.send_keys(review)
        time.sleep(2)

        submit_button = driver.find_element(By.XPATH, "//button[@jsname='IJM3w']")
        submit_button.click()
        time.sleep(3)
        
        return True
    except Exception as e:
        print(f"Error posting review: {str(e)}")
        return False

if __name__ == "__main__":
    root = tk.Tk()
    app = ReviewBotGUI(root)
    root.mainloop()
