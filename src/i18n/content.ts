/**
 * Per-locale content overrides for the pSEO data.
 *
 * The English base data lives in src/data/*.json. This module provides
 * optional overrides (title, description, category and tags) per locale.
 * Missing translations automatically fall back to English.
 *
 * Add more locales/records by extending the maps below.
 */
import type {
  AlternativeEntry,
  ApiEntry,
  WorkflowEntry,
} from "../lib/content";

type ApiOverride = Partial<
  Pick<ApiEntry, "title" | "description" | "category" | "tags">
>;
type AlternativeOverride = Partial<
  Pick<AlternativeEntry, "title" | "description" | "category" | "tags">
>;
type WorkflowOverride = Partial<
  Pick<WorkflowEntry, "title" | "description" | "category" | "tags">
>;

export const apiOverrides: Record<string, Record<string, ApiOverride>> = {
  de: {
    "openai-whisper-api": {
      title: "OpenAI Whisper API",
      description:
        "Die Whisper API von OpenAI transkribiert Audio mit hoher Genauigkeit in Text – in über 50 Sprachen, ideal für Podcasts, Meetings und Voice-Apps.",
      category: "KI & Speech",
      tags: ["speech-to-text", "transkription", "ki", "audio"],
    },
    "stripe-payments-api": {
      title: "Stripe Payments API",
      description:
        "Die Stripe Payments API ist die führende Schnittstelle für Online-Zahlungen, Abonnements und Finanzinfrastruktur mit exzellenter Developer Experience.",
      category: "Finanzen",
      tags: ["payments", "fintech", "abonnements", "checkout"],
    },
    "supabase-database-api": {
      title: "Supabase Database API",
      description:
        "Supabase bietet eine automatisch generierte REST- und GraphQL-API auf Basis von PostgreSQL – inklusive Auth, Storage und Realtime-Subscriptions.",
      category: "Backend",
      tags: ["postgresql", "backend", "open-source", "auth"],
    },
    "anthropic-claude-api": {
      title: "Anthropic Claude API",
      description:
        "Die Claude API von Anthropic bietet starke Reasoning-Fähigkeiten, ein großes Kontextfenster und sichere Agenten-Workflows für anspruchsvolle Anwendungen.",
      category: "KI & LLM",
      tags: ["llm", "reasoning", "agents", "sicherheit"],
    },
    "google-gemini-api": {
      title: "Google Gemini API",
      description:
        "Die Google Gemini API verbindet Text, Bild und Audio in einem multimodalen Modell – ideal für Vision-, Analyse- und Assistenz-Anwendungen.",
      category: "KI & Multimodal",
      tags: ["llm", "multimodal", "vision", "google"],
    },
    "resend-email-api": {
      title: "Resend E-Mail API",
      description:
        "Die Resend API vereinfacht transaktionale E-Mails mit sauberer Dokumentation, React-Email-Templates und zuverlässiger Zustellung.",
      category: "Kommunikation",
      tags: ["email", "transaktional", "developer-tools"],
    },
    "clerk-authentication-api": {
      title: "Clerk Authentication API",
      description:
        "Die Clerk API liefert fertige Authentifizierung mit SSO, Multi-Faktor-Login und Nutzerverwaltung – schnell integriert in moderne Web-Apps.",
      category: "Auth & Identity",
      tags: ["auth", "sso", "user-management", "security"],
    },
    "cloudflare-workers-api": {
      title: "Cloudflare Workers API",
      description:
        "Die Cloudflare Workers API führt Code direkt am Edge aus – für schnelle, skalierbare Serverless-Funktionen ohne eigenen Server.",
      category: "Edge Computing",
      tags: ["edge", "serverless", "cdn", "performance"],
    },
    "mapbox-maps-api": {
      title: "Mapbox Maps API",
      description:
        "Die Mapbox Maps API bietet interaktive Karten, Geocoding und Routing für Web- und Mobile-Anwendungen mit hoher Performance.",
      category: "Geodaten",
      tags: ["maps", "geolocation", "routing", "visualisierung"],
    },
    "twilio-messaging-api": {
      title: "Twilio Messaging API",
      description:
        "Die Twilio Messaging API versendet SMS, WhatsApp- und RCS-Nachrichten zuverlässig – ideal für Benachrichtigungen und Zwei-Faktor-Authentifizierung.",
      category: "Kommunikation",
      tags: ["sms", "whatsapp", "messaging", "notifications"],
    },
  },
};

export const alternativeOverrides: Record<
  string,
  Record<string, AlternativeOverride>
