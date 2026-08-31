#!/usr/bin/env python3
"""Direct Ollama test with exact Nexus system instructions."""

from __future__ import annotations

import json
import os
import re
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

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

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

# Extract OrchestratorResult JSON schema from schemas.md
orchestrator_result_schema = None
match = re.search(r"## OrchestratorResult\n\n.*?```json\n(.*?)\n```", schema_instruction, re.DOTALL)
if match:
    try:
        orchestrator_result_schema = json.loads(match.group(1))
    except json.JSONDecodeError:
        pass

if orchestrator_result_schema is None:
    orchestrator_result_schema = {
        "type": "object",
        "required": ["status", "complete", "actions"],
        "properties": {
            "status": {"type": "string", "enum": ["SUCCESS", "ERROR", "PARTIAL_SUCCESS"]},
            "complete": {"type": "boolean"},
            "decision": {"type": "string", "enum": ["CONTINUE", "NO_ACTION", "COMPLETE"]},
            "response": {
                "type": "object",
                "required": ["required", "text"],
                "properties": {
                    "required": {"type": "boolean"},
                    "text": {"type": "string"},
                    "metadata": {"type": "object"}
                }
            },
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["action_id", "plugin", "action", "data"],
                    "properties": {
                        "action_id": {"type": "string"},
                        "plugin": {"type": "string"},
                        "action": {"type": "string"},
                        "data": {"type": "object"},
                        "depends_on": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "background_tasks": {"type": "array", "items": {"type": "object"}},
            "metadata": {"type": "object"},
            "error": {"type": "object"}
        }
    }

# Test context - a simple user message
test_context = {
    "event": {
        "event_id": "test-ollama-001",
        "type": "USER_MESSAGE",
        "source": "test_client",
        "data": {"text": "When was my last bad day?"},
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

# Build the request payload for Ollama
payload = {
    "model": OLLAMA_MODEL,
    "stream": False,
    "format": orchestrator_result_schema,
    "messages": [
        {"role": "system", "content": full_system_prompt},
        {"role": "user", "content": json.dumps(test_context, indent=2)}
    ]
}

# Make the API call
url = f"{OLLAMA_BASE_URL}/api/chat"
headers = {"Content-Type": "application/json"}
data = json.dumps(payload).encode("utf-8")

print(f"Testing Ollama with model: {OLLAMA_MODEL}")
print(f"URL: {url}")
print(f"System prompt length: {len(full_system_prompt)} chars")
print(f"Context JSON length: {len(json.dumps(test_context))} chars")
print()

try:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=None) as resp:
        raw_response = resp.read().decode("utf-8")
        result = json.loads(raw_response)

    # Extract the assistant message content
    message = result.get("message", {})
    text_response = message.get("content", "")

    print("=== RAW LLM RESPONSE ===")
    print(raw_response)
    print()

    # Try to parse the content as JSON
    try:
        parsed = json.loads(text_response)
        print("=== PARSED JSON ===")
        print(json.dumps(parsed, indent=2))
        print()

        # Validate structure
        if "actions" in parsed and isinstance(parsed["actions"], list):
            print("Valid OrchestratorResult structure")
            print(f"  Status: {parsed.get('status')}")
            print(f"  Complete: {parsed.get('complete')}")
            print(f"  Decision: {parsed.get('decision')}")
            print(f"  Actions: {len(parsed['actions'])}")
            for action in parsed["actions"]:
                print(f"    - {action.get('plugin')}.{action.get('action')}: {action.get('data')}")
        else:
            print("Missing 'actions' array in response")
    except json.JSONDecodeError as e:
        print(f"Response is not valid JSON: {e}")
        print("This means the LLM did not follow the schema instruction.")

except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    print(e.read().decode())
except urllib.error.URLError as e:
    print(f"Connection Error: {e.reason}")
    print("Make sure Ollama is running and accessible at the configured URL.")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
