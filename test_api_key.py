#!/usr/bin/env python3
"""Test if the Anthropic API key works and has available credits"""

import os
import sys
import httpx
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY')

if not api_key:
    print("❌ ANTHROPIC_API_KEY not set in .env")
    sys.exit(1)

if not api_key.startswith('sk-ant-'):
    print(f"❌ API key format looks wrong: {api_key[:20]}...")
    sys.exit(1)

print(f"✓ Found API key: {api_key[:30]}...")
print()

# Test the API with a minimal request
try:
    http_client = httpx.Client(verify=False)
    client = Anthropic(api_key=api_key, http_client=http_client)

    print("Testing API connection...")
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=10,
        messages=[{"role": "user", "content": "test"}]
    )
    print(f"✓ API is working!")
    print(f"✓ Model: {response.model}")
    print(f"✓ Input tokens used: {response.usage.input_tokens}")
    print(f"✓ Output tokens used: {response.usage.output_tokens}")
    print()
    print("✅ Your API key has valid credits and is working correctly!")

except Exception as e:
    print(f"❌ API Error: {type(e).__name__}")
    print(f"   {str(e)}")
    sys.exit(1)
