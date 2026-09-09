# Social Media Auto-Reply Bot - Complete Setup Guide

## Overview

This bot automatically replies to messages on Facebook, Twitter, Instagram, TikTok, and Snapchat using AI (GPT/Gemini) or static replies. It uses GoLogin for multi-account management.

---

## Step-by-Step Setup Guide

### **Step 1: Install Required Python Packages**

Run these commands in your terminal:

```bash

# Install required packages
pip install selenium webdriver-manager gologin openai google-generativeai
```

---

### **Step 2: Create GoLogin Account & Get Profiles**

1. **Sign up for GoLogin:**
   - Go to https://gologin.com/
   - Create an account
   - Subscribe to a plan that supports multiple profiles

2. **Get Your API Token:**
   - Log into GoLogin dashboard
   - Go to Settings → API
   - Copy your API Token (looks like: `eyJhbGciOiJIUzI1NiIsInR5cCI6...`)

3. **Create Browser Profiles:**
   - In GoLogin app, click "New Profile"
   - For each social media account:
     - Create a separate profile
     - Give it a name (e.g., "Facebook Account 1", "Instagram Account 2")
     - Copy the Profile ID (found in profile settings)
   - **IMPORTANT:** Manually login to each social media platform within each GoLogin profile
     - Open the profile
     - Navigate to the platform (facebook.com, twitter.com, etc.)
     - Login with your credentials
     - Save the profile (cookies/session will be saved)

---

### **Step 3: Get AI API Keys (Optional but Recommended)**

#### **Option A: OpenAI (GPT)**

1. Go to https://platform.openai.com/
2. Create account or sign in
3. Go to API Keys section
4. Click "Create new secret key"
5. Copy the key (starts with `sk-...`)
6. **Note:** Requires credit card, pay-as-you-go pricing (~$0.002 per reply)

#### **Option B: Google Gemini**

1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Get API Key"
4. Create new API key
5. Copy the key
6. **Note:** Free tier available (60 requests per minute)

#### **Option C: Static Replies (Free)**

- No API key needed
- Uses fixed messages
- Fastest but not context-aware

---

### **Step 4: Configure auto_reply_accounts.csv**

Open `auto_reply_accounts.csv` and fill in your details:

```csv
profile_id,token,platform,ai_provider,ai_api_key,static_reply,check_interval,status
```

**Field Descriptions:**

- `profile_id`: Your GoLogin Profile ID (from Step 2)
- `token`: Your GoLogin API Token (from Step 2)
- `platform`: One of: `facebook`, `twitter`, `instagram`, `tiktok`, `snapchat`
- `ai_provider`: One of: `gpt`, `gemini`, or `static`
- `ai_api_key`: Your OpenAI or Gemini API key (leave empty for static)
- `static_reply`: Fallback message or fixed reply
- `check_interval`: Seconds between checks (default: 60)
- `status`: Leave empty to activate, use `disabled` to skip

**Example Configuration:**

```csv
profile_id,token,platform,ai_provider,ai_api_key,static_reply,check_interval,status
6a3b9d7c47cb48911683a2f8,eyJhbGciOiJIUzI1Ni...,facebook,gpt,sk-proj-abc123...,Thanks for messaging!,60,
8f2e1a9b23de49102847c3d1,eyJhbGciOiJIUzI1Ni...,instagram,gemini,AIzaSyD_xyz789...,Hi! Thanks!,60,
2c5d4f8a67bc58201937e4f2,eyJhbGciOiJIUzI1Ni...,twitter,static,,Thank you for reaching out!,60,
```

---

### **Step 5: Test Your Setup**

1. **Open one GoLogin profile manually** to verify you're logged in
2. **Send a test message** to that account from another account
3. **Run the bot in test mode:**

```bash
python auto_reply.py
```

4. **Watch the console output** for:
   - ✓ Profile started
   - ✓ Selenium connected
   - ✓ Found unread messages
   - ✓ Reply sent

---

### **Step 6: Configure for Production**

Edit `auto_reply.py` settings at the bottom:

```python
# Configuration
CSV_FILE = "auto_reply_accounts.csv"
DELAY_BETWEEN_ACCOUNTS = 30  # Wait time between accounts
CHECK_INTERVAL = 300  # Check every 5 minutes
ENABLE_CONTINUOUS = True  # Keep running
```

**Recommended Settings:**

- **Development/Testing:** `CHECK_INTERVAL = 60` (1 minute)
- **Production:** `CHECK_INTERVAL = 300` (5 minutes)
- **High Volume:** `CHECK_INTERVAL = 120` (2 minutes)

