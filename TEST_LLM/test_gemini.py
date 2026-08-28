#!/usr/bin/env python3
"""Direct Gemini test with exact Nexus system instructions."""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            if name and name not in os.environ:
                os.environ[name] = value.strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

# Load prompts
system_path = os.path.join(os.path.dirname(__file__), "..", "orchestrators", "prompts", "system.md")
developer_path = os.path.join(os.path.dirname(__file__), "..", "orchestrators", "prompts", "developer.md")
schemas_path = os.path.join(os.path.dirname(__file__), "..", "orchestrators", "prompts", "schemas.md")

with open(system_path, encoding="utf-8") as f:
    system_instruction = f.read()
with open(developer_path, encoding="utf-8") as f:
    developer_instruction = f.read()
with open(schemas_path, encoding="utf-8") as f:
    schema_instruction = f.read()

# Build the full system prompt
full_system_prompt = f"""{system_instruction}

{developer_instruction}

{schema_instruction}
"""

# Test context - a simple user message
test_context = {
    "event": {
        "event_id": "test-gemini-001",
        "type": "USER_MESSAGE",
        "source": "test_client",
        "data": {"text": "What files are in the current directory?"},
        "timestamp": "2026-08-28T12:00:00Z"
    },
    "user_context": {},
    "memories": [],
    "working_context": {
        "execution_history": [],
        "last_execution_results": []
    },
    "active_tasks": [],
    "system_context": {
        "runtime": {
            "plugins": {
                "terminal": {
                    "actions": ["EXECUTE", "STATUS", "STOP", "LIST", "UPDATE", "CLEANUP"],
                    "contracts": {
                        "EXECUTE": {"required": {"command": {"type": "string"}}, "optional": {}}
                    }
                },
                "filesystem": {
                    "actions": ["READ", "WRITE", "APPEND", "DELETE", "COPY", "MOVE", "RENAME", "MKDIR", "LIST", "SEARCH", "METADATA", "EXISTS"],
                    "contracts": {
                        "LIST": {"required": {"path": {"type": "string"}}, "optional": {}}
                    }
                }
            }
        }
    }
}

# Build the request payload
payload = {
    "contents": [
        {
            "parts": [
                {"text": full_system_prompt},
                {"text": json.dumps(test_context, indent=2)}
            ]
        }
    ],
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 2048,
        "responseMimeType": "application/json"
    }
}

# Make the API call
url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
headers = {"Content-Type": "application/json"}
data = json.dumps(payload).encode("utf-8")

print(f"Testing Gemini with model: {GEMINI_MODEL}")
print(f"URL: {GEMINI_API_KEY}")
print(f"System prompt length: {len(full_system_prompt)} chars")
print(f"Context JSON length: {len(json.dumps(test_context))} chars")
print()

try:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        
    # Extract the text response
    candidates = result.get("candidates", [])
    if candidates:
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if parts:
            text_response = parts[0].get("text", "")
            print("=== RAW LLM RESPONSE ===")
            print(text_response)
            print()
            
            # Try to parse as JSON
            try:
                parsed = json.loads(text_response)
                print("=== PARSED JSON ===")
                print(json.dumps(parsed, indent=2))
                print()
                
                # Validate structure
                if "actions" in parsed and isinstance(parsed["actions"], list):
                    print(f"? Valid OrchestratorResult structure")
                    print(f"  Status: {parsed.get('status')}")
                    print(f"  Complete: {parsed.get('complete')}")
                    print(f"  Decision: {parsed.get('decision')}")
                    print(f"  Actions: {len(parsed['actions'])}")
                    for action in parsed["actions"]:
                        print(f"    - {action.get('plugin')}.{action.get('action')}: {action.get('data')}")
                else:
                    print("? Missing 'actions' array in response")
            except json.JSONDecodeError as e:
                print(f"? Response is not valid JSON: {e}")
                print("This means the LLM did not follow the schema instruction.")
        else:
            print("No text parts in response")
    else:
        print("No candidates in response")
        print(json.dumps(result, indent=2))
        
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    print(e.read().decode())
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
