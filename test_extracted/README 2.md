# Social Listening & Sentiment Spike Pipeline – Implementation Kit

This kit contains everything you need to rebuild the workflow locally.

## Contents
- `blueprint.pdf` – the full architecture blueprint
- `workflow.py` – runnable Python script (standard library only)
- `.env.example` – required environment variables
- `mock_data.json` – realistic mock payloads for `--dry-run`
- `schema.sql` – Supabase table schema (if applicable)
- `requests.http` – all API calls for VS Code REST Client / Bruno / Postman
- `AI_IMPLEMENTATION_PROMPT.md` – prompt to port the workflow to another language
- `README.md` – this file

## Quick start
```bash
cp .env.example .env
python3 workflow.py --dry-run
```

## Checklist
- [ ] Step 1: Fetch brand mentions from X
- [ ] Step 2: Analyze sentiment with OpenAI
- [ ] Step 3: Cluster emerging topics
- [ ] Step 4: Persist trends in Supabase
- [ ] Step 5: Alert on sentiment spikes
