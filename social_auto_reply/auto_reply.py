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
from google import genai
from openai import OpenAI
import re
from selenium.webdriver.common.action_chains import ActionChains



class SocialMediaAutoReply:
    def __init__(self, profile_id, token, platform, ai_provider='static', ai_api_key='', static_reply='', pin='', system_prompt=''):
        self.profile_id = profile_id
        self.token = token
        self.platform = platform.lower()
        self.driver = None
        self.gl = None
        self.replied_messages = set()  # Track already replied messages
        self.ai_provider = ai_provider.lower()  # 'gpt', 'gemini', or 'static'
        self.ai_api_key = ai_api_key
        self.static_reply = static_reply
        self.pin = pin  # PIN for platforms that require it (Twitter/X, Facebook)
        self.system_prompt = system_prompt if system_prompt else "You are a helpful social media assistant. Reply to messages in a friendly, professional, and concise manner."
        
        # Initialize AI client if using AI
        if self.ai_provider == 'gpt' and self.ai_api_key:
            self.openai_client = OpenAI(api_key=self.ai_api_key)
        elif self.ai_provider == 'gemini' and self.ai_api_key:
            self.gemini_client = genai.Client(api_key=self.ai_api_key)
        else:
            self.openai_client = None
            self.gemini_client = None
    
    def extract_sender_name(self):
        """Extract sender name from the current conversation page"""
        try:
            # Try different selectors for different platforms
            name_selectors = [
                # Instagram - name with title attribute (most specific)
                "//h2//span[@title]",
                "//span[@title and string-length(@title) > 0]",
                
                # X/Twitter - conversation header with specific classes
                "//div[@data-testid='dm-conversation-header']//div[contains(@class, 'font-chirp') and contains(@class, 'font-medium')]",
                "//div[@data-testid='dm-conversation-header']//span",  # Twitter fallback
                
                # Facebook - h2 with specific classes
                "//h2[contains(@class, 'x1vvkbs')]//span[contains(@class, 'x1vvkbs')]",
                "//h2[contains(@class, 'html-h2')]//span[contains(@class, 'x1hl2dhg')]",
                "//h2[contains(@class, 'name')]",  # Facebook older
                
                # TikTok - chat nickname
                "//p[@data-e2e='chat-nickname']",
                "//p[contains(@class, 'PNickname')]",
                
                # Snapchat - nonIntl class
                "//span[contains(@class, 'bIpkz')]//span[@class='nonIntl']",
                "//span[@class='nonIntl' and string-length(text()) > 0]",
                
                # Generic selectors (fallback)
                "//span[contains(@dir, 'auto')][1]",  # Facebook alternate
                "//header//span[contains(@class, 'username')]",  # Instagram older
                "//h1//span",  # General header
                "//div[@role='heading']//span",
            ]
            
            for selector in name_selectors:
                try:
                    name_element = self.driver.find_element(By.XPATH, selector)
                    if name_element:
                        # For elements with title attribute, prefer the title
                        if name_element.get_attribute('title'):
                            name = name_element.get_attribute('title').strip()
                        else:
                            name = name_element.text.strip()
                        
                        # Clean up name (remove extra text)
                        name = name.split('\n')[0].strip()
                        if len(name) > 0 and len(name) < 50:  # Sanity check
                            print(f"✓ Extracted sender name: {name}")
                            return name
                except:
                    continue
            
            return ''  # Return empty if not found
        except Exception as e:
            print(f"⚠ Could not extract sender name: {str(e)}")
            return ''
    
    def parse_system_prompt_variables(self, sender_name='', incoming_message='', conversation_context=''):
        """Parse and replace variables in system prompt
        
        Supported variables:
        - %name% : Sender's name
        - %platform% : Current platform (facebook, twitter, etc.)
        - %message% : The incoming message
        - %context% : Brief conversation context/summary
        - %time% : Current time
        - %date% : Current date
        """
        try:
            prompt = self.system_prompt
            
            # Replace variables
            prompt = prompt.replace('%name%', sender_name if sender_name else 'User')
            prompt = prompt.replace('%platform%', self.platform.capitalize())
            prompt = prompt.replace('%message%', incoming_message if incoming_message else '')
            prompt = prompt.replace('%context%', conversation_context if conversation_context else '')
            prompt = prompt.replace('%time%', datetime.now().strftime('%H:%M:%S'))
            prompt = prompt.replace('%date%', datetime.now().strftime('%Y-%m-%d'))
            
            return prompt
        except Exception as e:
            print(f"⚠ Error parsing system prompt variables: {str(e)}")
            return self.system_prompt
    
    def remove_emojis(self, text):
        """Remove emojis from text to avoid ChromeDriver BMP issues"""
        # Pattern to match emojis and other non-BMP characters
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA00-\U0001FA6F"  # extended symbols
            "\U00002600-\U000026FF"  # miscellaneous symbols
            "\U00002700-\U000027BF"
            "]+", 
            flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text).strip()
    
    def generate_ai_reply(self, incoming_message, conversation_history=None, sender_name=''):
        """Generate AI-powered reply based on incoming message and conversation history"""
        try:
            # Create conversation context summary
            conversation_context = ''
            if conversation_history:
                context_msgs = [f"{msg.get('role', 'user')}: {msg.get('content', '')[:50]}..." for msg in conversation_history[-3:]]
                conversation_context = ' | '.join(context_msgs)
            
            # Parse system prompt with variables
            parsed_system_prompt = self.parse_system_prompt_variables(
                sender_name=sender_name,
                incoming_message=incoming_message,
                conversation_context=conversation_context
            )
            
            if self.ai_provider == 'gpt' and self.openai_client:
                print("→ Generating GPT reply...")
                # Build messages array with system prompt and conversation history
                messages = [{"role": "system", "content": parsed_system_prompt}]
                
                # Add conversation history if available
                if conversation_history:
                    for msg in conversation_history:
                        messages.append({"role": msg.get('role', 'user'), "content": msg['content']})
                
                # Add the current incoming message
                messages.append({"role": "user", "content": incoming_message})
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=150,
                    temperature=0.7
                )
                return self.remove_emojis(response.choices[0].message.content.strip())
            
            elif self.ai_provider == 'gemini' and self.gemini_client:
                print("→ Generating Gemini reply...")
                # Build prompt with system prompt and conversation history
                full_prompt = f"{parsed_system_prompt}\n\n"
                
                # Add conversation history if available
                if conversation_history:
                    full_prompt += "Previous conversation:\n"
                    for msg in conversation_history:
                        role = "User" if msg.get('role') == 'user' else "You"
                        full_prompt += f"{role}: {msg['content']}\n"
                    full_prompt += "\n"
                
                # Add the current incoming message
                full_prompt += f"Now reply to this message: {incoming_message}"
                
                response = self.gemini_client.models.generate_content(
                    model='gemini-flash-latest',
                    contents=full_prompt
                )
                return self.remove_emojis(response.text.strip())
            
            else:
                # Use static reply
                return self.static_reply
                
        except Exception as e:
            print(f"⚠ Error generating AI reply: {str(e)}")
            # Fallback to static reply
            return self.static_reply if self.static_reply else "Thank you for your message! I'll get back to you soon."
    
    def start_gologin_browser(self):
        """Initialize and start GoLogin browser with Selenium"""
        try:
            print("=" * 60)
            print("Starting GoLogin profile...")
            print(f"Profile ID: {self.profile_id[:20]}...")
            print(f"Platform: {self.platform.upper()}")
            
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
            time.sleep(10)
            
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
            
            # Clean up tabs - open new tab, switch to it, close others
            self.cleanup_browser_tabs()
            
            return True
            
        except Exception as e:
            print(f"✗ Error starting GoLogin browser: {str(e)}")
            return False
    
    def cleanup_browser_tabs(self):
        """Open new tab, switch to it, and close all other tabs to avoid confusion"""
        try:
            print("→ Cleaning up browser tabs...")
            
            # Get all current window handles
            all_handles = self.driver.window_handles
            print(f"  Found {len(all_handles)} existing tab(s)")
            
            # If only one tab, just use it
            if len(all_handles) == 1:
                print("✓ Only one tab exists, using it")
                return
            
            # Open a new tab
            self.driver.execute_script("window.open('about:blank', '_blank');")
            time.sleep(2)
            
            # Get updated handles
            updated_handles = self.driver.window_handles
            new_tab = updated_handles[-1]  # The newest tab
            
            # Switch to the new tab FIRST before closing anything
            self.driver.switch_to.window(new_tab)
            print(f"  Switched to new tab")
            
            # Close all other tabs (but stay on the new tab)
            for handle in all_handles:
                if handle != new_tab:  # Don't close the tab we're on
                    try:
                        # Try to close without switching (may not work in all browsers)
                        # So we temporarily switch, close, and come back
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                        # Immediately switch back to our safe tab
                        self.driver.switch_to.window(new_tab)
                    except Exception as e:
                        # If any error, make sure we're back on the new tab
                        try:
                            self.driver.switch_to.window(new_tab)
                        except:
                            pass  # Session might be invalid
            
            # Ensure we're on the new tab
            try:
                self.driver.switch_to.window(new_tab)
                print("✓ Browser tabs cleaned up - now using single fresh tab")
            except:
                print("⚠ Could not verify final tab state")
            
        except Exception as e:
            print(f"⚠ Error cleaning up tabs: {str(e)}")
            # Try to recover by just using whatever window is available
            try:
                handles = self.driver.window_handles
                if handles:
                    self.driver.switch_to.window(handles[0])
                    print("✓ Recovered by switching to first available tab")
            except:
                print("⚠ Could not recover - continuing with current session")
            # Continue anyway - not critical
    
    def read_conversation_history(self, max_messages=5):
        """Read recent conversation history from the current chat"""
        try:
            conversation_history = []
            
            # Try multiple selectors for message elements
            message_selectors = [
                "//div[contains(@class, 'message')]//div[contains(@dir, 'auto')]",
                "//div[@role='row']//div[contains(@dir, 'auto')]",
                "//div[contains(@class, 'text')]//span",
                "//div[@data-scope='messages_table']//span"
            ]
            
            messages = []
            for selector in message_selectors:
                try:
                    messages = self.driver.find_elements(By.XPATH, selector)
                    if messages and len(messages) > 0:
                        break
                except:
                    continue
            
            if messages:
                # Get last N messages (excluding the very last one which we're replying to)
                recent_messages = messages[-max_messages-1:-1] if len(messages) > max_messages else messages[:-1]
                
                for msg_element in recent_messages:
                    try:
                        text = msg_element.text.strip()
                        if text and len(text) > 0:
                            # Simple heuristic: alternate between user and assistant
                            # In a real scenario, you'd detect sender based on message alignment/class
                            conversation_history.append({
                                'role': 'user',  # Simplified - should detect actual sender
                                'content': text
                            })
                    except:
                        continue
            
            return conversation_history if len(conversation_history) > 0 else None
            
        except Exception as e:
            print(f"⚠ Error reading conversation history: {str(e)}")
            return None
    
    def enter_pin_if_required(self, platform='facebook'):
        """Check if PIN is required and enter it"""
        try:
            if not self.pin:
                return True
            
            print(f"→ Checking if PIN is required for {platform}...")
            time.sleep(8)  # Increased wait time for modal to appear
            
            # For Facebook, input is already focused - just type the PIN directly
            if platform == 'facebook':
                print("→ Entering PIN directly (input should be focused)...")
                try:
                    # Just send the keys - the input should already be focused
                    action = ActionChains(self.driver)
                    action.send_keys(self.pin).perform()
                    print(f"✓ Entered PIN: {self.pin}")
                    time.sleep(random.uniform(4, 8))
                    return True
                except Exception as e:
                    print(f"⚠ Could not enter PIN directly: {str(e)}")
                    # Fall through to try other methods
            
            # First, check for Twitter/X multi-input passcode (4 separate digit inputs)
            try:
                # Look for the Twitter/X passcode container
                twitter_pin_container = self.driver.find_element(
                    By.XPATH, 
                    "//div[@data-testid='pin-code-input-container']"
                )
                
                if twitter_pin_container and twitter_pin_container.is_displayed():
                    print("✓ Twitter/X passcode input detected! Entering passcode...")
                    
                    # Find all individual digit inputs
                    digit_inputs = twitter_pin_container.find_elements(
                        By.XPATH,
                        ".//input[@inputmode='numeric' and @maxlength='1']"
                    )
                    
                    if digit_inputs and len(digit_inputs) >= len(self.pin):
                        # Enter each digit into its respective input field
                        for i, digit in enumerate(self.pin[:len(digit_inputs)]):
                            digit_inputs[i].click()
                            time.sleep(0.2)
                            digit_inputs[i].send_keys(digit)
                            time.sleep(0.4)
                        
                        print(f"✓ Entered {len(self.pin)} digit passcode!")
                        time.sleep(random.uniform(4, 8))
                        
                        # After entering all digits, the form usually auto-submits
                        # But check if we need to click a submit button
                        time.sleep(4)
                        return True
                    else:
                        print(f"⚠ Found {len(digit_inputs) if digit_inputs else 0} input fields, PIN has {len(self.pin)} digits")
            except:
                pass  # Not Twitter/X multi-input, try other selectors
            
            # Try to find single PIN input field (Facebook and other platforms)
            pin_selectors = [
                # Facebook PIN selectors - most specific first
                "//input[@id='mw-numeric-code-input-prevent-composer-focus-steal']",  # Facebook messenger PIN
                "//input[@type='text' and @aria-label='PIN']",
                "//input[@type='text' and contains(@aria-label, 'PIN')]",
                "//input[@type='text' and @autocomplete='one-time-code']",
                "//input[@type='password' and contains(@aria-label, 'PIN')]",
                "//input[@type='tel' and contains(@aria-label, 'PIN')]",
                "//input[@type='password' and contains(@placeholder, 'PIN')]",
                "//input[@type='tel' and contains(@placeholder, 'PIN')]",
                "//input[@autocomplete='one-time-code']",
                "//input[@inputmode='numeric' and @type='password']",
                # Generic PIN/passcode selectors
                "//input[@data-testid='ocfEnterTextTextInput']",
                "//input[@name='text' and @type='text']",
                "//input[@autocomplete='off' and @type='text']",
            ]
            
            pin_input = None
            # Try multiple times to find the PIN input (modal may take time to appear)
            for attempt in range(3):
                if pin_input:
                    break
                
                for selector in pin_selectors:
                    try:
                        pin_input = self.driver.find_element(By.XPATH, selector)
                        if pin_input and pin_input.is_displayed():
                            print(f"✓ PIN input found with selector: {selector[:50]}...")
                            break
                        pin_input = None
                    except:
                        continue
                
                if not pin_input and attempt < 2:
                    print(f"  Attempt {attempt + 1}: No PIN input found, waiting...")
                    time.sleep(3)
            
            if pin_input:
                print(f"✓ PIN input detected! Entering PIN...")
                pin_input.clear()
                pin_input.send_keys(self.pin)
                time.sleep(2)
                
                # Try to find and click submit/next button
                submit_selectors = [
                    "//button[contains(text(), 'Next')]",
                    "//button[contains(text(), 'Submit')]",
                    "//button[contains(text(), 'Continue')]",
                    "//button[contains(text(), 'Verify')]",
                    "//button[@type='submit']",
                    "//div[@role='button' and contains(text(), 'Next')]",
                    "//span[text()='Next']/ancestor::div[@role='button']",
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_btn = self.driver.find_element(By.XPATH, selector)
                        if submit_btn and submit_btn.is_displayed():
                            submit_btn.click()
                            print("✓ PIN submitted!")
                            time.sleep(random.uniform(6, 10))
                            return True
                    except:
                        continue
                
                # If no button found, try pressing Enter
                pin_input.send_keys(Keys.RETURN)
                print("✓ PIN submitted via Enter key!")
                time.sleep(random.uniform(6, 10))
                return True
            else:
                print("✓ No PIN required")
                return True
                
        except Exception as e:
            print(f"⚠ Error checking/entering PIN: {str(e)}")
            return True  # Continue anyway
    
    def facebook_auto_reply(self, reply_message):
        """Auto-reply to Facebook messages (including message requests)"""
        try:
            print(f"\n{'='*60}")
            print("FACEBOOK MESSENGER AUTO-REPLY")
            print("="*60)
            
            # Navigate to Facebook Messenger
            messenger_url = "https://www.facebook.com/messages"
            print(f"→ Navigating to: {messenger_url}")
            self.driver.get(messenger_url)
            time.sleep(random.uniform(10, 16))
            
            # Check and enter PIN if required
            self.enter_pin_if_required('facebook')
            
            time.sleep(random.uniform(20, 30))
            
            wait = WebDriverWait(self.driver, 30)
            
            # Process both regular messages and message requests
            processed_any = False
            
            # 1. Check regular unread messages
            print("→ Checking regular unread messages...")
            try:
                unread_conversations = self.driver.find_elements(
                    By.XPATH, 
                    "//a[@role='link'][.//div[contains(@class, 'xzpqnlu')]]"
                )
                
                if unread_conversations:
                    print(f"✓ Found {len(unread_conversations)} unread conversation(s)")
                    processed_any = True
                    
                    for index, conversation in enumerate(unread_conversations[:5], 1):
                        try:
                            print(f"\n→ Processing regular conversation {index}...")
                            conversation.click()
                            time.sleep(random.uniform(2, 4))
                            
                            # Read conversation history
                            conversation_history = self.read_conversation_history(max_messages=5)
                            
                            # Extract sender name
                            sender_name = self.extract_sender_name()
                            
                            # Try to read the last message
                            incoming_message = "Hello"
                            try:
                                last_messages = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'message') or contains(@role, 'row')]//div[contains(@dir, 'auto')]")
                                if last_messages:
                                    incoming_message = last_messages[-1].text[:200]
                                    print(f"→ Received message: {incoming_message[:50]}...")
                            except:
                                pass
                            
                            # Generate reply with conversation history and sender name
                            reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                            
                            print("Problem not here")
                            
                            # Find message input box
                            message_box = wait.until(EC.presence_of_element_located(
                                (By.XPATH, "//div[@aria-label='Message' or @contenteditable='true']")
                            ))
                            
                            
                            # Type and send reply
                            print(f"→ Sending reply: {reply_text}")
                            try:
                                message_box.click()
                            except:
                                try:
                                    self.driver.execute_script("arguments[0].click();", message_box)
                                except:
                                    pass
                            
                            time.sleep(1)
                            message_box.send_keys(reply_text)
                            print("Problem not here")
                            time.sleep(2)
                            message_box.send_keys(Keys.RETURN)
                            
                            print("✓ Reply sent successfully!")
                            time.sleep(random.uniform(2, 4))
                            
                        except Exception as e:
                            # print(f"⚠ Could not reply to conversation {index}: {str(e)}")
                            print("⚠ No unread msgs or error in this conversation")
                            continue
                else:
                    print("✓ No regular unread messages")
            except Exception as e:
                try:
                    unread_conversations = self.driver.find_elements(
                        By.XPATH,
                        "//div[@role='grid' and @aria-label='Requests']//a[@role='link' and contains(@href, '/messages/requests/t/')] | "
                        "//div[@role='grid']//a[@role='link' and contains(@href, '/t/')]"
                    )
                    
                    if unread_conversations:
                        print(f"✓ Found {len(unread_conversations)} unread conversation(s)")
                        processed_any = True
                        
                        for index, conversation in enumerate(unread_conversations[:5], 1):
                            try:
                                print(f"\n→ Processing regular conversation {index}...")
                                conversation.click()
                                time.sleep(random.uniform(2, 4))
                                
                                # Read conversation history
                                conversation_history = self.read_conversation_history(max_messages=5)
                                
                                # Extract sender name
                                sender_name = self.extract_sender_name()
                                
                                # Try to read the last message
                                incoming_message = "Hello"
                                try:
                                    last_messages = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'message') or contains(@role, 'row')]//div[contains(@dir, 'auto')]")
                                    if last_messages:
                                        incoming_message = last_messages[-1].text[:200]
                                        print(f"→ Received message: {incoming_message[:50]}...")
                                except:
                                    pass
                                
                                # Generate reply with conversation history and sender name
                                reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                                
                                print("Problem not here")
                                
                                # Find message input box
                                message_box = wait.until(EC.presence_of_element_located(
                                    (By.XPATH, "//div[@aria-label='Message' or @contenteditable='true']")
                                ))
                                
                                
                                # Type and send reply
                                print(f"→ Sending reply: {reply_text}")
                                try:
                                    message_box.click()
                                except:
                                    try:
                                        self.driver.execute_script("arguments[0].click();", message_box)
                                    except:
                                        pass
                                
                                time.sleep(1)
                                message_box.send_keys(reply_text)
                                print("Problem not here")
                                time.sleep(2)
                                message_box.send_keys(Keys.RETURN)
                                
                                print("✓ Reply sent successfully!")
                                time.sleep(random.uniform(2, 4))
                                
                            except Exception as e:
                                # print(f"⚠ Could not reply to conversation {index}: {str(e)}")
                                print("⚠ No unread msgs or error in this conversation")
                                continue
                    else:
                        print("✓ No regular unread messages")
                except:
                    # print(f"⚠ Error checking regular messages: {str(e)}")
                    print("⚠ No unread msgs or error in this conversation")
                
            
            # 2. Check Message Requests
            print("\n→ Checking message requests...")
            try:
                # Navigate to message requests
                requests_url = "https://www.facebook.com/messages/requests"
                self.driver.get(requests_url)
                time.sleep(random.uniform(6, 10))
                
                self.enter_pin_if_required('facebook')
                
                time.sleep(random.uniform(20, 30))
                
                
                wait = WebDriverWait(self.driver, 60)
                
                
                
                # Look for message requests with more specific selector
                request_conversations = self.driver.find_elements(
                    By.XPATH,
                    "//div[@role='grid' and @aria-label='Requests']//a[@role='link' and contains(@href, '/messages/requests/t/')] | "
                    "//div[@role='grid']//a[@role='link' and contains(@href, '/t/')]"
                )
                
                if request_conversations:
                    print(f"✓ Found {len(request_conversations)} message request(s)")
                    processed_any = True
                    
                    for index, conversation in enumerate(request_conversations[:3], 1):  # Process up to 3 requests
                        try:
                            print(f"\n→ Processing message request {index}...")
                            conversation.click()
                            time.sleep(random.uniform(2, 4))
                            
                            # Accept the message request first
                            try:
                                accept_button = self.driver.find_element(
                                    By.XPATH,
                                    # "//div[@aria-label='Accept' or contains(text(), 'Accept')] | //button[contains(text(), 'Accept')]"
                                    "//div[@aria-label='Accept' or contains(text(), 'Accept')]"
                                )
                                accept_button.click()
                                print("✓ Message request accepted!")
                                time.sleep(random.uniform(1, 2))
                            except:
                                print("⚠ Could not find accept button (may already be accepted)")
                                
                            
                            # Read conversation history
                            conversation_history = self.read_conversation_history(max_messages=5)
                            
                            # Extract sender name
                            sender_name = self.extract_sender_name()
                            
                            # Try to read the last message
                            incoming_message = "Hello"
                            try:
                                last_messages = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'message') or contains(@role, 'row')]//div[contains(@dir, 'auto')]")
                                if last_messages:
                                    incoming_message = last_messages[-1].text[:200]
                                    print(f"→ Received message: {incoming_message[:50]}...")
                            except:
                                pass
                            
                            # Generate reply with conversation history and sender name
                            reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                            
                            # Find message input box
                            message_box = wait.until(EC.presence_of_element_located(
                                (By.XPATH, "//div[@aria-label='Message' or @contenteditable='true']")
                            ))
                            
                            # Type and send reply
                            print(f"→ Sending reply: {reply_text}")
                            message_box.click()
                            time.sleep(1)
                            message_box.send_keys(reply_text)
                            time.sleep(2)
                            message_box.send_keys(Keys.RETURN)
                            
                            print("✓ Reply sent to message request!")
                            time.sleep(random.uniform(2, 4))
                            
                        except Exception as e:
                            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
                            continue
                else:
                    print("✓ No message requests")
            except Exception as e:
                # print(f"⚠ Error checking message requests: {str(e)}")
                print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
                
            
            if not processed_any:
                print("\n✓ No new messages or requests to process")
                
            return True
            
        except Exception as e:
            # print(f"✗ Error in Facebook auto-reply: {str(e)}")
            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
            import traceback
            traceback.print_exc()
            return False
    
    def twitter_auto_reply(self, reply_message):
        """Auto-reply to Twitter/X direct messages (including message requests)"""
        try:
            print(f"\n{'='*60}")
            print("TWITTER/X DM AUTO-REPLY")
            print("="*60)
            
            # Navigate to Twitter Messages
            twitter_dm_url = "https://twitter.com/i/chat"
            print(f"→ Navigating to: {twitter_dm_url}")
            self.driver.get(twitter_dm_url)
            time.sleep(random.uniform(20, 26))
            
            # Check and enter PIN if required
            self.enter_pin_if_required('twitter')
            
            wait = WebDriverWait(self.driver, 30)
            processed_any = False
            
            # 1. Check regular unread messages
            print("→ Checking regular unread messages...")
            try:
                # Find conversations with unread indicator
                unread_conversations = self.driver.find_elements(
                    By.XPATH,
                    "//div[starts-with(@data-testid, 'dm-conversation-item') and contains(@aria-description, 'Unread')]"
                )
                
                if unread_conversations:
                    print(f"✓ Found {len(unread_conversations)} unread conversation(s)")
                    processed_any = True
                    
                    for index in range(min(5, len(unread_conversations))):
                        try:
                            # Click on conversation (re-fetch to avoid stale elements)
                            conversations = self.driver.find_elements(
                                By.XPATH,
                                "//div[starts-with(@data-testid, 'dm-conversation-item') and contains(@aria-description, 'Unread')]"
                            )
                            if conversations:
                                print(f"\n→ Processing conversation {index + 1}...")
                                conversations[index].click()
                                # self.driver.execute_script("arguments[0].click();", conversations[index])
                                time.sleep(random.uniform(4, 8))
                                
                                # Read conversation history
                                conversation_history = self.read_conversation_history(max_messages=5)
                                
                                # Get the last message text
                                incoming_message = "Hello"
                                try:
                                    message_list = self.driver.find_element(
                                        By.XPATH,
                                        "//div[@data-testid='dm-message-list']//ul"
                                    )
                                    messages = message_list.find_elements(By.XPATH, "./li")
                                    
                                    if messages:
                                        last_message = messages[-1]
                                        # Extract text from the last message
                                        message_text_elements = last_message.find_elements(
                                            By.XPATH,
                                            ".//div[starts-with(@data-testid, 'message-text-')]//span[@dir='auto']//span[contains(@class, 'font-chirp')]"
                                        )
                                        if message_text_elements:
                                            incoming_message = message_text_elements[0].text[:200]
                                            print(f"→ Received message: {incoming_message[:50]}...")
                                except:
                                    pass
                                
                                # Generate reply with conversation history
                                sender_name = self.extract_sender_name()
                                reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                                
                                # Find message input (textarea element)
                                message_input = wait.until(EC.presence_of_element_located(
                                    (By.XPATH, "//textarea[@data-testid='dm-composer-textarea']")
                                ))
                                
                                # Send reply
                                print(f"→ Sending reply: {reply_text}")
                                message_input.click()
                                time.sleep(1)
                                message_input.send_keys(reply_text)
                                time.sleep(2)
                                
                                try: 
                                    # Click send button
                                    send_button = self.driver.find_element(
                                        By.XPATH,
                                        "//div[@data-testid='dm-composer-send-button']"
                                    )
                                    send_button.click()
                                except:
                                    message_input.send_keys(Keys.RETURN)
                                
                                print(f"✓ Reply sent to conversation {index + 1}")
                                time.sleep(random.uniform(4, 8))
                        
                        except Exception as e:
                            # print(f"⚠ Could not reply to conversation {index + 1}: {str(e)}")
                            # print("⚠ No unread msgs or error in this conversation")
                            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")

                            continue
                else:
                    print("✓ No regular unread messages")
                    
            except Exception as e:
                # print(f"⚠ Error checking regular messages: {str(e)}")
                print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")

            
            # 2. Check Message Requests
            print("\n→ Checking message requests...")
            try:
                # Navigate to message requests
                requests_url = "https://x.com/messages/requests"
                self.driver.get(requests_url)
                time.sleep(random.uniform(6, 10))
                
                # Look for conversations in message requests (using correct selector)
                request_conversations = self.driver.find_elements(
                    By.XPATH,
                    "//div[@data-testid='conversation']"
                )
                
                if request_conversations:
                    print(f"✓ Found {len(request_conversations)} message request(s)")
                    processed_any = True
                    
                    for index in range(min(3, len(request_conversations))):  # Process up to 3 requests
                        try:
                            # Re-fetch conversations to avoid stale element
                            conversations = self.driver.find_elements(
                                By.XPATH,
                                "//div[@data-testid='conversation']"
                            )
                            if conversations and index < len(conversations):
                                print(f"\n→ Processing message request {index + 1}...")
                                self.driver.execute_script("arguments[0].click();", conversations[index])
                                time.sleep(random.uniform(4, 8))
                                
                                # Accept the message request if needed
                                try:
                                    accept_button = wait.until(EC.element_to_be_clickable(
                                        (By.XPATH, "//button[.//span[contains(text(), 'Accept')]]")
                                    ))
                                    accept_button.click()
                                    print("✓ Message request accepted!")
                                    time.sleep(random.uniform(4, 6))
                                except:
                                    print("⚠ Could not find accept button (may already be accepted)")
                                
                                # Read conversation history
                                conversation_history = self.read_conversation_history(max_messages=5)
                                
                                # Get the last message text
                                incoming_message = "Hello"
                                try:
                                    message_list = self.driver.find_element(
                                        By.XPATH,
                                        "//div[@data-testid='dm-message-list']//ul"
                                    )
                                    messages = message_list.find_elements(By.XPATH, "./li")
                                    
                                    if messages:
                                        last_message = messages[-1]
                                        # Extract text from the last message
                                        message_text_elements = last_message.find_elements(
                                            By.XPATH,
                                            ".//div[starts-with(@data-testid, 'message-text-')]//span[@dir='auto']//span[contains(@class, 'font-chirp')]"
                                        )
                                        if message_text_elements:
                                            incoming_message = message_text_elements[0].text[:200]
                                            print(f"→ Received message: {incoming_message[:50]}...")
                                except:
                                    pass
                                
                                # Generate reply with conversation history
                                sender_name = self.extract_sender_name()
                                reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                                
                                # Find message input (textarea element)
                                message_input = wait.until(EC.presence_of_element_located(
                                    (By.XPATH, "//textarea[@data-testid='dm-composer-textarea']")
                                ))
                                
                                # Send reply
                                print(f"→ Sending reply: {reply_text}")
                                message_input.click()
                                time.sleep(1)
                                message_input.send_keys(reply_text)
                                time.sleep(2)
                                
                                # Click send button
                                send_button = self.driver.find_element(
                                    By.XPATH,
                                    "//div[@data-testid='dm-composer-send-button']"
                                )
                                send_button.click()
                                
                                print(f"✓ Reply sent to message request {index + 1}")
                                time.sleep(random.uniform(4, 8))
                        
                        except Exception as e:
                            # print(f"⚠ Could not reply to message request {index + 1}: {str(e)}")
                            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")

                            continue
                else:
                    print("✓ No message requests")
            except Exception as e:
                # print(f"⚠ Error checking message requests: {str(e)}")
                print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
            
            if not processed_any:
                print("\n✓ No new messages or requests to process")
                
            return True
            
        except Exception as e:
            # print(f"✗ Error in Twitter auto-reply: {str(e)}")
            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")

            import traceback
            traceback.print_exc()
            return False
    
    def instagram_auto_reply(self, reply_message):
        """Auto-reply to Instagram direct messages (including message requests)"""
        try:
            print(f"\n{'='*60}")
            print("INSTAGRAM DM AUTO-REPLY")
            print("="*60)
            
            # Navigate to Instagram Direct
            instagram_dm_url = "https://www.instagram.com/direct/inbox/"
            print(f"→ Navigating to: {instagram_dm_url}")
            self.driver.get(instagram_dm_url)
            time.sleep(random.uniform(10, 16))
            
            wait = WebDriverWait(self.driver, 30)
            processed_any = False
            
            # 1. Check regular unread messages
            print("→ Checking regular unread messages...")
            try:
                # Look for unread conversations (usually have a blue dot indicator)
                unread_conversations = self.driver.find_elements(
                    By.XPATH,
                    "//div[@role='button'][.//div[text()='Unread']]"
                )
                
                if unread_conversations:
                    print(f"✓ Found {len(unread_conversations)} unread conversation(s)")
                    processed_any = True
                    
                    for index, conversation in enumerate(unread_conversations[:5], 1):
                        try:
                            print(f"\n→ Processing regular conversation {index}...")
                            conversation.click()
                            time.sleep(random.uniform(4, 8))
                            
                            # Read conversation history
                            conversation_history = self.read_conversation_history(max_messages=5)
                            
                            # Try to read the last message (actual message content in bubbles)
                            incoming_message = "Hello"
                            try:
                                last_messages = self.driver.find_elements(By.XPATH, "//div[@role='presentation']//div[@dir='auto' and contains(@class, 'x1gslohp')]")
                                if last_messages:
                                    incoming_message = last_messages[-1].text[:200]
                                    print(f"→ Received message: {incoming_message[:50]}...")
                            except:
                                pass
                            
                            # Generate reply with conversation history
                            sender_name = self.extract_sender_name()
                            reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                            
                            # Find message input
                            message_input = wait.until(EC.presence_of_element_located(
                                (By.XPATH, "//div[@placeholder='Message...' or @aria-label='Message' or @role='textbox' or @contenteditable='true' ]")
                            ))
                            
                            # Type and send reply
                            print(f"→ Sending reply: {reply_text}")
                            message_input.click()
                            time.sleep(1)
                            message_input.send_keys(reply_text)
                            time.sleep(2)
                            message_input.send_keys(Keys.RETURN)
                            
                            print("✓ Reply sent successfully!")
                            time.sleep(random.uniform(4, 8))
                            
                        except Exception as e:
                            # print(f"⚠ Could not reply to conversation {index}: {str(e)}")
                            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")

                            continue
                else:
                    print("✓ No regular unread messages")
            except Exception as e:
                # print(f"⚠ Error checking regular messages: {str(e)}")
                print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")

            
            # 2. Check Message Requests
            print("\n→ Checking message requests...")
            try:
                # Navigate to message requests
                requests_url = "https://www.instagram.com/direct/requests/"
                self.driver.get(requests_url)
                time.sleep(random.uniform(6, 10))
                
                # Look for clickable conversation buttons (all conversation items)
                # Find all conversation items (NOT the hidden requests folder)
                request_conversations = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((
                        By.XPATH,
                        "//div[@role='button' and @tabindex='0' and contains(@class, 'x1i10hfl') and .//img[@alt='user-profile-picture']]"
                    ))
                )

                # Alternative - find images then get their parent buttons:
                img_elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((
                        By.XPATH,
                        "//div[@role='button' and @tabindex='0']//img[@alt='user-profile-picture']"
                    ))
                )
                # Get the parent button for each image
                request_conversations = [img.find_element(By.XPATH, "./ancestor::div[@role='button' and @tabindex='0']") for img in img_elements]


                
                if request_conversations:
                    print(f"✓ Found {len(request_conversations)} message request(s)")
                    processed_any = True
                    
                    for index, conversation in enumerate(request_conversations[:3], 1):  # Process up to 3 requests
                        try:
                            print(f"\n→ Processing message request {index}...")
                            
                            # Click on the conversation to open it
                            try:
                                conversation.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", conversation)
                            time.sleep(random.uniform(2, 4))
                            
                            # Accept the message request first - click the Accept button
                            try:
                                # Look for the Accept button
                                accept_button = wait.until(EC.presence_of_element_located(
                                    (By.XPATH, "//div[@role='button' and text()='Accept'] | //button[contains(text(), 'Accept') or contains(text(), 'Allow')]")
                                ))
                                accept_button.click()
                                print("✓ Message request accepted!")
                                time.sleep(random.uniform(4, 6))
                            except Exception as e:
                                print(f"⚠ Could not reply to message request {index}: {str(e)}")
                                print("⚠ Could not find accept button (may already be accepted)")
                            
                            # Read conversation history
                            conversation_history = self.read_conversation_history(max_messages=5)
                            
                            # Try to read the last message (actual message content in bubbles)
                            incoming_message = "Hello"
                            try:
                                last_messages = self.driver.find_elements(By.XPATH, "//div[@role='row']//div[@dir='auto' and contains(@class, 'x1gslohp')]")
                                if last_messages:
                                    incoming_message = last_messages[-1].text[:200]
                                    print(f"→ Received message: {incoming_message[:50]}...")
                            except:
                                try:
                                    last_messages = self.driver.find_elements(By.XPATH, "//div[@role='presentation']//div[@dir='auto' and contains(@class, 'x1gslohp')]")
                                    if last_messages:
                                        incoming_message = last_messages[-1].text[:200]
                                        print(f"→ Received message: {incoming_message[:50]}...")
                                except:
                                    pass
                            
                            # Generate reply with conversation history
                            sender_name = self.extract_sender_name()
                            reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                            
                            # Find message input box (should be available after accepting)
                            message_input = wait.until(EC.presence_of_element_located(
                                (By.XPATH, "//textarea[@placeholder='Message...' or @aria-label='Message' or @role='textbox' or @contenteditable='true' ]")
                            ))
                            
                            # Type and send reply
                            print(f"→ Sending reply: {reply_text}")
                            message_input.click()
                            time.sleep(0.5)
                            message_input.send_keys(reply_text)
                            time.sleep(1)
                            message_input.send_keys(Keys.RETURN)
                            
                            print("✓ Reply sent to message request!")
                            time.sleep(random.uniform(4, 8))
                            
                            # Go back to requests page for next conversation
                            self.driver.get(requests_url)
                            time.sleep(random.uniform(4, 6))
                            
                            # Re-fetch conversations after processing one
                            request_conversations = self.driver.find_elements(
                                By.XPATH,
                                "//div[@role='button' and @tabindex='0' and contains(@class, 'x1i10hfl')]"
                            )
                            
                        except Exception as e:
                            print(f"⚠ Could not reply to message request {index}: {str(e)}")
                            # print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
                            
                            # Try to go back to requests page
                            try:
                                self.driver.get(requests_url)
                                time.sleep(random.uniform(4, 6))
                            except:
                                pass
                            continue
                else:
                    print("✓ No message requests")
            except Exception as e:
                print(f"⚠ Error checking message requests: {str(e)}")
                # print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
                
            
            if not processed_any:
                print("\n✓ No new messages or requests to process")
                
            return True
            
        except Exception as e:
            # print(f"✗ Error in Instagram auto-reply: {str(e)}")
            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
            import traceback
            traceback.print_exc()
            return False
    
    def tiktok_auto_reply(self, reply_message):
        """Auto-reply to TikTok direct messages (including message requests)"""
        try:
            print(f"\n{'='*60}")
            print("TIKTOK DM AUTO-REPLY")
            print("="*60)
            
            # Navigate to TikTok Messages
            tiktok_dm_url = "https://www.tiktok.com/messages"
            print(f"→ Navigating to: {tiktok_dm_url}")
            self.driver.get(tiktok_dm_url)
            time.sleep(random.uniform(10, 16))
            
            wait = WebDriverWait(self.driver, 30)
            processed_any = False
            
            # 1. Check regular unread messages
            print("→ Checking regular unread messages...")
            try:
                # Find unread conversations with the unread badge indicator
                unread_conversations = self.driver.find_elements(
                    By.XPATH,
                    "//div[@data-e2e='chat-list-item' and .//div[contains(@class, 'SpanNewMessage')]]"
                )
                
                if unread_conversations:
                    print(f"✓ Found {len(unread_conversations)} unread conversation(s)")
                    processed_any = True
                    
                    for index, conversation in enumerate(unread_conversations[:5], 1):
                        try:
                            print(f"\n→ Processing regular conversation {index}...")
                            conversation.click()
                            time.sleep(random.uniform(4, 8))
                            
                            # Read conversation history
                            conversation_history = self.read_conversation_history(max_messages=5)
                            
                            # Try to read the last message from the conversation
                            incoming_message = "Hello"
                            try:
                                # Find all chat items in the conversation
                                chat_items = self.driver.find_elements(
                                    By.XPATH, 
                                    "//div[@data-e2e='chat-item']"
                                )
                                if chat_items:
                                    # Get the last chat item
                                    last_chat_item = chat_items[-1]
                                    # Find the text content within it
                                    message_texts = last_chat_item.find_elements(
                                        By.XPATH, 
                                        ".//p[contains(@class, 'PText')]"
                                    )
                                    if message_texts:
                                        incoming_message = message_texts[0].text[:200]
                                        print(f"→ Received message: {incoming_message[:50]}...")
                            except:
                                pass
                            
                            # Generate reply with conversation history
                            sender_name = self.extract_sender_name()
                            reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                            
                            # Clean up reply - remove newlines to prevent multiple messages
                            reply_text = reply_text.replace('\n', ' ').replace('\r', ' ').strip()
                            # Remove multiple spaces
                            reply_text = ' '.join(reply_text.split())
                            
                            # Find message input box - it's a contenteditable div with aria-label
                            message_box = wait.until(EC.presence_of_element_located(
                                (By.XPATH, "//div[@contenteditable='true' and @aria-label='Send a message...'] | //div[@contenteditable='true' and contains(@class, 'DraftEditor-content')]")
                            ))
                            
                            # Type and send reply
                            print(f"→ Sending reply: {reply_text}")
                            message_box.click()
                            time.sleep(1)
                            message_box.send_keys(reply_text)
                            time.sleep(2)
                            message_box.send_keys(Keys.RETURN)
                            
                            # Check if TikTok blocked the message
                            time.sleep(3)
                            try:
                                blocked_notification = self.driver.find_elements(
                                    By.XPATH,
                                    "//*[@data-e2e='dm-message-notification'] | //*[@data-e2e='dm-warning']"
                                )
                                if blocked_notification:
                                    print("✗ MESSAGE BLOCKED BY TIKTOK — Reply was detected as a violation of Community Guidelines and was not delivered.")
                                    return True
                            except:
                                pass
                            
                            print("✓ Reply sent successfully!")
                            time.sleep(random.uniform(4, 8))
                            
                            return True
                            
                        except Exception as e:
                            print(f"⚠ Could not reply to conversation or no unread msgs")
                            return True
                else:
                    print("✓ No regular unread messages")
                    return True
            except Exception as e:
                print(f"⚠ Error checking regular messages or no msg to reply to. ")
                return True
            
            return True
            
            # 2. Check Message Requests
            print("\n→ Checking message requests...")
            try:
                # Click on "Requests" or "Message Requests" tab
                try:
                    requests_tab = self.driver.find_element(
                        By.XPATH,
                        "//div[contains(text(), 'Requests') or contains(text(), 'Request')] | //button[contains(text(), 'Requests')]"
                    )
                    requests_tab.click()
                    print("✓ Navigated to message requests")
                    time.sleep(random.uniform(4, 8))
                except:
                    print("⚠ Could not find message requests tab")
                    return processed_any
                
                # Look for message request conversations
                request_conversations = self.driver.find_elements(
                    By.XPATH,
                    "//div[@data-e2e='chat-list-item'] | //div[contains(@class, 'chat-item')]"
                )
                
                if request_conversations:
                    print(f"✓ Found {len(request_conversations)} message request(s)")
                    processed_any = True
                    
                    for index, conversation in enumerate(request_conversations[:3], 1):  # Process up to 3 requests
                        try:
                            print(f"\n→ Processing message request {index}...")
                            conversation.click()
                            time.sleep(random.uniform(4, 8))
                            
                            # Accept the message request first
                            try:
                                accept_button = self.driver.find_element(
                                    By.XPATH,
                                    "//button[contains(text(), 'Accept') or contains(text(), 'Allow')] | //div[@data-e2e='accept-request-button']"
                                )
                                accept_button.click()
                                print("✓ Message request accepted!")
                                time.sleep(random.uniform(2, 4))
                            except:
                                print("⚠ Could not find accept button (may already be accepted)")
                            
                            # Read conversation history
                            conversation_history = self.read_conversation_history(max_messages=5)
                            
                            # Try to read the last message
                            incoming_message = "Hello"
                            try:
                                last_messages = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'ChatMessage') or contains(@class, 'message')]//span")
                                if last_messages:
                                    incoming_message = last_messages[-1].text[:200]
                                    print(f"→ Received message: {incoming_message[:50]}...")
                            except:
                                pass
                            
                            # Generate reply with conversation history
                            sender_name = self.extract_sender_name()
                            reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                            
                            # Find message input box
                            message_box = wait.until(EC.presence_of_element_located(
                                (By.XPATH, "//div[@contenteditable='true' and @data-e2e='chat-input'] | //div[@contenteditable='true' and contains(@placeholder, 'Message')]")
                            ))
                            
                            # Type and send reply
                            print(f"→ Sending reply: {reply_text}")
                            message_box.click()
                            time.sleep(1)
                            message_box.send_keys(reply_text)
                            time.sleep(2)
                            message_box.send_keys(Keys.RETURN)
                            
                            # Check if TikTok blocked the message
                            time.sleep(3)
                            try:
                                blocked_notification = self.driver.find_elements(
                                    By.XPATH,
                                    "//*[@data-e2e='dm-message-notification'] | //*[@data-e2e='dm-warning']"
                                )
                                if blocked_notification:
                                    print("✗ MESSAGE BLOCKED BY TIKTOK — Reply was detected as a violation of Community Guidelines and was not delivered.")
                                    continue
                            except:
                                pass
                            
                            print("✓ Reply sent to message request!")
                            time.sleep(random.uniform(4, 8))
                            
                        except Exception as e:
                            print(f"⚠ Could not reply to message request {index}: {str(e)}")
                            continue
                else:
                    print("✓ No message requests")
            except Exception as e:
                print(f"⚠ Error checking message requests: {str(e)}")
            
            if not processed_any:
                print("\n✓ No new messages or requests to process")
                
            return True
            
        except Exception as e:
            # print(f"✗ Error in TikTok auto-reply: {str(e)}")
            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
            import traceback
            traceback.print_exc()
            return False
    
    def snapchat_auto_reply(self, reply_message):
        """Auto-reply to Snapchat web messages (including new contacts)"""
        try:
            print(f"\n{'='*60}")
            print("SNAPCHAT WEB AUTO-REPLY")
            print("="*60)
            
            # Navigate to Snapchat Web
            snapchat_url = "https://www.snapchat.com/web"
            print(f"→ Navigating to: {snapchat_url}")
            self.driver.get(snapchat_url)
            time.sleep(random.uniform(10, 16))
            
            wait = WebDriverWait(self.driver, 30)
            processed_any = False
            
            # 0. Handle notification popup if it appears
            print("→ Checking for notification popup...")
            try:
                # Look for the "Not now" button in the notification modal
                not_now_button = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(@class, 'Bnaur') and not(contains(@class, 're7ND')) and .//span[contains(text(), 'Not now')]]")
                ))
                print("✓ Found notification popup")
                not_now_button.click()
                print("✓ Clicked 'Not now' button")
                time.sleep(random.uniform(2, 4))
            except:
                print("✓ No notification popup found")
            
            # 1. First, check and accept all friend requests
            print("→ Checking for friend requests...")
            try:
                # Click the friend requests button
                friend_request_button = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//button[@title='View friend requests' or contains(@class, 'kwuI_')]")
                ))
                friend_request_button.click()
                print("✓ Opened friend requests panel")
                time.sleep(random.uniform(4, 6))
                
                # Find all "Accept" buttons
                accept_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@class, 'F7jpS') and .//span[text()='Accept']]"
                )
                
                if accept_buttons:
                    print(f"✓ Found {len(accept_buttons)} friend request(s) to accept")
                    
                    for index, accept_btn in enumerate(accept_buttons, 1):
                        try:
                            print(f"→ Accepting friend request {index}...")
                            accept_btn.click()
                            time.sleep(random.uniform(2, 4))
                            print(f"✓ Friend request {index} accepted!")
                        except Exception as e:
                            # print(f"⚠ Could not accept request {index}: {str(e)}")
                            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
                            
                            continue
                    
                    print("✓ All friend requests processed")
                    time.sleep(random.uniform(4, 6))
                    
                    # Close the friend requests panel (click outside or press ESC)
                    try:
                        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(2)
                    except:
                        pass
                else:
                    print("✓ No pending friend requests")
                    # Close the panel
                    try:
                        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(2)
                    except:
                        pass
                    
            except Exception as e:
                # print(f"⚠ Error checking friend requests: {str(e)}")
                print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
                
            
            # 2. Now check for unread messages (including from newly accepted friends)
            print("\n→ Checking for unread messages...")
            try:
                # Find unread conversations (includes messages from non-friends)
                unread_conversations = self.driver.find_elements(
                    By.XPATH,
                    "//div[@role='listitem' and (.//span[text()='New Chat'] or .//div[contains(@class, 'unread')] or .//div[contains(@style, 'bold')])]"
                )
                
                if unread_conversations:
                    print(f"✓ Found {len(unread_conversations)} unread conversation(s)")
                    processed_any = True
                    
                    for index, conversation in enumerate(unread_conversations[:5], 1):
                        try:
                            print(f"\n→ Processing conversation {index}...")
                            try:
                                conversation.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", conversation)
                            time.sleep(random.uniform(4, 8))
                        
                            
                            # Read conversation history
                            conversation_history = self.read_conversation_history(max_messages=5)
                            
                            # Try to read the last message (excluding system messages with "SNAPCHAT" and "WEB")
                            incoming_message = "Hello"
                            try:
                                last_messages = self.driver.find_elements(By.XPATH, "//div[@role='textbox']//span | //div[contains(@class, 'message')]//span")
                                if last_messages:
                                    # Find the last message that doesn't contain both "SNAPCHAT" and "WEB" in capitals
                                    for msg in reversed(last_messages):
                                        msg_text = msg.text
                                        if msg_text and not ("SNAPCHAT" in msg_text and "WEB" in msg_text):
                                            incoming_message = msg_text[:200]
                                            print(f"→ Received message: {incoming_message[:50]}...")
                                            break
                            except:
                                pass
                            
                            # Generate reply with conversation history
                            sender_name = self.extract_sender_name()
                            reply_text = self.generate_ai_reply(incoming_message, conversation_history, sender_name)
                            
                            # Find message input
                            message_input = wait.until(EC.presence_of_element_located(
                                (By.XPATH, "//div[@role='textbox' and @contenteditable='true']")
                            ))
                            
                            # Type and send reply
                            print(f"→ Sending reply: {reply_text}")
                            message_input.click()
                            time.sleep(1)
                            message_input.send_keys(reply_text)
                            time.sleep(2)
                            message_input.send_keys(Keys.RETURN)
                            
                            print("✓ Reply sent successfully!")
                            time.sleep(random.uniform(4, 8))
                            
                        except Exception as e:
                            # print(f"⚠ Could not reply to conversation {index}: {str(e)}")
                            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
                            
                            continue
                else:
                    print("✓ No unread messages")
            except Exception as e:
                # print(f"⚠ Error checking messages: {str(e)}")
                print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
            
            if not processed_any:
                print("\n✓ No new messages to process")
                
            return True
            
        except Exception as e:
            # print(f"✗ Error in Snapchat auto-reply: {str(e)}")
            print(f"⚠ Could not reply to message request. It means that there are no request msgs (most prolly). ")
            
            import traceback
            traceback.print_exc()
            return False
    
    def check_and_reply(self, reply_message, check_interval=60):
        """Main method to check and reply to messages"""
        try:
            if self.platform == 'facebook' or self.platform == 'fb':
                return self.facebook_auto_reply(reply_message)
            elif self.platform == 'twitter' or self.platform == 'tw':
                return self.twitter_auto_reply(reply_message)
            elif self.platform == 'instagram' or self.platform == 'ig':
                return self.instagram_auto_reply(reply_message)
            elif self.platform == 'tiktok':
                return self.tiktok_auto_reply(reply_message)
            elif self.platform == 'snapchat':
                return self.snapchat_auto_reply(reply_message)
            else:
                print(f"✗ Unknown platform: {self.platform}")
                return False
                
        except Exception as e:
            print(f"✗ Error in check_and_reply: {str(e)}")
            return False
    
    def cleanup(self):
        """Cleanup browser and profile"""
        try:
            if self.driver:
                print("\n→ Closing browser...")
                self.driver.quit()
                time.sleep(4)
            
            if self.gl:
                print("→ Stopping GoLogin profile...")
                self.gl.stop()
                print("✓ Profile stopped")
                time.sleep(6)
        except Exception as e:
            print(f"⚠ Cleanup error: {str(e)}")


