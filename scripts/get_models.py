#!/usr/bin/env python3
"""Get available Claude models from Anthropic API"""

import os
import httpx
from anthropic import Anthropic

def get_available_models():
    """Fetch all available models from Anthropic API"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return []

    # Use insecure client for corporate proxy
    http_client = httpx.Client(verify=False)
    client = Anthropic(api_key=api_key, http_client=http_client)

    try:
        models = client.models.list()
        return models.data
    except Exception as e:
        print(f"❌ Failed to fetch models: {e}")
        return []

def test_model(model_id):
    """Test if a model is available"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return False, "API key not set"

    http_client = httpx.Client(verify=False)
    client = Anthropic(api_key=api_key, http_client=http_client)

    try:
        client.messages.create(
            model=model_id,
            max_tokens=10,
            messages=[{"role": "user", "content": "test"}]
        )
        return True, "Available"
    except Exception as e:
        error_str = str(e).lower()
        if "not_found" in error_str or "not found" in error_str:
            return False, "Not found"
        return False, str(e)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test specific model
        model_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not model_id:
            print("Usage: python get_models.py test <model_id>")
            sys.exit(1)
        available, status = test_model(model_id)
        print(f"{model_id}: {'✅' if available else '❌'} {status}")
        sys.exit(0 if available else 1)
    
    # List all models
    print("Fetching available models from Anthropic API...\n")
    models = get_available_models()
    
    if not models:
        print("No models found or API error")
        sys.exit(1)

    print(f"Found {len(models)} models:\n")
    print("Available Claude models (working):")
    for model in models:
        available, status = test_model(model.id)
        status_icon = "✅" if available else "❌"
        print(f"  {status_icon} {model.id}")

    # Generate Python code for configuration
    print("\n\nUpdate AVAILABLE_MODELS in backend/services/ingestion.py:")
    print("AVAILABLE_MODELS = [")
    for model in models:
        available, _ = test_model(model.id)
        if available:
            print(f'    "{model.id}",')
    print("]")
