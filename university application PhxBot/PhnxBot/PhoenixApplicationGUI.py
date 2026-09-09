import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import logging
from datetime import datetime
import time
import random
from PhoenixUniversityApplicationUtils import PhoenixUniversityApplicationUtils
from Gsheets import GoogleSheetHandler

class PhoenixApplicationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Phoenix University Application Bot")
        self.root.geometry("800x600")
        
        self.instance_queue = queue.Queue()

        self.profile_list = []
        self.used_profiles = set()
        self.profile_instances = {}  # Map profile ID to instance number

        self.current_profile_index = 0
        self.running = False
        self.pause_new_instances = False
        self.active_threads = []
        self.max_concurrent = 1
        self.next_instance_number = 1
        self.instances_completed = 0
        self.instances_failed = 0
        
        self.driver_apps = []  
        self.gsheets = GoogleSheetHandler("phoenix-462906-c4271d0cdf4b.json", "")
        self.api_tok = None

        self.setup_gui()
        self.setup_logging()


    def setup_gui(self):
        # Profile ID input
        profile_frame = ttk.LabelFrame(self.root, text="Profile IDs", padding="5")
        profile_frame.pack(fill="x", padx=5, pady=5)


        
        self.use_profiles_var = tk.BooleanVar()
        self.use_profiles_checkbox = ttk.Checkbutton(
            profile_frame, 
            text="Use Dolphin profiles",
            variable=self.use_profiles_var
        )
        self.use_profiles_checkbox.pack(anchor="w", padx=5)
        
        # Add headless mode checkbox right after profile checkbox
        self.headless_var = tk.BooleanVar()
        self.headless_checkbox = ttk.Checkbutton(
            profile_frame, 
            text="Run in headless mode",
            variable=self.headless_var
        )
        self.headless_checkbox.pack(anchor="w", padx=5)
        
        self.profile_text = scrolledtext.ScrolledText(profile_frame, height=5)
        self.profile_text.pack(fill="x", padx=5, pady=5)
        ttk.Label(profile_frame, text="Enter Profile IDs (one per line)").pack()
        
        # Add API token input
        api_frame = ttk.LabelFrame(self.root, text="Dolphin API Token", padding="5")
        api_frame.pack(fill="x", padx=5, pady=5)

        # Use Text widget instead of Entry for multi-line token support
        self.api_token_text = scrolledtext.ScrolledText(api_frame, height=3)
        self.api_token_text.pack(fill="x", padx=5, pady=5)
        ttk.Label(api_frame, text="Enter Dolphin API Token or Null").pack()
        
        # Instance count frame
        count_frame = ttk.LabelFrame(self.root, text="Instance Settings", padding="5")
        count_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(count_frame, text="Concurrent instances:").pack(side="left")
        self.concurrent_count = ttk.Entry(count_frame, width=10)
        self.concurrent_count.pack(side="left", padx=5)
        self.concurrent_count.insert(0, "2")

        # Control buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_instances)
        self.start_btn.pack(side="left", padx=5)
        
        self.pause_btn = ttk.Button(btn_frame, text="Stop New Instances", 
                                  command=self.pause_new_instances_only)
        self.pause_btn.pack(side="left", padx=5)
        
        self.stop_all_btn = ttk.Button(btn_frame, text="Stop All", 
                                     command=self.stop_all_instances)
        self.stop_all_btn.pack(side="left", padx=5)
        
        # Initially disable stop buttons
        self.pause_btn.config(state="disabled")
        self.stop_all_btn.config(state="disabled")
        
        # Add status bar (add this before the log frame)
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var)
        status_bar.pack(fill="x", padx=5, pady=2)
        
        # Log output
        log_frame = ttk.LabelFrame(self.root, text="Logs", padding="5")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame)
        self.log_text.pack(fill="both", expand=True)

    def setup_logging(self):
        # Configure logging to write to both file and GUI
        class RequestFilter(logging.Filter):
            def filter(self, record):
                # List of strings to filter out
                filtered_strings = [
                    "Capturing request:",
                    "Capturing response:",
                    "Failed to resolve address",
                    "ERROR:services\\network\\p2p\\socket_manager",
                    "downloads?name=",
                    "optimizationguide-pa",
                    "idsync.rlcdn.com",
                    "cookielaw.org",
                    "ipapi.co",
                    "GroupMarkerNotSet",
                    "WebGL",
                    "swiftshader",
                    "stun."  # This will catch all stun server related messages
                ]
                message = record.getMessage()
                return not any(s in message for s in filtered_strings)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('phoenix_gui.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.addFilter(RequestFilter())  # Add the filter
        
    def load_profiles(self):
        """Load profile IDs from the text input"""
        if not self.use_profiles_var.get():
            return True
            
        profile_text = self.profile_text.get("1.0", "end-1c").strip()
        if not profile_text:
            self.log_message("No profile IDs entered but profiles are enabled.")
            return False
            
        self.profile_list = [p.strip() for p in profile_text.split("\n") if p.strip()]
        
        if not self.profile_list:
            self.log_message("No valid profile IDs found in input")
            return False
            
        self.log_message(f"Loaded {len(self.profile_list)} profile IDs")
        
        # Use the current max_concurrent value for validation
        if len(self.profile_list) < self.max_concurrent:
            self.log_message(f"Warning: Need at least {self.max_concurrent} profile IDs for {self.max_concurrent} concurrent instances")
            return False
            
        return True

    def get_next_available_profile(self):
        """Get the next unused profile ID"""
        if not self.use_profiles_var.get():
            return None
            
        if not self.profile_list:
            return None
            
        # Try to find an unused profile
        available_profiles = [p for p in self.profile_list if p not in self.used_profiles]
        if available_profiles:
            profile_id = random.choice(available_profiles)  # picks a random available
            self.used_profiles.add(profile_id)
            return profile_id
                
        return None

    def release_profile(self, profile_id):
        """Release a profile ID back to the pool"""
        if profile_id in self.used_profiles:
            self.used_profiles.remove(profile_id)
            self.log_message(f"Released profile ID: {profile_id}")

    def run_application_process(self, instance_num):
        app = None
        profile_id = None
        try:
            app =  PhoenixUniversityApplicationUtils(self.api_tok)
            app.headless = self.headless_var.get()  # Set headless mode before setup
            self.log_message(f"Starting instance {instance_num} {'in headless mode' if app.headless else 'in visible mode'}")
            
            if self.use_profiles_var.get():
                profile_id = self.get_next_available_profile()
                if not profile_id:
                    raise Exception("No available profile IDs")
                self.log_message(f"Instance {instance_num}: Using profile ID: {profile_id}")
                self.profile_instances[instance_num] = profile_id
                app.setup(profile_id=profile_id)
            else:
                app.setup()

            # Track the driver instance
            self.driver_apps.append(app)
            
            time.sleep(random.uniform(2, 5))
            
            # # Navigate and fill forms
            self.navigate_and_fill_forms(app, instance_num)
            success = True
            if success:
                self.instances_completed += 1
                self.log_message(f"Instance {instance_num} completed successfully!")

        except Exception as e:
            self.log_message(f"Error in instance {instance_num}: {str(e)}")
            self.instances_failed += 1
        finally:
            if profile_id:
                self.release_profile(profile_id)
                if instance_num in self.profile_instances:
                    del self.profile_instances[instance_num]
            if app:
                app.cleanup()
                # Remove from tracked instances
                if app in self.driver_apps:
                    self.driver_apps.remove(app)
            
            # Remove thread from active threads
            active_threads_copy = self.active_threads[:]
            for thread in active_threads_copy:
                if thread.ident == threading.current_thread().ident:
                    self.active_threads.remove(thread)
                    break
            
            self.update_status()
            
            self.log_message(f"Waiting 10 seconds before starting replacement instance if program is still running")
            time.sleep(10)
            
            if self.running and not self.pause_new_instances:
                replacement_instance_num = self.get_next_instance_number()
                self.instance_queue.put(replacement_instance_num)
                self.log_message(f"Queued replacement instance {replacement_instance_num}")
            
            if self.running and not self.pause_new_instances:
                self.start_pending_instances()


    def get_next_instance_number(self):
        """Generate the next instance number"""
        instance_num = self.next_instance_number
        self.next_instance_number += 1
        return instance_num

    def update_status(self):
        """Update the status bar with current progress"""
        completed = self.instances_completed
        failed = self.instances_failed
        active = len(self.active_threads)
        queued = self.instance_queue.qsize()
        
        if self.running:
            self.status_var.set(f"Running - Completed: {completed} | Failed: {failed} | Active: {active} | Queued: {queued}")
        else:
            self.status_var.set(f"Stopped - Completed: {completed} | Failed: {failed}")

    def start_pending_instances(self):
        """Start new instances if under max concurrent limit"""
        while (len(self.active_threads) < self.max_concurrent and 
               not self.instance_queue.empty() and 
               self.running and 
               not self.pause_new_instances):
            next_instance = self.instance_queue.get()
            thread = threading.Thread(target=self.run_application_process, 
                                   args=(next_instance,))
            thread.daemon = True
            thread.start()
            self.active_threads.append(thread)
            self.log_message(f"Started new instance {next_instance}")

    def instance_controller_loop(self):
        while self.running:
            if (len(self.active_threads) < self.max_concurrent and
                not self.instance_queue.empty() and
                not self.pause_new_instances):
                
                next_instance = self.instance_queue.get()
                thread = threading.Thread(target=self.run_application_process, args=(next_instance,))
                thread.daemon = True
                thread.start()
                self.active_threads.append(thread)
                self.log_message(f"Controller started instance {next_instance}")
                time.sleep(5)  # Add 5 second delay between instances
            
            # If we have no active threads and no queued instances, create new ones
            elif (len(self.active_threads) < self.max_concurrent and
                  self.instance_queue.empty() and
                  not self.pause_new_instances and
                  self.running):
                
                # Create a new instance to maintain the concurrent count
                new_instance_num = self.get_next_instance_number()
                thread = threading.Thread(target=self.run_application_process, args=(new_instance_num,))
                thread.daemon = True
                thread.start()
                self.active_threads.append(thread)
                self.log_message(f"Controller started new instance {new_instance_num}")
            
            # Clean up finished threads
            self.active_threads = [t for t in self.active_threads if t.is_alive()]
            
            # Update status periodically
            self.update_status()
                
            time.sleep(2)  # Check every 2 seconds
        
        # Final cleanup when controller stops
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_all_btn.config(state="disabled")
        self.update_status()

    def start_instances(self):
        try:
            # Get and validate API token first
            self.api_tok = self.api_token_text.get("1.0", "end-1c").strip()

                
            # Get and validate max_concurrent first
            max_concurrent = int(self.concurrent_count.get())
            if max_concurrent < 1:
                raise ValueError("Concurrent instance count must be positive")
            
            # Set max_concurrent before profile validation
            self.max_concurrent = max_concurrent
            
            if self.use_profiles_var.get():
                if not self.load_profiles():
                    self.log_message("Cannot start - profile validation failed")
                    return
                    
                if len(self.profile_list) < max_concurrent:
                    self.log_message(f"Need at least {max_concurrent} profile IDs")
                    return

            # Reset instance-related variables
            self.running = True
            self.pause_new_instances = False
            self.instances_completed = 0
            self.instances_failed = 0
            self.next_instance_number = 1
            self.active_threads.clear()  # Clear any existing threads
            
            # Clear any existing queue items
            while not self.instance_queue.empty():
                self.instance_queue.get()
            
            # Queue up initial instances based on new max_concurrent
            for i in range(max_concurrent):
                self.instance_queue.put(self.get_next_instance_number())
            
            self.log_message(f"Starting continuous instances with {max_concurrent} concurrent limit")

            # Reset controller thread if it exists
            if hasattr(self, 'controller_thread') and self.controller_thread.is_alive():
                self.running = False  # Stop old controller
                self.controller_thread.join(timeout=2.0)  # Wait for it to finish
            
            # Start new controller thread
            self.running = True
            self.controller_thread = threading.Thread(target=self.instance_controller_loop)
            self.controller_thread.daemon = True
            self.controller_thread.start()
            
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.stop_all_btn.config(state="normal")
            self.update_status()
            
        except Exception as e:
            self.log_message(f"Error starting instances: {str(e)}")

    def stop_all_instances(self):
        """Stop all running instances immediately"""
        self.running = False
        self.pause_new_instances = True
        
        def cleanup_instances():
            # Handle cleanup in batches to prevent GUI freezing
            batch_size = 2
            driver_batches = [self.driver_apps[i:i + batch_size] 
                            for i in range(0, len(self.driver_apps), batch_size)]
            
            for batch in driver_batches:
                for app in batch:
                    try:
                        app.cleanup()
                    except Exception as e:
                        self.log_message(f"Error closing browser instance: {str(e)}")
                    # Small delay between batch processing
                    time.sleep(0.5)
            
            # Clear all tracking collections
            self.active_threads.clear()
            self.driver_apps.clear()
            self.used_profiles.clear()
            self.profile_instances.clear()
            
            # Clear the queue
            while not self.instance_queue.empty():
                self.instance_queue.get()
            
            # Update UI
            self.root.after(0, self._update_ui_after_stop)
        
        # Disable buttons immediately
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="disabled")
        self.stop_all_btn.config(state="disabled")
        
        # Start cleanup in separate thread
        cleanup_thread = threading.Thread(target=cleanup_instances)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        self.log_message("Stopping all instances...")
        
        # Schedule a check to ensure cleanup completed
        self.root.after(30000, self._force_cleanup_if_needed)


    def _update_ui_after_stop(self):
        """Update UI elements after stop (called from cleanup thread)"""
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_all_btn.config(state="disabled")
        self.update_status()
        self.log_message("All instances stopped")


    def _force_cleanup_if_needed(self):
        """Force cleanup if normal cleanup didn't complete"""
        if len(self.driver_apps) > 0 or len(self.active_threads) > 0:
            self.log_message("Forcing cleanup of remaining instances...")
            self.driver_apps.clear()
            self.active_threads.clear()
            self.used_profiles.clear()
            self.profile_instances.clear()
            self._update_ui_after_stop()

    def pause_new_instances_only(self):
        """Stop creation of new instances but let current ones finish"""
        self.pause_new_instances = True
        self.pause_btn.config(state="disabled")
        # Don't release profiles for running instances
        self.log_message("Stopped creation of new instances")

    def extract_first_last(self, full_name):
        parts = full_name.strip().split()
        if len(parts) == 0:
            return None, None
        elif len(parts) == 1:
            return parts[0], None
        else:
            return parts[0], parts[-1]  # First and Last, ignoring anything in the middle
        

    def navigate_and_fill_forms(self, app, instance_num):
        try:
            logged_in = False
            # Get next unprocessed row from Google Sheets
            unprocessed = self.gsheets.get_next_n_unprocessed(1)
            if not unprocessed:
                self.log_message(f"Instance {instance_num}: No unprocessed records found in sheets")
                return

            row_index, row_data = unprocessed[0]
            self.log_message(f"Instance {instance_num}: Processing row {row_index + 2} from sheets")


            # Update status to IN_PROGRESS
            self.gsheets.update_status(row_index, "IN_PROGRESS")

            """Handle navigation and form filling"""
            max_nav_retries = 1
            time.sleep(5)  # Initial wait before navigation
            for nav_attempt in range(max_nav_retries):
                try:
                    #clear history
                    app.close_other_tabs_except_current()

                    app.driver.get("https://www.phoenix.edu/application/quick-app/personal-info")

                    time.sleep(20)
                    if "University of Phoenix" in app.driver.title:
                        break
                except Exception as nav_error:
                    if nav_attempt == max_nav_retries - 1:
                        raise
                    self.log_message(f"Navigation attempt {nav_attempt + 1} failed, retrying...")
                    time.sleep(2)


            # Fill personal information
            self.log_message(f"Instance {instance_num}: Filling personal information...")

            email = row_data['email']
            ssn = row_data['ssn']
            first_name, last_name = self.extract_first_last(row_data['name'])
            address = row_data["address"]
            city = row_data["city"]
            state = row_data["state"]
            zip_code = row_data["zip"]
            phone_number = row_data["phone number"]
            password = row_data["password"]

            dob = row_data['dob']
            gender = row_data['Gender']

            degree_level = row_data['degree level']
            area_of_interest = row_data['Area of Interest']
            program_name = row_data['program name']
            start_date = row_data['Start dates']

            high_school = row_data['high school']
            school_year = str(row_data['completion year'])
            school_month = row_data['high school completion month']

            demographics = row_data['demographics']


            
            app.fill_personal_info(
                email= email,
                first_name=first_name,
                last_name=last_name,
                address=address,
                phone=phone_number,
                password=password,
                city=city,
                state=state,
                zipcode=zip_code
            )


            time.sleep(30)
            logged_in = True
            # Fill additional information
            self.log_message(f"Instance {instance_num}: Filling additional information...")
            app.fill_additional_info(
                dob = dob,
                gender = gender,
                ssn=ssn
            )

            # Fill military information
            self.log_message(f"Instance {instance_num}: Filling military information...")
            app.fill_military_info(military_status="No")

            # # Fill program information
            # self.log_message(f"Instance {instance_num}: Filling program information...")
            # app.fill_program_info(
            #     degree_level = degree_level,
            #     area_of_interest = area_of_interest,
            #     program_name = program_name,
            #     start_date=start_date
            # )

            # Fill program information
            self.log_message(f"Instance {instance_num}: Filling program information...")
            app.fill_program_info(
                degree_level="Certificate",
                area_of_interest="Business and Management",
                program_name="Marketing Certificate (Undergraduate)",
                start_date="July 01, 2025"
            )           

            time.sleep(10)
            # Fill education information
            self.log_message(f"Instance {instance_num}: Filling education information...")
            app.fill_high_school_info(
                state=state,
                school_name=high_school,
                city=city,
                month=school_month,
                year=school_year
            )



            # Fill education confirmation
            self.log_message(f"Instance {instance_num}: Confirming education...")
            app.fill_education_confirmation()

            # Fill work information
            self.log_message(f"Instance {instance_num}: Filling work information...")
            app.fill_work_info()

            # Fill financial plan
            self.log_message(f"Instance {instance_num}: Filling financial plan...")
            app.fill_financial_plan()
            time.sleep(5)

            app.open_profile_info()
            app.edit_email_address("Phnxsysfs.kzmxv")
            time.sleep(5)

            app.switch_to_first_tab()
            time.sleep(5)
            app.refresh_page()
            time.sleep(15)

            app.review_section()
            
            time.sleep(15)
            # we reach the ack page
            app.update_loan()
            
            domain = email.split('@')[1]
            app.edit_email_address(domain)
            time.sleep(3.5)
            app.switch_to_first_tab()
            
            time.sleep(10)
            app.acknowledge_fill()

            time.sleep(10)
            app.sign_application(first_name, last_name)
            app.submit_application()

            time.sleep(10)
            app.action_items(demographics)

            # Update sheet status on completion
            self.gsheets.update_status(row_index, "COMPLETED")
            self.log_message(f"Instance {instance_num}: Form filling completed successfully!")
            
        except Exception as e:
            self.log_message(f"Error during form filling in instance {instance_num}: {str(e)}")
            # Update sheet status on failure
            if 'row_index' in locals():
                if logged_in:
                    self.gsheets.update_status(row_index, "FAILED")
                else:
                    self.gsheets.update_status(row_index, "")    
            raise
        finally:
            app.cleanup()


        

    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.logger.info(message)

