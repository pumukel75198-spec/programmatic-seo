import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const dataDir = path.resolve(process.cwd(), "src/data");

const newApis = [
  {
    slug: "mistral-ai-api",
    title: "Mistral AI API",
    description:
      "The Mistral AI API offers fast, efficient open-weight language models for chat, coding and retrieval tasks at competitive prices.",
    category: "AI & LLM",
    tags: ["llm", "open-weight", "chat", "efficiency"],
    details: {
      provider: "Mistral AI",
      pricing: "Pay-as-you-go per token",
      features: ["Open-weight models", "Fast inference", "Function calling", "Multilingual support"],
      useCase: "Cost-efficient chat, coding and RAG applications",
      website: "https://mistral.ai",
    },
  },
  {
    slug: "groq-inference-api",
    title: "Groq Inference API",
    description:
      "The Groq API delivers extremely fast LLM inference on custom hardware, ideal for real-time chat and voice applications.",
    category: "AI & Inference",
    tags: ["llm", "inference", "speed", "realtime"],
    details: {
      provider: "Groq",
      pricing: "Pay-as-you-go per token",
      features: ["Ultra-low latency inference", "Open-model support", "Streaming responses", "OpenAI-compatible API"],
      useCase: "Real-time chat, voice agents and latency-critical apps",
      website: "https://groq.com",
    },
  },
  {
    slug: "together-ai-api",
    title: "Together AI API",
    description:
      "The Together AI API provides access to a wide range of open-source models with fine-tuning, embeddings and serverless inference.",
    category: "AI & LLM",
    tags: ["llm", "open-source", "fine-tuning", "inference"],
    details: {
      provider: "Together AI",
      pricing: "Pay-as-you-go per token",
      features: ["Many open-source models", "Fine-tuning support", "Embeddings and image models", "Serverless inference"],
      useCase: "Custom models, fine-tuning and multi-model applications",
      website: "https://www.together.ai",
    },
  },
  {
    slug: "replicate-model-api",
    title: "Replicate Model API",
    description:
      "Replicate lets you run thousands of open-source models via a simple API, from image generation to speech and language tasks.",
    category: "AI & ML",
    tags: ["models", "image-generation", "api", "open-source"],
    details: {
      provider: "Replicate",
      pricing: "Pay-per-second of compute",
      features: ["Thousands of community models", "Image, audio and text tasks", "Custom model deployment", "Simple REST API"],
      useCase: "Prototyping and running open-source models without infrastructure",
      website: "https://replicate.com",
    },
  },
  {
    slug: "elevenlabs-voice-api",
    title: "ElevenLabs Voice API",
    description:
      "The ElevenLabs API generates natural, expressive speech and clones voices for apps, audiobooks and voice agents.",
    category: "AI & Voice",
    tags: ["text-to-speech", "voice-cloning", "audio", "ai"],
    details: {
      provider: "ElevenLabs",
      pricing: "Free tier, then per character",
      features: ["Natural text-to-speech", "Voice cloning", "Multilingual voices", "Low-latency streaming"],
      useCase: "Voiceovers, audiobooks and conversational voice agents",
      website: "https://elevenlabs.io",
    },
  },
  {
    slug: "deepgram-speech-api",
    title: "Deepgram Speech API",
    description:
      "Deepgram offers fast, accurate speech-to-text and text-to-speech APIs for real-time transcription and voice interfaces.",
    category: "AI & Speech",
    tags: ["speech-to-text", "transcription", "realtime", "audio"],
    details: {
      provider: "Deepgram",
      pricing: "Pay-as-you-go per minute",
      features: ["Real-time transcription", "Speaker diarization", "Multilingual support", "Text-to-speech"],
      useCase: "Meeting transcription, call analytics and voice interfaces",
      website: "https://deepgram.com",
    },
  },
  {
    slug: "stability-ai-image-api",
    title: "Stability AI Image API",
    description:
      "The Stability AI API generates and edits images with Stable Diffusion models, including upscaling and inpainting.",
    category: "AI & Image",
    tags: ["image-generation", "stable-diffusion", "inpainting", "ai"],
    details: {
      provider: "Stability AI",
      pricing: "Pay-as-you-go per image",
      features: ["Text-to-image generation", "Inpainting and upscaling", "Multiple model versions", "REST API access"],
      useCase: "Marketing visuals, concept art and image editing",
      website: "https://stability.ai",
    },
  },
  {
    slug: "weaviate-vector-api",
    title: "Weaviate Vector API",
    description:
      "Weaviate is an open-source vector database with a GraphQL API for semantic search, hybrid search and RAG at scale.",
    category: "Vector Database",
    tags: ["vector-database", "semantic-search", "rag", "open-source"],
    details: {
      provider: "Weaviate",
      pricing: "Open-source, cloud usage-based",
      features: ["Open-source and managed cloud", "Hybrid search", "GraphQL API", "Built-in vectorizers"],
      useCase: "Semantic search, RAG and recommendation systems",
      website: "https://weaviate.io",
    },
  },
  {
    slug: "qdrant-vector-api",
    title: "Qdrant Vector API",
    description:
      "Qdrant is a high-performance vector database with REST and gRPC APIs for similarity search and RAG workloads.",
    category: "Vector Database",
    tags: ["vector-database", "similarity-search", "rag", "rust"],
    details: {
      provider: "Qdrant",
      pricing: "Open-source, cloud usage-based",
      features: ["REST and gRPC APIs", "Payload filtering", "Hybrid search", "Self-hosting option"],
      useCase: "Similarity search, RAG and large-scale recommendations",
      website: "https://qdrant.tech",
    },
  },
  {
    slug: "mongodb-atlas-api",
    title: "MongoDB Atlas API",
    description:
      "MongoDB Atlas provides a managed document database with a flexible Data API for serverless and app-driven workloads.",
    category: "Databases",
    tags: ["database", "document-db", "serverless", "api"],
    details: {
      provider: "MongoDB",
      pricing: "Free tier, then usage-based",
      features: ["Managed MongoDB clusters", "Data API for HTTPS access", "Full-text and vector search", "Global distribution"],
      useCase: "Flexible document storage for modern applications",
      website: "https://www.mongodb.com/atlas",
    },
  },
  {
    slug: "neon-postgres-api",
    title: "Neon Postgres API",
    description:
      "Neon is a serverless Postgres platform with branching, autoscaling and a simple API for modern application backends.",
    category: "Databases",
    tags: ["postgresql", "serverless", "database", "branching"],
    details: {
      provider: "Neon",
      pricing: "Free tier, then usage-based",
      features: ["Serverless Postgres", "Database branching", "Autoscaling", "REST and SQL access"],
      useCase: "Serverless apps, preview environments and modern backends",
      website: "https://neon.tech",
    },
  },
  {
    slug: "planetscale-database-api",
    title: "PlanetScale Database API",
    description:
      "PlanetScale offers a MySQL-compatible serverless database with branching, safe schema changes and a developer-friendly API.",
    category: "Databases",
    tags: ["mysql", "serverless", "database", "branching"],
    details: {
      provider: "PlanetScale",
      pricing: "Free tier, then usage-based",
      features: ["MySQL-compatible serverless DB", "Database branching", "Non-blocking schema changes", "Connection management"],
      useCase: "Scalable SaaS backends and safe schema migrations",
      website: "https://planetscale.com",
    },
  },
  {
    slug: "upstash-redis-api",
    title: "Upstash Redis API",
    description:
      "Upstash provides serverless Redis and Kafka with REST APIs and pay-per-request pricing for edge and serverless apps.",
    category: "Databases",
    tags: ["redis", "serverless", "caching", "rest"],
    details: {
      provider: "Upstash",
      pricing: "Pay-per-request, free tier",
      features: ["Serverless Redis", "REST API", "Global replication", "Kafka and QStash"],
      useCase: "Caching, rate limiting and queues in serverless apps",
      website: "https://upstash.com",
    },
  },
  {
    slug: "vercel-blob-api",
    title: "Vercel Blob API",
    description:
      "Vercel Blob offers simple, scalable object storage with a TypeScript-friendly API for uploads, downloads and public assets.",
    category: "Storage",
    tags: ["storage", "files", "serverless", "cdn"],
    details: {
      provider: "Vercel",
      pricing: "Usage-based",
      features: ["Object storage for files", "Simple upload API", "CDN delivery", "Integration with Next.js"],
      useCase: "User uploads, images and static assets in serverless apps",
      website: "https://vercel.com/docs/storage/vercel-blob",
    },
  },
  {
    slug: "liveblocks-collaboration-api",
    title: "Liveblocks Collaboration API",
    description:
      "Liveblocks adds real-time multiplayer collaboration to apps with presence, comments, notifications and conflict-free storage.",
    category: "Realtime",
    tags: ["realtime", "collaboration", "presence", "multiplayer"],
    details: {
      provider: "Liveblocks",
      pricing: "Free tier, then usage-based",
      features: ["Presence and cursors", "Collaborative storage", "Comments and threads", "Webhooks and notifications"],
      useCase: "Collaborative editors, whiteboards and design tools",
      website: "https://liveblocks.io",
    },
  },
  {
    slug: "ably-realtime-api",
    title: "Ably Realtime API",
    description:
      "Ably provides globally distributed realtime messaging with pub/sub channels, presence and reliable delivery at scale.",
    category: "Realtime",
    tags: ["realtime", "pubsub", "websockets", "messaging"],
    details: {
      provider: "Ably",
      pricing: "Free tier, then usage-based",
      features: ["Pub/sub channels", "Presence and history", "WebSocket and SSE", "Global edge network"],
      useCase: "Chat, live dashboards and collaborative apps",
      website: "https://ably.com",
    },
  },
  {
    slug: "posthog-analytics-api",
    title: "PostHog Analytics API",
    description:
      "PostHog combines product analytics, session replay, feature flags and experiments in one privacy-friendly platform.",
    category: "Analytics",
    tags: ["analytics", "product", "feature-flags", "session-replay"],
    details: {
      provider: "PostHog",
      pricing: "Free tier, then usage-based",
      features: ["Product analytics", "Session replay", "Feature flags", "A/B experiments"],
      useCase: "Product teams measuring activation, retention and experiments",
      website: "https://posthog.com",
    },
  },
  {
    slug: "sentry-error-api",
    title: "Sentry Error API",
    description:
      "Sentry captures errors, traces and performance data across your stack so teams can find and fix issues faster.",
    category: "Observability",
    tags: ["monitoring", "errors", "tracing", "performance"],
    details: {
      provider: "Sentry",
      pricing: "Free tier, then usage-based",
      features: ["Error tracking", "Distributed tracing", "Release health", "SDKs for every stack"],
      useCase: "Debugging production errors and monitoring performance",
      website: "https://sentry.io",
    },
  },
  {
    slug: "launchdarkly-feature-api",
    title: "LaunchDarkly Feature API",
    description:
      "LaunchDarkly lets teams ship features safely with feature flags, targeting rules, experiments and gradual rollouts.",
    category: "DevOps",
    tags: ["feature-flags", "devops", "experimentation", "rollouts"],
    details: {
      provider: "LaunchDarkly",
      pricing: "Free tier, then usage-based",
      features: ["Feature flags", "Targeting and segments", "Gradual rollouts", "Experimentation"],
      useCase: "Safe releases, A/B tests and kill switches",
      website: "https://launchdarkly.com",
    },
  },
  {
    slug: "doppler-secrets-api",
    title: "Doppler Secrets API",
    description:
      "Doppler centralizes secrets and environment configuration with a secure API and integrations for every major cloud.",
    category: "Security",
    tags: ["secrets", "security", "devops", "configuration"],
    details: {
      provider: "Doppler",
      pricing: "Free tier, then per user",
      features: ["Centralized secrets", "Environment configs", "Access controls and audit logs", "CI/CD integrations"],
      useCase: "Managing secrets and config across environments",
      website: "https://www.doppler.com",
    },
  },
];