def read_accounts_from_csv(csv_file):
    """Read account configurations from CSV file"""
    accounts = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row_index, row in enumerate(csv_reader, start=2):
                # Get status (default to empty if not present)
                status = row.get('status', '').strip().lower()
                
                accounts.append({
                    'profile_id': row['profile_id'].strip(),
                    'token': row['token'].strip(),
                    'platform': row['platform'].strip(),
                    'ai_provider': row.get('ai_provider', 'static').strip(),
                    'ai_api_key': row.get('ai_api_key', '').strip(),
                    'static_reply': row.get('static_reply', 'Thank you for your message!').strip(),
                    'check_interval': int(row.get('check_interval', 60)),
                    'pin': row.get('pin', '').strip(),  # PIN for Twitter/X and Facebook
                    'system_prompt': row.get('system_prompt', '').strip(),  # System prompt for AI
                    'status': status,
                    'row_index': row_index
                })
        
        print(f"✓ Loaded {len(accounts)} accounts from CSV")
        
        # Count accounts by status
        active_count = sum(1 for a in accounts if a['status'] != 'disabled')
        disabled_count = len(accounts) - active_count
        
        print(f"✓ Active accounts: {active_count}")
        print(f"✓ Disabled accounts: {disabled_count}")
        
        return accounts
    except FileNotFoundError:
        print(f"✗ Error: CSV file '{csv_file}' not found!")
        return []
    except Exception as e:
        print(f"✗ Error reading CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def update_account_status(csv_file, row_index, new_status):
    """Update the status of a specific account in the CSV file"""
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
        if row_index - 2 < len(rows):
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


def process_auto_replies(csv_file, delay_between_accounts=30):
    """Process auto-replies for all accounts from CSV file"""
    
    print("\n" + "="*60)
    print("SOCIAL MEDIA AUTO-REPLY BOT - MULTI-PLATFORM")
    print("="*60)
    
    # Read accounts from CSV
    all_accounts = read_accounts_from_csv(csv_file)
    
    if not all_accounts:
        print("✗ No accounts to process. Exiting...")
        return False
    
    # Filter out disabled accounts
    accounts = [a for a in all_accounts if a['status'] != 'disabled']
    
    if not accounts:
        print("\n⚠ All accounts are disabled!")
        print("✓ No accounts to process in this cycle.")
        return True
    
    print(f"\n Processing {len(accounts)} active accounts (skipping {len(all_accounts) - len(accounts)} disabled)")
    
    # Statistics
    total_accounts = len(accounts)
    successful = 0
    failed = 0
    results = []
    
    # Process each account
    for account_index, account in enumerate(accounts, 1):
        print("\n" + "#"*60)
        print(f"PROCESSING ACCOUNT {account_index}/{total_accounts}")
        print("#"*60)
        print(f"Profile ID: {account['profile_id'][:20]}...")
        print(f"Platform: {account['platform'].upper()}")
        print(f"AI Provider: {account['ai_provider'].upper()}")
        print(f"Static Reply: {account['static_reply'][:50]}...")
        print(f"Check Interval: {account['check_interval']} seconds")
        print(f"PIN configured: {'Yes' if account['pin'] else 'No'}")
        print(f"Current status: {account['status'] if account['status'] else 'active'}")
        print("#"*60)
        
        replier = None
        account_success = True
        
        try:
            # Create auto-reply instance with system_prompt
            replier = SocialMediaAutoReply(
                profile_id=account['profile_id'],
                token=account['token'],
                platform=account['platform'],
                ai_provider=account['ai_provider'],
                ai_api_key=account['ai_api_key'],
                static_reply=account['static_reply'],
                pin=account['pin'],
                system_prompt=account.get('system_prompt', '')  # Pass system_prompt
            )
            
            # Start GoLogin browser
            if not replier.start_gologin_browser():
                print(f"✗ Failed to start browser for account {account_index}")
                account_success = False
                failed += 1
                results.append({
                    'account': account_index,
                    'platform': account['platform'],
                    'success': False,
                    'reason': 'Failed to start browser'
                })
                continue
            
            # Check and reply to messages
            print(f"\n{'='*60}")
            print(f"CHECKING MESSAGES FOR {account['platform'].upper()}")
            print(f"AI Provider: {account['ai_provider'].upper()}")
            print(f"{'='*60}")
            
            success = replier.check_and_reply(
                reply_message=account['static_reply'],
                check_interval=account['check_interval']
            )
            
            # Record result
            if success:
                successful += 1
                print(f"\n ACCOUNT {account_index} - SUCCESS")
                results.append({
                    'account': account_index,
                    'platform': account['platform'],
                    'success': True,
                    'reason': 'Auto-reply completed successfully'
                })
            else:
                failed += 1
                account_success = False
                print(f"\n ACCOUNT {account_index} - FAILED")
                results.append({
                    'account': account_index,
                    'platform': account['platform'],
                    'success': False,
                    'reason': 'Auto-reply failed'
                })
            
        except Exception as e:
            failed += 1
            account_success = False
            print(f"\n✗ Error processing account {account_index}: {str(e)}")
            results.append({
                'account': account_index,
                'platform': account['platform'],
                'success': False,
                'reason': str(e)
            })
        
        finally:
            # Cleanup browser for this account
            if replier:
                replier.cleanup()
        
        # Wait before processing next account
        if account_index < total_accounts:
            print(f"\n Waiting {delay_between_accounts} seconds before next account...")
            time.sleep(delay_between_accounts)
    
    # Print final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total Accounts Processed: {total_accounts}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    if total_accounts > 0:
        print(f"Success Rate: {(successful/total_accounts*100):.1f}%")
    print("="*60)
    
    print("\n DETAILED RESULTS:")
    print("-"*60)
    for result in results:
        status = "✅ SUCCESS" if result['success'] else " FAILED"
        print(f"\nAccount #{result['account']} ({result['platform'].upper()}): {status}")
        if not result['success']:
            print(f"  Reason: {result['reason']}")
    print("-"*60)
    
    return True


def run_continuous_monitoring(csv_file, cycle_interval=300, delay_between_accounts=30):
    """Run continuous monitoring with periodic checks (every 5 minutes by default)"""
    
    cycle_count = 0
    
    while True:
        cycle_count += 1
        
        print("\n" + ""*30)
        print(f"AUTO-REPLY CYCLE #{cycle_count}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(""*30 + "\n")
        
        # Process all accounts
        success = process_auto_replies(
            csv_file=csv_file,
            delay_between_accounts=delay_between_accounts
        )
        
        if not success:
            print("\n Auto-reply cycle failed!")
        else:
            print("\n AUTO-REPLY CYCLE COMPLETED!")
        
        # Calculate next run time
        next_run = datetime.now() + timedelta(seconds=cycle_interval)
        print("\n" + ""*30)
        print(f"Next check cycle at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Waiting {cycle_interval} seconds ({cycle_interval//60} minutes)...")
        print(""*30)
        
        # Wait for next cycle
        remaining_seconds = cycle_interval
        
        while remaining_seconds > 0:
            minutes_left = remaining_seconds // 60
            seconds_left = remaining_seconds % 60
            
            print(f"\r Time until next cycle: {minutes_left}m {seconds_left}s remaining...", end='', flush=True)
            
            # Sleep for 10 seconds and update
            sleep_time = min(10, remaining_seconds)
            time.sleep(sleep_time)
            remaining_seconds -= sleep_time
        
        print("\n")


# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    # Configuration
    CSV_FILE = "auto_reply_accounts.csv"
    DELAY_BETWEEN_ACCOUNTS = 30  # Seconds to wait between accounts
    CHECK_INTERVAL = 300  # Check for messages every 5 minutes (300 seconds)
    ENABLE_CONTINUOUS = True  # Set to False to run only once
    
    print("\n" + "="*60)
    print("SOCIAL MEDIA AUTO-REPLY BOT")
    print("="*60)
    print(f"CSV File: {CSV_FILE}")
    print(f"Delay between accounts: {DELAY_BETWEEN_ACCOUNTS} seconds")
    print(f"Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
    print(f"Continuous monitoring: {'ENABLED' if ENABLE_CONTINUOUS else 'DISABLED'}")
    print("="*60)
    
    print("\n📋 CSV FORMAT EXPECTED:")
    print("  profile_id, token, platform, ai_provider, ai_api_key, static_reply, check_interval, pin, system_prompt, status")
    print("\n  platform: facebook, twitter, instagram, tiktok, snapchat")
    print("  ai_provider: 'gpt', 'gemini', or 'static' (for fixed replies)")
    print("  ai_api_key: Your OpenAI or Gemini API key (leave empty for static)")
    print("  static_reply: Fallback reply or reply when ai_provider='static'")
    print("  pin: PIN/passcode for Twitter/X and Facebook (if required to access chats)")
    print("  system_prompt: Custom instructions for AI (defines AI's personality and response style)")
    print("  status: Leave empty for active accounts, 'disabled' to skip")
    print("  check_interval: Optional, defaults to 60 seconds")
    print("="*60)
    
    print("\n📱 SUPPORTED PLATFORMS:")
    print("  • Facebook (facebook, fb) - Includes Pages & Profiles + Message Requests")
    print("  • Twitter/X (twitter, tw)")
    print("  • Instagram (instagram, ig) - Includes Message Requests")
    print("  • TikTok (tiktok) - Includes Message Requests")
    print("  • Snapchat Web (snapchat) - Includes Non-Friend Messages")
    print("="*60)
    
    print("\n🔄 HOW IT WORKS:")
    print("  1. Bot checks each active account for unread messages & message requests")
    print("  2. Reads incoming message content + conversation history (last 5 messages)")
    print("  3. Generates AI reply using GPT/Gemini with system prompt or uses static reply")
    print("  4. Automatically sends personalized response")
    print("  5. Cycles through all accounts periodically")
    print("  6. Accounts marked 'disabled' are skipped")
    print("="*60)
    
    print("\n🤖 AI REPLY MODES:")
    print("  • GPT (OpenAI): Intelligent context-aware replies using ChatGPT")
    print("    - Uses system_prompt to define AI personality")
    print("    - Reads conversation history for context-aware responses")
    print("  • Gemini (Google): Smart responses using Google's Gemini AI")
    print("    - Uses system_prompt to define AI personality")
    print("    - Reads conversation history for context-aware responses")
    print("  • Static: Fixed message (no AI, fastest, no conversation history)")
    print("="*60)
    
    print("\n💡 SYSTEM PROMPT EXAMPLES:")
    print("  Facebook: 'You are a helpful customer service assistant. Reply professionally.'")
    print("  Twitter: 'You are a concise Twitter manager. Keep replies under 280 chars.'")
    print("  Instagram: 'You are a friendly brand ambassador. Reply in a casual, fun tone.'")
    print("="*60)
    
    print("\n🔧 SYSTEM PROMPT VARIABLES:")
    print("  Use dynamic variables in your system prompts to personalize AI responses:")
    print("  • %name% - Sender's name (e.g., 'Hello %name%!')")
    print("  • %platform% - Platform name (Facebook, Twitter, Instagram, etc.)")
    print("  • %message% - The incoming message text")
    print("  • %context% - Recent conversation context/summary")
    print("  • %time% - Current time (HH:MM:SS)")
    print("  • %date% - Current date (YYYY-MM-DD)")
    print("")
    print("  Example: 'You are a helpful assistant. Hi %name%! You messaged on %platform% at %time%.'")
    print("  Result: 'You are a helpful assistant. Hi John! You messaged on Facebook at 14:30:25.'")
    print("="*60)
    
    # input("\n  Press ENTER to start auto-reply bot...")
    
    if ENABLE_CONTINUOUS:
        # Run with continuous monitoring
        run_continuous_monitoring(
            csv_file=CSV_FILE,
            cycle_interval=CHECK_INTERVAL,
            delay_between_accounts=DELAY_BETWEEN_ACCOUNTS
        )
    else:
        # Run once
        process_auto_replies(
            csv_file=CSV_FILE,
            delay_between_accounts=DELAY_BETWEEN_ACCOUNTS
        )
    
    print("\n" + "="*60)
    print("SCRIPT FINISHED")
    print("="*60)
