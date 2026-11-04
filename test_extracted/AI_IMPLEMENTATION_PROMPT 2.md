# AI Implementation Prompt – Social Listening & Sentiment Spike Pipeline

You are a senior software engineer. Port the following workflow to the target
language and framework requested by the user. Preserve the exact API contracts,
authentication flow, error handling and data flow. Use only the target
language's standard library where possible. Keep all comments in English.

## Source
- Title: Social Listening & Sentiment Spike Pipeline
- Category: Marketing & Analytics
- Tools: X API, OpenAI API, Supabase, Slack

## Requirements
1. Read `workflow.py` (or `api_client.py`) and `requests.http` first.
2. Reproduce every HTTP call with the same method, headers and payload.
3. Keep the `--dry-run` mode working against `mock_data.json`.
4. Never hardcode secrets; read them from environment variables.
5. Add type hints and English docstrings.
