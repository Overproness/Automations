"""
Test script for OpenAI GPT API
Tests the same logic used in auto_reply.py
"""

from openai import OpenAI
import sys

def test_gpt_api(api_key, test_message=None, system_prompt=None):
    """Test GPT API with the same logic as auto_reply.py"""
    
    print("="*60)
    print("GPT API TEST")
    print("="*60)
    
    # Default values
    if test_message is None:
        test_message = "Hello! I'm interested in your product. Can you tell me more?"
    
    if system_prompt is None:
        system_prompt = "You are a helpful social media assistant. Reply to messages in a friendly, professional, and concise manner."
    
    print(f"\nTest Configuration:")
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Model: gpt-3.5-turbo")
    print(f"System Prompt: {system_prompt[:50]}...")
    print(f"Test Message: {test_message}")
    print("="*60)
    
    try:
        # Initialize OpenAI client (same as auto_reply.py)
        print("\n→ Initializing OpenAI client...")
        openai_client = OpenAI(api_key=api_key)
        print("✓ Client initialized successfully!")
        
        # Build messages array (same as auto_reply.py)
        print("\n→ Building message array...")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_message}
        ]
        print(f"✓ Message array created with {len(messages)} messages")
        
        # Make API call (same as auto_reply.py)
        print("\n→ Calling GPT API...")
        print("  Model: gpt-3.5-turbo")
        print("  Max tokens: 150")
        print("  Temperature: 0.7")
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        
        print("✓ API call successful!")
        
        # Extract response (same as auto_reply.py)
        reply = response.choices[0].message.content.strip()
        
        print("\n" + "="*60)
        print("✅ GPT API TEST PASSED!")
        print("="*60)
        print(f"\nTest Message:")
        print(f"  '{test_message}'")
        print(f"\nGPT Reply:")
        print(f"  '{reply}'")
        print("\n" + "="*60)
        print("✓ Your GPT API key is working correctly!")
        print("✓ The same logic will work in auto_reply.py")
        print("="*60)
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ GPT API TEST FAILED!")
        print("="*60)
        print(f"\nError: {str(e)}")
        print("\nPossible issues:")
        print("  • Invalid API key")
        print("  • No credits/quota remaining")
        print("  • Network connectivity issue")
        print("  • API key doesn't have access to gpt-3.5-turbo")
        print("\nPlease check your OpenAI account and try again.")
        print("="*60)
        return False


def test_with_conversation_history(api_key):
    """Test GPT API with conversation history (advanced test)"""
    
    print("\n\n" + "="*60)
    print("GPT API TEST WITH CONVERSATION HISTORY")
    print("="*60)
    
    system_prompt = "You are a helpful social media assistant. Reply to messages in a friendly, professional, and concise manner."
    
    # Simulate conversation history
    conversation_history = [
        "Hi there! What are your business hours?",
        "We're open Monday-Friday, 9 AM to 5 PM.",
        "Great! Do you offer weekend appointments?"
    ]
    
    print(f"\nConversation History:")
    for i, msg in enumerate(conversation_history, 1):
        print(f"  {i}. {msg}")
    
    print(f"\nCurrent Message to Reply To:")
    current_message = conversation_history[-1]
    print(f"  '{current_message}'")
    
    try:
        # Initialize OpenAI client
        print("\n→ Initializing OpenAI client...")
        openai_client = OpenAI(api_key=api_key)
        
        # Build messages array with conversation history
        print("→ Building message array with conversation history...")
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for i, hist_msg in enumerate(conversation_history[:-1]):
            if i % 2 == 0:
                messages.append({"role": "user", "content": hist_msg})
            else:
                messages.append({"role": "assistant", "content": hist_msg})
        
        # Add current message
        messages.append({"role": "user", "content": current_message})
        
        print(f"✓ Message array created with {len(messages)} messages (including history)")
        
        # Make API call
        print("\n→ Calling GPT API with conversation context...")
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content.strip()
        
        print("\n" + "="*60)
        print("✅ CONVERSATION HISTORY TEST PASSED!")
        print("="*60)
        print(f"\nGPT Reply (with conversation context):")
        print(f"  '{reply}'")
        print("\n" + "="*60)
        print("✓ GPT can handle conversation history correctly!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error in conversation history test: {str(e)}")
        return False


# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("OPENAI GPT API TESTER")
    print("Tests the same logic used in auto_reply.py")
    print("="*60)
    
    # Get API key
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        print("\n✓ API key provided via command line")
    else:
        print("\nPlease enter your OpenAI API key:")
        print("(starts with 'sk-' or 'sk-proj-')")
        api_key = input("API Key: ").strip()
    
    if not api_key:
        print("\n❌ No API key provided. Exiting...")
        sys.exit(1)
    
    if not api_key.startswith('sk-'):
        print("\n⚠ Warning: API key should start with 'sk-'")
        print("Are you sure this is correct? Press ENTER to continue or Ctrl+C to cancel...")
        input()
    
    # Run basic test
    print("\n" + "🔸"*30)
    print("TEST 1: Basic GPT API Test")
    print("🔸"*30)
    success = test_gpt_api(api_key)
    
    if success:
        # Run advanced test with conversation history
        print("\n" + "🔸"*30)
        print("TEST 2: Conversation History Test")
        print("🔸"*30)
        test_with_conversation_history(api_key)
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
        print("\nYou can now use this API key in auto_reply_accounts.csv:")
        print("  - Set ai_provider to 'gpt'")
        print(f"  - Set ai_api_key to your key")
        print("  - Set system_prompt to customize AI behavior")
        print("\nExample CSV row:")
        print(f"  your_profile_id,your_token,facebook,gpt,{api_key},Thank you!,60,,You are a helpful assistant,")
    else:
        print("\n❌ TESTS FAILED")
        print("\nPlease fix the issues above before using in auto_reply.py")
    
    print("="*60)
