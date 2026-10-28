export interface ApiEntry {
  slug: string;
  title: string;
  category: string;
  description: string;
  longDescription: string;
  features: string[];
  pricing: string;
  website: string;
  rating: number;
  tags: string[];
}

export const apis: ApiEntry[] = [
  {
    slug: 'openai',
    title: 'OpenAI API',
    category: 'KI & LLM',
    description:
      'Die OpenAI API liefert Zugriff auf GPT-Modelle für Text, Code, Vision und Sprachverarbeitung – der De-facto-Standard für KI-gestützte Anwendungen.',
    longDescription:
      'Die OpenAI API ist eine der meistgenutzten Schnittstellen für generative KI. Sie bietet Zugriff auf die GPT-Familie, Embeddings, Bildgenerierung und Speech-to-Text. Dank umfangreicher SDKs für JavaScript, Python und viele weitere Sprachen lässt sich die API schnell in bestehende Anwendungen integrieren. Rate-Limits, Token-Preise und Modellauswahl machen die Plattform flexibel für Prototypen bis hin zu produktiven Workloads.',
    features: [
      'GPT-Modelle für Text, Code und Vision',
      'Embeddings für semantische Suche',
      'Function Calling & strukturierte Ausgaben',
      'Umfangreiche SDKs und Dokumentation',
    ],
    pricing: 'Pay-as-you-go pro Token',
    website: 'https://platform.openai.com',
    rating: 4.8,
    tags: ['LLM', 'Text', 'Embeddings', 'Vision'],
  },
  {
    slug: 'anthropic',
    title: 'Anthropic Claude API',
    category: 'KI & LLM',
    description:
      'Die Claude API von Anthropic überzeugt mit langem Kontextfenster, starker Reasoning-Leistung und einem Fokus auf sichere KI-Systeme.',
    longDescription:
      'Anthropic bietet mit der Claude API leistungsfähige Sprachmodelle, die besonders für lange Dokumente, komplexe Analyseaufgaben und agentische Workflows geeignet sind. Das große Kontextfenster erlaubt die Verarbeitung umfangreicher Codebasen oder Verträge in einem einzigen Aufruf. Die API ist für ihre Zuverlässigkeit und ihr Sicherheitsdesign bekannt.',
    features: [
      'Sehr großes Kontextfenster',
      'Starke Reasoning- und Coding-Fähigkeiten',
      'Tool Use & Agenten-Workflows',
      'Fokus auf KI-Sicherheit',
    ],
    pricing: 'Pay-as-you-go pro Token',
    website: 'https://www.anthropic.com',
    rating: 4.7,
    tags: ['LLM', 'Reasoning', 'Agents', 'Sicherheit'],
  },
  {
    slug: 'stripe',
    title: 'Stripe API',
    category: 'Finanzen',
    description:
      'Die Stripe API ist die führende Plattform für Online-Zahlungen, Abonnements und Finanzinfrastruktur mit exzellenter Developer Experience.',
    longDescription:
      'Stripe stellt eine umfassende API für Zahlungsabwicklung, Abonnements, Rechnungsstellung und Auszahlungen bereit. Die Dokumentation gilt als Goldstandard, und mit Stripe Elements sowie Checkout lässt sich ein professioneller Bezahlvorgang in wenigen Stunden integrieren. Webhooks und ein mächtiges Dashboard runden das Angebot ab.',
    features: [
      'Zahlungen & Abonnements',
      'Stripe Checkout & Elements',
      'Webhooks und Event-Streaming',
      'Hervorragende Dokumentation',
    ],
    pricing: 'Transaktionsbasiert (ca. 1,5 % + 0,25 €)',
    website: 'https://stripe.com',
    rating: 4.9,
    tags: ['Payments', 'Fintech', 'Abonnements'],
  },
  {
    slug: 'supabase',
    title: 'Supabase API',
    category: 'Backend',
    description:
      'Supabase ist das Open-Source-Backend auf Basis von PostgreSQL und bietet Auth, Datenbank, Storage und Realtime in einer einzigen Plattform.',
    longDescription:
      'Supabase kombiniert eine vollwertige PostgreSQL-Datenbank mit Authentifizierung, Dateispeicher, Edge Functions und Realtime-Subscriptions. Die automatisch generierte REST- und GraphQL-API macht aus jeder Tabelle sofort eine Schnittstelle. Als Open-Source-Alternative zu Firebase ist Supabase besonders bei Startups und Indie-Developern beliebt.',
    features: [
      'PostgreSQL mit automatischer REST-API',
      'Authentifizierung & Row Level Security',
      'Storage und Edge Functions',
      'Realtime-Subscriptions',
    ],
    pricing: 'Kostenloser Tarif, danach ab 25 $/Monat',
    website: 'https://supabase.com',
    rating: 4.6,
    tags: ['Backend', 'PostgreSQL', 'Open Source', 'Auth'],
  },
  {
    slug: 'resend',
    title: 'Resend API',
    category: 'Kommunikation',
    description:
      'Resend ist eine moderne E-Mail-API für Entwickler mit sauberer Dokumentation, React-Email-Support und zuverlässiger Zustellung.',
    longDescription:
      'Resend vereinfacht den Versand transaktionaler E-Mails erheblich. Die API ist minimalistisch, bietet SDKs für alle gängigen Sprachen und integriert sich nahtlos in React Email für typsichere Templates. Zustellbarkeit, Logging und Webhooks sind von Anfang an dabei.',
    features: [
      'Transaktionale E-Mails',
      'React Email Templates',
      'Zustellbarkeits-Tracking',
      'Einfache SDK-Integration',
    ],
    pricing: 'Kostenlos bis 3.000 E-Mails/Monat',
    website: 'https://resend.com',
    rating: 4.5,
    tags: ['E-Mail', 'Developer Tools', 'Transaktional'],
  },
];
