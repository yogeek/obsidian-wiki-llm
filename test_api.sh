#!/bin/bash
# Test Anthropic API key and check if credits are available
# Lists available models and lets you choose which one to test

if [ ! -f .env ]; then
    echo "❌ .env file not found"
    exit 1
fi

# Load .env but be careful with special characters
ANTHROPIC_API_KEY=$(grep "^ANTHROPIC_API_KEY=" .env | cut -d'=' -f2 | tr -d '"')

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not found in .env"
    exit 1
fi

if [[ ! $ANTHROPIC_API_KEY =~ ^sk-ant- ]]; then
    echo "❌ API key format looks wrong: ${ANTHROPIC_API_KEY:0:20}..."
    exit 1
fi

echo "✓ Found API key: ${ANTHROPIC_API_KEY:0:30}..."
echo ""
echo "📋 Testing API connection..."
echo ""

# Test with a simple message first
RESPONSE=$(curl --silent -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-opus-4-6",
    "max_tokens": 100,
    "messages": [
      {"role": "user", "content": "Say hello briefly"}
    ]
  }')

echo "Raw response:"
echo "$RESPONSE" | python3 -m json.tool 2>&1 || echo "$RESPONSE"

echo ""

# Check for specific error types
if echo "$RESPONSE" | grep -q "not_found_error"; then
    echo "⚠️  Model not found. Your account may not have access to opus-4-6."
    echo ""
    echo "Trying with available models..."
    echo ""

    # Try common models in order of cost
    for MODEL in "claude-3-5-sonnet-20241022" "claude-3-sonnet-20240229" "claude-opus-4-1" "claude-3-opus-20240229"; do
        echo "Trying model: $MODEL"
        TEST=$(curl --silent -X POST https://api.anthropic.com/v1/messages \
          -H "x-api-key: $ANTHROPIC_API_KEY" \
          -H "anthropic-version: 2023-06-01" \
          -H "content-type: application/json" \
          -d "{
            \"model\": \"$MODEL\",
            \"max_tokens\": 100,
            \"messages\": [
              {\"role\": \"user\", \"content\": \"Say hello briefly\"}
            ]
          }")

        if echo "$TEST" | grep -q "usage"; then
            echo "✅ Success with $MODEL!"
            echo ""
            echo "$TEST" | python3 -m json.tool
            echo ""
            echo "💡 Update your backend to use: $MODEL"
            break
        elif echo "$TEST" | grep -q "insufficient_quota\|credit"; then
            echo "❌ Insufficient credits"
            echo "$TEST" | python3 -m json.tool 2>&1 || echo "$TEST"
            break
        else
            echo "   Not available"
        fi
    done

elif echo "$RESPONSE" | grep -q "insufficient_quota\|credit"; then
    echo "❌ Insufficient credits or quota"

elif echo "$RESPONSE" | grep -q "usage"; then
    echo "✅ API is working!"

else
    echo "⚠️  Check response above for errors"
fi

echo ""
echo "✅ API test complete!"
