"""Curated workflow seeds – the single source of truth for workflow topics.

Every workflow is built from an explicit, hand-curated combination of real
records from ``src/data/apis.json`` and ``src/data/alternatives.json``. There is
no heuristic name matching anymore: a seed names the exact API slugs and
alternative slugs it is allowed to use.

Each seed becomes a workflow skeleton. The LLM fills the editorial content
(steps, code, glossary, troubleshooting) but may only ground on the APIs listed
in ``details.api_slugs`` and may only reference the alternatives listed in
``details.alternative_slugs``.
"""

from __future__ import annotations

from typing import Any


def _seed(
    slug: str,
    title: str,
    category: str,
    tags: list[str],
    api_slugs: list[str],
    alternative_slugs: list[str],
    difficulty: str,
    duration: str,
    use_case: str,
    description: str,
    steps: list[tuple[str, str]],
) -> dict[str, Any]:
    return {
        "slug": slug,
        "title": title,
        "category": category,
        "tags": tags,
        "api_slugs": api_slugs,
        "alternative_slugs": alternative_slugs,
        "difficulty": difficulty,
        "duration": duration,
        "use_case": use_case,
        "description": description,
        "steps": [{"title": t, "description": d} for t, d in steps],
    }


# --------------------------------------------------------------------------- #
# Curated catalogue (76 workflows, proportional to the previous distribution)
# --------------------------------------------------------------------------- #
SEEDS: list[dict[str, Any]] = [
    # ----------------------------- AI & LLM (8) ---------------------------- #
    _seed(
        "ai-content-generation-pipeline",
        "AI Content Generation Pipeline",
        "AI & LLM",
        ["ai", "content", "llm", "automation"],
        ["openai-gpt-4-api", "anthropic-claude-api", "supabase-database-api"],
        ["openai-alternatives", "notion-ai-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Generate, review and store long-form content with two LLMs and a Supabase content queue.",
        "Build a two-model content pipeline that drafts articles with OpenAI, critiques them with Anthropic Claude and stores approved drafts in Supabase for publication.",
        [
            ("Load the content brief queue", "Read pending briefs from a local JSON fixture and normalise their fields."),
            ("Draft the article with OpenAI", "Call the chat completions endpoint and store the returned draft text."),
            ("Critique the draft with Anthropic Claude", "Send the draft to the messages endpoint and capture structured feedback."),
            ("Persist approved drafts in Supabase", "Upsert the reviewed draft into a content table through the REST API."),
            ("Export a publication report", "Summarise the processed drafts and write a deterministic JSON report."),
        ],
    ),
    _seed(
        "multi-model-prompt-router",
        "Multi-Model Prompt Router",
        "AI & LLM",
        ["ai", "llm", "routing", "inference"],
        ["groq-inference-api", "together-ai-api", "openai-gpt-4-api"],
        ["openai-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Route prompts to the cheapest suitable model while keeping one OpenAI-compatible contract.",
        "Classify incoming prompts and route them to Groq, Together AI or OpenAI based on complexity, latency budget and cost.",
        [
            ("Classify the incoming prompt", "Score prompt complexity deterministically from length and keyword signals."),
            ("Select the inference provider", "Map the complexity score to a provider endpoint and document the routing table."),
            ("Call the selected chat endpoint", "Execute one OpenAI-compatible chat completion request with a shared helper."),
            ("Log the routing decision", "Write provider, latency and token estimates to a JSON routing log."),
        ],
    ),
    _seed(
        "llm-evaluation-benchmark",
        "LLM Evaluation Benchmark",
        "AI & LLM",
        ["ai", "llm", "evaluation", "benchmark"],
        ["openai-gpt-4-api", "mistral-ai-api", "airtable-api"],
        ["openai-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Benchmark two LLM providers on the same prompts and store the scores in Airtable.",
        "Run a fixed prompt suite against OpenAI and Mistral, score the answers and record the benchmark rows in Airtable.",
        [
            ("Load and validate the prompt suite", "Read benchmark cases from a deterministic fixture and reject malformed entries."),
            ("Run the OpenAI baseline", "Collect answers from the chat completions endpoint for every case."),
            ("Run the Mistral comparison", "Collect answers from the Mistral chat endpoint for the same cases."),
            ("Score and rank the answers", "Apply deterministic length and keyword scoring and rank the providers."),
            ("Write benchmark rows to Airtable", "Create records in the benchmark table through the REST API."),
        ],
    ),
    _seed(
        "batch-llm-processing",
        "Batch LLM Processing",
        "AI & LLM",
        ["ai", "llm", "batch", "cost"],
        ["openai-batch-api", "openai-gpt-4-api", "supabase-database-api"],
        ["openai-alternatives", "supabase-alternatives"],
        "Advanced",
        "60–90 minutes",
        "Submit large prompt sets as an OpenAI batch job and reconcile the results in Supabase.",
        "Prepare a JSONL batch file, submit it to the OpenAI Batch API, poll the job status and store completed results in Supabase.",
        [
            ("Build the JSONL batch file", "Transform the queued prompts into the batch request format."),
            ("Upload and submit the batch job", "Create the batch job through the Batch API and capture its identifier."),
            ("Poll the batch status", "Check the job until it reaches a terminal state without tight looping."),
            ("Reconcile results into Supabase", "Upsert the completed answers into a results table."),
        ],
    ),
    _seed(
        "ai-customer-insights",
        "AI Customer Insights",
        "AI & LLM",
        ["ai", "analytics", "customer", "insights"],
        ["openai-gpt-4-api", "posthog-analytics-api", "supabase-database-api"],
        ["openai-alternatives", "google-analytics-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Turn product analytics events into AI-written customer insights stored for the team.",
        "Pull PostHog event cohorts, summarise behaviour patterns with OpenAI and persist the generated insights in Supabase.",
        [
            ("Pull event cohorts from PostHog", "Query the events endpoint and aggregate counts per cohort."),
            ("Summarise behaviour with OpenAI", "Send the aggregated cohort summary to the chat completions endpoint."),
            ("Store insights in Supabase", "Upsert each insight with its cohort key into the insights table."),
            ("Generate the insight digest", "Produce a deterministic markdown digest for the growth team."),
        ],
    ),
    _seed(
        "claude-document-summarizer",
        "Claude Document Summarizer",
        "AI & LLM",
        ["ai", "documents", "summary", "claude"],
        ["anthropic-claude-api", "aws-s3-api"],
        ["openai-alternatives"],
        "Intermediate",
        "45–60 minutes",
        "Summarise uploaded documents with Anthropic Claude and archive the summaries on S3.",
        "Read document manifest entries, request concise summaries from the Anthropic messages endpoint and archive the results in S3.",
        [
            ("Load the document manifest", "Read S3 object keys and metadata from a deterministic manifest."),
            ("Summarise each document with Claude", "Call the messages endpoint and request a fixed-length summary."),
            ("Archive summaries to S3", "Write the summary objects back to the archive prefix."),
            ("Report failing documents", "List unreadable or unsupported documents in a JSON report."),
        ],
    ),
    _seed(
        "gemini-multimodal-analyzer",
        "Gemini Multimodal Analyzer",
        "AI & LLM",
        ["ai", "multimodal", "gemini", "images"],
        ["google-gemini-api", "vercel-blob-api"],
        ["openai-alternatives", "canva-alternatives"],
        "Advanced",
        "60–75 minutes",
        "Analyse product images with Gemini and store the extracted attributes with the blob URL.",
        "Send image references to the Gemini API, extract structured attributes and keep the results next to the Vercel Blob asset URL.",
        [
            ("List image assets from Vercel Blob", "Collect the blob URLs and content types for the analysis batch."),
            ("Analyse each image with Gemini", "Request structured JSON attributes from the Gemini endpoint."),
            ("Normalise the extracted attributes", "Validate the JSON shape and drop incomplete records."),
            ("Write the attribute report", "Produce a deterministic report keyed by blob URL."),
        ],
    ),
    _seed(
        "watson-assistant-helpdesk",
        "Watson Assistant Helpdesk",
        "AI & LLM",
        ["assistant", "helpdesk", "ai", "support"],
        ["ibm-watson-assistant-api", "zendesk-support-api"],
        ["intercom-alternatives", "zendesk-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Deflect repetitive helpdesk tickets with Watson Assistant and escalate the rest to Zendesk.",
        "Send incoming questions to Watson Assistant, detect low-confidence answers and create Zendesk tickets for escalation.",
        [
            ("Send the question to Watson Assistant", "Call the message endpoint and capture the answer and confidence."),
            ("Apply the confidence threshold", "Decide whether the answer is safe to auto-send or must be escalated."),
            ("Create an escalation ticket in Zendesk", "Open a ticket with the original question and conversation context."),
            ("Produce the deflection report", "Count resolved and escalated questions deterministically."),
        ],
    ),

    # ------------------------- AI & Speech / Vision (4) -------------------- #
    _seed(
        "podcast-transcription-pipeline",
        "Podcast Transcription Pipeline",
        "AI & Speech",
        ["transcription", "podcast", "speech", "ai"],
        ["openai-whisper-api", "deepgram-speech-api", "supabase-database-api"],
        ["deepgram-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Transcribe podcast episodes with two speech APIs and store transcripts in Supabase.",
        "Transcribe episode audio through Whisper and Deepgram, compare the transcripts and store the preferred result in Supabase.",
        [
            ("Prepare the episode queue", "Read audio URLs and metadata from a deterministic manifest."),
            ("Transcribe with OpenAI Whisper", "Call the audio transcriptions endpoint for each episode."),
            ("Transcribe with Deepgram", "Call the Deepgram listen endpoint for the same episodes."),
            ("Choose and store the transcript", "Select the longer transcript and upsert it into Supabase."),
        ],
    ),
    _seed(
        "ai-voiceover-production",
        "AI Voiceover Production",
        "AI & Speech",
        ["voice", "audio", "tts", "production"],
        ["elevenlabs-voice-api", "aws-polly-api", "aws-s3-api"],
        ["elevenlabs-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Generate voiceovers with ElevenLabs and Polly and archive the audio on S3.",
        "Create voiceover audio from a script, render an ElevenLabs and an AWS Polly variant, and archive both under the S3 media prefix.",
        [
            ("Validate the voiceover scripts", "Reject empty scripts and normalise inline markers."),
            ("Generate the ElevenLabs variant", "Call the text-to-speech endpoint with a fixed voice identifier."),
            ("Generate the Polly variant", "Call the Polly synthesis endpoint for the same script."),
            ("Archive audio variants on S3", "Store both audio objects and write an asset manifest."),
        ],
    ),
    _seed(
        "ai-image-generation-pipeline",
        "AI Image Generation Pipeline",
        "AI & Vision",
        ["image", "generation", "ai", "assets"],
        ["stability-ai-image-api", "api-ai-image-generator", "vercel-blob-api"],
        ["canva-alternatives", "figma-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Generate campaign images with two image APIs and publish them to Vercel Blob.",
        "Render a base image with Stability AI, create a stylised variant with DeepAI and upload both assets to Vercel Blob.",
        [
            ("Validate the creative briefs", "Normalise prompts, aspect ratios and asset names."),
            ("Render the Stability AI image", "Call the generation endpoint and capture the binary result."),
            ("Render the DeepAI variant", "Call the text-to-image endpoint for the stylised variant."),
            ("Upload assets to Vercel Blob", "Store both images and write a public asset manifest."),
        ],
    ),

    # --------------------------- Search & Vector (4) ----------------------- #
    _seed(
        "semantic-search-knowledge-base",
        "Semantic Search Knowledge Base",
        "Search & Vector",
        ["search", "embeddings", "vector", "knowledge"],
        ["openai-embeddings-api", "pinecone-vector-api", "notion-api"],
        ["pinecone-alternatives", "notion-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Index Notion pages as embeddings in Pinecone and answer semantic queries.",
        "Export Notion page text, create OpenAI embeddings, upsert them into Pinecone and run a semantic nearest-neighbour query.",
        [
            ("Export pages from Notion", "Query the search endpoint and extract plain text blocks."),
            ("Create embeddings with OpenAI", "Batch the page text and request vectors from the embeddings endpoint."),
            ("Upsert vectors into Pinecone", "Write vectors and metadata into the knowledge index namespace."),
            ("Run a semantic query", "Embed a query string and return the top matching pages."),
        ],
    ),
    _seed(
        "hybrid-search-product-catalog",
        "Hybrid Search Product Catalog",
        "Search & Vector",
        ["search", "ecommerce", "catalog", "embeddings"],
        ["algolia-search-api", "cohere-embed-api", "shopify-admin-api"],
        ["algolia-alternatives", "shopify-alternatives"],
        "Advanced",
        "90–120 minutes",
        "Combine keyword and vector search for a Shopify product catalog using Algolia and Cohere.",
        "Sync Shopify products into Algolia, enrich them with Cohere embeddings and merge keyword and semantic ranking for search results.",
        [
            ("Fetch products from Shopify", "Page through the Admin API product endpoint and normalise fields."),
            ("Create Cohere embeddings", "Embed product titles and descriptions for semantic ranking."),
            ("Index products in Algolia", "Push records with keyword attributes and embedding references."),
            ("Merge keyword and semantic results", "Re-rank Algolia hits with embedding similarity and return the top results."),
        ],
    ),
    _seed(
        "rag-document-assistant",
        "RAG Document Assistant",
        "Search & Vector",
        ["rag", "embeddings", "vector", "assistant"],
        ["openai-embeddings-api", "qdrant-vector-api", "openai-gpt-4-api"],
        ["pinecone-alternatives", "openai-alternatives"],
        "Advanced",
        "90–120 minutes",
        "Build a retrieval-augmented assistant over internal documents with Qdrant and OpenAI.",
        "Chunk documents, embed them with OpenAI, store vectors in Qdrant and answer questions with retrieval-augmented completions.",
        [
            ("Chunk the source documents", "Split text into overlapping chunks with stable identifiers."),
            ("Embed and upsert chunks into Qdrant", "Create embeddings and write points with source metadata."),
            ("Retrieve relevant context", "Embed the question and search the Qdrant collection."),
            ("Answer with a grounded completion", "Send retrieved context and the question to the chat endpoint."),
        ],
    ),
    _seed(
        "content-similarity-audit",
        "Content Similarity Audit",
        "Search & Vector",
        ["content", "similarity", "vector", "audit"],
        ["weaviate-vector-api", "cohere-embed-api", "airtable-api"],
        ["pinecone-alternatives", "airtable-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Detect near-duplicate content with Weaviate embeddings and log the audit in Airtable.",
        "Embed published articles with Cohere, index them in Weaviate and flag near-duplicate pairs in an Airtable audit table.",
        [
            ("Load the article inventory", "Read article identifiers and body text from a deterministic fixture."),
            ("Embed articles with Cohere", "Request document embeddings for every article."),
            ("Index and compare in Weaviate", "Upsert objects and query for nearest neighbours per article."),
            ("Log duplicate pairs in Airtable", "Create audit rows with similarity scores and recommendations."),
        ],
    ),

    # -------------------------- Communication (7) --------------------------- #
    _seed(
        "transactional-email-delivery",
        "Transactional Email Delivery",
        "Communication",
        ["email", "transactional", "delivery", "reliability"],
        ["resend-email-api", "sendgrid-email-api", "supabase-database-api"],
        ["mailchimp-alternatives"],
        "Intermediate",
        "45–60 minutes",
        "Send transactional emails through Resend with a SendGrid fallback and log delivery attempts.",
        "Send queued transactional emails through Resend, fall back to SendGrid on failure and record delivery outcomes in Supabase.",
        [
            ("Load the outbound email queue", "Validate recipients and template identifiers from a deterministic queue."),
            ("Send through Resend", "Call the emails endpoint and capture the provider message id."),
            ("Retry through SendGrid", "Fall back to the SendGrid mail send endpoint for failed messages."),
            ("Record delivery outcomes in Supabase", "Insert one row per attempt with status and provider."),
        ],
    ),
    _seed(
        "email-campaign-automation",
        "Email Campaign Automation",
        "Communication",
        ["email", "campaign", "marketing", "automation"],
        ["sendinblue-email-api", "resend-email-api", "airtable-api"],
        ["mailchimp-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Run a segmented email campaign with Sendinblue and track campaign state in Airtable.",
        "Select campaign recipients from Airtable, send segmented campaigns with Sendinblue and record per-recipient status rows.",
        [
            ("Select campaign segments", "Read contacts and segments from the Airtable base."),
            ("Render personalised content", "Merge contact fields into the campaign template deterministically."),
            ("Send the campaign with Sendinblue", "Call the transactional email endpoint for each recipient."),
            ("Update campaign status in Airtable", "Mark sent, skipped and failed recipients."),
        ],
    ),
    _seed(
        "sms-alert-system",
        "SMS Alert System",
        "Communication",
        ["sms", "alerts", "twilio", "notifications"],
        ["twilio-messaging-api", "sendinblue-sms-api", "supabase-database-api"],
        ["whatsapp-alternatives"],
        "Intermediate",
        "45–60 minutes",
        "Deliver critical SMS alerts through Twilio and Sendinblue with delivery tracking.",
        "Route critical incidents to SMS through Twilio, use Sendinblue as a secondary provider and store delivery receipts in Supabase.",
        [
            ("Load and prioritise alerts", "Read alerts from the queue and keep only critical severities."),
            ("Send SMS through Twilio", "Call the Messages endpoint with the alert body."),
            ("Send fallback SMS through Sendinblue", "Use the SMS endpoint when Twilio returns a rate-limit error."),
            ("Store delivery receipts in Supabase", "Insert provider, message id and status for each alert."),
        ],
    ),
    _seed(
        "slack-incident-notifications",
        "Slack Incident Notifications",
        "Communication",
        ["slack", "incidents", "notifications", "devops"],
        ["slack-web-api", "slack-api", "sentry-error-api"],
        ["slack-alternatives"],
        "Intermediate",
        "45–60 minutes",
        "Turn new Sentry issues into structured Slack incident messages.",
        "Poll Sentry for unresolved issues, format an incident summary and post it to a Slack channel with severity colouring.",
        [
            ("Fetch unresolved issues from Sentry", "Query the issues endpoint and normalise severity fields."),
            ("Format the incident blocks", "Build Slack Block Kit payloads with level, culprit and link."),
            ("Post to the incident channel", "Call chat.postMessage with the formatted blocks."),
            ("Deduplicate already-notified issues", "Track notified issue ids in a local state file."),
        ],
    ),
    _seed(
        "telegram-community-bot",
        "Telegram Community Bot",
        "Communication",
        ["telegram", "community", "bot", "ai"],
        ["telegram-bot-api", "openai-gpt-4-api", "supabase-database-api"],
        ["openai-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Answer community questions on Telegram with a moderated AI assistant.",
        "Receive Telegram updates, answer eligible questions with OpenAI and log conversations in Supabase for moderation.",
        [
            ("Fetch Telegram updates", "Call getUpdates and keep only new message ids."),
            ("Generate a moderated answer", "Send the question to the OpenAI chat endpoint with a strict system prompt."),
            ("Send the reply on Telegram", "Call sendMessage with the generated answer."),
            ("Log conversations in Supabase", "Store question, answer and chat id for moderation review."),
        ],
    ),
    _seed(
        "video-call-summarizer",
        "Video Call Summarizer",
        "Communication",
        ["video", "meetings", "summary", "transcription"],
        ["twilio-video-api", "openai-whisper-api", "notion-api"],
        ["zoom-alternatives", "notion-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Summarise Twilio Video recordings with Whisper and publish notes to Notion.",
        "List completed Twilio Video rooms, transcribe their recordings with Whisper and create structured Notion meeting notes.",
        [
            ("List completed video rooms", "Query the Video rooms endpoint and select recordings to process."),
            ("Transcribe the recordings", "Submit recording media to the Whisper transcriptions endpoint."),
            ("Summarise the transcript", "Call OpenAI to extract decisions and action items."),
            ("Publish meeting notes to Notion", "Create a page in the meetings database with the summary."),
        ],
    ),
    _seed(
        "conversational-messaging-hub",
        "Conversational Messaging Hub",
        "Communication",
        ["messaging", "conversations", "crm", "ai"],
        ["twilio-conversations-api", "hubspot-crm-api", "openai-gpt-4-api"],
        ["intercom-alternatives", "hubspot-alternatives"],
        "Advanced",
        "90–120 minutes",
        "Unify Twilio conversations, HubSpot contacts and AI replies in one inbox workflow.",
        "Read Twilio Conversations messages, enrich them with HubSpot contact data and draft AI replies for agent review.",
        [
            ("Fetch conversation messages", "List conversations and messages from the Twilio Conversations API."),
            ("Match senders to HubSpot contacts", "Search HubSpot contacts by phone or email and attach the CRM context."),
            ("Draft replies with OpenAI", "Generate a suggested reply using the CRM context and conversation history."),
            ("Queue replies for agent review", "Write drafts and CRM context to a review queue file."),
        ],
    ),

    # ----------------------------- CRM & Sales (3) ------------------------- #
    _seed(
        "crm-lead-scoring",
        "CRM Lead Scoring",
        "CRM & Sales",
        ["crm", "leads", "scoring", "sales"],
        ["hubspot-crm-api", "openai-gpt-4-api", "slack-web-api"],
        ["hubspot-alternatives", "salesforce-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Score HubSpot leads with AI and notify the sales team about hot opportunities.",
        "Fetch new HubSpot contacts, enrich them with OpenAI-based fit scoring and post high-score leads to Slack.",
        [
            ("Fetch new contacts from HubSpot", "Query recent contacts with the properties required for scoring."),
            ("Score lead fit with OpenAI", "Send firmographic data to the chat endpoint and parse a numeric score."),
            ("Notify sales about hot leads", "Post leads above the score threshold to the sales Slack channel."),
            ("Write the scoring summary", "Produce a deterministic summary of scored and skipped leads."),
        ],
    ),
    _seed(
        "salesforce-pipeline-sync",
        "Salesforce Pipeline Sync",
        "CRM & Sales",
        ["salesforce", "pipeline", "sync", "reporting"],
        ["salesforce-rest-api", "airtable-api", "slack-web-api"],
        ["salesforce-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Sync Salesforce opportunities into Airtable and publish a weekly pipeline snapshot to Slack.",
        "Query Salesforce opportunities, mirror the pipeline in Airtable and post a weekly forecast summary to Slack.",
        [
            ("Query Salesforce opportunities", "Run a SOQL query and normalise stage and amount fields."),
            ("Upsert the pipeline into Airtable", "Match records by opportunity id and update changed fields."),
            ("Compute the pipeline forecast", "Aggregate weighted amounts per stage deterministically."),
            ("Publish the forecast to Slack", "Post the weekly snapshot with stage totals to the revenue channel."),
        ],
    ),
    _seed(
        "personalized-outreach-engine",
        "Personalized Outreach Engine",
        "CRM & Sales",
        ["outreach", "personalization", "sales", "email"],
        ["hubspot-crm-api", "openai-gpt-4-api", "resend-email-api"],
        ["zoominfo-alternatives", "hubspot-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Generate personalised outbound emails from CRM data and send them through Resend.",
        "Read target contacts from HubSpot, generate a personalised first line with OpenAI and send approved outreach emails via Resend.",
        [
            ("Load target contacts from HubSpot", "Select contacts that match the outbound segment criteria."),
            ("Generate personalised copy", "Ask OpenAI for a concise subject and first line per contact."),
            ("Send outreach emails", "Call the Resend emails endpoint for each approved message."),
            ("Log outreach status", "Record sent contact ids and provider message ids in a JSON log."),
        ],
    ),

    # --------------------------- Customer Support (3) ---------------------- #
    _seed(
        "support-ticket-triage",
        "Support Ticket Triage",
        "Customer Support",
        ["support", "tickets", "triage", "ai"],
        ["zendesk-support-api", "openai-gpt-4-api", "supabase-database-api"],
        ["zendesk-alternatives", "intercom-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Classify incoming Zendesk tickets and route them to the right queue.",
        "Read new Zendesk tickets, classify intent and urgency with OpenAI and write routing decisions to Supabase.",
        [
            ("Fetch new Zendesk tickets", "Query open tickets that have not been triaged yet."),
            ("Classify intent and urgency", "Call OpenAI and parse a constrained JSON classification."),
            ("Route the ticket in Zendesk", "Update tags and assignee group based on the classification."),
            ("Record triage decisions in Supabase", "Store ticket id, intent, urgency and target group."),
        ],
    ),
    _seed(
        "ai-help-center-search",
        "AI Help Center Search",
        "Customer Support",
        ["helpcenter", "search", "embeddings", "support"],
        ["notion-api", "openai-embeddings-api", "pinecone-vector-api"],
        ["notion-alternatives", "intercom-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Index help center articles from Notion and answer support questions with semantic search.",
        "Export Notion help articles, embed them into Pinecone and expose a semantic search function for support agents.",
        [
            ("Export help articles from Notion", "Read published help center pages and extract clean text."),
            ("Create article embeddings", "Request vectors from the OpenAI embeddings endpoint."),
            ("Upsert vectors into Pinecone", "Store vectors with article titles and URLs as metadata."),
            ("Answer support queries", "Embed the question and return the best matching articles."),
        ],
    ),
    _seed(
        "csat-feedback-analysis",
        "CSAT Feedback Analysis",
        "Customer Support",
        ["csat", "feedback", "sentiment", "support"],
        ["zendesk-support-api", "google-sheets-api", "openai-gpt-4-api"],
        ["zendesk-alternatives", "google-analytics-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Analyse CSAT comments and write sentiment summaries into a Google Sheet.",
        "Collect CSAT responses from Zendesk, classify sentiment with OpenAI and append weekly summaries to Google Sheets.",
        [
            ("Collect CSAT responses from Zendesk", "Query satisfaction ratings with their comments."),
            ("Classify feedback sentiment", "Send comments to OpenAI and parse sentiment and theme labels."),
            ("Append summaries to Google Sheets", "Write one row per theme with counts and example comments."),
            ("Detect negative feedback spikes", "Compare weekly negative ratios and flag significant increases."),
        ],
    ),

    # --------------------------- Finance & Payments (6) -------------------- #
    _seed(
        "subscription-billing-automation",
        "Subscription Billing Automation",
        "Finance & Payments",
        ["billing", "subscriptions", "stripe", "automation"],
        ["stripe-payments-api", "resend-email-api", "supabase-database-api"],
        ["stripe-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Create Stripe subscriptions, send receipts and reconcile billing state.",
        "Create subscription checkouts in Stripe, send branded receipts with Resend and reconcile subscription state in Supabase.",
        [
            ("Create or fetch Stripe customers", "Resolve the customer by email and create it when missing."),
            ("Start the subscription", "Create a subscription with the configured price identifier."),
            ("Send the receipt email", "Call the Resend emails endpoint with the invoice summary."),
            ("Reconcile billing state", "Upsert subscription status and renewal dates into Supabase."),
        ],
    ),
    _seed(
        "invoice-reconciliation",
        "Invoice Reconciliation",
        "Finance & Payments",
        ["invoices", "reconciliation", "stripe", "finance"],
        ["stripe-payments-api", "google-sheets-api", "openai-gpt-4-api"],
        ["quickbooks-alternatives", "stripe-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Reconcile Stripe invoices against a Google Sheets ledger and flag mismatches.",
        "List paid Stripe invoices, compare them with ledger rows in Google Sheets and explain discrepancies with OpenAI.",
        [
            ("List paid Stripe invoices", "Page through invoices and normalise amounts and customer ids."),
            ("Read the Google Sheets ledger", "Fetch ledger rows and index them by invoice number."),
            ("Detect reconciliation mismatches", "Compare amounts and dates deterministically."),
            ("Explain mismatches with OpenAI", "Generate a short explanation and suggested action per mismatch."),
        ],
    ),
    _seed(
        "paypal-payout-monitoring",
        "PayPal Payout Monitoring",
        "Finance & Payments",
        ["paypal", "payouts", "monitoring", "finance"],
        ["paypal-payments-api", "slack-web-api", "airtable-api"],
        ["stripe-alternatives", "quickbooks-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Monitor PayPal payout batches and alert finance about failed transfers.",
        "Read PayPal payout batch status, record every item in Airtable and alert finance about failures in Slack.",
        [
            ("Fetch payout batches", "List recent payout batches and their item statuses."),
            ("Normalise payout items", "Map receiver, amount and status fields into stable records."),
            ("Record payouts in Airtable", "Upsert one row per payout item."),
            ("Alert finance about failures", "Post failed and returned items to the finance Slack channel."),
        ],
    ),
    _seed(
        "stock-market-alerts",
        "Stock Market Alerts",
        "Finance & Payments",
        ["stocks", "alerts", "market", "finance"],
        ["finnhub-stock-api", "twelvedata-api", "slack-web-api"],
        ["quickbooks-alternatives"],
        "Intermediate",
        "45–60 minutes",
        "Detect price movements with Finnhub and Twelve Data and send Slack alerts.",
        "Fetch quotes from Finnhub, cross-check them with Twelve Data and post alerts when price thresholds are crossed.",
        [
            ("Fetch the watchlist quotes", "Request quotes from Finnhub for the configured tickers."),
            ("Cross-check with Twelve Data", "Fetch time series values for the same tickers."),
            ("Evaluate price thresholds", "Compare daily change and volume against configured thresholds."),
            ("Send Slack market alerts", "Post a formatted alert for every triggered ticker."),
        ],
    ),
    _seed(
        "crypto-portfolio-tracker",
        "Crypto Portfolio Tracker",
        "Finance & Payments",
        ["crypto", "portfolio", "tracking", "telegram"],
        ["finnhub-crypto-api", "google-sheets-api", "telegram-bot-api"],
        ["stripe-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Track a crypto portfolio in Google Sheets and send Telegram valuation updates.",
        "Read portfolio holdings from Google Sheets, price them with Finnhub Crypto and send daily valuation updates via Telegram.",
        [
            ("Read holdings from Google Sheets", "Load symbol and amount rows from the portfolio sheet."),
            ("Price holdings with Finnhub Crypto", "Fetch current prices and compute position values."),
            ("Update the portfolio sheet", "Write valuation and change columns back to the sheet."),
            ("Send the Telegram valuation update", "Post the total value and top movers to the portfolio chat."),
        ],
    ),
    _seed(
        "bank-transaction-enrichment",
        "Bank Transaction Enrichment",
        "Finance & Payments",
        ["banking", "transactions", "enrichment", "plaid"],
        ["plaid-financial-api", "openai-gpt-4-api", "airtable-api"],
        ["quickbooks-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Categorise Plaid bank transactions with AI and sync them to Airtable.",
        "Fetch Plaid transactions, categorise merchants with OpenAI and upsert enriched transaction rows into Airtable.",
        [
            ("Fetch transactions from Plaid", "Sync transactions for the configured access token."),
            ("Categorise merchants with OpenAI", "Classify merchant names into a fixed category set."),
            ("Upsert enriched rows into Airtable", "Match by transaction id and update category fields."),
            ("Summarise monthly spending", "Aggregate spend per category deterministically."),
        ],
    ),

    # ---------------------------- Data & Databases (6) --------------------- #
    _seed(
        "supabase-realtime-dashboard",
        "Supabase Realtime Dashboard",
        "Data & Databases",
        ["supabase", "realtime", "dashboard", "analytics"],
        ["supabase-database-api", "posthog-analytics-api", "vercel-blob-api"],
        ["supabase-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Feed a Supabase-backed dashboard with product events and cached chart assets.",
        "Aggregate PostHog events, upsert hourly metrics into Supabase and store rendered chart snapshots in Vercel Blob.",
        [
            ("Aggregate PostHog events", "Query event counts per hour and normalise the metric shape."),
            ("Upsert hourly metrics into Supabase", "Write one row per metric and hour with conflict handling."),
            ("Render the chart snapshot", "Build a deterministic SVG summary from the metric rows."),
            ("Upload the snapshot to Vercel Blob", "Store the rendered chart and record its public URL."),
        ],
    ),
    _seed(
        "airtable-content-sync",
        "Airtable Content Sync",
        "Data & Databases",
        ["airtable", "content", "sync", "notion"],
        ["airtable-api", "notion-api", "resend-email-api"],
        ["airtable-alternatives", "notion-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Sync editorial records from Airtable into Notion and notify authors by email.",
        "Read approved content rows from Airtable, mirror them as Notion pages and email authors about newly published items.",
        [
            ("Read approved rows from Airtable", "Filter records by the approved status and normalise fields."),
            ("Create or update Notion pages", "Match by external id and update the page body."),
            ("Send author notifications", "Call the Resend emails endpoint for every published item."),
            ("Log the sync result", "Write a deterministic sync report with created and updated counts."),
        ],
    ),
    _seed(
        "mongodb-data-pipeline",
        "MongoDB Data Pipeline",
        "Data & Databases",
        ["mongodb", "pipeline", "documents", "ai"],
        ["mongodb-atlas-api", "aws-s3-api", "openai-gpt-4-api"],
        ["microsoft-access-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Process MongoDB documents with AI and archive curated extracts on S3.",
        "Read documents from MongoDB Atlas, generate AI summaries and archive the curated extracts as S3 objects.",
        [
            ("Query documents from MongoDB Atlas", "Fetch documents updated since the last checkpoint."),
            ("Summarise documents with OpenAI", "Generate a short summary and topic labels per document."),
            ("Archive extracts on S3", "Write one JSON object per document batch."),
            ("Update the checkpoint", "Persist the latest processed timestamp deterministically."),
        ],
    ),
    _seed(
        "postgres-backup-reporting",
        "Postgres Backup Reporting",
        "Data & Databases",
        ["postgres", "backup", "reporting", "neon"],
        ["neon-postgres-api", "slack-web-api", "google-sheets-api"],
        ["supabase-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Track Neon Postgres backup health and publish a weekly report.",
        "Collect Neon backup metadata, append health rows to Google Sheets and post a weekly backup report to Slack.",
        [
            ("Collect Neon backup metadata", "Query the backups endpoint and normalise timestamps and sizes."),
            ("Append health rows to Google Sheets", "Write one row per backup with age and status."),
            ("Evaluate backup freshness", "Flag backups older than the configured retention window."),
            ("Post the weekly backup report", "Send the summary to the operations Slack channel."),
        ],
    ),
    _seed(
        "redis-rate-limit-store",
        "Redis Rate Limit Store",
        "Data & Databases",
        ["redis", "rate-limiting", "upstash", "edge"],
        ["upstash-redis-api", "cloudflare-workers-api", "sentry-error-api"],
        ["supabase-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Implement a distributed rate limiter with Upstash Redis and report violations to Sentry.",
        "Increment Upstash Redis counters per API key, enforce a sliding window and report limit violations as Sentry events.",
        [
            ("Increment the Upstash counter", "Call the Redis REST command endpoint for the current window."),
            ("Enforce the rate limit decision", "Compare the counter with the configured quota and return an allow or deny decision."),
            ("Report violations to Sentry", "Send a structured event when a key exceeds its quota."),
            ("Write the limiter audit report", "Summarise allowed and denied requests per key."),
        ],
    ),
    _seed(
        "google-sheets-reporting-hub",
        "Google Sheets Reporting Hub",
        "Data & Databases",
        ["sheets", "reporting", "automation", "ai"],
        ["google-sheets-api", "openai-gpt-4-api", "resend-email-api"],
        ["microsoft-excel-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Turn spreadsheet data into an AI-written executive email report.",
        "Read KPI rows from Google Sheets, generate a narrative summary with OpenAI and email the report with Resend.",
        [
            ("Read KPI rows from Google Sheets", "Fetch the configured range and validate numeric columns."),
            ("Generate the executive narrative", "Send computed deltas to the OpenAI chat endpoint."),
            ("Email the report with Resend", "Send an HTML email containing the narrative and key metrics."),
            ("Record the report run", "Append a run row with timestamp and delivery status."),
        ],
    ),

    # --------------------------- Developer Tools (8) ----------------------- #
    _seed(
        "deployment-monitoring-alerts",
        "Deployment Monitoring Alerts",
        "Developer Tools",
        ["deployment", "monitoring", "cloudflare", "sentry"],
        ["cloudflare-workers-api", "sentry-performance-api", "slack-web-api"],
        ["vercel-alternatives", "netlify-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Correlate Cloudflare Worker deployments with Sentry performance regressions.",
        "Read Cloudflare deployment metadata, compare Sentry error rates before and after each release and alert on regressions.",
        [
            ("Read Cloudflare deployments", "List recent Worker deployments and their timestamps."),
            ("Fetch Sentry error rates", "Query performance data for the deploy window and the baseline window."),
            ("Detect performance regressions", "Compare error rates and p95 latency deterministically."),
            ("Post the deployment report", "Send a regression summary to the engineering Slack channel."),
        ],
    ),
    _seed(
        "feature-flag-rollout",
        "Feature Flag Rollout",
        "Developer Tools",
        ["feature-flags", "rollout", "launchdarkly", "github"],
        ["launchdarkly-feature-api", "github-rest-api", "slack-web-api"],
        ["github-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Progressively roll out a feature flag and report rollout state to Slack.",
        "Increase a LaunchDarkly rollout percentage in steps, verify the linked GitHub release and post rollout state to Slack.",
        [
            ("Read the current flag configuration", "Fetch the LaunchDarkly flag and its current rollout percentage."),
            ("Advance the rollout percentage", "Update the flag to the next rollout stage."),
            ("Verify the linked release", "Check the GitHub release tag matches the expected version."),
            ("Announce the rollout stage", "Post the flag key, percentage and release link to Slack."),
        ],
    ),
    _seed(
        "secrets-rotation-audit",
        "Secrets Rotation Audit",
        "Developer Tools",
        ["secrets", "security", "rotation", "doppler"],
        ["doppler-secrets-api", "github-rest-api", "slack-web-api"],
        ["docker-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Audit secret rotation age in Doppler and alert the security team.",
        "Read Doppler secret metadata, compute rotation age and compare it with the repository secret inventory in GitHub.",
        [
            ("Fetch Doppler secret metadata", "List secrets and their last-updated timestamps."),
            ("Read the GitHub secret inventory", "List repository secrets that must exist in production."),
            ("Compute rotation age and drift", "Flag secrets older than the policy and inventory mismatches."),
            ("Alert the security channel", "Post the audit findings to the security Slack channel."),
        ],
    ),
    _seed(
        "serverless-job-scheduler",
        "Serverless Job Scheduler",
        "Developer Tools",
        ["serverless", "scheduler", "lambda", "supabase"],
        ["aws-lambda-api", "supabase-database-api", "sentry-error-api"],
        ["aws-ec2-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Trigger scheduled Lambda jobs and track execution results in Supabase.",
        "Invoke a Lambda function for each due job, record the execution result in Supabase and report failures to Sentry.",
        [
            ("Read due jobs from Supabase", "Select jobs whose next_run_at is in the past."),
            ("Invoke the Lambda function", "Call the Lambda invoke endpoint with the job payload."),
            ("Record execution results", "Update the job row with status and next run time."),
            ("Report failures to Sentry", "Send an event for every failed invocation."),
        ],
    ),
    _seed(
        "api-health-monitoring",
        "API Health Monitoring",
        "Developer Tools",
        ["api", "health", "monitoring", "sentry"],
        ["sentry-performance-api", "posthog-analytics-api", "slack-web-api"],
        ["postman-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Monitor API health with Sentry transactions and PostHog usage and alert on anomalies.",
        "Compare Sentry transaction latency with PostHog request volume, detect unhealthy windows and post alerts to Slack.",
        [
            ("Fetch Sentry transaction latency", "Query p95 latency for the monitored API endpoints."),
            ("Fetch PostHog request volume", "Aggregate request events per endpoint per interval."),
            ("Detect unhealthy windows", "Flag endpoints that breach latency or error thresholds."),
            ("Send the health alert", "Post endpoint status and metrics to the on-call Slack channel."),
        ],
    ),
    _seed(
        "linear-roadmap-sync",
        "Linear Roadmap Sync",
        "Developer Tools",
        ["linear", "roadmap", "notion", "github"],
        ["linear-graphql-api", "notion-api", "github-rest-api"],
        ["jira-alternatives", "notion-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Sync Linear projects into a Notion roadmap page and link GitHub milestones.",
        "Query Linear projects with GraphQL, create or update Notion roadmap sections and attach the matching GitHub milestone.",
        [
            ("Query Linear projects", "Run the GraphQL query for active projects and their progress."),
            ("Match GitHub milestones", "Find milestones that belong to each project."),
            ("Update the Notion roadmap", "Create or update roadmap sections with progress and links."),
            ("Write the roadmap changelog", "Record changed project states in a deterministic changelog."),
        ],
    ),
    _seed(
        "release-notes-generator",
        "Release Notes Generator",
        "Developer Tools",
        ["release", "notes", "github", "ai"],
        ["github-rest-api", "openai-gpt-4-api", "resend-email-api"],
        ["github-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Generate release notes from merged pull requests and email the changelog.",
        "Collect merged pull requests since the last release, generate a readable changelog with OpenAI and email subscribers.",
        [
            ("Collect merged pull requests", "List merged PRs since the last release tag."),
            ("Generate the changelog", "Ask OpenAI for categorised, user-facing release notes."),
            ("Publish the GitHub release", "Create a release entry with the generated notes."),
            ("Email the changelog", "Send the release notes to the subscriber list via Resend."),
        ],
    ),

    # ----------------------------- Content & SEO (7) ----------------------- #
    _seed(
        "programmatic-seo-pipeline",
        "Programmatic SEO Pipeline",
        "Content & SEO",
        ["seo", "programmatic", "content", "algolia"],
        ["openai-gpt-4-api", "supabase-database-api", "algolia-search-api"],
        ["supabase-alternatives", "openai-alternatives"],
        "Advanced",
        "90–120 minutes",
        "Generate programmatic SEO landing pages from keyword clusters and index them for site search.",
        "Cluster keywords, generate page copy with OpenAI, store page records in Supabase and index the published pages in Algolia.",
        [
            ("Cluster the keyword inventory", "Group raw keywords into deterministic topic clusters."),
            ("Generate page copy with OpenAI", "Create title, meta description and body copy per cluster."),
            ("Store page records in Supabase", "Upsert slugs, titles and generated content."),
            ("Index published pages in Algolia", "Push searchable page records with keywords and URLs."),
        ],
    ),
    _seed(
        "ai-content-automation",
        "AI Content Automation",
        "Content & SEO",
        ["content", "ai", "notion", "email"],
        ["openai-gpt-4-api", "notion-api", "resend-email-api"],
        ["notion-alternatives", "openai-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Draft editorial content in Notion and notify reviewers by email.",
        "Read briefs from Notion, draft articles with OpenAI, create review pages and email the editorial team.",
        [
            ("Read briefs from Notion", "Query the briefs database for items waiting for a draft."),
            ("Draft the article with OpenAI", "Generate the article body and a suggested title."),
            ("Create the Notion review page", "Write the draft into the review database with status review."),
            ("Notify reviewers by email", "Send the review link to the editorial distribution list."),
        ],
    ),
    _seed(
        "seo-content-audit",
        "SEO Content Audit",
        "Content & SEO",
        ["seo", "audit", "content", "analytics"],
        ["algolia-search-api", "google-sheets-api", "openai-gpt-4-api"],
        ["google-analytics-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Audit indexed content for missing keywords and produce an SEO action list.",
        "Export indexed pages from Algolia, compare keywords with the target list in Google Sheets and generate recommendations.",
        [
            ("Export indexed pages from Algolia", "Page through records and extract titles, slugs and keywords."),
            ("Read target keywords from Google Sheets", "Load the keyword universe and priority tiers."),
            ("Score keyword coverage", "Detect missing and cannibalised keywords deterministically."),
            ("Generate SEO recommendations", "Ask OpenAI for prioritised, page-level actions."),
        ],
    ),
    _seed(
        "blog-cms-publishing",
        "Blog CMS Publishing",
        "Content & SEO",
        ["cms", "contentful", "blog", "publishing"],
        ["contentful-cms-api", "openai-gpt-4-api", "cloudflare-workers-api"],
        ["wordpress-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Draft, review and publish blog entries from Contentful and trigger an edge rebuild.",
        "Create Contentful draft entries with AI-generated copy, publish approved entries and trigger a Cloudflare Workers build hook.",
        [
            ("Create draft entries in Contentful", "Write AI-generated blog fields into the draft environment."),
            ("Validate editorial requirements", "Check mandatory fields, slug uniqueness and asset references."),
            ("Publish the approved entry", "Move the entry to published when it passes validation."),
            ("Trigger the edge rebuild", "Call the Cloudflare build hook after publishing."),
        ],
    ),
    _seed(
        "local-seo-landing-pages",
        "Local SEO Landing Pages",
        "Content & SEO",
        ["local-seo", "geodata", "landing-pages", "maps"],
        ["mapbox-maps-api", "google-sheets-api", "openai-gpt-4-api"],
        ["google-analytics-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Generate local landing pages from service areas and geocoded locations.",
        "Read service areas from Google Sheets, geocode them with Mapbox and generate local page copy with OpenAI.",
        [
            ("Read service areas from Google Sheets", "Load city names and target service keywords."),
            ("Geocode service areas with Mapbox", "Resolve coordinates and normalise place names."),
            ("Generate local page copy", "Create unique headings, intros and local highlights with OpenAI."),
            ("Write the landing page manifest", "Produce a deterministic page list with slugs and metadata."),
        ],
    ),
    _seed(
        "newsletter-automation",
        "Newsletter Automation",
        "Content & SEO",
        ["newsletter", "email", "content", "supabase"],
        ["supabase-database-api", "resend-email-api", "openai-gpt-4-api"],
        ["mailchimp-alternatives", "supabase-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Assemble and send a curated newsletter from Supabase content with AI summaries.",
        "Select approved newsletter items from Supabase, summarise them with OpenAI and send the issue through Resend.",
        [
            ("Select newsletter items from Supabase", "Query approved items for the current issue."),
            ("Summarise items with OpenAI", "Create short blurbs and a subject line."),
            ("Render the newsletter HTML", "Compose the issue from the ordered item list."),
            ("Send the issue with Resend", "Deliver the newsletter and record the broadcast id."),
        ],
    ),
    _seed(
        "content-localization-pipeline",
        "Content Localization Pipeline",
        "Content & SEO",
        ["localization", "translation", "contentful", "content"],
        ["ibm-watson-language-translator-api", "contentful-cms-api", "aws-s3-api"],
        ["wordpress-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Translate Contentful entries into target languages and archive translation assets.",
        "Read source entries from Contentful, translate them with IBM Watson Language Translator and archive the localized payloads on S3.",
        [
            ("Read source entries from Contentful", "Select entries marked ready for localization."),
            ("Translate with Watson Language Translator", "Call the translate endpoint for each target language."),
            ("Create localized Contentful entries", "Write translated fields into the target locale."),
            ("Archive translation assets on S3", "Store source and translated payloads for audit."),
        ],
    ),

    # ---------------------- Productivity & Collaboration (7) ---------------- #
    _seed(
        "meeting-notes-automation",
        "Meeting Notes Automation",
        "Productivity & Collaboration",
        ["meetings", "notes", "notion", "transcription"],
        ["openai-whisper-api", "notion-api", "slack-web-api"],
        ["notion-alternatives", "zoom-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Turn meeting recordings into Notion notes and share the summary in Slack.",
        "Transcribe recordings with Whisper, create structured Notion meeting notes and post the summary to the project channel.",
        [
            ("Transcribe the meeting recording", "Submit the recording to the Whisper transcriptions endpoint."),
            ("Extract decisions and owners", "Call OpenAI to parse action items with owners and due dates."),
            ("Create the Notion meeting page", "Write the notes into the meetings database."),
            ("Share the summary in Slack", "Post decisions and action items to the project channel."),
        ],
    ),
    _seed(
        "notion-task-sync",
        "Notion Task Sync",
        "Productivity & Collaboration",
        ["notion", "asana", "tasks", "sync"],
        ["notion-api", "asana-api", "slack-web-api"],
        ["notion-alternatives", "asana-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Sync Notion tasks into Asana and report overdue work to Slack.",
        "Read open tasks from Notion, create or update Asana tasks and post overdue tasks to Slack.",
        [
            ("Read open tasks from Notion", "Query the tasks database for items not marked done."),
            ("Create or update Asana tasks", "Match by external id and sync assignee and due date."),
            ("Detect overdue tasks", "Compare due dates with the current date."),
            ("Report overdue work in Slack", "Post overdue tasks grouped by owner."),
        ],
    ),
    _seed(
        "document-approval-workflow",
        "Document Approval Workflow",
        "Productivity & Collaboration",
        ["documents", "approval", "notion", "pdf"],
        ["notion-api", "pdf-co-api", "slack-web-api"],
        ["docusign-alternatives", "adobe-acrobat-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Render Notion documents as PDFs and route approval requests to Slack.",
        "Read document records from Notion, render PDFs with PDF.co and send approval requests with the PDF link to Slack.",
        [
            ("Read document records from Notion", "Select documents waiting for approval."),
            ("Render the PDF with PDF.co", "Call the HTML-to-PDF endpoint and store the result URL."),
            ("Send the approval request", "Post the document summary and PDF link to the approvers channel."),
            ("Update the document status", "Write the approval state back to Notion."),
        ],
    ),
    _seed(
        "form-submission-routing",
        "Form Submission Routing",
        "Productivity & Collaboration",
        ["forms", "routing", "notion", "email"],
        ["notion-forms-api", "resend-email-api", "airtable-api"],
        ["notion-alternatives", "airtable-alternatives"],
        "Intermediate",
        "45–60 minutes",
        "Route website form submissions to the right team and confirm receipt.",
        "Read form submissions, classify the request type, route it to Airtable and send a confirmation email.",
        [
            ("Read form submissions", "Fetch new submission entries and validate required fields."),
            ("Classify the request type", "Map submission fields to support, sales or billing deterministically."),
            ("Route the submission to Airtable", "Create a record in the matching team table."),
            ("Send the confirmation email", "Call the Resend emails endpoint with a tailored receipt."),
        ],
    ),
    _seed(
        "team-wiki-search",
        "Team Wiki Search",
        "Productivity & Collaboration",
        ["wiki", "search", "embeddings", "notion"],
        ["notion-api", "openai-embeddings-api", "pinecone-vector-api"],
        ["notion-wiki-alternatives", "notion-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Index the internal team wiki and provide embedding-based search over pages.",
        "Export wiki pages from Notion, create embeddings and index them in Pinecone for fast internal search.",
        [
            ("Export wiki pages from Notion", "Collect all pages under the wiki root and extract text."),
            ("Create embeddings for wiki pages", "Batch page text through the OpenAI embeddings endpoint."),
            ("Upsert wiki vectors into Pinecone", "Store vectors with page title and URL metadata."),
            ("Search the team wiki", "Embed a query and return the most relevant pages."),
        ],
    ),
    _seed(
        "design-feedback-collection",
        "Design Feedback Collection",
        "Productivity & Collaboration",
        ["design", "feedback", "airtable", "slack"],
        ["airtable-api", "slack-web-api", "notion-api"],
        ["figma-alternatives", "miro-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Collect design feedback in Airtable and summarise open feedback in Slack.",
        "Read design review records from Airtable, group feedback by asset and post a digest to the design Slack channel.",
        [
            ("Read design review records from Airtable", "Fetch feedback rows for active design assets."),
            ("Group feedback by asset and theme", "Cluster comments deterministically by asset and label."),
            ("Update the Notion review index", "Write asset status and feedback counts to Notion."),
            ("Post the feedback digest to Slack", "Summarise open feedback per asset in Slack."),
        ],
    ),
    _seed(
        "collaboration-presence-sync",
        "Collaboration Presence Sync",
        "Realtime & Collaboration",
        ["realtime", "presence", "liveblocks", "ably"],
        ["liveblocks-collaboration-api", "ably-realtime-api", "supabase-database-api"],
        ["miro-alternatives", "canva-whiteboard-alternatives"],
        "Advanced",
        "90–120 minutes",
        "Synchronise room presence between Liveblocks and Ably and persist session metrics.",
        "Read Liveblocks room presence, publish presence updates through Ably and store session metrics in Supabase.",
        [
            ("Read Liveblocks room presence", "Fetch active users for the configured rooms."),
            ("Publish presence events through Ably", "Send presence updates to the collaboration channel."),
            ("Persist session metrics in Supabase", "Upsert room, user count and timestamp rows."),
            ("Detect stale presence sessions", "Flag sessions without updates beyond the timeout."),
        ],
    ),

    # -------------------------- Analytics & Monitoring (4) ----------------- #
    _seed(
        "product-analytics-dashboard",
        "Product Analytics Dashboard",
        "Analytics & Monitoring",
        ["analytics", "product", "posthog", "reporting"],
        ["posthog-analytics-api", "google-sheets-api", "slack-web-api"],
        ["google-analytics-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Build a weekly product analytics report from PostHog and deliver it to stakeholders.",
        "Query PostHog product metrics, write the weekly cohort table to Google Sheets and post a summary to Slack.",
        [
            ("Query PostHog product metrics", "Fetch weekly active users and conversion events."),
            ("Write the cohort table to Google Sheets", "Append weekly rows with metric values."),
            ("Compute week-over-week changes", "Calculate deltas and flag significant movements."),
            ("Post the analytics summary", "Send the weekly summary to the product Slack channel."),
        ],
    ),
    _seed(
        "error-tracking-alerts",
        "Error Tracking Alerts",
        "Analytics & Monitoring",
        ["errors", "monitoring", "sentry", "alerts"],
        ["sentry-error-api", "slack-web-api", "linear-graphql-api"],
        ["jira-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Turn recurring Sentry errors into Linear issues and Slack alerts.",
        "Group new Sentry errors, create or update Linear issues for regressions and alert the engineering channel.",
        [
            ("Group new Sentry errors", "Fetch unresolved issues and group them by fingerprint."),
            ("Create or update Linear issues", "Match by external id and set priority from event volume."),
            ("Alert the engineering channel", "Post new and escalated errors to Slack."),
            ("Write the error digest", "Summarise counts and owners in a deterministic JSON file."),
        ],
    ),
    _seed(
        "website-performance-reporting",
        "Website Performance Reporting",
        "Analytics & Monitoring",
        ["performance", "monitoring", "cloudflare", "email"],
        ["posthog-analytics-api", "cloudflare-workers-api", "resend-email-api"],
        ["google-analytics-alternatives", "netlify-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Measure website performance and traffic and email a weekly performance report.",
        "Combine Cloudflare Worker analytics with PostHog traffic, generate a performance report and email it to stakeholders.",
        [
            ("Fetch Cloudflare Worker analytics", "Read request counts and latency for the reporting window."),
            ("Fetch PostHog traffic metrics", "Aggregate sessions and top landing pages."),
            ("Generate the performance report", "Compute Core Web Vitals proxies and traffic deltas."),
            ("Email the weekly report", "Send the HTML report to the stakeholder list via Resend."),
        ],
    ),
    _seed(
        "social-media-analytics",
        "Social Media Analytics",
        "Analytics & Monitoring",
        ["social", "analytics", "twitch", "reporting"],
        ["twitch-analytics-api", "twitch-api", "google-sheets-api"],
        ["tiktok-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Collect Twitch channel analytics and append weekly performance rows to Google Sheets.",
        "Fetch Twitch analytics and channel metadata, compute engagement metrics and append weekly rows to Google Sheets.",
        [
            ("Fetch Twitch analytics", "Query stream and viewer metrics for the reporting period."),
            ("Fetch channel metadata", "Read follower counts and stream schedules."),
            ("Compute engagement metrics", "Derive average viewers and retention proxies."),
            ("Append rows to Google Sheets", "Write one row per channel and week."),
        ],
    ),

    # ------------------------------ E-commerce (3) ------------------------- #
    _seed(
        "shopify-order-automation",
        "Shopify Order Automation",
        "E-commerce",
        ["shopify", "orders", "automation", "email"],
        ["shopify-admin-api", "resend-email-api", "supabase-database-api"],
        ["shopify-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Process new Shopify orders, send confirmations and store order analytics.",
        "Fetch new Shopify orders, send branded confirmations with Resend and store order analytics in Supabase.",
        [
            ("Fetch new Shopify orders", "Query paid orders since the last checkpoint."),
            ("Send the order confirmation", "Call the Resend emails endpoint with order details."),
            ("Store order analytics in Supabase", "Upsert order value, items and customer segment."),
            ("Detect unusual order patterns", "Flag high-value or repeated-risk orders deterministically."),
        ],
    ),
    _seed(
        "inventory-sync-automation",
        "Inventory Sync Automation",
        "E-commerce",
        ["inventory", "shopify", "airtable", "sync"],
        ["shopify-admin-api", "airtable-api", "slack-web-api"],
        ["shopify-alternatives", "airtable-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Sync Shopify inventory levels into Airtable and alert on low stock.",
        "Read Shopify inventory levels, mirror them in Airtable and alert the operations channel about low-stock variants.",
        [
            ("Read Shopify inventory levels", "Fetch variants and their available quantities."),
            ("Mirror levels in Airtable", "Match by SKU and update quantity fields."),
            ("Detect low-stock variants", "Compare quantities with the configured reorder point."),
            ("Alert the operations channel", "Post low-stock variants to Slack with SKU and quantity."),
        ],
    ),

    # ---------------------------- Geodata & Weather (2) ------------------- #
    _seed(
        "weather-driven-ops-alerts",
        "Weather-Driven Ops Alerts",
        "Geodata & Weather",
        ["weather", "ops", "alerts", "monitoring"],
        ["openweather-weather-api", "weatherapi", "slack-web-api"],
        ["microsoft-azure-alternatives"],
        "Intermediate",
        "45–60 minutes",
        "Trigger operations alerts from severe weather forecasts for field teams.",
        "Check OpenWeather and WeatherAPI forecasts for operating regions and alert the operations channel about severe conditions.",
        [
            ("Fetch forecasts for operating regions", "Query both weather APIs for the configured locations."),
            ("Normalise weather conditions", "Map provider-specific condition codes to a shared severity scale."),
            ("Evaluate alert thresholds", "Flag locations with severe wind, rain or temperature conditions."),
            ("Post operations weather alerts", "Send the affected locations and conditions to Slack."),
        ],
    ),
    _seed(
        "store-locator-geocoding",
        "Store Locator Geocoding",
        "Geodata & Weather",
        ["geocoding", "store-locator", "maps", "ecommerce"],
        ["mapbox-maps-api", "google-maps-api", "airtable-api"],
        ["shopify-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Geocode store addresses and maintain a store locator dataset in Airtable.",
        "Geocode store addresses with Mapbox, verify them with Google Maps and publish the canonical store records to Airtable.",
        [
            ("Read store addresses from Airtable", "Load stores that are missing coordinates."),
            ("Geocode addresses with Mapbox", "Resolve coordinates and normalise formatted addresses."),
            ("Verify coordinates with Google Maps", "Cross-check the geocode result and detect mismatches."),
            ("Publish canonical store records", "Write coordinates and verification status back to Airtable."),
        ],
    ),

    # ------------------------- Storage & Infrastructure (2) --------------- #
    _seed(
        "asset-backup-automation",
        "Asset Backup Automation",
        "Storage & Infrastructure",
        ["backup", "storage", "s3", "assets"],
        ["aws-s3-api", "vercel-blob-api", "ibm-cloud-object-storage-api"],
        ["dropbox-alternatives", "google-drive-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Back up Vercel Blob assets to S3 and mirror critical files to IBM Cloud Object Storage.",
        "List Vercel Blob assets, copy them to an S3 backup prefix and mirror critical files to IBM Cloud Object Storage.",
        [
            ("List assets from Vercel Blob", "Collect asset URLs, sizes and checksums."),
            ("Copy assets to S3", "Write each asset to the backup prefix and verify the checksum."),
            ("Mirror critical assets to IBM COS", "Copy the flagged subset to the secondary storage bucket."),
            ("Write the backup manifest", "Produce a deterministic manifest with verification status."),
        ],
    ),

    _seed(
        "s3-static-site-publishing",
        "S3 Static Site Publishing",
        "Storage & Infrastructure",
        ["s3", "static-site", "cloudflare", "deployment"],
        ["aws-s3-api", "cloudflare-workers-api", "sentry-error-api"],
        ["netlify-alternatives", "vercel-alternatives"],
        "Advanced",
        "75–90 minutes",
        "Publish a static build to S3, purge the edge cache and verify the deployment health.",
        "Upload build artifacts to an S3 bucket, trigger a Cloudflare cache purge and report deployment health to Sentry.",
        [
            ("Upload build artifacts to S3", "Sync the build directory and set content types and cache headers."),
            ("Purge the Cloudflare cache", "Call the Workers cache purge for the changed asset paths."),
            ("Verify deployment health", "Fetch the published entry point and check the expected checksum."),
            ("Report deployment health", "Send a deployment event and alert on failed verification."),
        ],
    ),

    # ---------------------------- Auth & Identity (2) --------------------- #
    _seed(
        "auth0-sso-provisioning",
        "Auth0 SSO Provisioning",
        "Auth & Identity",
        ["auth0", "sso", "provisioning", "identity"],
        ["auth0-authentication-api", "microsoft-graph-api", "slack-web-api"],
        ["auth0-alternatives"],
        "Advanced",
        "90–120 minutes",
        "Provision Auth0 users from Microsoft 365 groups and report provisioning results.",
        "Read Microsoft Graph group members, create or update Auth0 users and post provisioning results to Slack.",
        [
            ("Read members from Microsoft Graph", "Fetch members of the onboarding security group."),
            ("Create or update Auth0 users", "Match by email and sync profile fields."),
            ("Assign roles and groups", "Apply the configured Auth0 roles for new users."),
            ("Report provisioning results", "Post created, updated and failed users to Slack."),
        ],
    ),
    _seed(
        "clerk-user-onboarding",
        "Clerk User Onboarding",
        "Auth & Identity",
        ["clerk", "onboarding", "users", "identity"],
        ["clerk-authentication-api", "resend-email-api", "supabase-database-api"],
        ["auth0-alternatives"],
        "Intermediate",
        "60–75 minutes",
        "Onboard new Clerk users with welcome emails and profile records.",
        "Read new Clerk users, create profile records in Supabase and send a welcome email through Resend.",
        [
            ("Read new Clerk users", "List users created since the last onboarding checkpoint."),
            ("Create profile records in Supabase", "Upsert user id, email and onboarding status."),
            ("Send the welcome email", "Call the Resend emails endpoint with onboarding steps."),
            ("Update the onboarding checkpoint", "Persist the latest processed timestamp."),
        ],
    ),
]


def validate_seed_catalog(
    apis: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
) -> list[str]:
    """Return a list of problems in the curated seed catalogue.

    The catalogue is the contract between data files and generated workflows:
    every referenced API and alternative slug must exist, slugs must be unique
    and every seed must state at least one API and one alternative.
    """
    api_slugs = {str(item.get("slug")) for item in apis}
    alt_slugs = {str(item.get("slug")) for item in alternatives}
    errors: list[str] = []
    seen: set[str] = set()
    for seed in SEEDS:
        slug = str(seed.get("slug") or "")
        if not slug:
            errors.append("Seed without a slug")
            continue
        if slug in seen:
            errors.append(f"Duplicate seed slug: {slug}")
        seen.add(slug)
        for api_slug in seed.get("api_slugs") or []:
            if api_slug not in api_slugs:
                errors.append(f"{slug}: unknown API slug '{api_slug}'")
        for alt_slug in seed.get("alternative_slugs") or []:
            if alt_slug not in alt_slugs:
                errors.append(f"{slug}: unknown alternative slug '{alt_slug}'")
        if not (seed.get("api_slugs") or []):
            errors.append(f"{slug}: no API slugs")
        if not (seed.get("alternative_slugs") or []):
            errors.append(f"{slug}: no alternative slugs")
        if not (3 <= len(seed.get("steps") or []) <= 8):
            errors.append(f"{slug}: steps must be between 3 and 8")
    return errors


def _api_titles(
    api_slugs: list[str], api_index: dict[str, dict[str, Any]]
) -> list[str]:
    return [
        str(api_index[slug].get("title"))
        for slug in api_slugs
        if slug in api_index
    ]


def build_workflow_from_seed(
    seed: dict[str, Any],
    api_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a complete workflow skeleton from a curated seed."""
    api_slugs = list(seed.get("api_slugs") or [])
    return {
        "slug": seed["slug"],
        "title": seed["title"],
        "description": seed["description"],
        "category": seed["category"],
        "tags": list(seed.get("tags") or []),
        "details": {
            "difficulty": seed.get("difficulty") or "Intermediate",
            "duration": seed.get("duration") or "45–60 minutes",
            "tools": _api_titles(api_slugs, api_index),
            "api_slugs": api_slugs,
            "alternative_slugs": list(seed.get("alternative_slugs") or []),
            "useCase": seed.get("use_case") or "",
            "steps": [
                {"title": step["title"], "description": step["description"]}
                for step in seed.get("steps") or []
            ],
            "prerequisites": [],
            "glossary": [],
            "troubleshooting": [],
            "resources": [],
        },
    }


def _is_complete(workflow: dict[str, Any]) -> bool:
    details = workflow.get("details") or {}
    steps = details.get("steps") or []
    prerequisites = details.get("prerequisites") or []
    return bool(
        3 <= len(steps) <= 8
        and len(prerequisites) >= 4
        and len(details.get("glossary") or []) >= 4
        and len(details.get("troubleshooting") or []) >= 3
        and details.get("resources")
        and str(workflow.get("created_and_verified_at") or "").strip()
    )


def sync_workflows(
    existing: list[dict[str, Any]],
    apis: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rebuild ``workflows.json`` from the curated seed catalogue.

    Existing complete records are preserved only when their tool list exactly
    matches the curated API titles. Everything else becomes a fresh skeleton so
    the pipeline regenerates it against the curated grounding.
    """
    problems = validate_seed_catalog(apis, alternatives)
    if problems:
        raise ValueError("; ".join(problems))

    api_index = {str(item.get("slug")): item for item in apis}
    existing_by_slug = {str(item.get("slug")): item for item in existing}
    result: list[dict[str, Any]] = []
    report = {"created": [], "kept": [], "replaced": [], "removed": []}
    seed_slugs = {str(seed["slug"]) for seed in SEEDS}

    for seed in SEEDS:
        slug = str(seed["slug"])
        current = existing_by_slug.get(slug)
        expected_titles = _api_titles(seed.get("api_slugs") or [], api_index)
        if (
            current is not None
            and _is_complete(current)
            and set(
                str(tool) for tool in (current.get("details") or {}).get("tools") or []
            )
            == set(expected_titles)
        ):
            details = current.setdefault("details", {})
            details["api_slugs"] = list(seed.get("api_slugs") or [])
            details["alternative_slugs"] = list(seed.get("alternative_slugs") or [])
            current["category"] = seed["category"]
            current["tags"] = list(seed.get("tags") or [])
            result.append(current)
            report["kept"].append(slug)
        else:
            result.append(build_workflow_from_seed(seed, api_index))
            report["replaced" if current is not None else "created"].append(slug)

    report["removed"] = sorted(
        str(item.get("slug"))
        for item in existing
        if str(item.get("slug")) not in seed_slugs
    )
    return result, report


def build_dynamic_seed(
    topic: dict[str, Any],
    api_slugs: list[str],
    alternative_slugs: list[str],
) -> dict[str, Any]:
    """Combine an LLM topic proposal with the curated batch API/alternative slugs.

    The topic may choose a title and step outline, but the grounding is owned by
    the pipeline: only the slugs passed in here are allowed in the workflow.
    """
    steps = [
        {
            "title": str(step.get("title") or "").strip(),
            "description": str(step.get("description") or "").strip(),
        }
        for step in topic.get("steps") or []
        if isinstance(step, dict) and str(step.get("title") or "").strip()
    ]
    return _seed(
        slug=str(topic.get("slug") or "").strip(),
        title=str(topic.get("title") or "").strip(),
        category=str(topic.get("category") or "").strip() or "Data & Automation",
        tags=[str(tag).strip() for tag in topic.get("tags") or [] if str(tag).strip()],
        api_slugs=list(api_slugs),
        alternative_slugs=list(alternative_slugs),
        difficulty=str(topic.get("difficulty") or "Intermediate").strip(),
        duration=str(topic.get("duration") or "45–60 minutes").strip(),
        use_case=str(topic.get("use_case") or topic.get("useCase") or "").strip(),
        description=str(topic.get("description") or "").strip(),
        steps=[(step["title"], step["description"]) for step in steps],
    )