> = {
  de: {
    "notion-alternatives": {
      title: "Notion Alternativen",
      description:
        "Die besten Notion-Alternativen für Wissensmanagement, Projektplanung und kollaborative Dokumente – von Open Source bis Enterprise.",
      category: "Produktivität",
      tags: ["wissensmanagement", "notizen", "kollaboration", "produktivität"],
    },
    "zapier-alternatives": {
      title: "Zapier Alternativen",
      description:
        "Zapier-Alternativen für Automatisierung und Integrationen – günstiger, datenschutzfreundlicher oder mit mehr Kontrolle über deine Workflows.",
      category: "Automatisierung",
      tags: ["automatisierung", "no-code", "integrationen", "workflows"],
    },
    "figma-alternatives": {
      title: "Figma Alternativen",
      description:
        "Figma-Alternativen für UI-Design und Prototyping – inklusive Open-Source- und datenschutzfreundlicher Optionen.",
      category: "Design",
      tags: ["design", "ui-ux", "prototyping", "open-source"],
    },
    "slack-alternatives": {
      title: "Slack Alternativen",
      description:
        "Slack-Alternativen für Team-Chat und Kommunikation – datenschutzfreundlicher, günstiger oder mit Self-Hosting-Option für mehr Kontrolle.",
      category: "Kommunikation",
      tags: ["team-chat", "kommunikation", "kollaboration"],
    },
    "airtable-alternatives": {
      title: "Airtable Alternativen",
      description:
        "Airtable-Alternativen für No-Code-Datenbanken und Tabellen – mit Open-Source-Optionen, Self-Hosting und fairer Preisgestaltung.",
      category: "Datenbanken",
      tags: ["no-code", "datenbank", "tabellen", "automatisierung"],
    },
    "mailchimp-alternatives": {
      title: "Mailchimp Alternativen",
      description:
        "Mailchimp-Alternativen für Newsletter und E-Mail-Marketing – günstiger, DSGVO-freundlicher und ohne komplexe Preisstufen.",
      category: "Marketing",
      tags: ["email-marketing", "newsletter", "crm"],
    },
    "trello-alternatives": {
      title: "Trello Alternativen",
      description:
        "Trello-Alternativen für Kanban-Boards und Projektmanagement – mit mehr Automatisierung, Open-Source-Optionen und faireren Preisen.",
      category: "Projektmanagement",
      tags: ["kanban", "projektmanagement", "aufgaben"],
    },
    "google-analytics-alternatives": {
      title: "Google Analytics Alternativen",
      description:
        "Google-Analytics-Alternativen für datenschutzfreundliches Web-Tracking – cookielos, DSGVO-konform und ohne Datenexport in die USA.",
      category: "Analytics",
      tags: ["analytics", "datenschutz", "tracking"],
    },
  },
};

export const workflowOverrides: Record<
  string,
  Record<string, WorkflowOverride>
> = {
  de: {
    "content-automation": {
      title: "Content-Automation mit KI",
      description:
        "Ein vollständiger Workflow, um mit KI und APIs Content-Ideen zu recherchieren, zu schreiben und automatisiert zu veröffentlichen.",
      category: "Content & SEO",
      tags: ["ki", "content", "seo", "automatisierung"],
    },
    "lead-qualification": {
      title: "Lead-Qualifizierung automatisieren",
      description:
        "Eingehende Leads automatisch bewerten, anreichern und an das richtige Team weiterleiten – ohne manuelle Sortierung.",
      category: "Sales & CRM",
      tags: ["sales", "crm", "ki", "automatisierung"],
    },
    "programmatic-seo-pipeline": {
      title: "Programmatic-SEO-Pipeline",
      description:
        "Der komplette Workflow für tausende SEO-Seiten: Datenquellen, Template-Engine, Build-Prozess und Monitoring.",
      category: "SEO & Skalierung",
      tags: ["seo", "astro", "skalierung", "deployment"],
    },
    "newsletter-automation": {
      title: "Newsletter-Automation",
      description:
        "Ein Workflow für automatisierte Newsletter: Anmeldungen erfassen, Inhalte aufbereiten und E-Mails zuverlässig über die Resend API versenden.",
      category: "Marketing & Content",
      tags: ["newsletter", "email", "automatisierung", "content"],
    },
    "social-media-scheduling": {
      title: "Social-Media-Scheduling",
      description:
        "Social-Media-Scheduling automatisieren: Inhalte per KI erstellen, redaktionell freigeben und zeitgesteuert über mehrere Kanäle veröffentlichen.",
      category: "Marketing & Content",
      tags: ["social-media", "scheduling", "automatisierung", "content"],
    },
    "customer-support-chatbot": {
      title: "Customer-Support-Chatbot",
      description:
        "Ein KI-Chatbot für den Kundensupport: Anfragen verstehen, aus einer Wissensdatenbank beantworten und bei Bedarf an Menschen übergeben.",
      category: "Support & KI",
      tags: ["chatbot", "support", "ki", "automatisierung"],
    },
    "data-enrichment-pipeline": {
      title: "Daten-Anreicherungs-Pipeline",
      description:
        "Eine Pipeline zur Datenanreicherung: Rohdaten importieren, per API ergänzen, mit KI normalisieren und strukturiert in Supabase speichern.",
      category: "Daten & Automatisierung",
      tags: ["daten", "enrichment", "api", "automatisierung"],
    },
    "seo-monitoring-dashboard": {
      title: "SEO-Monitoring-Dashboard",
      description:
        "Ein Dashboard für SEO-Monitoring: Rankings, Indexierung und Core Web Vitals automatisch erfassen und übersichtlich visualisieren.",
      category: "SEO & Analytics",
      tags: ["seo", "monitoring", "analytics", "dashboard"],
    },
  },
};

export function localizeApi(api: ApiEntry, lang: string): ApiEntry {
  const override = apiOverrides[lang]?.[api.slug];
  return override ? { ...api, ...override } : api;
}

export function localizeAlternative(
  entry: AlternativeEntry,
  lang: string
): AlternativeEntry {
  const override = alternativeOverrides[lang]?.[entry.slug];
  return override ? { ...entry, ...override } : entry;
}

export function localizeWorkflow(
  workflow: WorkflowEntry,
  lang: string
): WorkflowEntry {
  const override = workflowOverrides[lang]?.[workflow.slug];
  return override ? { ...workflow, ...override } : workflow;
}
