#!/usr/bin/env bash
# Test Von HTTP server using curl (matches TypeSafe API format)

SERVER_URL=${1:-"http://localhost:8000"}

echo "1. Checking Health..."
curl -s "${SERVER_URL}/health" | jq .

echo -e "\n2. Listing Models..."
curl -s "${SERVER_URL}/v1/models" | jq .

echo -e "\n3. Testing System One Decision..."
curl -s -X POST "${SERVER_URL}/v1/systemone" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "von-latest",
    "state": {
      "ticket": "My database crashed and customers cannot log in."
    },
    "questions": {
      "category": {
        "type": "choice",
        "instructions": "What kind of issue is `ticket`?",
        "criteria": {
          "bug": "Software bug or crash",
          "billing": "Invoice or card charge",
          "other": "Other inquiry"
        }
      },
      "is_urgent": {
        "type": "noul",
        "instructions": "Is this an emergency or urgent situation?"
      }
    }
  }' | jq .