const newAlternatives = [
  {
    slug: "monday-alternatives",
    title: "Monday.com Alternatives",
    description:
      "Monday.com alternatives for work management – simpler, cheaper or open-source options for teams that need flexible boards.",
    category: "Project Management",
    tags: ["work-management", "boards", "project-management", "collaboration"],
    details: {
      original: "Monday.com",
      alternatives: ["ClickUp", "Plane", "Vikunja"],
      bestFor: "Teams that want flexible boards without high per-seat pricing",
      pricing: "Free to about $12/user/month",
      features: ["Boards and timelines", "Automations and integrations", "Open-source options"],
    },
  },
  {
    slug: "clickup-alternatives",
    title: "ClickUp Alternatives",
    description:
      "ClickUp alternatives for all-in-one productivity – focused, faster and easier to adopt for small and mid-sized teams.",
    category: "Productivity",
    tags: ["productivity", "tasks", "project-management", "collaboration"],
    details: {
      original: "ClickUp",
      alternatives: ["Asana", "Linear", "Plane"],
      bestFor: "Teams that find ClickUp too complex or overwhelming",
      pricing: "Free to about $10/user/month",
      features: ["Task and project views", "Docs and goals", "Developer-friendly alternatives"],
    },
  },
  {
    slug: "miro-alternatives",
    title: "Miro Alternatives",
    description:
      "Miro alternatives for visual collaboration and whiteboarding – open-source, self-hosted or simpler tools for workshops.",
    category: "Collaboration",
    tags: ["whiteboard", "collaboration", "workshops", "visual"],
    details: {
      original: "Miro",
      alternatives: ["Excalidraw", "tldraw", "Penpot"],
      bestFor: "Teams that need whiteboarding with privacy or self-hosting",
      pricing: "Free to about $10/user/month",
      features: ["Infinite canvas", "Real-time collaboration", "Open-source options"],
    },
  },
  {
    slug: "loom-alternatives",
    title: "Loom Alternatives",
    description:
      "Loom alternatives for screen recording and async video – privacy-friendly, open-source or lower-cost options for teams.",
    category: "Communication",
    tags: ["screen-recording", "video", "async", "communication"],
    details: {
      original: "Loom",
      alternatives: ["Cap", "OBS Studio", "Screen Studio"],
      bestFor: "Teams that want async video without per-seat subscription costs",
      pricing: "Free to about $15/user/month",
      features: ["Screen and camera recording", "Sharing and comments", "Open-source recording with OBS"],
    },
  },
  {
    slug: "intercom-alternatives",
    title: "Intercom Alternatives",
    description:
      "Intercom alternatives for customer messaging and support – AI-ready, affordable and privacy-friendly helpdesk options.",
    category: "Support",
    tags: ["support", "chat", "helpdesk", "customer-messaging"],
    details: {
      original: "Intercom",
      alternatives: ["Crisp", "Chatwoot", "Freshdesk"],
      bestFor: "Support teams that need chat and helpdesk without enterprise pricing",
      pricing: "Free to about $20/agent/month",
      features: ["Live chat and inbox", "Knowledge base and bots", "Open-source helpdesk"],
    },
  },
  {
    slug: "zendesk-alternatives",
    title: "Zendesk Alternatives",
    description:
      "Zendesk alternatives for customer support – open-source, AI-assisted and lower-cost helpdesk platforms for growing teams.",
    category: "Support",
    tags: ["helpdesk", "support", "ticketing", "customer-service"],
    details: {
      original: "Zendesk",
      alternatives: ["Zammad", "Chatwoot", "Freshdesk"],
      bestFor: "Support teams that want ticketing with self-hosting or lower costs",
      pricing: "Free to about $25/agent/month",
      features: ["Ticketing and SLAs", "Knowledge base", "Open-source and self-hosting options"],
    },
  },
  {
    slug: "jira-alternatives",
    title: "Jira Alternatives",
    description:
      "Jira alternatives for issue tracking and agile planning – faster, simpler and developer-friendly tools for software teams.",
    category: "DevOps",
    tags: ["issue-tracking", "agile", "project-management", "developers"],
    details: {
      original: "Jira",
      alternatives: ["Linear", "Plane", "YouTrack"],
      bestFor: "Engineering teams that want fast, focused issue tracking",
      pricing: "Free to about $10/user/month",
      features: ["Issue tracking and backlogs", "Sprints and roadmaps", "Git integrations"],
    },
  },
  {
    slug: "github-alternatives",
    title: "GitHub Alternatives",
    description:
      "GitHub alternatives for source code hosting and collaboration – self-hosted, privacy-focused or open-source platforms.",
    category: "DevOps",
    tags: ["git", "code-hosting", "devops", "open-source"],
    details: {
      original: "GitHub",
      alternatives: ["GitLab", "Gitea", "Bitbucket"],
      bestFor: "Teams that need self-hosting, CI/CD or more control over their code",
      pricing: "Free to about $10/user/month, self-hosting optional",
      features: ["Git repositories", "Pull requests and reviews", "CI/CD and self-hosting"],
    },
  },
  {
    slug: "gitlab-alternatives",
    title: "GitLab Alternatives",
    description:
      "GitLab alternatives for DevOps and code hosting – lighter, self-hosted or open-source platforms with strong CI/CD.",
    category: "DevOps",
    tags: ["git", "devops", "ci-cd", "code-hosting"],
    details: {
      original: "GitLab",
      alternatives: ["GitHub", "Gitea", "Forgejo"],
      bestFor: "Teams that want lighter self-hosted DevOps platforms",
      pricing: "Free to about $10/user/month, self-hosting optional",
      features: ["Git hosting and merge requests", "CI/CD pipelines", "Lightweight self-hosting"],
    },
  },
  {
    slug: "bitbucket-alternatives",
    title: "Bitbucket Alternatives",
    description:
      "Bitbucket alternatives for Git hosting and CI – open-source, self-hosted or tightly integrated developer platforms.",
    category: "DevOps",
    tags: ["git", "code-hosting", "ci-cd", "devops"],
    details: {
      original: "Bitbucket",
      alternatives: ["GitLab", "Gitea", "GitHub"],
      bestFor: "Teams looking for more CI/CD flexibility or self-hosting",
      pricing: "Free to about $8/user/month, self-hosting optional",
      features: ["Git repositories", "Pipelines and integrations", "Self-hosting options"],
    },
  },
  {
    slug: "netlify-alternatives",
    title: "Netlify Alternatives",
    description:
      "Netlify alternatives for static hosting and serverless deploys – with more control, self-hosting or generous free tiers.",
    category: "Hosting",
    tags: ["hosting", "static-site", "serverless", "deployment"],
    details: {
      original: "Netlify",
      alternatives: ["Vercel", "Cloudflare Pages", "Render"],
      bestFor: "Teams that need static hosting with edge functions or self-hosting",
      pricing: "Free to about $20/month",
      features: ["Static and serverless hosting", "Preview deployments", "Edge functions and CDN"],
    },
  },
  {
    slug: "vercel-alternatives",
    title: "Vercel Alternatives",
    description:
      "Vercel alternatives for frontend hosting and serverless – open, self-hosted or more predictable pricing for growing projects.",
    category: "Hosting",
    tags: ["hosting", "frontend", "serverless", "deployment"],
    details: {
      original: "Vercel",
      alternatives: ["Netlify", "Cloudflare Pages", "Coolify"],
      bestFor: "Teams that want predictable pricing or self-hosted deployments",
      pricing: "Free to about $20/month, self-hosting optional",
      features: ["Frontend hosting", "Preview deployments", "Self-hosting with Coolify"],
    },
  },
];

