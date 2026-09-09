"""
Test script for Gemini API (Free Tier - Gemini 1.5 Flash)
This script tests the Gemini API functionality using the same logic as auto_reply.py
"""

from google import genai
import time


def test_gemini_api(api_key):
    """Test Gemini API with a simple prompt"""
    
    print("="*60)
    print("GEMINI API TEST")
    print("="*60)
    
    try:
        # Initialize Gemini client (same as in auto_reply.py)
        print("\n→ Initializing Gemini client...")
        gemini_client = genai.Client(api_key=api_key)
        print("✓ Gemini client initialized successfully!")
        
        # List available models first
        print("\n→ Fetching available models...")
        try:
            models_list = gemini_client.models.list()
            print("✓ Available Gemini models:")
            flash_models = []
            for model in models_list:
                model_name = model.name if hasattr(model, 'name') else str(model)
                print(f"  • {model_name}")
                if 'flash' in model_name.lower():
                    flash_models.append(model_name)
            
            # Select the flash model
            if flash_models:
                selected_model = flash_models[0]
                print(f"\n✓ Selected model: {selected_model}")
            else:
                # Default fallback
                selected_model = 'gemini-flash-latest'
                print(f"\n→ Using default model name: {selected_model}")
        except Exception as e:
            print(f"⚠ Could not list models: {e}")
            selected_model = 'gemini-flash-latest'
            print(f"→ Using default model name: {selected_model}")
        
        # Test 1: Simple message
        print("\n" + "-"*60)
        print("TEST 1: Simple Reply")
        print("-"*60)
        
        system_prompt = "You are a helpful social media assistant. Reply to messages in a friendly, professional, and concise manner."
        incoming_message = "Hello! How are you today?"
        
        print(f"System Prompt: {system_prompt}")
        print(f"Incoming Message: {incoming_message}")
        
        # Build prompt (same logic as auto_reply.py)
        full_prompt = f"{system_prompt}\n\n"
        full_prompt += f"Now reply to this message: {incoming_message}"
        
        print("\n→ Generating Gemini reply...")
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = gemini_client.models.generate_content(
                    model=selected_model,
                    contents=full_prompt
                )
                reply = response.text.strip()
                print(f"\n✓ Gemini Reply: {reply}")
                break
            except Exception as e:
                if '503' in str(e) or 'overloaded' in str(e).lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"⚠ Model overloaded, retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        raise
                else:
                    raise
        
        # Wait between tests to avoid rate limiting
        print("\n→ Waiting 3 seconds before next test...")
        time.sleep(3)
        
        # Test 2: With conversation history
        print("\n" + "-"*60)
        print("TEST 2: Reply with Conversation History")
        print("-"*60)
        
        conversation_history = [
            {'role': 'user', 'content': 'Hi, I need help with my order'},
            {'role': 'assistant', 'content': 'Hello! I\'d be happy to help. What\'s your order number?'},
            {'role': 'user', 'content': 'It\'s #12345'}
        ]
        
        incoming_message_2 = "When will it arrive?"
        
        print("Conversation History:")
        for msg in conversation_history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            print(f"  {role}: {msg['content']}")
        print(f"\nNew Incoming Message: {incoming_message_2}")
        
        # Build prompt with history (same logic as auto_reply.py)
        full_prompt_2 = f"{system_prompt}\n\n"
        full_prompt_2 += "Previous conversation:\n"
        for msg in conversation_history:
            role = "User" if msg.get('role') == 'user' else "You"
            full_prompt_2 += f"{role}: {msg['content']}\n"
        full_prompt_2 += "\n"
        full_prompt_2 += f"Now reply to this message: {incoming_message_2}"
        
        print("\n→ Generating Gemini reply with context...")
        
        for attempt in range(max_retries):
            try:
                response_2 = gemini_client.models.generate_content(
                    model=selected_model,
                    contents=full_prompt_2
                )
                reply_2 = response_2.text.strip()
                print(f"\n✓ Gemini Reply: {reply_2}")
                break
            except Exception as e:
                if '503' in str(e) or 'overloaded' in str(e).lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"⚠ Model overloaded, retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        raise
                else:
                    raise
        
        # Wait between tests to avoid rate limiting
        print("\n→ Waiting 3 seconds before next test...")
        time.sleep(3)
        
        # Test 3: Custom system prompt
        print("\n" + "-"*60)
        print("TEST 3: Custom System Prompt (Twitter Style)")
        print("-"*60)
        
        twitter_prompt = "You are a concise Twitter manager. Keep replies under 280 characters and use a friendly, casual tone."
        incoming_message_3 = "Love your product! When's the next sale?"
        
        print(f"System Prompt: {twitter_prompt}")
        print(f"Incoming Message: {incoming_message_3}")
        
        full_prompt_3 = f"{twitter_prompt}\n\n"
        full_prompt_3 += f"Now reply to this message: {incoming_message_3}"
        
        print("\n→ Generating Gemini reply...")
        
        for attempt in range(max_retries):
            try:
                response_3 = gemini_client.models.generate_content(
                    model=selected_model,
                    contents=full_prompt_3
                )
                reply_3 = response_3.text.strip()
                print(f"\n✓ Gemini Reply: {reply_3}")
                print(f"   (Length: {len(reply_3)} characters)")
                break
            except Exception as e:
                if '503' in str(e) or 'overloaded' in str(e).lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"⚠ Model overloaded, retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        raise
                else:
                    raise
        
        # Success summary
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("Your Gemini API key is working correctly!")
        print("The gemini-flash model is responding as expected.")
        print("You can now use this API key in auto_reply_accounts.csv")
        print("="*60)
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED!")
        print("="*60)
        print(f"Error: {str(e)}")
        print("\nPossible issues:")
        if '503' in str(e) or 'overloaded' in str(e).lower():
            print("  ⚠ The Gemini servers are currently overloaded")
            print("  → This is temporary - try running the test again in a few minutes")
            print("  → Your API key is valid and working!")
        else:
            print("  1. Invalid API key")
            print("  2. API key not activated")
            print("  3. Network connection issue")
            print("  4. Gemini API quota exceeded")
            print("  5. Missing 'google-genai' package")
        print("\nTo install required package:")
        print("  pip install google-genai")
        print("="*60)
        
        import traceback
        traceback.print_exc()
        
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("GEMINI API TESTER")
    print("Free Tier - Gemini 1.5 Flash Model")
    print("="*60)
    
    # Prompt for API key
    print("\nEnter your Gemini API key:")
    print("(Get it from: https://aistudio.google.com/app/apikey)")
    api_key = input("\nAPI Key: ").strip()
    
    if not api_key:
        print("\n❌ Error: No API key provided!")
        print("Please run the script again and enter your API key.")
    else:
        # Run tests
        test_gemini_api(api_key)
    
    print("\n")