---

## Running the Bot

### **One-Time Run (for testing):**

```bash
python auto_reply.py
```

### **Continuous Monitoring:**

Set `ENABLE_CONTINUOUS = True` in the script, then run:

```bash
python auto_reply.py
```

Press ENTER to start. Bot will run indefinitely, checking every X minutes.

### **Run in Background (Windows):**

```bash
Start-Process -FilePath "uc_env\Scripts\python.exe" -ArgumentList "auto_reply.py" -WindowStyle Hidden
```

---

## Understanding the CSV Format

### **Multiple Accounts Example:**

```csv
profile_id,token,platform,ai_provider,ai_api_key,static_reply,check_interval,status
profile1,token1,facebook,gpt,sk-abc...,Hi there!,60,
profile2,token2,instagram,gpt,sk-abc...,Thanks!,60,
profile3,token3,twitter,gemini,AIza...,Hello!,60,disabled
profile4,token4,tiktok,static,,Thank you!,60,
```

**Note:**

- Each row = 1 social media account
- Same GoLogin profile can be used for multiple platforms (but create separate rows)
- Use `disabled` status to temporarily skip accounts

---

## Troubleshooting

### **Problem: "Error starting GoLogin browser"**

**Solution:**

- Check your GoLogin API token is correct
- Verify profile_id exists in your GoLogin account
- Make sure GoLogin app is running

### **Problem: "No unread messages" (but there are messages)**

**Solution:**

- Social media platforms update their HTML frequently
- You may need to manually log in to the GoLogin profile first
- Check the browser window to see what's happening

### **Problem: "AI reply generation failed"**

**Solution:**

- Verify API key is correct
- Check you have credits/quota remaining
- Fallback to static reply will be used automatically

### **Problem: "Message not sending"**

**Solution:**

- Platform may have changed their UI
- Try manually in GoLogin profile first to confirm login works
- Reduce `DELAY_BETWEEN_ACCOUNTS` if timeout occurs

---

## Best Practices

1. **Start Small:** Test with 1-2 accounts first
2. **Manual Login First:** Always log in manually in GoLogin profile before running bot
3. **Use AI Wisely:** GPT/Gemini cost money - use static for simple "thanks" messages
4. **Monitor First Run:** Watch the console output on first run
5. **Check Quotas:** Monitor your API usage on OpenAI/Gemini dashboards
6. **Backup CSV:** Keep a backup of your CSV configuration
7. **Update Regularly:** Social media platforms change - you may need to update selectors

---

## CSV Template for Copy-Paste

```csv
profile_id,token,platform,ai_provider,ai_api_key,static_reply,check_interval,status
YOUR_PROFILE_ID,YOUR_TOKEN,facebook,gpt,YOUR_API_KEY,Thank you!,60,
YOUR_PROFILE_ID,YOUR_TOKEN,instagram,gemini,YOUR_API_KEY,Hi there!,60,
YOUR_PROFILE_ID,YOUR_TOKEN,twitter,static,,Thanks for messaging!,60,
```

---

## Quick Start Checklist

- [ ] Install Python packages
- [ ] Create GoLogin account
- [ ] Get GoLogin API token
- [ ] Create GoLogin profiles
- [ ] Manually login to each platform in each profile
- [ ] Get OpenAI or Gemini API key (optional)
- [ ] Fill out `auto_reply_accounts.csv`
- [ ] Test with one account
- [ ] Run in continuous mode
- [ ] Monitor for first 30 minutes
- [ ] Set up background running (optional)

---

## Cost Estimates

### **GoLogin:**

- Starter Plan: ~$24/month (10 profiles)
- Professional: ~$49/month (100 profiles)

### **OpenAI (GPT):**

- ~$0.002 per reply
- 1000 replies = ~$2
- 10,000 replies/month = ~$20

### **Google Gemini:**

- Free tier: 60 requests/minute
- Paid: ~$0.001 per reply (cheaper than GPT)

### **Static Replies:**

- Free! Only GoLogin cost

---

## Support & Updates

If platforms change their UI, you may need to update the XPath selectors in `auto_reply.py`. Look for sections like:

```python
# Find unread conversations
unread_conversations = self.driver.find_elements(
    By.XPATH,
    "//div[contains(@aria-label, 'Unread')]"  # ← Update this
)
```

Use browser DevTools (F12) to inspect elements and find new selectors.

---

## You're Ready!

Follow the steps above, and your auto-reply bot will be running across all platforms!
