"""
Quick script to test OpenRouter API key and check rate limit status.
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('OPENROUTER_API_KEY')

if not API_KEY:
    print("[ERROR] OPENROUTER_API_KEY not found in .env file")
    sys.exit(1)

print("=" * 70)
print("Parse Pro AI - OpenRouter API Key Test")
print("=" * 70)
print()

# Test 1: Check rate limit status
print("[*] Checking rate limit status...")
print("-" * 70)

try:
    response = requests.get(
        "https://openrouter.ai/api/v1/key",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json().get("data", {})
        
        print("[OK] API Key is valid!")
        print()
        print(f"Account Type:      {'FREE TIER' if data.get('is_free_tier') else 'PAID'}")
        print(f"Credit Limit:      {data.get('limit') or 'Unlimited'}")
        print(f"Credits Remaining: {data.get('limit_remaining') or 'N/A'}")
        print(f"Usage (Today):     {data.get('usage_daily', 0)} credits")
        print(f"Usage (This Week): {data.get('usage_weekly', 0)} credits")
        print(f"Usage (All Time):  {data.get('usage', 0)} credits")
        
        # Free tier specific info
        if data.get('is_free_tier'):
            print()
            print("[!] FREE TIER NOTES:")
            print("   - Daily request limit applies to :free models")
            print("   - Model fallbacks are configured for resilience")
            print("   - Consider adding credits for higher limits")
    else:
        print(f"[ERROR] API Key check failed: HTTP {response.status_code}")
        print(f"Response: {response.text[:200]}")
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR] Error checking API key: {e}")
    sys.exit(1)

print()
print("-" * 70)

# Test 2: Make a simple API call
print("[*] Testing API with a simple request...")
print("-" * 70)

try:
    test_response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://parsepro.local",
            "X-Title": "Parse Pro AI Test",
        },
        json={
            "model": "qwen/qwen3-next-80b-a3b-instruct:free",
            "messages": [
                {"role": "user", "content": "Say 'API test successful' and nothing else."}
            ],
            "temperature": 0.1,
            "provider": {
                "data_collection": "allow"  # Required for some free models
            }
        },
        timeout=30
    )
    
    if test_response.status_code == 200:
        result = test_response.json()
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        actual_model = result.get("model", "unknown")
        
        print("[OK] API call successful!")
        print()
        print(f"Model Used:        {actual_model}")
        print(f"Model Response:    {content}")
        print(f"Tokens Used:       {usage.get('total_tokens', 0)} (prompt: {usage.get('prompt_tokens', 0)}, completion: {usage.get('completion_tokens', 0)})")
        print(f"Cost:              ${usage.get('cost', 0)}")
        
    elif test_response.status_code == 429:
        print("[WARNING] Rate limit hit (429)")
        retry_after = test_response.headers.get("Retry-After", "Unknown")
        print(f"Retry After:       {retry_after} seconds")
        print(f"Note: Model fallbacks are configured in the app")
        print()
        print("You can still continue - the app will use fallback models automatically.")
        
    else:
        print(f"[ERROR] API call failed: HTTP {test_response.status_code}")
        print(f"Response: {test_response.text[:200]}")
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR] Error making API call: {e}")
    sys.exit(1)

print()
print("=" * 70)
print("[OK] All tests passed! Your API key is working correctly.")
print("=" * 70)
print()
print("Next steps:")
print("  1. Start the application: .\\scripts\\start-parsepro.ps1")
print("  2. Access the web UI: http://localhost:8000")
print("  3. Upload some test resumes")
print()
