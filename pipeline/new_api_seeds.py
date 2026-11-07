"""Curated catalogue of real APIs that are not yet in ``src/data/apis.json``.

The unattended daemon must ADD new API products (and therefore new API pages),
not merely regenerate kits for existing records. Every seed below uses a real
official endpoint and documentation URL. The daemon still performs the live
docs/endpoint check before it generates a kit, so a stale seed is rejected
automatically and the next candidate is used.

The list is intentionally longer than one batch (3 APIs) so the 72-hour daemon
has deterministic replacement candidates even if a domain is temporarily down.
"""

from __future__ import annotations

from typing import Any

NEW_API_SEEDS: list[dict[str, Any]] = [
    {
        "slug": "figma-rest-api",
        "title": "Figma REST API",
        "description": (
            "The Figma REST API exposes files, components, styles and comments "
            "so teams can automate design handoff, asset export and design-system audits."
        ),
        "category": "Design & Collaboration",
        "tags": ["design", "figma", "assets", "design-system"],
        "details": {
            "provider": "Figma",
            "pricing": "Free; paid plans from $12/editor/month",
            "features": [
                "Read file and node trees",
                "Export frames and image assets",
                "Create and resolve comments",
                "Inspect components and styles",
            ],
            "useCase": "Automate design-to-code handoff, asset export and design-system consistency checks.",
            "website": "https://www.figma.com",
            "endpoint": "https://api.figma.com/v1/files/{file_key}",
            "authentication": "OAuth2 or personal access token (Bearer)",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "Tier-based; see the Figma developer documentation",
            "docsUrl": "https://www.figma.com/developers/api",
        },
    },
    {
        "slug": "miro-rest-api",
        "title": "Miro REST API",
        "description": (
            "The Miro REST API manages boards, items, sticky notes and connectors, "
            "enabling automated workshops, visual planning and collaboration sync."
        ),
        "category": "Collaboration & Productivity",
        "tags": ["collaboration", "whiteboard", "miro", "workshops"],
        "details": {
            "provider": "Miro",
            "pricing": "Free; paid plans from $8/member/month",
            "features": [
                "Create and read boards",
                "Manage items and sticky notes",
                "Create connectors between items",
                "Manage board members and sharing",
            ],
            "useCase": "Automate workshop boards, retrospective templates and visual planning sync.",
            "website": "https://miro.com",
            "endpoint": "https://api.miro.com/v2/boards",
            "authentication": "OAuth2 access token (Bearer)",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "100 requests per minute per user by default",
            "docsUrl": "https://developers.miro.com/reference/api-reference",
        },
    },
    {
        "slug": "calendly-api",
        "title": "Calendly API",
        "description": (
            "The Calendly API exposes scheduled events, invitees, availability and "
            "webhooks so teams can automate meeting workflows and CRM synchronization."
        ),
        "category": "Scheduling & Productivity",
        "tags": ["scheduling", "meetings", "calendly", "webhooks"],
        "details": {
            "provider": "Calendly",
            "pricing": "Free; paid plans from $10/seat/month",
            "features": [
                "List scheduled events",
                "Read invitee details",
                "Query availability",
                "Subscribe to webhooks",
            ],
            "useCase": "Automate meeting follow-ups, CRM synchronization and reminder workflows.",
            "website": "https://calendly.com",
            "endpoint": "https://api.calendly.com/scheduled_events",
            "authentication": "OAuth2 or personal access token (Bearer)",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "Tier-based; see the Calendly developer documentation",
            "docsUrl": "https://developer.calendly.com/api-docs",
        },
    },
    {
        "slug": "intercom-api",
        "title": "Intercom API",
        "description": (
            "The Intercom API manages contacts, conversations, tags and admins so "
            "support teams can automate inbox workflows and CRM synchronization."
        ),
        "category": "Customer Support",
        "tags": ["support", "messaging", "intercom", "crm"],
        "details": {
            "provider": "Intercom",
            "pricing": "Paid plans from $39/seat/month",
            "features": [
                "Create and update contacts",
                "Read and reply to conversations",
                "Apply tags and segments",
                "Manage admins and teams",
            ],
            "useCase": "Automate support triage, customer context sync and follow-up workflows.",
            "website": "https://www.intercom.com",
            "endpoint": "https://api.intercom.io/contacts",
            "authentication": "OAuth2 access token or API token (Bearer)",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "Tier-based; see the Intercom API reference",
            "docsUrl": "https://developers.intercom.com/intercom-api-reference",
        },
    },
    {
        "slug": "webflow-api",
        "title": "Webflow API",
        "description": (
            "The Webflow API manages sites, collections, CMS items and publishing, "
            "so content teams can automate programmatic SEO and CMS workflows."
        ),
        "category": "Content & SEO",
        "tags": ["cms", "seo", "webflow", "publishing"],
        "details": {
            "provider": "Webflow",
            "pricing": "Free; paid site plans from $14/site/month",
            "features": [
                "List and read sites",
                "Manage CMS collections",
                "Create and update items",
                "Publish site changes",
            ],
            "useCase": "Automate programmatic SEO pages, CMS publishing and content synchronization.",
            "website": "https://webflow.com",
            "endpoint": "https://api.webflow.com/v2/sites",
            "authentication": "OAuth2 or site API token (Bearer)",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "60 requests per minute by default",
            "docsUrl": "https://developers.webflow.com/data/reference",
        },
    },
    {
        "slug": "klaviyo-api",
        "title": "Klaviyo API",
        "description": (
            "The Klaviyo API manages profiles, lists, events and campaigns for "
            "e-commerce marketing automation and customer segmentation."
        ),
        "category": "Marketing & Analytics",
        "tags": ["email", "marketing", "klaviyo", "ecommerce"],
        "details": {
            "provider": "Klaviyo",
            "pricing": "Free up to 250 contacts; paid plans from $20/month",
            "features": [
                "Create and update profiles",
                "Manage lists and segments",
                "Track custom events",
                "Read campaign performance",
            ],
            "useCase": "Automate welcome flows, abandoned-cart journeys and customer segmentation.",
            "website": "https://www.klaviyo.com",
            "endpoint": "https://a.klaviyo.com/api/profiles",
            "authentication": "Private API key (Bearer)",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "Tier-based; see the Klaviyo API overview",
            "docsUrl": "https://developers.klaviyo.com/en/reference/api_overview",
        },
    },
    {
        "slug": "trello-api",
        "title": "Trello API",
        "description": (
            "The Trello REST API manages boards, lists, cards and webhooks so teams "
            "can automate project workflows and synchronize task boards."
        ),
        "category": "Productivity",
        "tags": ["project-management", "trello", "tasks", "automation"],
        "details": {
            "provider": "Trello",
            "pricing": "Free; paid plans from $5/user/month",
            "features": [
                "Create and read boards",
                "Manage lists and cards",
                "Add comments and checklists",
                "Subscribe to webhooks",
            ],
            "useCase": "Automate project boards, task routing and cross-tool synchronization.",
            "website": "https://trello.com",
            "endpoint": "https://api.trello.com/1/boards",
            "authentication": "API key and token",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "300 requests per 10 seconds per API key",
            "docsUrl": "https://developer.atlassian.com/cloud/trello/rest/",
        },
    },
    {
        "slug": "jira-rest-api",
        "title": "Jira REST API",
        "description": (
            "The Jira REST API manages issues, projects, transitions and webhooks, "
            "enabling automated engineering workflows and release synchronization."
        ),
        "category": "Developer Tools",
        "tags": ["jira", "issues", "project-management", "devops"],
        "details": {
            "provider": "Atlassian",
            "pricing": "Free up to 10 users; paid plans from $7.75/user/month",
            "features": [
                "Create and update issues",
                "Read projects and boards",
                "Transition issue status",
                "Subscribe to webhooks",
            ],
            "useCase": "Automate backlog triage, release notes and cross-team issue synchronization.",
            "website": "https://www.atlassian.com/software/jira",
            "endpoint": "https://{your-domain}.atlassian.net/rest/api/3/issue",
            "authentication": "API token with Basic auth or OAuth2",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "Tier-based; see the Jira REST API documentation",
            "docsUrl": "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/",
        },
    },
    {
        "slug": "convertkit-api",
        "title": "ConvertKit API",
        "description": (
            "The ConvertKit API manages subscribers, forms, tags and sequences for "
            "newsletter automation and creator marketing workflows."
        ),
        "category": "Marketing & Analytics",
        "tags": ["newsletter", "email", "convertkit", "creators"],
        "details": {
            "provider": "ConvertKit",
            "pricing": "Free up to 1,000 subscribers; paid plans from $15/month",
            "features": [
                "Create and update subscribers",
                "Manage forms and landing pages",
                "Apply tags and segments",
                "Add subscribers to sequences",
            ],
            "useCase": "Automate newsletter signups, tag-based segmentation and email sequences.",
            "website": "https://convertkit.com",
            "endpoint": "https://api.convertkit.com/v3/subscribers",
            "authentication": "API key and secret",
            "apiKeyRequired": True,
            "sdkLanguages": ["Python", "JavaScript", "cURL"],
            "rateLimit": "120 requests per minute",
            "docsUrl": "https://developers.convertkit.com/",
        },
    },
]