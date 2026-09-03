# Nexus Environment Variables

This document lists the environment variables that Nexus reads at runtime and a practical example for local development.

## Required and optional variables

### Core runtime

- `ORCHESTRATOR_PROVIDER` — selects the provider backend. Supported values in this project include `dummy`, `gemini`, `local`, and `ollama`.
- `NEXUS_CONTEXT_BUILDER_ENABLED` — enables or disables runtime context enrichment. Typical values: `1` or `0`.
- `NEXUS_PLUGIN_TIMEOUT_SECONDS` — timeout for plugin execution in seconds.

### Dashboard companion

- `NEXUS_DASHBOARD_PORT` — port for the dashboard server, default `11882`.
- `NEXUS_RUNTIME_URL` — base URL for the Nexus runtime server, default `http://127.0.0.1:8765`.

### Gemini provider

These are used when `ORCHESTRATOR_PROVIDER=gemini`.

- `GEMINI_API_KEY` — single Gemini API key.
- `GEMINI_API_KEYS` — comma-separated fallback pool of Gemini API keys.
- `GEMINI_MODEL` — model name such as `gemini-3.6-flash`.
- `GEMINI_TIMEOUT_SECONDS` — request timeout in seconds.
- `GEMINI_MAX_RETRIES` — max retry count.
- `GEMINI_RETRY_BACKOFF_SECONDS` — backoff delay between retries.
- `GEMINI_MAX_OUTPUT_TOKENS` — max output length.
- `GEMINI_CREDENTIAL_COOLDOWN_SECONDS` — cooldown period for failed credentials.

### Ollama provider

These are used when `ORCHESTRATOR_PROVIDER=ollama`.

- `OLLAMA_MODEL` — model name such as `qwen2.5:1.5b`.
- `OLLAMA_BASE_URL` — Ollama endpoint, default `http://127.0.0.1:11434`.
- `OLLAMA_TIMEOUT_SECONDS` — request timeout in seconds.
- `OLLAMA_MAX_RETRIES` — max retry count.
- `OLLAMA_RETRY_BACKOFF_SECONDS` — backoff delay between retries.
- `OLLAMA_MAX_OUTPUT_TOKENS` — max output length.
- `OLLAMA_KEEP_ALIVE` — Ollama keep-alive setting.

## Local `.env` example

Copy this into a local `.env` file in the project root:

```env
# Core Nexus settings
ORCHESTRATOR_PROVIDER=gemini
NEXUS_CONTEXT_BUILDER_ENABLED=1
NEXUS_PLUGIN_TIMEOUT_SECONDS=30.0

# Dashboard settings
NEXUS_DASHBOARD_PORT=11882
NEXUS_RUNTIME_URL=http://127.0.0.1:8765

# Gemini configuration
GEMINI_API_KEY=your_gemini_api_key_here
# GEMINI_API_KEYS=first-key,second-key,third-key
GEMINI_MODEL=gemini-3.6-flash
GEMINI_TIMEOUT_SECONDS=30
GEMINI_MAX_RETRIES=2
GEMINI_RETRY_BACKOFF_SECONDS=1
GEMINI_MAX_OUTPUT_TOKENS=16000
GEMINI_CREDENTIAL_COOLDOWN_SECONDS=30

# Ollama configuration (optional if not using Ollama)
OLLAMA_MODEL=qwen2.5:1.5b
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_TIMEOUT_SECONDS=180
OLLAMA_MAX_RETRIES=2
OLLAMA_RETRY_BACKOFF_SECONDS=1
OLLAMA_MAX_OUTPUT_TOKENS=1024
OLLAMA_KEEP_ALIVE=10m
```

## Notes

- The project's server loads `.env` automatically from the working directory in [nexus_server.py](nexus_server.py).
- Real credentials should stay in a local `.env` file and should not be committed to source control.
- The checked-in template in [.env.example](.env.example) is the safe version to share.
- `scripts/Set-NexusEnvironment.ps1` loads the root `.env` into the current PowerShell process without printing secret values.