const newWorkflows = [
  {
    slug: "document-summarization",
    title: "Document Summarization",
    description:
      "Summarize long documents automatically: ingest PDFs, chunk content, generate concise summaries and store them for search.",
    category: "AI & Content",
    tags: ["summarization", "documents", "ai", "automation"],
    details: {
      difficulty: "Advanced",
      duration: "About 2–3 hours setup",
      tools: ["OpenAI API", "Supabase", "n8n", "Pinecone Vector API"],
      steps: ["Ingest PDFs and documents", "Extract and chunk text", "Generate summaries with AI", "Store summaries and embeddings", "Expose a search endpoint"],
      useCase: "Research teams, legal review and knowledge management",
    },
  },
  {
    slug: "ai-customer-feedback-analysis",
    title: "AI Customer Feedback Analysis",
    description:
      "Analyze customer feedback at scale: classify sentiment, extract themes and route insights to the right teams automatically.",
    category: "Support & AI",
    tags: ["feedback", "sentiment", "ai", "analytics"],
    details: {
      difficulty: "Advanced",
      duration: "About 2–3 hours setup",
      tools: ["OpenAI API", "Supabase", "PostHog Analytics API", "n8n"],
      steps: ["Collect feedback from multiple sources", "Classify sentiment and topics", "Extract actionable themes", "Store insights in Supabase", "Send weekly summaries"],
      useCase: "Product and support teams prioritizing improvements",
    },
  },
  {
    slug: "automated-code-review",
    title: "Automated Code Review",
    description:
      "Automate pull-request reviews: summarize diffs, flag risks and post structured comments with AI assistance.",
    category: "Engineering",
    tags: ["code-review", "ai", "github", "devops"],
    details: {
      difficulty: "Expert",
      duration: "About 3–4 hours setup",
      tools: ["OpenAI API", "GitHub Alternatives", "n8n", "Slack"],
      steps: ["Receive pull-request webhooks", "Fetch and summarize diffs", "Flag risky changes with AI", "Post review comments", "Notify the team"],
      useCase: "Engineering teams that want faster, consistent reviews",
    },
  },
  {
    slug: "lead-scraping-enrichment",
    title: "Lead Scraping & Enrichment",
    description:
      "Build a lead pipeline: collect prospects from public sources, enrich company data and score leads for outreach.",
    category: "Sales & CRM",
    tags: ["leads", "scraping", "enrichment", "sales"],
    details: {
      difficulty: "Advanced",
      duration: "About 3 hours setup",
      tools: ["n8n", "OpenAI API", "Supabase", "Resend Email API"],
      steps: ["Collect prospect data", "Normalize and deduplicate leads", "Enrich company information", "Score leads with AI", "Export to CRM"],
      useCase: "Sales teams building targeted outbound pipelines",
    },
  },
  {
    slug: "support-ticket-triage",
    title: "Support Ticket Triage",
    description:
      "Triage support tickets automatically: classify intent, set priority and route each ticket to the right queue.",
    category: "Support & AI",
    tags: ["support", "triage", "ai", "automation"],
    details: {
      difficulty: "Advanced",
      duration: "About 2 hours setup",
      tools: ["OpenAI API", "Zendesk Alternatives", "n8n", "Slack"],
      steps: ["Receive incoming tickets", "Classify intent and urgency", "Assign priority and tags", "Route to the right queue", "Escalate critical issues"],
      useCase: "Support teams handling high ticket volumes",
    },
  },
  {
    slug: "content-repurposing",
    title: "Content Repurposing",
    description:
      "Repurpose long-form content into social posts, newsletters and summaries while keeping brand voice consistent.",
    category: "Content & SEO",
    tags: ["content", "repurposing", "social-media", "ai"],
    details: {
      difficulty: "Advanced",
      duration: "About 2 hours setup",
      tools: ["OpenAI API", "Notion API", "Buffer", "n8n"],
      steps: ["Ingest long-form content", "Generate channel-specific variants", "Apply brand voice guidelines", "Schedule posts", "Track performance"],
      useCase: "Content teams maximizing reach from each asset",
    },
  },
  {
    slug: "social-listening",
    title: "Social Listening",
    description:
      "Monitor brand mentions and trends across channels: collect posts, analyze sentiment and alert the team to spikes.",
    category: "Marketing & Analytics",
    tags: ["social-media", "listening", "sentiment", "monitoring"],
    details: {
      difficulty: "Advanced",
      duration: "About 3 hours setup",
      tools: ["n8n", "OpenAI API", "Supabase", "Slack"],
      steps: ["Collect mentions from channels", "Detect language and sentiment", "Cluster emerging topics", "Store trends in Supabase", "Alert on spikes"],
      useCase: "Brand and marketing teams monitoring reputation",
    },
  },
  {
    slug: "price-monitoring",
    title: "Price Monitoring",
    description:
      "Track competitor prices automatically: scrape product pages, detect changes and trigger alerts or repricing rules.",
    category: "E-commerce",
    tags: ["pricing", "monitoring", "ecommerce", "automation"],
    details: {
      difficulty: "Advanced",
      duration: "About 3 hours setup",
      tools: ["n8n", "Supabase", "OpenAI API", "Resend Email API"],
      steps: ["Define competitor product URLs", "Scrape prices on a schedule", "Detect and store changes", "Apply alert thresholds", "Notify the pricing team"],
      useCase: "E-commerce teams keeping prices competitive",
    },
  },
  {
    slug: "competitor-analysis",
    title: "Competitor Analysis",
    description:
      "Automate competitor research: collect updates, summarize changes and generate weekly competitive intelligence briefs.",
    category: "Marketing & Analytics",
    tags: ["competitors", "research", "ai", "automation"],
    details: {
      difficulty: "Advanced",
      duration: "About 3 hours setup",
      tools: ["OpenAI API", "n8n", "Supabase", "Resend Email API"],
      steps: ["Track competitor sources", "Collect new content and updates", "Summarize changes with AI", "Store insights over time", "Send weekly briefs"],
      useCase: "Product marketing and strategy teams",
    },
  },
  {
    slug: "onboarding-email-sequence",
    title: "Onboarding Email Sequence",
    description:
      "Run behavior-based onboarding emails: trigger sequences from user events and personalize content automatically.",
    category: "Marketing & CRM",
    tags: ["onboarding", "email", "automation", "lifecycle"],
    details: {
      difficulty: "Advanced",
      duration: "About 2 hours setup",
      tools: ["Resend Email API", "Supabase", "n8n", "OpenAI API"],
      steps: ["Capture signup events", "Segment users by behavior", "Trigger email sequences", "Personalize content with AI", "Track activation metrics"],
      useCase: "SaaS teams improving activation and retention",
    },
  },
  {
    slug: "churn-prediction",
    title: "Churn Prediction",
    description:
      "Predict customer churn from usage signals: score accounts, flag at-risk customers and trigger retention playbooks.",
    category: "Analytics & CRM",
    tags: ["churn", "prediction", "retention", "analytics"],
    details: {
      difficulty: "Expert",
      duration: "About 4 hours setup",
      tools: ["OpenAI API", "Supabase", "PostHog Analytics API", "n8n"],
      steps: ["Collect usage and billing signals", "Build churn features", "Score accounts with a model", "Flag at-risk customers", "Trigger retention playbooks"],
      useCase: "SaaS teams reducing churn proactively",
    },
  },
  {
    slug: "meeting-notes-automation",
    title: "Meeting Notes Automation",
    description:
      "Automate meeting notes: transcribe calls, extract action items and sync summaries to your workspace.",
    category: "Productivity & AI",
    tags: ["meetings", "transcription", "notes", "ai"],
    details: {
      difficulty: "Advanced",
      duration: "About 2–3 hours setup",
      tools: ["Deepgram Speech API", "OpenAI API", "Notion API", "n8n"],
      steps: ["Join or upload meeting audio", "Transcribe with Deepgram", "Summarize and extract actions", "Create notes in Notion", "Notify participants"],
      useCase: "Teams that want reliable meeting documentation",
    },
  },
];

function append(file, records) {
  const filePath = path.join(dataDir, file);
  const existing = JSON.parse(readFileSync(filePath, "utf8"));
  const existingSlugs = new Set(existing.map((r) => r.slug));
  const additions = records.filter((r) => !existingSlugs.has(r.slug));
  const merged = [...existing, ...additions];
  writeFileSync(filePath, JSON.stringify(merged, null, 2) + "\n");
  console.log(`${file}: +${additions.length} (total ${merged.length})`);
}

append("apis.json", newApis);
append("alternatives.json", newAlternatives);
append("workflows.json", newWorkflows);
