import time
import random
import csv
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from gologin import GoLogin


class FacebookGroupPoster:
    def __init__(self, profile_id, token):
        self.profile_id = profile_id
        self.token = token
        self.driver = None
        self.gl = None
    
    def start_gologin_browser(self):
        """Initialize and start GoLogin browser with Selenium"""
        try:
            print("=" * 60)
            print("Starting GoLogin profile...")
            print(f"Profile ID: {self.profile_id[:20]}...")
            
            # Initialize GoLogin
            self.gl = GoLogin({
                "token": self.token,
                "profile_id": self.profile_id,
                "extra_params": [
                       "--no-sandbox",
                       "--disable-setuid-sandbox"
                ]                
            })
            
            # Start the profile
            debugger_address = self.gl.start()
            print(f"✓ Profile started! Debugger address: {debugger_address}")
            
            # Get Chromium version
            chromium_version = self.gl.get_chromium_version()
            print(f"✓ GoLogin Chromium version: {chromium_version}")
            
            # Wait for browser to initialize
            print("→ Waiting for browser to initialize...")
            time.sleep(5)
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", debugger_address)
            
            # Connect Selenium with matching ChromeDriver
            print(f"→ Installing ChromeDriver version {chromium_version}...")
            service = Service(ChromeDriverManager(driver_version=chromium_version).install())
            
            print("→ Connecting Selenium to GoLogin browser...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            print("✓ Selenium connected successfully!")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"✗ Error starting GoLogin browser: {str(e)}")
            return False
    
    def post_image_or_video(self, group_url, file_path, description=""):
        """Post image or video to Facebook group"""
        try:
            # Add /media to the group URL for image/video uploads
            if not group_url.endswith('/'):
                group_url += '/'
            media_url = group_url + 'media'
            
            print(f"\n{'='*60}")
            print(f"POSTING IMAGE/VIDEO")
            print("="*60)
            print(f"→ Navigating to: {media_url}")
            self.driver.get(media_url)
            
            # Wait for page to load
            time.sleep(random.uniform(8, 12))
            
            # Verify file exists
            if not os.path.exists(file_path):
                print(f"✗ Error: File not found at {file_path}")
                return False
            
            print(f"✓ File found: {file_path}")
            
            # Find and upload file
            print("→ Looking for file input...")
            wait = WebDriverWait(self.driver, 10)
            file_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='file']")
            ))
            
            print(f"→ Uploading file: {file_path}")
            file_input.send_keys(file_path)
            print("✓ File uploaded successfully")
            
            # Wait for upload to process
            time.sleep(5)
            
            # Add description/caption if provided
            if description:
                print(f"→ Adding description: {description}")
                try:
                    text_field_selector = 'div[contenteditable="true"][role="textbox"][data-lexical-editor="true"]'
                    text_field = wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, text_field_selector)
                    ))
                    text_field.click()
                    time.sleep(1)
                    text_field.send_keys(description)
                    print("✓ Description added successfully")
                    time.sleep(2)
                except Exception as e:
                    print(f"⚠ Could not add description: {str(e)}")
            
            # Click Post button
            print("→ Clicking Post button...")
            try:
                post_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//span[text()='Post']")
                ))
                post_button.click()
                print("✓ Post button clicked successfully")
                time.sleep(5)
                
                print("✅ IMAGE/VIDEO POSTED SUCCESSFULLY!")
                return True
                
            except Exception as e:
                print(f"✗ Could not click Post button: {str(e)}")
                return False
            
        except Exception as e:
            print(f"✗ Error posting image/video: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def post_text(self, group_url, text_content):
        """Post text-only content to Facebook group"""
        try:
            print(f"\n{'='*60}")
            print(f"POSTING TEXT")
            print("="*60)
            print(f"→ Navigating to: {group_url}")
            self.driver.get(group_url)
            
            # Wait for page to load
            time.sleep(random.uniform(8, 12))
            
            wait = WebDriverWait(self.driver, 10)
            
            # Click on "Write something" to open post composer
            print("→ Opening post composer...")
            try:
                composer_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(), 'Write something')]")
                ))
                composer_button.click()
                print("✓ Clicked on post composer")
                time.sleep(2)
            except Exception as e:
                print(f"⚠ Could not find 'Write something' button: {str(e)}")
                return False
            
            # Find and click on the text input area
            print(f"→ Writing text: {text_content}")
            try:
                text_area = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div[aria-placeholder="Create a public post…"]')
                ))
                text_area.click()
                time.sleep(1)
                text_area.send_keys(text_content)
                print(f"✓ Successfully wrote text")
                time.sleep(2)
            except Exception as e:
                print(f"✗ Could not write text: {str(e)}")
                return False
            
            # Click Post button
            print("→ Clicking Post button...")
            try:
                self.driver.execute_script('document.querySelector(\'div[aria-label="Post"]\').click();')
                print("✓ Post button clicked")
                time.sleep(5)
                
                print("✅ TEXT POST PUBLISHED SUCCESSFULLY!")
                return True
                
            except Exception as e:
                print(f"✗ Could not click Post button: {str(e)}")
                return False
            
        except Exception as e:
            print(f"✗ Error posting text: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_post(self, group_url, content_type, content_path, description):
        """Main method to create a post based on content type"""
        try:
            content_type = content_type.lower().strip()
            
            if content_type in ['image', 'video']:
                return self.post_image_or_video(group_url, content_path, description)
            elif content_type == 'text':
                return self.post_text(group_url, description)
            else:
                print(f"✗ Unknown content type: {content_type}")
                return False
                
        except Exception as e:
            print(f"✗ Error creating post: {str(e)}")
            return False
    
    def cleanup(self):
        """Cleanup browser and profile"""
        try:
            if self.driver:
                print("\n→ Closing browser...")
                self.driver.quit()
                time.sleep(2)
            
            if self.gl:
                print("→ Stopping GoLogin profile...")
                self.gl.stop()
                print("✓ Profile stopped")
                time.sleep(3)
        except Exception as e:
            print(f"⚠ Cleanup error: {str(e)}")


def read_posts_from_csv(csv_file):
    """Read posts configuration from CSV file with support for multiple group URLs and status"""
    posts = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row_index, row in enumerate(csv_reader, start=2):  # start=2 because row 1 is header
                # Split group URLs by comma
                group_urls = [url.strip() for url in row['group_urls'].split(',') if url.strip()]
                
                # Get status (default to empty string if not present)
                status = row.get('status', '').strip().lower()
                
                posts.append({
                    'profile_id': row['profile_id'].strip(),
                    'token': row['token'].strip(),
                    'group_urls': group_urls,
                    'content_type': row['content_type'].strip(),
                    'content_path': row['content_path'].strip(),
                    'description': row['description'].strip(),
                    'status': status,
                    'row_index': row_index  # Track the row number for updating
                })
        
        print(f"✓ Loaded {len(posts)} profiles from CSV")
        
        # Count profiles by status
        completed_count = sum(1 for p in posts if p['status'] == 'completed')
        pending_count = len(posts) - completed_count
        
        print(f"✓ Completed profiles: {completed_count}")
        print(f"✓ Pending profiles: {pending_count}")
        
        # Count total groups for pending profiles
        total_groups = sum(len(post['group_urls']) for post in posts if post['status'] != 'completed')
        print(f"✓ Total groups to post (pending only): {total_groups}")
        
        return posts
    except FileNotFoundError:
        print(f"✗ Error: CSV file '{csv_file}' not found!")
        return []
    except Exception as e:
        print(f"✗ Error reading CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def update_profile_status(csv_file, row_index, new_status):
    """Update the status of a specific profile in the CSV file"""
    try:
        # Read all rows
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            fieldnames = csv_reader.fieldnames
            
            # Ensure 'status' column exists
            if 'status' not in fieldnames:
                fieldnames = list(fieldnames) + ['status']
            
            for row in csv_reader:
                rows.append(row)
        
        # Update the specific row
        if row_index - 2 < len(rows):  # -2 because row_index starts at 2 (after header)
            rows[row_index - 2]['status'] = new_status
            print(f"✓ Updated row {row_index} status to: {new_status}")
        
        # Write back to CSV
        with open(csv_file, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        return True
        
    except Exception as e:
        print(f"✗ Error updating status: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def process_all_posts(csv_file, delay_between_groups=10, delay_between_profiles=30):
    """Process all posts from CSV file with multiple groups per profile and status tracking"""
    
    print("\n" + "="*60)
    print("FACEBOOK GROUP AUTO-POSTER - MULTI-GROUPS PER PROFILE")
    print("="*60)
    
    # Read posts from CSV
    all_profiles = read_posts_from_csv(csv_file)
    
    if not all_profiles:
        print("✗ No profiles to process. Exiting...")
        return False
    
    # Filter out completed profiles
    profiles = [p for p in all_profiles if p['status'] != 'completed']
    
    if not profiles:
        print("\n✅ All profiles are already completed!")
        print("✓ No profiles to process in this cycle.")
        return True
    
    print(f"\n📋 Processing {len(profiles)} pending profiles (skipping {len(all_profiles) - len(profiles)} completed)")
    
    # Statistics
    total_profiles = len(profiles)
    total_posts = sum(len(profile['group_urls']) for profile in profiles)
    successful = 0
    failed = 0
    results = []
    
    # Process each profile
    for profile_index, profile in enumerate(profiles, 1):
        print("\n" + "#"*60)
        print(f"PROCESSING PROFILE {profile_index}/{total_profiles}")
        print("#"*60)
        print(f"Profile ID: {profile['profile_id'][:20]}...")
        print(f"Groups to post: {len(profile['group_urls'])}")
        print(f"Content Type: {profile['content_type']}")
        print(f"Current status: {profile['status'] if profile['status'] else 'empty'}")
        print("#"*60)
        
        poster = None
        profile_success = True  # Track if all groups succeeded for this profile
        
        try:
            # Create poster instance for this profile
            poster = FacebookGroupPoster(
                profile_id=profile['profile_id'],
                token=profile['token']
            )
            
            # Start GoLogin browser
            if not poster.start_gologin_browser():
                print(f"✗ Failed to start browser for profile {profile_index}")
                profile_success = False
                # Mark all groups for this profile as failed
                for group_url in profile['group_urls']:
                    failed += 1
                    results.append({
                        'profile': profile_index,
                        'group_url': group_url,
                        'success': False,
                        'reason': 'Failed to start browser'
                    })
                continue
            
            # Post to each group for this profile
            for group_index, group_url in enumerate(profile['group_urls'], 1):
                print(f"\n{'='*60}")
                print(f"Profile {profile_index}/{total_profiles} - Group {group_index}/{len(profile['group_urls'])}")
                print(f"{'='*60}")
                print(f"Group URL: {group_url}")
                
                try:
                    # Create the post
                    success = poster.create_post(
                        group_url=group_url,
                        content_type=profile['content_type'],
                        content_path=profile['content_path'],
                        description=profile['description']
                    )
                    
                    # Record result
                    if success:
                        successful += 1
                        print(f"\n✅ Posted to group {group_index}/{len(profile['group_urls'])} - SUCCESS")
                        results.append({
                            'profile': profile_index,
                            'group_url': group_url,
                            'success': True,
                            'reason': 'Posted successfully'
                        })
                    else:
                        failed += 1
                        profile_success = False  # Mark profile as not fully successful
                        print(f"\n❌ Posted to group {group_index}/{len(profile['group_urls'])} - FAILED")
                        results.append({
                            'profile': profile_index,
                            'group_url': group_url,
                            'success': False,
                            'reason': 'Post failed'
                        })
                    
                except Exception as e:
                    failed += 1
                    profile_success = False  # Mark profile as not fully successful
                    print(f"\n✗ Error posting to group: {str(e)}")
                    results.append({
                        'profile': profile_index,
                        'group_url': group_url,
                        'success': False,
                        'reason': str(e)
                    })
                
                # Wait before posting to next group (within same profile)
                if group_index < len(profile['group_urls']):
                    print(f"\n⏳ Waiting {delay_between_groups} seconds before next group...")
                    time.sleep(delay_between_groups)
            
            # Update profile status to "completed" if all groups succeeded
            if profile_success:
                print(f"\n{'='*60}")
                print(f"✅ ALL GROUPS COMPLETED FOR PROFILE {profile_index}")
                print(f"{'='*60}")
                print("→ Updating status to 'completed' in CSV...")
                
                if update_profile_status(csv_file, profile['row_index'], 'completed'):
                    print("✓ Status updated successfully!")
                else:
                    print("⚠️  Warning: Could not update status in CSV")
            else:
                print(f"\n{'='*60}")
                print(f"⚠️  SOME GROUPS FAILED FOR PROFILE {profile_index}")
                print(f"{'='*60}")
                print("→ Status remains empty - will retry in next cycle")
            
        except Exception as e:
            print(f"\n✗ Error processing profile {profile_index}: {str(e)}")
            profile_success = False
            # Mark remaining groups as failed
            for group_url in profile['group_urls']:
                if not any(r['group_url'] == group_url and r['profile'] == profile_index for r in results):
                    failed += 1
                    results.append({
                        'profile': profile_index,
                        'group_url': group_url,
                        'success': False,
                        'reason': str(e)
                    })
        
        finally:
            # Cleanup browser for this profile
            if poster:
                poster.cleanup()
        
        # Wait before processing next profile
        if profile_index < total_profiles:
            print(f"\n⏳ Waiting {delay_between_profiles} seconds before next profile...")
            time.sleep(delay_between_profiles)
    
    # Print final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total Profiles Processed: {total_profiles}")
    print(f"Total Posts Attempted: {total_posts}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    if total_posts > 0:
        print(f"Success Rate: {(successful/total_posts*100):.1f}%")
    print("="*60)
    
    print("\n📋 DETAILED RESULTS:")
    print("-"*60)
    for result in results:
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        print(f"\nProfile #{result['profile']}: {status}")
        print(f"  Group: {result['group_url'][:50]}...")
        if not result['success']:
            print(f"  Reason: {result['reason']}")
    print("-"*60)
    
    return True


def run_with_24h_repeat(csv_file, delay_between_groups=10, delay_between_profiles=30):
    """Run the posting process and repeat every 24 hours"""
    
    run_count = 0
    
    while True:
        run_count += 1
        
        print("\n" + "🔄"*30)
        print(f"POSTING CYCLE #{run_count}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🔄"*30 + "\n")
        
        # Process all posts
        success = process_all_posts(
            csv_file=csv_file,
            delay_between_groups=delay_between_groups,
            delay_between_profiles=delay_between_profiles
        )
        
        if not success:
            print("\n❌ Posting cycle failed!")
        else:
            print("\n✅ POSTING CYCLE COMPLETED!")
        
        # Calculate next run time
        next_run = datetime.now() + timedelta(hours=24)
        print("\n" + "⏰"*30)
        print(f"Next posting cycle at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Waiting 24 hours...")
        print(f"Note: Only profiles with empty status will be processed")
        print("⏰"*30)
        
        # Wait for 24 hours (86400 seconds)
        # Show countdown every hour
        remaining_seconds = 86400
        
        while remaining_seconds > 0:
            hours_left = remaining_seconds // 3600
            minutes_left = (remaining_seconds % 3600) // 60
            
            print(f"\r⏳ Time until next cycle: {hours_left}h {minutes_left}m remaining...", end='', flush=True)
            
            # Sleep for 5 minutes and update
            sleep_time = min(300, remaining_seconds)  # Sleep 5 min or remaining time
            time.sleep(sleep_time)
            remaining_seconds -= sleep_time
        
        print("\n")  # New line after countdown


# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    # Configuration
    CSV_FILE = "profiles.csv"  # Your CSV file name
    DELAY_BETWEEN_GROUPS = 10  # Seconds to wait between groups (same profile)
    DELAY_BETWEEN_PROFILES = 30  # Seconds to wait between profiles
    ENABLE_24H_REPEAT = True  # Set to False to run only once
    
    print("\n" + "="*60)
    print("FACEBOOK GROUP AUTO-POSTER WITH STATUS TRACKING")
    print("="*60)
    print(f"CSV File: {CSV_FILE}")
    print(f"Delay between groups: {DELAY_BETWEEN_GROUPS} seconds")
    print(f"Delay between profiles: {DELAY_BETWEEN_PROFILES} seconds")
    print(f"24-hour repeat: {'ENABLED' if ENABLE_24H_REPEAT else 'DISABLED'}")
    print("="*60)
    
    print("\n📋 CSV FORMAT EXPECTED:")
    print("  profile_id, token, group_urls, content_type, content_path, description, status")
    print("\n  group_urls: Use comma to separate multiple groups")
    print("  Example: https://facebook.com/groups/123,https://facebook.com/groups/456")
    print("\n  status: Leave empty for new profiles, will auto-update to 'completed'")
    print("  - Empty = Will be processed")
    print("  - completed = Will be skipped")
    print("="*60)
    
    print("\n📝 HOW STATUS TRACKING WORKS:")
    print("  1. Bot processes profiles with empty status")
    print("  2. After all groups succeed → status = 'completed'")
    print("  3. Next cycle (after 24h) → skips 'completed' profiles")
    print("  4. Only retries profiles with empty status")
    print("="*60)
    
    input("\n⏸️  Press ENTER to start posting...")
    
    if ENABLE_24H_REPEAT:
        # Run with 24-hour repeat
        run_with_24h_repeat(
            csv_file=CSV_FILE,
            delay_between_groups=DELAY_BETWEEN_GROUPS,
            delay_between_profiles=DELAY_BETWEEN_PROFILES
        )
    else:
        # Run once
        process_all_posts(
            csv_file=CSV_FILE,
            delay_between_groups=DELAY_BETWEEN_GROUPS,
            delay_between_profiles=DELAY_BETWEEN_PROFILES
        )
    
    print("\n" + "="*60)
    print("SCRIPT FINISHED")
    print("="*60)
